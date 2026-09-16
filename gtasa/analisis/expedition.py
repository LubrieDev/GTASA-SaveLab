#!/usr/bin/env python3
"""
Expedicion: N partidas, N-1 diferenciales, una sola pasada.

Se guarda una ranura despues de cada accion. Este script las compara y separa lo que
cambio *solo* en un diferencial (candidato a ser esa accion) de lo que cambia en casi
todos (ruido: reloj, posicion, temporizadores).

Por defecto compara todas contra la primera (ESTRELLA). Con `--cadena`, por parejas
consecutivas.

Sin linea base explicita, el ruido se estima por frecuencia: un byte que se mueve en
todos los diferenciales no distingue nada. No es tan bueno como dos guardados seguidos
sin hacer nada, y el informe lo dice donde toca.

    python expedition.py base.b:base sf2.b:camisa sf3.b:vaqueros ...
    python expedition.py --cadena ...      si cada partida salio de la anterior
"""

import struct
import sys

BLOCK_SIG = b"BLOCK"
NOMBRES_BLOQUE = {
    0: "SimpleVars", 1: "Scripts", 2: "Pools", 3: "Garages",
    15: "PlayerInfo", 16: "Stats",
}
HUECO = 8          # bytes iguales que se toleran dentro de una misma region
STATS_BLOQUE = 16
STATS_FLOATS = 82  # float[0..81] ocupan los primeros 328 bytes de datos


def bloques(data):
    offs, i = [], 0
    while (i := data.find(BLOCK_SIG, i)) != -1:
        offs.append(i)
        i += 5
    return offs


def carga(spec):
    """`ruta.b:etiqueta` -> (etiqueta, bytes). La etiqueta es opcional."""
    ruta, _, etiqueta = spec.partition(":")
    with open(ruta, "rb") as f:
        data = f.read()
    guardado = struct.unpack_from("<I", data, len(data) - 4)[0]
    if guardado != sum(data[:-4]) & 0xFFFFFFFF:
        print(f"  AVISO: checksum malo en {ruta}", file=sys.stderr)
    return etiqueta or ruta, data


def situa(offs, pos):
    """Devuelve (indice de bloque, offset dentro del bloque) para un offset global."""
    idx = -1
    for i, o in enumerate(offs):
        if o <= pos:
            idx = i
        else:
            break
    if idx < 0:
        return None, pos
    # +5 de la firma BLOCK, +4 del tamano del bloque: los datos empiezan en +9
    return idx, pos - offs[idx] - 9


def etiqueta_bloque(idx):
    nombre = NOMBRES_BLOQUE.get(idx)
    return f"bloque {idx} ({nombre})" if nombre else f"bloque {idx}"


def regiones(posiciones, hueco=HUECO):
    """Agrupa offsets sueltos en tramos contiguos, tolerando huecos pequenos."""
    if not posiciones:
        return []
    ordenadas = sorted(posiciones)
    out = [[ordenadas[0], ordenadas[0]]]
    for p in ordenadas[1:]:
        if p - out[-1][1] <= hueco:
            out[-1][1] = p
        else:
            out.append([p, p])
    return [(a, b + 1) for a, b in out]


def lecturas(antes, ahora, ini, fin):
    """Interpretaciones plausibles de un tramo corto. Nada de inventar tipos largos."""
    n = fin - ini
    a, b = antes[ini:fin], ahora[ini:fin]
    if n > 8:
        return f"{n} bytes"
    hex_a, hex_b = a.hex(" "), b.hex(" ")
    fuera = [f"{hex_a} -> {hex_b}"]
    if n == 1:
        fuera.append(f"u8 {a[0]} -> {b[0]}")
    if n == 4:
        fuera.append(f"i32 {struct.unpack('<i', a)[0]} -> {struct.unpack('<i', b)[0]}")
        fa, fb = struct.unpack("<f", a)[0], struct.unpack("<f", b)[0]
        if all(abs(x) < 1e9 for x in (fa, fb)):
            fuera.append(f"f32 {fa:.2f} -> {fb:.2f}")
    if n == 2:
        fuera.append(f"u16 {struct.unpack('<H', a)[0]} -> {struct.unpack('<H', b)[0]}")
    return "   ".join(fuera)


def nombre_stat(rel):
    """Si el tramo cae en el bloque Stats, di que indice de stat es."""
    if rel < 0:
        return ""
    if rel < STATS_FLOATS * 4:
        return f"  = float[{rel // 4}]" + ("" if rel % 4 == 0 else f"+{rel % 4}")
    r = rel - STATS_FLOATS * 4
    if r < (305 - STATS_FLOATS) * 4:
        return f"  = int[{STATS_FLOATS + r // 4}]" + ("" if r % 4 == 0 else f"+{r % 4}")
    return ""


def main():
    specs = [s for s in sys.argv[1:] if s != "--cadena"]
    estrella = "--cadena" not in sys.argv
    if len(specs) < 3:
        print(__doc__)
        return 1

    saves = [carga(s) for s in specs]
    tam = {len(d) for _, d in saves}
    if len(tam) != 1:
        print(f"ERROR: tamanos distintos {sorted(tam)}; el diferencial por offset no vale")
        return 2

    offs = bloques(saves[0][1])
    for etiqueta, d in saves[1:]:
        if bloques(d) != offs:
            print(f"ERROR: {etiqueta} tiene los bloques en otro sitio; no se puede comparar")
            return 2

    fin = len(saves[0][1]) - 4          # los 4 ultimos bytes son el checksum
    print(f"{len(saves)} partidas  {fin + 4} bytes  {len(offs)} bloques  "
          f"mismo reparto de bloques en todas\n")

    # --- los diferenciales ---------------------------------------------------
    # Dos formas de jugar una expedicion, y hay que saber cual fue:
    #
    #   CADENA:   cada partida sale de la anterior. Se comparan por parejas.
    #   ESTRELLA: se recarga la base antes de cada cosa, asi que todas son
    #             hermanas. Se comparan TODAS contra la base.
    #
    # La del 6 de agosto fue estrella, y salio mejor: en cadena, el diferencial
    # 2->3 mezcla "quitarse la camisa" con "ponerse los vaqueros"; contra la base
    # cada partida trae un solo cambio y nada mas.
    difs = []
    if estrella:
        e0, d0 = saves[0]
        for eb, b in saves[1:]:
            difs.append((f"{e0} -> {eb}", [i for i in range(fin) if d0[i] != b[i]], d0, b))
    else:
        for (ea, a), (eb, b) in zip(saves, saves[1:]):
            difs.append((f"{ea} -> {eb}", [i for i in range(fin) if a[i] != b[i]], a, b))

    frec = {}
    for _, cambia, _, _ in difs:
        for p in cambia:
            frec[p] = frec.get(p, 0) + 1

    n = len(difs)
    print("=" * 72)
    print("RESUMEN")
    print("=" * 72)
    for titulo, cambia, _, _ in difs:
        solos = [p for p in cambia if frec[p] == 1]
        print(f"  {titulo:34} {len(cambia):6} bytes cambian, "
              f"{len(solos):5} solo aqui  ({len(regiones(solos))} regiones)")

    reparto = {}
    for p, c in frec.items():
        reparto[c] = reparto.get(c, 0) + 1
    print(f"\n  Bytes que se mueven en... " +
          "  ".join(f"{c}/{n}: {reparto.get(c, 0)}" for c in range(1, n + 1)))
    print(f"  Los de {n}/{n} son ruido puro (reloj, posicion, temporizadores): "
          f"{reparto.get(n, 0)} bytes")

    # --- lo exclusivo de cada diferencial ------------------------------------
    for titulo, cambia, a, b in difs:
        solos = [p for p in cambia if frec[p] == 1]
        regs = regiones(solos)
        print("\n" + "=" * 72)
        print(f"{titulo}   ({len(regs)} regiones exclusivas)")
        print("=" * 72)
        if not regs:
            print("  nada exclusivo: todo lo que cambio aqui cambia tambien en otros")
            continue
        for ini, tope in regs:
            idx, rel = situa(offs, ini)
            extra = nombre_stat(rel) if idx == STATS_BLOQUE else ""
            print(f"  {etiqueta_bloque(idx):24} +{rel:<7} ({tope - ini:3} b)  "
                  f"{lecturas(a, b, ini, tope)}{extra}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

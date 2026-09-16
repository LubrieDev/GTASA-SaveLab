#!/usr/bin/env python3
"""
Identifica campos del save cruzando transcripciones de la pantalla de estadisticas.

    python harvest.py partidas/stats/STATSsf1.md partidas/stats/GTASAsf1.b
    python harvest.py A.md A.b  B.md B.b        # cruza dos parejas
    python harvest.py A.md A.b --nivel A        # solo lo inatacable

DE DONDE SALE ESTO
------------------
Cada linea de una transcripcion es un valor que el jugador LEYO EN PANTALLA. Buscar
ese valor dentro del save que le corresponde es el truco de la minigun con 487 balas,
pero aplicado a 150 valores de golpe y sin gastar un viaje al movil.

Con una sola pareja (.md + .b) salieron 106 campos. Ver PROJECT-MEMORY.md, bloque 16.

LOS DOS NIVELES DE CONFIANZA, QUE NO HAY QUE MEZCLAR
-----------------------------------------------------
NIVEL A  el valor aparece UNA sola vez en todo el fichero. Inatacable.

NIVEL B  aparece varias veces, pero solo UNA cae en ranura valida del bloque 16
         (float[0..81] o int[82..304], alineada a 4). Las otras caen en mitad de
         otros bloques o desalineadas, donde un stat no puede vivir. Es aplicar una
         estructura ya verificada, NO "elegir la que encaja".

         El nivel B SE ROMPE con valores pequenos: cuatro ranuras las reclaman dos
         anclas distintas con el mismo valor (ver COLISIONES en gtasa_editor.py).
         Por eso se marcan aparte y no se apuntan como confirmadas.

EL CRUCE DE DOS PAREJAS ES LO QUE MULTIPLICA
---------------------------------------------
Un ancla ambigua deja un CONJUNTO de posiciones candidatas. Con dos partidas cuyo
valor para ese stat es distinto, se cruzan los dos conjuntos:

    "Sobornos policiales"  partida 1 -> {A, B, C}
                           partida 2 -> {B, D}
                           interseccion -> {B}     resuelto

No es acumular anclas, es multiplicarlas: cada valor que haya cambiado entre las dos
partidas se convierte en un filtro independiente.

REGLA QUE NO SE SALTA
---------------------
Solo vale el ancla que deja UN candidato. Con dos no se sabe cual es, y en este
proyecto "es la unica que encaja" nunca ha confirmado nada.
"""

import argparse
import re
import struct
import sys
import unicodedata
from pathlib import Path

from ..editor import find_blocks

BLOQUE_STATS = 16
FLOATS_HASTA = 328          # float[0..81]
INTS_DESDE, INTS_HASTA = 328, 1220   # int[82..304]


# ----------------------------------------------------------------------
#  Parsear la transcripcion
# ----------------------------------------------------------------------

def parsea_linea(linea):
    """'- Balas disparadas: 88587' -> [('Balas disparadas', 88587, 'i')]

    Tipos: 'i' entero, 'f' float, '%' porcentaje (la escala del juego es valor/10,
    y la pantalla redondea, asi que se busca un rango).
    """
    m = re.match(r"^-\s*(.+?):\s*(.+?)\s*$", linea)
    if not m:
        return []
    et, v = m.group(1), m.group(2).replace(",", "")

    reglas = (
        (r"^(\d+)\s+de\s+(\d+)$", lambda g: [(f"{et} (hechos)", int(g[0]), "i"),
                                             (f"{et} (total)", int(g[1]), "i")]),
        (r"^\$(-?[\d.]+)$",        lambda g: [(et, float(g[0]), "f")]),
        (r"^(-?[\d.]+)\s*m$",      lambda g: [(et, float(g[0]), "f")]),
        (r"^(-?[\d.]+)%$",         lambda g: [(et, float(g[0]), "%")]),
        (r"^(-?\d+)\s*(?:kgs|°)$", lambda g: [(et, int(g[0]), "i")]),
        (r"^(\d+):(\d{2})$",       lambda g: [(f"{et} (seg)",
                                               int(g[0]) * 60 + int(g[1]), "i")]),
        (r"^(-?\d+)$",             lambda g: [(et, int(g[0]), "i")]),
        (r"^(-?[\d.]+)$",          lambda g: [(et, float(g[0]), "f")]),
    )
    for patron, hacer in reglas:
        mm = re.match(patron, v)
        if mm:
            return hacer(mm.groups())
    return []       # texto libre: "Ballas", "As", "Asesino Profesional"...


def lee_transcripcion(path):
    anclas = []
    for l in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        anclas.extend(parsea_linea(l))
    return anclas


# ----------------------------------------------------------------------
#  Buscar en el save
# ----------------------------------------------------------------------

class Save:
    def __init__(self, path):
        self.path = Path(path)
        self.d = self.path.read_bytes()
        self.off = find_blocks(self.d)
        self.fin = self.off + [len(self.d) - 4]
        self.st = self.off[BLOQUE_STATS] + 5

    def ranura(self, pos, tipo):
        """Nombre de la ranura del bloque 16 en esa posicion, o None si no lo es."""
        if not (self.off[BLOQUE_STATS] <= pos < self.fin[BLOQUE_STATS + 1]):
            return None
        r = pos - self.st
        if r < 0 or r % 4:
            return None
        if tipo in "f%":
            return f"float[{r // 4}]" if r < FLOATS_HASTA else None
        if INTS_DESDE <= r < INTS_HASTA:
            return f"int[{82 + (r - INTS_DESDE) // 4}]"
        return None

    def busca(self, val, tipo):
        """Todas las posiciones donde aparece ese valor."""
        hits = []
        if tipo == "%":
            lo, hi = val * 10, val * 10 + 10        # 55% -> [550, 560)
            for p in range(len(self.d) - 4):
                if lo <= struct.unpack_from("<f", self.d, p)[0] < hi:
                    hits.append(p)
        else:
            fmt = "<i" if tipo == "i" else "<f"
            for p in range(len(self.d) - 4):
                try:
                    v = struct.unpack_from(fmt, self.d, p)[0]
                except struct.error:
                    continue
                if (v == val) if tipo == "i" else (abs(v - val) < 0.005):
                    hits.append(p)
        return hits

    def candidatos(self, val, tipo):
        """Las posiciones que ademas son ranura valida -> {nombre: nº de hits}."""
        hits = self.busca(val, tipo)
        ranuras = {self.ranura(p, tipo) for p in hits}
        ranuras.discard(None)
        return ranuras, len(hits)


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()


# ----------------------------------------------------------------------
#  Cosechar
# ----------------------------------------------------------------------

def cosecha(parejas, nivel_min="B"):
    """parejas = [(md, b), ...]. Devuelve {etiqueta: (ranura, nivel, detalle)}."""
    por_ancla = {}      # etiqueta -> lista de (ranuras, nº hits totales, tipo)
    for md, b in parejas:
        save = Save(b)
        for et, val, tipo in lee_transcripcion(md):
            ranuras, n = save.candidatos(val, tipo)
            por_ancla.setdefault(et, []).append((ranuras, n, tipo, val))

    resultado = {}
    for et, medidas in por_ancla.items():
        # Interseccion de los candidatos de todas las partidas: si un stat es la
        # ranura X, tiene que salir candidata en TODAS.
        comun = set.intersection(*(m[0] for m in medidas)) if medidas else set()
        if len(comun) != 1:
            continue
        r = comun.pop()
        unico_en_fichero = any(m[1] == 1 for m in medidas)
        nivel = "A" if unico_en_fichero else "B"
        if nivel == "B" and nivel_min == "A":
            continue
        resultado[et] = (r, nivel, [(m[3], m[1]) for m in medidas])
    return resultado


def colisiones(res):
    """Ranuras que reclaman dos etiquetas distintas: como mucho una es correcta."""
    por_ranura = {}
    for et, (r, niv, _) in res.items():
        por_ranura.setdefault(r, []).append(et)
    return {r: ets for r, ets in por_ranura.items() if len(ets) > 1}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pareja", nargs="+", metavar="MD B",
                    help="una o mas parejas: transcripcion.md partida.b")
    ap.add_argument("--nivel", choices=["A", "B"], default="B",
                    help="A = solo lo inatacable (por defecto B = todo)")
    ap.add_argument("--codigo", action="store_true",
                    help="imprime los dicts listos para gtasa_editor.py")
    args = ap.parse_args()

    if len(args.pareja) % 2:
        ap.error("hacen falta parejas: un .md y un .b por cada partida")
    parejas = list(zip(args.pareja[0::2], args.pareja[1::2]))
    for md, b in parejas:
        if not Path(md).exists() or not Path(b).exists():
            ap.error(f"no existe {md} o {b}")

    print(f"=== cosecha sobre {len(parejas)} pareja(s) ===")
    for md, b in parejas:
        print(f"  {md}  +  {b}   ({len(lee_transcripcion(md))} anclas)")
    print()

    res = cosecha(parejas, args.nivel)
    cols = colisiones(res)

    orden = lambda kv: (0 if kv[1][0].startswith("f") else 1,
                        int(re.search(r"\[(\d+)\]", kv[1][0]).group(1)))
    for nivel in ("A", "B"):
        de_ese = {k: v for k, v in res.items() if v[1] == nivel and v[0] not in cols}
        if not de_ese:
            continue
        print("=" * 78)
        titulo = ("unico en todo el fichero" if nivel == "A"
                  else "unico en ranura valida del bloque 16")
        print(f"NIVEL {nivel} — {titulo}   ({len(de_ese)} campos)")
        print("=" * 78)
        for et, (r, _, detalle) in sorted(de_ese.items(), key=orden):
            vals = "  ".join(f"{v:,.2f}" for v, _ in detalle)
            print(f"  {r:<11} {vals:>26}   {et}")
        print()

    if cols:
        print("=" * 78)
        print(f"COLISIONES — dos anclas reclaman la misma ranura ({len(cols)})")
        print("  Como mucho una es correcta y no se sabe cual: NO se apuntan.")
        print("=" * 78)
        for r, ets in sorted(cols.items()):
            print(f"  {r:<11} {' / '.join(ets)}")
        print()

    firmes = len(res) - sum(len(e) for e in cols.values())
    print(f"TOTAL identificado: {firmes} campos"
          f"   ({len(cols)} ranuras descartadas por colision)")

    if args.codigo:
        print("\n=== para gtasa_editor.py ===")
        for kind in ("float", "int"):
            print(f"\n# --- {kind} ---")
            for et, (r, niv, _) in sorted(res.items(), key=orden):
                if r.startswith(kind) and r not in cols:
                    i = int(re.search(r"\[(\d+)\]", r).group(1))
                    print(f'    {i}: "{slug(et)[:30]}",'
                          f'{"" if niv == "A" else "   # [B]"}')


if __name__ == "__main__":
    main()

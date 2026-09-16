#!/usr/bin/env python3
"""
The houses in San Andreas THAT HAVE A GARAGE, extracted from the save itself.

    python houses.py map                       the table of the 20 houses with garage
    python houses.py view SAVE.b               what is parked in each one
    python houses.py check SAVE.b              validates the map against the save
    python houses.py properties SAVE.b         the table of PURCHASED houses (flags)
    python houses.py clean SAVE.b --output NEW.b    removes ghost slots

WHERE THIS COMES FROM
---------------------
`garage.py` found the 4 slots of CJ's garage at `block3 + 39 + k*1280` and left the
1280 jump unexplained. The explanation is that **there is not one garage, there are
twenty**:

    1280 = 20 x 64      car record = 64 bytes

    block3 + 5 + 39 + 64*g + 1280*k     g = 0..19 (garage), k = 0..3 (slot)

And right after that grid comes the garage array, which fits exactly:

    car grid          +39   .. +5159    20 x 4 x 64 = 5120
    garage array    +5159   .. +9159    50 x 80     = 4000
    block 3 payload = 9159 bytes                    <- exact, no leftover

Each 80-byte entry carries **the internal garage name** at +68 (`cjsafe`,
`beacsv`, `imp_la`, `dhangar`...), the type at +0, the position at +4 and the
bounding box at +44. Crossing the bounding box with the zone table from block 10
yields the neighborhood of each.

HOW EACH SLOT WAS TIED TO ITS HOUSE
-------------------------------------
Field truth: a car saved in garage g is, by definition, INSIDE the bounding box
of garage g. The 20x4 slots from 71 saves were read and containment in the bounding
box was voted on. Fourteen of the twenty came out straight, direct and without a tie:

    0,1,2,3,4,6,8,11,13,15,16,17,18,19

The other six have no car in any save. They are resolved because the grid order is
ASCENDING by garage type in the fourteen confirmed ones (16,17,18,24,25, 27,29,32,
34,39,40,41,42,45), and the gaps only admit one candidate each. The result
validates itself: the four missing houses are exactly the four purchasable houses
with garages that had no slot left (Dillimore, Whitewood Estates, Redsands West,
Verdant Bluffs), and the two remaining gaps are `imp_la` and `imp_lv`, which
complete the trio of police impounds with the already-confirmed `imp_sf`.

Marked with [i] in the table. They are inference, not measurement; see
CASAS-CON-GARAJE.md.
"""

import argparse
import math
import string
import struct
import sys
from pathlib import Path

from .editor import (find_blocks, platform_warnings, STATS_BLOCK, OFF_RANURA,
                          calc_checksum, stored_checksum, fix_checksum)
from .garage import describir, es_fantasma, PLAZA_LIBRE, PLAZA_LEN
from . import armor as B
from .vehicles import (etiqueta, mejora, admite, nombre as nombre_vehiculo,
                       MEJORAS, MEJORAS_VISTAS, SIN_MEJORA)
from . import globals as GL

BLOQUE_GARAJES = 3
BLOQUE_ZONAS = 10

REJILLA = 39            # first slot within the payload
PASO_GARAJE = 64        # from one garage to the next, same slot
PASO_PLAZA = 1280       # from one slot to the next, same garage (= 20 x 64)
N_GARAJES = 20
N_PLAZAS = 4

ARRAY = 5159            # 39 + 20*4*64
LEN_ENTRADA = 80
N_ENTRADAS = 50
OFF_TIPO = 0
OFF_POS = 4
OFF_CAJA = 44           # x1, x2, y1, y2
OFF_NOMBRE = 68

STAT_GASTO_PROPIEDADES = 15

# Car upgrades: ten int16 slots within the 64-byte slot record. Located by
# differential between two cars in the same save -- a tuned Remington and a tow truck
# with nothing: the tow truck has all ten at 0xffff and the Remington has eight set.
# All values fall in 1000..1193, which is the game's upgrade ID range.
# See vehiculos.MEJORAS.
#
# There are TEN and it is counted: among the 2544 saved cars in the file, slots 0..9
# have a value sometimes (from 673 cars for the first to 189 for the tenth) and the
# five following (+40..+50) are 0xffff in all without exception.
MEJORAS_OFF = 20
MEJORAS_N = 10
MODELO_OFF = 18

# The table. `tipo` is byte +0 of the garage array entry and is the key that links
# the grid slot to the physical garage. `[i]` = inferred, see the header.
#
# `clase`: "compra" means you pay and it is a house; "gratis" comes with the story;
# "aerodromo" is Verdant Meadows, which is an asset and takes two slots; "deposito"
# is the police impound where your car ends up if they bust you, which is not a house
# but stores cars just the same.
#
#   grid: (type, internal name, house, zone, price, class, inferred)
CASAS = {
    0:  (16, "cjsafe",  "Johnson House (Grove Street)", "GAN1",     None, "gratis", False),
    1:  (17, "beacsv",  "Santa Maria Beach",            "SMB2",    30000, "compra", False),
    2:  (18, "vEsvgrg", "Rockshore West",               "RSW2",    20000, "compra", False),
    3:  (24, "cn2gar1", "Fort Carson",                  "CARSO",   30000, "compra", False),
    4:  (25, "cn2gar2", "Verdant Meadows (garaje)",     "MEAD",    80000, "aerodromo", False),
    5:  (26, "burbdo2", "Dillimore",                    "DILLI",   40000, "compra", True),
    6:  (27, "blob69",  "Prickle Pine",                 "PRP2",    50000, "compra", False),
    7:  (28, "blob7",   "Whitewood Estates",            "WWE",     30000, "compra", True),
    8:  (29, "burbdoo", "Palomino Creek",               "CA1",     35000, "compra", False),
    9:  (30, "blob6",   "Redsands West",                "REDW2",   30000, "compra", True),
    10: (31, "carlas1", "Verdant Bluffs",               "ELCO1",   10000, "compra", True),
    11: (32, "CEsafe1", "Mulholland",                   "MUL2B",  120000, "compra", False),
    12: (33, "imp_la",  "LS police impound",            "PER1",     None, "deposito", True),
    13: (34, "imp_sf",  "SF police impound",            "SFDWT5",   None, "deposito", False),
    14: (35, "imp_lv",  "LV police impound",            "ISLE",     None, "deposito", True),
    15: (39, "sav1sfe", "Calton Heights",               "CALT",   100000, "compra", False),
    16: (40, "sav1sfw", "Paradiso",                     "PARA",    20000, "compra", False),
    17: (41, "LCKSfse", "Doherty garage",               "EEK1",     None, "gratis", False),
    18: (42, "svgsfs1", "Hashbury",                     "HASH",    40000, "compra", False),
    19: (45, "dhangar", "Verdant Meadows (hangar)",     "MEAD",     None, "aerodromo", False),
}

# The "house purchased" flags live separately, in the globals of block 1, and are
# ANOTHER thing: 29 flags for the 29 purchasable houses, whether they have a garage
# or not. So far only three are identified and two are the only ones measured with a
# BEFORE/AFTER pair. See PRUEBA-PROPIEDADES.md.
PROPIEDADES = range(730, 759)
CASILLAS = {
    739: "Mulholland ($120,000), measured with own pair",
    757: "Willowfield ($10,000), measured with own pair",
    733: "a $50,000 house, unidentified",
}

OK_ZONA = set(string.ascii_uppercase + string.digits + "_")


# --- block 3 reading ------------------------------------------------
def payload(data):
    return find_blocks(data)[BLOQUE_GARAJES] + 5


def off_plaza(data, garaje, plaza):
    return payload(data) + REJILLA + PASO_GARAJE * garaje + PASO_PLAZA * plaza


def entrada(data, i):
    """One entry from the array of 50 garages."""
    o = payload(data) + ARRAY + i * LEN_ENTRADA
    x, y, z = struct.unpack_from("<3f", data, o + OFF_POS)
    x1, x2, y1, y2 = struct.unpack_from("<4f", data, o + OFF_CAJA)
    nombre = data[o + OFF_NOMBRE:o + OFF_NOMBRE + 8].split(b"\x00")[0]
    return dict(i=i, tipo=data[o + OFF_TIPO], nombre=nombre.decode("latin-1", "replace"),
                x=x, y=y, z=z,
                x1=min(x1, x2), x2=max(x1, x2), y1=min(y1, y2), y2=max(y1, y2))


def garajes(data):
    return [entrada(data, i) for i in range(N_ENTRADAS)]


def por_tipo(data, tipo):
    for g in garajes(data):
        if g["tipo"] == tipo:
            return g
    return None


# --- zones (block 10), to put a neighborhood name on a coordinate -----
def zonas(data):
    def limpio(b):
        s = b.split(b"\x00")[0].decode("latin-1")
        return s if s and all(c in OK_ZONA for c in s) else None

    offs = find_blocks(data)
    ini, fin = offs[BLOQUE_ZONAS], offs[BLOQUE_ZONAS + 1]
    out = []
    for o in range(ini, fin - 32):
        nombre, gxt = limpio(data[o:o + 8]), limpio(data[o + 8:o + 16])
        if not nombre or not gxt:
            continue
        x1, y1, z1, x2, y2, z2 = struct.unpack_from("<6h", data, o + 16)
        if x1 < x2 and y1 < y2 and z1 < z2 and all(-3200 <= v <= 3200 for v in (x1, y1, x2, y2)):
            out.append((nombre, x1, y1, x2, y2, (x2 - x1) * (y2 - y1)))
    return out


def zona_de(zs, x, y):
    """The neighborhood: among the zones containing the point, the smallest one."""
    dentro = sorted([z for z in zs if z[1] <= x <= z[3] and z[2] <= y <= z[4]],
                    key=lambda z: z[5])
    return dentro[0][0] if dentro else "?"


def gasto_propiedades(data):
    off = find_blocks(data)[STATS_BLOCK] + 5 + STAT_GASTO_PROPIEDADES * 4
    return struct.unpack_from("<f", data, off)[0]


# --- commands --------------------------------------------------------
def mapa(args):
    print(f"  {N_GARAJES} garage slots in the save, {N_PLAZAS} cars each.\n")
    print(f"  {'slot':>5}  {'name':<9} {'house':<32} {'zone':<7} {'price':>10}")
    for g in range(N_GARAJES):
        tipo, nombre, casa, zona, precio, clase, inferido = CASAS[g]
        txt = f"${precio:,}" if precio else {"gratis": "free"}.get(clase, "--")
        print(f"  {g:5d}  {nombre:<9} {casa:<32} {zona:<7} {txt:>10}"
              f"{'   [i]' if inferido else ''}")

    compra = [c for c in CASAS.values() if c[5] == "compra"]
    print(f"\n  {len(compra)} PURCHASABLE houses with garage, ${sum(c[4] for c in compra):,} "
          f"in total")
    print("  2 free houses (Grove Street and Doherty garage)")
    print("  2 Verdant Meadows airfield slots ($80,000, it is an asset)")
    print("  3 police impounds, which are not houses but store cars")
    print("\n  [i] = inferred by type order, not measured. See CASAS-CON-GARAJE.md")


def ver(args):
    data = Path(args.save).read_bytes()
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)
    gs = {g["tipo"]: g for g in garajes(data)}

    print(f"=== {args.save}")
    print(f"  property spending: ${gasto_propiedades(data):,.0f}\n")

    total = fantasmas = 0
    for g in range(N_GARAJES):
        tipo, nombre, casa, zona, precio, clase, inferido = CASAS[g]
        gar = gs.get(tipo)
        sitio = f"({gar['x']:7.1f},{gar['y']:8.1f})" if gar else "(not found)"
        estados = [describir(data, off_plaza(data, g, k))[5] for k in range(N_PLAZAS)]
        n_coches = estados.count("ocupada")
        n_fantasmas = estados.count("FANTASMA")
        total += n_coches
        fantasmas += n_fantasmas

        cabecera = f"  {g:2d} {casa:<32} {sitio}"
        if not n_coches and not n_fantasmas and not args.todo:
            print(f"{cabecera}  empty")
            continue
        print(cabecera)
        for k in range(N_PLAZAS):
            off = off_plaza(data, g, k)
            x, y, z, marca, modelo, estado = describir(data, off)
            if estado in ("LIBRE (limpia)", "libre") and not args.todo:
                continue
            pos = (f"({x:7.1f},{y:8.1f},{z:6.1f})"
                   if all(math.isfinite(v) for v in (x, y, z)) else "        (NaN)         ")
            marca_f = "  <-- occupies slot but no car to extract" if estado == "FANTASMA" else ""
            print(f"       slot {k}  {etiqueta(modelo):<26} {pos}  {estado}{marca_f}")

    print(f"\n  {total} car(s) stored in total")
    if fantasmas:
        print(f"  {fantasmas} GHOST slot(s): remove with "
              f"`houses.py limpiar {args.save} --salida NUEVO.b`")


def comprobar(args):
    """Validates the map against the save: sizes, types, names and zones."""
    data = Path(args.save).read_bytes()
    offs = find_blocks(data)
    ini, fin = offs[BLOQUE_GARAJES], offs[BLOQUE_GARAJES + 1]
    tam = fin - ini - 5
    fallos = []

    esperado = ARRAY + N_ENTRADAS * LEN_ENTRADA
    print(f"  block 3 payload: {tam} bytes (grid {ARRAY} + garages "
          f"{N_ENTRADAS * LEN_ENTRADA} = {esperado})")
    if tam != esperado:
        fallos.append(f"payload measures {tam}, not {esperado}")

    zs = zonas(data)
    print(f"  {len(zs)} zones read from block 10\n")
    print(f"  {'slot':>5} {'type':>4} {'name':<9} {'expected':<9} {'zone':<8} "
          f"{'expected':<8}")
    for g in range(N_GARAJES):
        tipo, nombre, casa, zona, precio, clase, inferido = CASAS[g]
        gar = por_tipo(data, tipo)
        if gar is None:
            fallos.append(f"slot {g}: there is no garage of type {tipo}")
            print(f"  {g:5d} {tipo:4d} {'--':<9} {nombre:<9} MISSING")
            continue
        z = zona_de(zs, gar["x"], gar["y"])
        bien_n = gar["nombre"] == nombre
        bien_z = z == zona
        if not bien_n:
            fallos.append(f"slot {g}: the garage of type {tipo} is called "
                          f"{gar['nombre']!r}, not {nombre!r}")
        if not bien_z:
            fallos.append(f"slot {g}: garage {nombre} is in zone {z}, not {zona}")
        print(f"  {g:5d} {tipo:4d} {gar['nombre']:<9} {nombre:<9} {z:<8} {zona:<8}"
              f"  {'ok' if bien_n and bien_z else 'NO'}")

    # A car saved in a HOUSE falls inside that house's bounding box: that is the proof
    # that ties the map. Impounds don't count, there the game stores the car with the
    # position where it took it from you, which could be anywhere in the region.
    fuera = 0
    for g in range(N_GARAJES):
        if CASAS[g][5] == "deposito":
            continue
        gar = por_tipo(data, CASAS[g][0])
        if gar is None:
            continue
        for k in range(N_PLAZAS):
            x, y, z, marca, modelo, estado = describir(data, off_plaza(data, g, k))
            if estado != "ocupada":
                continue
            if not (gar["x1"] - 8 <= x <= gar["x2"] + 8
                    and gar["y1"] - 8 <= y <= gar["y2"] + 8):
                fuera += 1
                print(f"  warning: the car in slot {g}.{k} ({x:.0f},{y:.0f}) falls "
                      f"outside the bounding box of {CASAS[g][2]}")

    print()
    if fallos:
        for f in fallos:
            print(f"  BAD: {f}")
        sys.exit(1)
    print(f"  the map matches this save"
          f"{f' ({fuera} cars outside bounding box)' if fuera else ''}")


def limpiar(args):
    """Frees the GHOST slots of the 20 garages. Never touches a car.

    Writes the `PLAZA_LIBRE` pattern from garage.py, which is what the game leaves
    when emptying a slot -- nothing is invented. With `--todo` it also normalizes
    slots that are already free but without that exact pattern; that is cosmetic and
    not needed (see `garaje.es_fantasma`), so by default it is not done.

    CONFIRMED IN-GAME (August 7), and outside CJ's garage: the three ghosts were
    cleaned from the player's 100% save and now four cars fit in HASHBURY. Before,
    it had Sultan + Bullet + a ghost and the game counted 3 out of 4, with the ghost
    slot impossible to clear by playing. Before/after in
    `partidas/archivo/13-limpieza-garajes-07ago/`.
    """
    destino = Path(args.salida)
    if destino.exists() and not args.forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(args.save).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        print("Source is not usable:", file=sys.stderr)
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    buf = bytearray(data)
    tocadas = []
    for g in range(N_GARAJES):
        if args.garaje is not None and g != args.garaje:
            continue
        for k in range(N_PLAZAS):
            off = off_plaza(data, g, k)
            x, y, z, marca, modelo, estado = describir(data, off)
            fantasma = es_fantasma(data, off)
            if not fantasma and not (args.todo and estado == "libre"):
                continue
            buf[off:off + PLAZA_LEN] = PLAZA_LIBRE
            tocadas.append((g, k, modelo, "FANTASMA" if fantasma else estado))

    if not tocadas:
        print("  no ghost slots; nothing written.")
        return

    for g, k, modelo, que in tocadas:
        print(f"  {CASAS[g][2]:<32} slot {k}  {etiqueta(modelo):<26} "
              f"{que} -> FREE (clean)")

    fix_checksum(buf)
    assert len(buf) == len(data), "the size cannot change"
    destino.write_bytes(buf)

    # re-read from disk and re-validate, like the rest of the tools
    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)
    quedan = sum(1 for g in range(N_GARAJES) for k in range(N_PLAZAS)
                 if es_fantasma(check, off_plaza(check, g, k)))
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])

    print(f"\n  {len(tocadas)} slot(s) · {cambiados} bytes changed")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, "
          f"{len(find_blocks(check)) - 1} blocks OK")
    print(f"  ghosts remaining: {quedan}")


def lee_mejoras(data, off):
    return [struct.unpack_from("<H", data, off + MEJORAS_OFF + 2 * i)[0]
            for i in range(MEJORAS_N)]


def tunear(args):
    """Adds or removes upgrades from a saved car. Does not change the model.

    TESTED IN-GAME TWICE (August 7), with different results:

        Hangar Rhino    8 body kit pieces from a Remington    THE GAME CRASHED
        CJ's Patriot    1 nitro                               loaded fine

    Both models are equally "impossible" -- the Rhino appears 81 times in the file
    and the Patriot 106, none with upgrades, and the mod shop offers them nothing --
    so **an unsupported upgrade is not enough to crash the game**. What broke the
    tank was the volume or some specific part, probably the body kit pieces, which
    need an anchor in the model. Nitro is not mounted anywhere.

    And the Patriot settled it: it was loaded, driven and saved on the phone, and the
    save that came back had the record REWRITTEN by the game with the `1010` intact.
    So **the game saves the upgrades array without validating it and ignores it when
    spawning the car**: adding a upgrade the model does not support gives no error
    and no advantage, it is inert.

    That is why the whitelist `vehiculos.MEJORAS_VISTAS` -- what the game HAS actually
    placed on each model in real saves -- is the default criterion: outside of it
    normally nothing happens at all, and the worst case is what happened with the Rhino.
    """
    destino = Path(args.salida)
    if destino.exists() and not args.forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(args.save).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        print("Source is not usable:", file=sys.stderr)
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    off = off_plaza(data, args.garaje, args.plaza)
    x, y, z, marca, modelo, estado = describir(data, off)
    if estado != "ocupada":
        sys.exit(f"error: slot {args.plaza} of {CASAS[args.garaje][2]} is "
                 f"{estado}; there is no car to tune")

    if args.quitar:
        nuevas = []
    else:
        nuevas = [int(m) for m in args.mejoras.split(",") if m.strip()]
        if len(nuevas) > MEJORAS_N:
            sys.exit(f"error: {MEJORAS_N} upgrades fit, you requested {len(nuevas)}")
        desconocidas = [m for m in nuevas if m not in MEJORAS]
        if desconocidas:
            sys.exit(f"error: these are not upgrade IDs (1000..1193): {desconocidas}")
        # The game puts ONE part per slot: among the 649 upgraded cars in the file
        # there is not a single case of two from the same category. We don't skip
        # that by hand.
        categorias = [MEJORAS[m] for m in nuevas]
        repes = {c for c in categorias if categorias.count(c) > 1}
        if repes:
            sys.exit(f"error: two upgrades for the same slot: {sorted(repes)}")

        # The brake that caused a game crash. See the docstring.
        ajenas = [m for m in nuevas if not admite(modelo, m)]
        if ajenas and not args.aunque_reviente:
            vistas = MEJORAS_VISTAS.get(modelo)
            print(f"error: a {etiqueta(modelo)} has never been seen with "
                  f"{', '.join(mejora(m) for m in ajenas)}", file=sys.stderr)
            if vistas:
                print(f"  what it does support: "
                      f"{', '.join(mejora(m) for m in sorted(vistas))}", file=sys.stderr)
            else:
                print(f"  this model has never had ANY upgrade in the file's saves; "
                      f"the mod shop probably offers none", file=sys.stderr)
            sys.exit("  use --even-if-it-crashes to try it anyway: with 8 pieces on "
                     "the Rhino the game crashed, with 1 nitro on the Patriot it did not")

    antes = lee_mejoras(data, off)
    buf = bytearray(data)
    for i in range(MEJORAS_N):
        valor = nuevas[i] if i < len(nuevas) else SIN_MEJORA
        struct.pack_into("<H", buf, off + MEJORAS_OFF + 2 * i, valor)

    print(f"  {CASAS[args.garaje][2]}, slot {args.plaza}: {etiqueta(modelo)}")
    print(f"    before: {[mejora(m) for m in antes if m != SIN_MEJORA] or 'no upgrades'}")
    print(f"    after:  {[mejora(m) for m in nuevas] or 'no upgrades'}")

    if args.ranura is not None:
        # The phone chooses the slot by the FILE NAME, but the save carries its own
        # inside and a raw copy leaves it lying. Same fix as gta.py clone.
        pos = find_blocks(data)[0] + 5 + OFF_RANURA
        vieja = struct.unpack_from("<i", data, pos)[0]
        struct.pack_into("<i", buf, pos, args.ranura)
        print(f"    internal slot: {vieja} -> {args.ranura}")

    fix_checksum(buf)
    assert len(buf) == len(data), "the size cannot change"
    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)
    cambiados = [i for i in range(len(data)) if data[i] != check[i]]
    zona = range(off + MEJORAS_OFF, off + MEJORAS_OFF + 2 * MEJORAS_N)
    fuera = [i for i in cambiados
             if i not in zona and i < len(data) - 4
             and not (args.ranura is not None
                      and find_blocks(data)[0] + 5 + OFF_RANURA <= i
                      < find_blocks(data)[0] + 9 + OFF_RANURA)]
    print(f"\n  {len(cambiados)} bytes changed, {len(fuera)} outside what was expected")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, "
          f"{len(find_blocks(check)) - 1} blocks OK")


def cambiar_coche(args):
    """Changes the MODEL of the car in a slot. The rest of the record stays.

    The only thing changed is the int16 model and the ten upgrade slots, which are
    emptied: the old car's upgrades don't work on the new one, and eight body kit
    pieces from another model are exactly what crashed the game with the Rhino.

    What is NOT changed, on purpose: the position (so it appears in its place), the
    color, the proof flags byte and the tail of the record. Change one thing at a time.

    VERIFIED IN-GAME (August 7). CJ's garage Patriot was changed to an FBI Truck
    (model 528) -- a vehicle that cannot be obtained through any legitimate means and
    is not parked in any of the 101 saves in the file, i.e. no donor to copy from.
    It appeared in the garage and is drivable. Five bytes.

    And it arrived ARMORED: byte +16 is not touched, and the truck inherited the
    proof flags the Patriot had. Proof flags belong to the SLOT, not the car.
    """
    destino = Path(args.salida)
    if destino.exists() and not args.forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(args.save).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        print("Source is not usable:", file=sys.stderr)
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    if nombre_vehiculo(args.modelo) is None:
        sys.exit(f"error: {args.modelo} is not a vehicle model (400..611)")

    off = off_plaza(data, args.garaje, args.plaza)
    x, y, z, marca, viejo, estado = describir(data, off)
    if estado != "ocupada":
        sys.exit(f"error: slot {args.plaza} of {CASAS[args.garaje][2]} is "
                 f"{estado}; there is no car to change")

    buf = bytearray(data)
    struct.pack_into("<h", buf, off + MODELO_OFF, args.modelo)
    for i in range(MEJORAS_N):
        struct.pack_into("<H", buf, off + MEJORAS_OFF + 2 * i, SIN_MEJORA)

    print(f"  {CASAS[args.garaje][2]}, slot {args.plaza}")
    print(f"    {etiqueta(viejo)}  ->  {etiqueta(args.modelo)}")
    quitadas = [mejora(m) for m in lee_mejoras(data, off) if m != SIN_MEJORA]
    print(f"    upgrades it had: {quitadas or 'none'} -> none")
    print(f"    stays at ({x:.1f}, {y:.1f}, {z:.1f})")

    if args.ranura is not None:
        pos = find_blocks(data)[0] + 5 + OFF_RANURA
        vieja = struct.unpack_from("<i", data, pos)[0]
        struct.pack_into("<i", buf, pos, args.ranura)
        print(f"    internal slot: {vieja} -> {args.ranura}")

    fix_checksum(buf)
    assert len(buf) == len(data), "the size cannot change"
    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)
    cambiados = [i for i in range(len(data)) if data[i] != check[i]]
    previsto = set(range(off + MODELO_OFF, off + MODELO_OFF + 2))
    previsto |= set(range(off + MEJORAS_OFF, off + MEJORAS_OFF + 2 * MEJORAS_N))
    previsto |= set(range(len(data) - 4, len(data)))
    if args.ranura is not None:
        p0 = find_blocks(data)[0] + 5 + OFF_RANURA
        previsto |= set(range(p0, p0 + 4))
    fuera = [i for i in cambiados if i not in previsto]
    print(f"\n  {len(cambiados)} bytes changed, {len(fuera)} outside what was expected")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, "
          f"{len(find_blocks(check)) - 1} blocks OK")


def blindar(args):
    """Proofs the cars in all 20 garages in one pass.

    Writes the five proof bits of `armor.MASCARA` and RESPECTS the others, which
    belong to the car and we don't know what they are. It is the same operation as
    `armor.py`, which only reached CJ's garage, applied to all 80 slots.

    WHAT HAPPENS WITH EMPTY SLOTS (and why they are not touched by default)
    --------------------------------------------------------------------------
    The byte lives in the SAVED CAR RECORD, not in the slot. When you park a car the
    game writes the entire record from the vehicle it has in front, so it will most
    likely overwrite what we left there. In the file, out of the 2544 saved cars
    **2278 have the byte at 0x00** and cars that appear new in a slot almost always
    come out normal.

    TESTED IN-GAME AND IT DOES NOT WORK (August 7). All 80 slots were proofed, the
    player emptied the Santa Maria Beach garage, put in a street car, closed, opened
    and shot it: it burned. The file shows why -- the slot that received the car came
    back with the byte at 0x00 and those that stayed empty kept the 0x1f:

        slot 0   Cheetah 0x1f  ->  Greenwood 0x00    <- the game overwrote it on parking
        slot 1   Infernus 0xdf ->  (empty) 0xdf      <- nobody wrote there

    That is why `--empty` is not useful for anything practical and must be requested
    explicitly.

    What IS confirmed in-game: proofing a car that is ALREADY saved (Patriot 470 and
    Remington 534, both withstood the minigun), and that the proof flags stay in the
    record if you change the model -- that is how the FBI Truck came out proofed.
    """
    destino = Path(args.salida)
    if destino.exists() and not args.forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(args.save).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        print("Source is not usable:", file=sys.stderr)
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    valor = B.NORMAL if args.quitar else B.BLINDADO
    buf = bytearray(data)
    tocadas, saltadas = [], 0
    for g in range(N_GARAJES):
        if args.garaje is not None and g != args.garaje:
            continue
        for k in range(N_PLAZAS):
            off = off_plaza(data, g, k)
            estado = describir(data, off)[5]
            if estado != "ocupada" and not args.vacias:
                saltadas += 1
                continue
            antes, ahora = B.aplicar(buf, off, valor)
            if antes != ahora:
                tocadas.append((g, k, describir(data, off)[4], estado, antes, ahora))

    if not tocadas:
        print("  nothing to change; nothing written.")
        return

    for g, k, modelo, estado, antes, ahora in tocadas:
        coche = etiqueta(modelo) if estado == "ocupada" else f"({estado})"
        print(f"  {CASAS[g][2]:<30} slot {k}  {coche:<26} "
              f"0x{antes:02x} -> 0x{ahora:02x}")

    fix_checksum(buf)
    assert len(buf) == len(data), "the size cannot change"
    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {len(tocadas)} slot(s) · {cambiados} bytes changed"
          f"{f' · {saltadas} empty untouched' if saltadas else ''}")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, "
          f"{len(find_blocks(check)) - 1} blocks OK")


def propiedades(args):
    """The purchased house flags from block 1. Another table, another thing."""
    data = Path(args.save).read_bytes()
    g = GL.carga(args.save)[2]
    encendidas = [i for i in PROPIEDADES if g[i] == 1]
    raras = [(i, g[i]) for i in PROPIEDADES if g[i] not in (0, 1)]

    print(f"=== {args.save}")
    print(f"  property spending: ${gasto_propiedades(data):,.0f}")
    print(f"  houses purchased: {len(encendidas)} out of {len(PROPIEDADES)}\n")
    for i in PROPIEDADES:
        que = CASILLAS.get(i, "unidentified")
        print(f"  global[{i}]  {g[i]}   {que}")
    if raras:
        print(f"\n  warning: flags that are neither 0 nor 1: {raras}")
    print("\n  Only 3 of the 29 flags have a name and only 2 are measured.")
    print("  The flag->house mapping is half-done: see PRUEBA-PROPIEDADES.md.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)

    sub.add_parser("mapa", aliases=["map"], help="the table of the 20 houses with garage")

    v = sub.add_parser("ver", aliases=["see"], help="what is parked in each house")
    v.add_argument("save")
    v.add_argument("--todo", action="store_true", help="also show free slots")

    c = sub.add_parser("comprobar", aliases=["check"], help="validates the map against the save")
    c.add_argument("save")

    p = sub.add_parser("propiedades", aliases=["properties"], help="the purchased house flags (block 1)")
    p.add_argument("save")

    l = sub.add_parser("limpiar", aliases=["clean"], help="removes ghost slots from the 20 garages")
    l.add_argument("save")
    l.add_argument("--salida", required=True)
    l.add_argument("--garaje", type=int, choices=range(N_GARAJES), metavar="N",
                   help="only that garage (0..19); default: all twenty")
    l.add_argument("--todo", action="store_true",
                   help="also normalize already-free slots (cosmetic)")
    l.add_argument("--forzar", action="store_true")

    t = sub.add_parser("tunear", aliases=["tune"], help="adds or removes upgrades from a saved car")
    t.add_argument("save")
    t.add_argument("--garaje", type=int, required=True, choices=range(N_GARAJES),
                   metavar="N")
    t.add_argument("--plaza", type=int, required=True, choices=range(N_PLAZAS))
    t.add_argument("--mejoras", default="", metavar="ID,ID,...",
                   help=f"up to {MEJORAS_N} IDs from 1000..1193")
    t.add_argument("--quitar", action="store_true", help="remove all upgrades")
    t.add_argument("--ranura", type=int, choices=range(1, 11), metavar="N",
                   help="changes the slot that the save carries internally")
    t.add_argument("--salida", required=True)
    t.add_argument("--forzar", action="store_true", help="overwrite the output file")
    t.add_argument("--aunque-reviente", action="store_true",
                   dest="aunque_reviente",
                   help="add upgrades that model has never had")

    cc = sub.add_parser("cambiar-coche", aliases=["change-car"], help="changes the car model in a slot")
    cc.add_argument("save")
    cc.add_argument("--garaje", type=int, required=True, choices=range(N_GARAJES),
                    metavar="N")
    cc.add_argument("--plaza", type=int, required=True, choices=range(N_PLAZAS))
    cc.add_argument("--modelo", type=int, required=True, metavar="ID",
                    help="new model, 400..611")
    cc.add_argument("--ranura", type=int, choices=range(1, 11), metavar="N")
    cc.add_argument("--salida", required=True)
    cc.add_argument("--forzar", action="store_true")

    bl = sub.add_parser("blindar", aliases=["proof"], help="applies proof flags to cars in all 20 garages")
    bl.add_argument("save")
    bl.add_argument("--garaje", type=int, choices=range(N_GARAJES), metavar="N")
    bl.add_argument("--quitar", action="store_true", help="removes proof flags (0x00)")
    bl.add_argument("--vacias", action="store_true",
                    help="also touch empty slots (without checking if it works)")
    bl.add_argument("--salida", required=True)
    bl.add_argument("--forzar", action="store_true")

    args = ap.parse_args()
    if args.orden in ("tunear", "tune") and not args.mejoras and not args.quitar:
        ap.error("provide --mejoras ID,ID or --quitar")
    comandos = {
        "mapa": mapa, "map": mapa, "ver": ver, "see": ver,
        "comprobar": comprobar, "check": comprobar,
        "limpiar": limpiar, "clean": limpiar,
        "tunear": tunear, "tune": tunear,
        "cambiar-coche": cambiar_coche, "change-car": cambiar_coche,
        "blindar": blindar, "proof": blindar,
        "propiedades": propiedades, "properties": propiedades,
    }
    comandos[args.orden](args)


if __name__ == "__main__":
    main()

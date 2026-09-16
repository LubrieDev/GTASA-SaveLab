#!/usr/bin/env python3
"""
General tool for the 20 garages in GTA SA Mobile.

    python garages.py ver SAVE.b [--todo]
    python garages.py anadir SAVE.b --salida NUEVO.b --garaje 19 --plaza 0 --modelo 596
    python garages.py anadir SAVE.b --salida NUEVO.b --garaje 19 --plaza 0 --modelo 596 --x 423 --y 2500 --z 16
    python garages.py quitar SAVE.b --salida NUEVO.b --garaje 19 --plaza 0
    python garages.py limpiar SAVE.b --salida NUEVO.b [--garaje N]
    python garages.py coches                    the table of vehicle IDs

HOW IT WORKS
------------
Block 3 of the save contains a grid of 20 garages x 4 slots x 64 bytes.
Each slot has: position (x,y,z), mark, model, and upgrades.

The default coordinates for a new car are the center of the indicated garage,
so it appears inside. If you want to place it somewhere else, use
--x, --y, --z.

VERIFIED IN-GAME: the game loads the car at the position in the slot. If the
position is inside the garage, it appears inside. If it is outside, it appears
outside. The coordinates you set are where the car will spawn.
"""

import argparse
import math
import struct
import sys
from pathlib import Path

from .editor import calc_checksum, stored_checksum, find_blocks, platform_warnings, fix_checksum
from .garage import PLAZA_LIBRE, PLAZA_LEN, describir, es_fantasma
from .houses import (
    off_plaza, N_GARAJES, N_PLAZAS, CASAS,
    garajes as leer_garajes, entrada as leer_entrada,
)
from .vehicles import etiqueta, nombre, NOMBRES


# Default positions for each garage (center of the parking area)
# Measured from real saves or calculated from the garage bounding box
POSICIONES_POR_DEFECTO = {
    0:  (2495.0, -1695.0, 13.0),   # Johnson House (Grove Street)
    1:  (320.0, -1770.0, 4.0),     # Santa Maria Beach
    2:  (2450.0, 695.0, 11.0),     # Rockshore West
    3:  (-365.0, 1195.0, 7.0),     # Fort Carson
    4:  (430.0, 2540.0, 17.0),     # Verdant Meadows (garage)
    5:  (783.0, -493.0, 13.0),     # Dillimore
    6:  (1270.0, 2525.0, 10.0),    # Prickle Pine
    7:  (930.0, 2008.0, 10.0),     # Whitewood Estates
    8:  (2228.0, 168.0, 10.0),     # Palomino Creek
    9:  (1409.0, 1900.0, 10.0),    # Redsands West
    10: (1695.0, -2089.0, 13.0),   # Verdant Bluffs
    11: (1353.0, -637.0, 53.0),    # Mulholland
    12: (1524.0, -1653.0, 5.0),    # LS police impound
    13: (-1653.0, 647.0, 31.0),    # SF police impound
    14: (2218.0, 2448.0, 10.0),    # LV police impound
    15: (-2109.0, 887.0, 66.0),    # Calton Heights
    16: (-2699.0, 822.0, 42.0),    # Paradiso
    17: (-2043.0, 119.0, 28.0),    # Doherty garage
    18: (-2454.0, -132.0, 26.0),   # Hashbury
    19: (423.0, 2500.0, 17.0),     # Verdant Meadows (hangar)
}


def cmd_ver(args):
    """Shows the contents of all 20 garages."""
    data = Path(args.save).read_bytes()
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)

    gs = {g["tipo"]: g for g in leer_garajes(data)}

    print(f"=== {args.save}\n")

    total_coches = 0
    total_fantasmas = 0

    for g in range(N_GARAJES):
        tipo, nombre_g, casa, zona, precio, clase, inferido = CASAS[g]
        gar = gs.get(tipo)
        sitio = f"({gar['x']:7.1f},{gar['y']:8.1f})" if gar else "(not found)"

        estados = [describir(data, off_plaza(data, g, k))[5] for k in range(N_PLAZAS)]
        n_coches = estados.count("ocupada")
        n_fantasmas = estados.count("FANTASMA")
        total_coches += n_coches
        total_fantasmas += n_fantasmas

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
            marca_f = "  <-- ghost" if estado == "FANTASMA" else ""
            print(f"       slot {k}  {etiqueta(modelo):<26} {pos}  {estado}{marca_f}")

    print(f"\n  {total_coches} car(s), {total_fantasmas} ghost(s)")


def cmd_anadir(args):
    """Adds a car to an empty slot."""
    destino = Path(args.salida)
    if destino.exists() and not args.forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    if nombre(args.modelo) is None:
        sys.exit(f"error: {args.modelo} is not a vehicle model (400..611)")

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
    _, _, _, _, _, estado = describir(data, off)
    if estado == "ocupada":
        sys.exit(f"error: slot {args.plaza} of {CASAS[args.garaje][2]} already has a car")
    if estado == "FANTASMA":
        sys.exit(f"error: slot {args.plaza} of {CASAS[args.garaje][2]} has a ghost; "
                 f"clean it first with 'garajes.py clean'")

    x = args.x if args.x is not None else POSICIONES_POR_DEFECTO[args.garaje][0]
    y = args.y if args.y is not None else POSICIONES_POR_DEFECTO[args.garaje][1]
    z = args.z if args.z is not None else POSICIONES_POR_DEFECTO[args.garaje][2]

    buf = bytearray(data)

    # Position
    struct.pack_into("<fff", buf, off, x, y, z)
    # Mark (2 = occupied, seen in real saves)
    buf[off + 12] = 2
    # Unknown bytes +13..+17 (common pattern)
    buf[off + 13] = 0x02
    buf[off + 14] = 0x04
    buf[off + 15] = 0x00
    buf[off + 16] = 0x00
    buf[off + 17] = 0x00
    # Model
    struct.pack_into("<h", buf, off + 18, args.modelo)
    # Tail: 0xff
    for i in range(20, 24):
        buf[off + i] = 0xff

    fix_checksum(buf)
    assert len(buf) == len(data)

    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)

    nombre_g = CASAS[args.garaje][2]
    print(f"  {nombre_g}, slot {args.plaza}: {etiqueta(args.modelo)}")
    print(f"    position: ({x:.1f}, {y:.1f}, {z:.1f})")

    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK")


def cmd_quitar(args):
    """Empties a slot (makes it free)."""
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
    if estado in ("LIBRE (limpia)", "libre"):
        sys.exit(f"error: slot {args.plaza} of {CASAS[args.garaje][2]} is already free")

    buf = bytearray(data)
    buf[off:off + PLAZA_LEN] = PLAZA_LIBRE

    fix_checksum(buf)
    assert len(buf) == len(data)

    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)

    nombre_g = CASAS[args.garaje][2]
    print(f"  {nombre_g}, slot {args.plaza}: {etiqueta(modelo)} -> FREE (clean)")

    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK")


def cmd_limpiar(args):
    """Cleans all slots in one or all garages."""
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
    tocadas = 0

    garajes_a_limpiar = [args.garaje] if args.garaje is not None else range(N_GARAJES)

    for g in garajes_a_limpiar:
        for k in range(N_PLAZAS):
            off = off_plaza(data, g, k)
            if buf[off:off + PLAZA_LEN] == PLAZA_LIBRE:
                continue
            modelo = struct.unpack_from("<h", data, off + 18)[0]
            buf[off:off + PLAZA_LEN] = PLAZA_LIBRE
            tocadas += 1
            nombre_g = CASAS[g][2]
            print(f"  {nombre_g:<32} slot {k}  {etiqueta(modelo):<26} -> FREE (clean)")

    if not tocadas:
        print("  everything was already clean; nothing written.")
        return

    fix_checksum(buf)
    assert len(buf) == len(data)

    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)

    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {tocadas} slot(s) cleaned · {cambiados} bytes changed")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK")


def cmd_coches(args):
    """Shows the vehicle ID table."""
    print(f"  {'ID':>5}  {'Name':<25}")
    print(f"  {'---':>5}  {'------':<25}")
    for mid in sorted(NOMBRES.keys()):
        print(f"  {mid:5d}  {NOMBRES[mid]}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)

    # VIEW
    v = sub.add_parser("ver", aliases=["see"], help="shows the contents of all 20 garages")
    v.add_argument("save")
    v.add_argument("--todo", action="store_true",
                   help="also show free slots")

    # ADD
    a = sub.add_parser("anadir", aliases=["add"], help="adds a car to an empty slot")
    a.add_argument("save")
    a.add_argument("--salida", required=True)
    a.add_argument("--garaje", type=int, required=True, choices=range(N_GARAJES),
                   metavar="N", help="garage (0..19)")
    a.add_argument("--plaza", type=int, required=True, choices=range(N_PLAZAS),
                   metavar="N", help="slot (0..3)")
    a.add_argument("--modelo", type=int, required=True, metavar="ID",
                   help="vehicle ID (400..611)")
    a.add_argument("--x", type=float, help="X coordinate (default: garage center)")
    a.add_argument("--y", type=float, help="Y coordinate")
    a.add_argument("--z", type=float, help="Z coordinate")
    a.add_argument("--forzar", action="store_true")

    # REMOVE
    q = sub.add_parser("quitar", aliases=["remove"], help="empties a slot")
    q.add_argument("save")
    q.add_argument("--salida", required=True)
    q.add_argument("--garaje", type=int, required=True, choices=range(N_GARAJES),
                   metavar="N")
    q.add_argument("--plaza", type=int, required=True, choices=range(N_PLAZAS),
                   metavar="N")
    q.add_argument("--forzar", action="store_true")

    # CLEAN
    l = sub.add_parser("limpiar", aliases=["clean"], help="cleans slots in one or all garages")
    l.add_argument("save")
    l.add_argument("--salida", required=True)
    l.add_argument("--garaje", type=int, choices=range(N_GARAJES), metavar="N",
                   help="only that garage; default: all 20")
    l.add_argument("--forzar", action="store_true")

    # VEHICLES
    sub.add_parser("coches", aliases=["vehicles"], help="the table of vehicle IDs")

    args = ap.parse_args()

    if args.orden in ("ver", "see"):
        cmd_ver(args)
    elif args.orden in ("anadir", "add"):
        cmd_anadir(args)
    elif args.orden in ("quitar", "remove"):
        cmd_quitar(args)
    elif args.orden in ("limpiar", "clean"):
        cmd_limpiar(args)
    elif args.orden in ("coches", "vehicles"):
        cmd_coches(args)


if __name__ == "__main__":
    main()

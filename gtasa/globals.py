#!/usr/bin/env python3
"""
The script's global variables (the `main.scm`), which live in block 1.

This is the state that the game does NOT save in the stats: girlfriends, driving
school, and -- what brought this tool -- the gym's daily limit.

WHERE THEY START, THE ONLY TRICKY PART
---------------------------------------
Not at byte 0 of the block. Block 1 carries a signature (4) + size (4) and then a
counter at `+5`, which is what `platform_warnings` reads to distinguish mobile from
PC. The array starts at **+9**, and it is proven with the girlfriends, which are
confirmed in-game:

    girlfriends.py addresses progress at byte 1441 + 4n and the mask at 1629
    1441 - 9 = 1432 = 4 x 358        1629 - 9 = 1620 = 4 x 405

Both divide evenly, so `global[i]` lives at `block1 + 9 + 4i`. It is the same
system that `girlfriends.py` already uses, only there the byte offsets were written raw.

WHERE THEY END, EQUALLY IMPORTANT
-----------------------------------
Block 1 does NOT measure the same in all saves -- 61375 bytes in 100% saves,
61673 in a 34.8% one, 61971 in a 26.2% one -- but the counter at `+5` is
**49212 in all of them**. That counter is the size in bytes of the globals array:

    49212 / 4 = 12303 globals

What grows and shrinks is what goes AFTER: the running script threads. So from a
61375-byte block, only the first 12303 slots are globals; the ~3000 following are
thread state, which means neither the same between saves nor at the same position.
Comparing them is pure noise, and that is why they are cut off here.

That globals come FIRST (and therefore that the index means the same thing in two
different saves) is verified: the girlfriend check gives the same byte 1441 in saves
with three different block sizes, with Denise at 74 -- the value that `girlfriends.py`
documents as the original player's -- and Michelle going from 0 to 25 between 26.2%
and 34.8%. Real progression, same address.

THE COMMUNITY'S NUMBERING DOES NOT TRANSFER
-------------------------------------------
In the PC main.scm the community has identified the gym's daily limit:

    $5345 current day   $5346 current month   $5347 day limit   $5348 month limit
    $5349 state

Reading `global[5345..5349]` in a mobile save yields floats, not dates: **the mobile
is not the same build**. That was already known from another angle -- 49212 globals
vs 43808 on PC, which is the strong discriminator in `gtasa_editor.platform_warnings`.
The globals exist, but renumbered, and they must be found by differential, not by
number.

    python globals.py view SAVE.b --global 358
    python globals.py view SAVE.b --byte 1441
    python globals.py diff BEFORE.b AFTER.b
    python globals.py diff BEFORE.b AFTER.b --format date
    python globals.py inspect BEFORE.b LOCKED.b STAR.b --globals 39,42,1234-1240
"""

import argparse
import struct
import sys
from pathlib import Path

from .editor import (find_blocks, platform_warnings, calc_checksum,
                          stored_checksum, fix_checksum)

BLOQUE_SCRIPTS = 1
# Proven with the girlfriends, see above. If it ever stops working, the check is
# in `diff --control`: if the girlfriends don't fall where they should, trust nothing.
INICIO = 9

# THE GYM'S DAILY LIMIT. Found by differential on August 6 and CONFIRMED IN-GAME:
# the star save had 25/2 in the second pair and answered "You have done enough
# exercise for today" without ever letting you train; setting it to -1 unlocked it.
# Eight bytes.
#
# Two pairs (day, month). The first one is set WHEN USING the gym; the second one
# ONLY WHEN EXCEEDING IT, and it is the one that blocks:
#
#   save                              6729-6730   6731-6732   gym
#   GTASAsf5.b (before)               -1, -1      -1, -1     0 visits
#   GTASAsf6.b (with the message)       5, 1        5, 1     1 visit, blocked
#   partidas/originales/GTASAsf9.b              4, 5      -1, -1     2 visits, no message
#   partidas/originales/GTASAsf7_2921...        4, 5      -1, -1     2 visits, no message
#
# What remains UNKNOWN is why the star save did not expire it with 764 days of
# play time on top. That would require the game's clock, which has not been located.
# See PRUEBA-GIMNASIO.md.
GIMNASIO_USO = (6729, 6730)         # (day, month) of last use
GIMNASIO_LIMITE = (6731, 6732)      # (day, month) when the limit was reached
SIN_FECHA = -1                      # the "never" sentinel

# Byte offsets already confirmed in-game, to validate alignment without leaving home.
CONTROL = {
    1441: "girlfriend 0 (Denise) -- progress",
    1445: "girlfriend 1 (Michelle)",
    1449: "girlfriend 2 (Helena)",
    1453: "girlfriend 3 (Barbara)",
    1457: "girlfriend 4 (Katie)",
    1461: "girlfriend 5 (Millie)",
}


def carga(path):
    """Returns (data, block offset, list of globals as int32).

    Cuts at the DECLARED size of the array (the counter at `+5`), not at the end
    of the block: what remains are script threads, not globals. See the header.
    """
    data = Path(path).read_bytes()
    offs = find_blocks(data)
    ini, fin = offs[BLOQUE_SCRIPTS], offs[BLOQUE_SCRIPTS + 1]
    declarado = struct.unpack_from("<I", data, ini + 5)[0]
    n = declarado // 4
    if ini + INICIO + declarado > fin:
        raise ValueError(f"the counter says {declarado} bytes of globals but block "
                         f"1 only has {fin - ini - INICIO} available")
    g = [struct.unpack_from("<i", data, ini + INICIO + i * 4)[0] for i in range(n)]
    return data, ini, g


def como_float(v):
    return struct.unpack("<f", struct.pack("<i", v))[0]


def gimnasio(buf):
    """Returns ((day, month) of use, (day, month) of limit). `-1, -1` = no date."""
    data = bytes(buf)
    ini = find_blocks(data)[BLOQUE_SCRIPTS]
    v = [struct.unpack_from("<i", data, ini + INICIO + i * 4)[0]
         for i in GIMNASIO_USO + GIMNASIO_LIMITE]
    return (v[0], v[1]), (v[2], v[3])


def arreglar_gimnasio(buf):
    """Clears the daily limit date. Returns the previous date, or None.

    Only touches the SECOND pair. The first is the last visit and blocks nothing:
    clearing it too would be touching more than needed for the same effect.
    """
    antes = gimnasio(buf)[1]
    if antes == (SIN_FECHA, SIN_FECHA):
        return None
    ini = find_blocks(bytes(buf))[BLOQUE_SCRIPTS]
    for i in GIMNASIO_LIMITE:
        struct.pack_into("<i", buf, ini + INICIO + i * 4, SIN_FECHA)
    return antes


def fecha(par):
    return "no date" if par == (SIN_FECHA, SIN_FECHA) else f"{par[0]}/{par[1]}"


def indice(byte_off):
    if (byte_off - INICIO) % 4:
        raise ValueError(f"byte {byte_off} does not fall on a global "
                         f"(must be {INICIO} + 4k)")
    return (byte_off - INICIO) // 4


def ver(args):
    data, ini, g = carga(args.save)
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)
    offs = find_blocks(data)
    cola = offs[BLOQUE_SCRIPTS + 1] - offs[BLOQUE_SCRIPTS] - INICIO - len(g) * 4
    print(f"  {len(g)} globals in block 1, starting at byte {INICIO}")
    print(f"  ({cola} more bytes of script threads behind, which are not globals)\n")

    if args.control:
        print("  CONTROL -- girlfriends, confirmed in-game:")
        for byte_off, que in CONTROL.items():
            i = indice(byte_off)
            print(f"    byte {byte_off:>6} = global[{i:>5}]  {g[i]:>12}   {que}")
        return

    i = args.glob if args.glob is not None else indice(args.byte)
    if not 0 <= i < len(g):
        sys.exit(f"error: global[{i}] out of range (there are {len(g)})")
    for k in range(max(0, i - args.contexto), min(len(g), i + args.contexto + 1)):
        marca = "->" if k == i else "  "
        f = como_float(g[k])
        extra = f"  = {f:g} as float" if abs(f) > 1e-6 and abs(f) < 1e9 else ""
        print(f"  {marca} global[{k:>5}]  byte {INICIO + k*4:>6}  {g[k]:>12}{extra}")


def comparar(args):
    ga, gb = carga(args.antes)[2], carga(args.despues)[2]
    if len(ga) != len(gb):
        # Should not happen between saves of the same build: the globals array
        # measures 49212 bytes in all mobile saves seen, from 26% to 100%.
        print(f"  warning: {len(ga)} globals in BEFORE and {len(gb)} in AFTER; "
              f"they are different builds and the comparison is not very useful",
              file=sys.stderr)

    def dia(v): return 1 <= v <= 31
    def mes(v): return 1 <= v <= 12

    cambios = [(i, x, y) for i, (x, y) in enumerate(zip(ga, gb)) if x != y]
    print(f"  BEFORE  {args.antes}")
    print(f"  AFTER   {args.despues}")
    print(f"  {len(cambios)} globals changed out of {min(len(ga), len(gb))}\n")

    if args.forma == "fecha":
        # A daily limit is stored as (day, month): small values, in calendar range,
        # and next to another that is also one.
        cambios = [(i, x, y) for i, x, y in cambios
                   if (dia(x) or dia(y))
                   and i + 1 < min(len(ga), len(gb))
                   and (mes(gb[i + 1]) or mes(ga[i + 1]))]
        print(f"  filtered by date shape: {len(cambios)}\n")

    print(f"  {'global':>8} {'byte':>8} {'before':>12} {'after':>12}   neighbors (after)")
    for i, x, y in cambios[:args.max]:
        alrededor = " ".join(f"{gb[k]:>6}" for k in range(max(0, i - 1),
                                                          min(len(gb), i + 4)))
        print(f"  {i:>8} {INICIO + i*4:>8} {x:>12} {y:>12}   {alrededor}")
    if len(cambios) > args.max:
        print(f"  ... and {len(cambios) - args.max} more (increase --max)")


def mirar(args):
    """The SAME indices across several saves, side by side.

    This is the step that closes the loop: a flag is located by differential in a
    save where the mechanism works, and then that same flag is read in the broken
    save. It works because the index means the same thing in all of them -- see the
    header.
    """
    idx = []
    for trozo in args.globals.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if "-" in trozo.lstrip("-"):
            a, b = trozo.split("-")
            idx.extend(range(int(a), int(b) + 1))
        else:
            idx.append(int(trozo))

    tablas = []
    for p in args.saves:
        g = carga(p)[2]
        tablas.append((p, g))

    ancho = max(len(Path(p).name) for p, _ in tablas)
    print(f"  {'global':>8} {'byte':>8}   " +
          "  ".join(f"{Path(p).name:>{ancho}}" for p, _ in tablas))
    for i in idx:
        celdas = []
        for p, g in tablas:
            celdas.append(f"{g[i]:>{ancho}}" if 0 <= i < len(g) else f"{'--':>{ancho}}")
        print(f"  {i:>8} {INICIO + i*4:>8}   " + "  ".join(celdas))


def escribir(args):
    """Writes individual globals and produces a new file. Never overwrites the source."""
    salida = Path(args.salida)
    if salida.exists() and not args.forzar:
        sys.exit(f"error: {salida} already exists (use --force if you really want to overwrite)")

    data, ini, g = carga(args.save)
    if calc_checksum(data) != stored_checksum(data):
        sys.exit("error: the source has an invalid checksum; not editing")
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)

    buf = bytearray(data)
    hechos = []
    for par in args.poner.split(","):
        i_txt, v_txt = par.split("=")
        i, v = int(i_txt.strip()), int(v_txt.strip())
        if not 0 <= i < len(g):
            sys.exit(f"error: global[{i}] out of range (there are {len(g)})")
        antes = g[i]
        struct.pack_into("<i", buf, ini + INICIO + i * 4, v)
        hechos.append((i, antes, v))

    fix_checksum(buf)
    assert len(buf) == len(data), "the size cannot change"
    salida.write_bytes(buf)

    for i, antes, v in hechos:
        print(f"  global[{i:>5}]  byte {INICIO + i*4:>6}   {antes:>12}  ->  {v}")

    check = salida.read_bytes()
    assert calc_checksum(check) == stored_checksum(check), "checksum written incorrectly"
    find_blocks(check)
    print(f"\n  {len(hechos)} globals · {len(hechos)*4} bytes · wrote {salida}, "
          f"checksum OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)

    v = sub.add_parser("ver", aliases=["view"], help="reads a global and its neighbors")
    v.add_argument("save")
    v.add_argument("--global", dest="glob", type=int, help="global index")
    v.add_argument("--byte", type=int, help="byte offset within block 1")
    v.add_argument("--contexto", type=int, default=4)
    v.add_argument("--control", action="store_true",
                   help="reads girlfriends to check alignment is still good")

    c = sub.add_parser("comparar", aliases=["compare"], help="lists globals that change between two saves")
    c.add_argument("antes")
    c.add_argument("despues")
    c.add_argument("--forma", choices=["fecha"],
                   help="keep only those that look like (day, month)")
    c.add_argument("--max", type=int, default=60)

    m = sub.add_parser("mirar", aliases=["inspect"],
                       help="the same indices across several saves, in columns")
    m.add_argument("saves", nargs="+")
    m.add_argument("--globals", required=True, metavar="LIST",
                   help="comma-separated indices; ranges are accepted, "
                        "e.g. 39,42,1234-1240")

    w = sub.add_parser("escribir", aliases=["write"], help="writes individual globals to a new file")
    w.add_argument("save")
    w.add_argument("--poner", required=True, metavar="N=V[,N=V]",
                   help="index=value, comma-separated")
    w.add_argument("--salida", required=True)
    w.add_argument("--forzar", action="store_true")

    args = ap.parse_args()
    if args.orden in ("escribir", "write"):
        escribir(args)
        return
    if args.orden in ("ver", "view"):
        if not args.control and args.glob is None and args.byte is None:
            ap.error("provide --global N, --byte N, or --control")
        ver(args)
    elif args.orden in ("mirar", "inspect"):
        mirar(args)
    else:
        comparar(args)


if __name__ == "__main__":
    main()

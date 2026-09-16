#!/usr/bin/env python3
"""
Inspect and clean the garage slots in a GTA SA Mobile save.

    python garage.py <save> --inspect
    python garage.py <save> --clean --output GTASAsf3clean.b

HOW THIS WAS FOUND
-------------------
Pattern searching did not work: block 3 is 45% zeros and 14% bytes 0xff, so any
2-byte vehicle ID hits by chance (models NOT in the garage gave more matches than
those that were). It was located by DIFFERENTIAL: three saves from the same garage
with one vehicle difference between them, and the bytes that change are the data.
Anchored with field truth: Kart = model 571 and NRG-500 = 522, at (2506, -1693,
12.8), which is Grove Street.

    block 3, payload + 39 + k*1280, k = 0..3   ->4 slots

64-byte CStoredCar record:
    +0   float x, y, z      vehicle position (NaN if slot is empty)
    +12  u32                installed upgrade flags
    +16  u16                packed flags (proof flags in bits 0-4)
    +18  u16               model ID (571 Kart, 522 NRG-500, 0 in clean slot)
    +20  u16 x 15          upgrades / tuning, 0xFFFF = empty slot
    +50  u8 x 4            colors (primary, secondary, tertiary, quaternary)
    +54  u8                radio station
    +55  u8                extra 1
    +56  u8                extra 2
    +57  u8                bomb type
    +58  u8                paintjob (0xFF = none)
    +59  u8                nitro count
    +60  i8 x 3            orientation (X, Y, Z)
    +63  u8                padding, not written

WHAT --clean DOES
-----------------
Writes the empty slot pattern EXACTLY AS THE GAME DOES IT on all 4 slots: the one
that appears in slot 3 after emptying the garage. No values are invented.

CONFIRMED IN-GAME. CJ's garage from the 100% downloaded save had two slots with
model 524 and NaN position; the game counted them as full and did not allow putting
in a third car, and there was no way to clear them by playing because the car does
not exist anywhere in the world. Cleaning them fixed it. See PROJECT-MEMORY.md.

That said, --clean is a blunt instrument: it rewrites the four slots that don't
already have the pattern, ghost or not. It has since been learned that an empty
slot with the departing car's position is written by the game itself and does not
cause problems -- see `es_fantasma()`, which explains it with the saves that prove it.

For precision work, and for the other 19 garages in the game, use `houses.py clean`.
"""

import argparse
import math
import struct
import sys
from pathlib import Path

from .editor import calc_checksum, stored_checksum, find_blocks, platform_warnings
from .vehicles import etiqueta

BLOQUE_GARAJES = 3
PLAZA_BASE = 39
PLAZA_PASO = 1280
PLAZAS = 4
PLAZA_LEN = 24        # first 24 bytes of the 64-byte CStoredCar record

# Empty slot pattern observed in slot 3 of saves B and C, written by the game itself
# after emptying the garage. NaN position, mark 0, model 0.
PLAZA_LIBRE = bytes.fromhex("0000c0ff 0000c07f 0000c0ff 00 02040000 00 0000 ffffffff".replace(" ", ""))
assert len(PLAZA_LIBRE) == PLAZA_LEN


def plazas(data):
    offs = find_blocks(data)
    base = offs[BLOQUE_GARAJES] + 5
    for k in range(PLAZAS):
        yield k, base + PLAZA_BASE + k * PLAZA_PASO


def describir(data, off):
    """Returns (x, y, z, mark, model, state).

    Four states, and the difference between them matters a lot -- see below:

        occupied       real model and real position: there is a car
        GHOST          real model and NaN position: no car but slot counts
        FREE (clean)   the exact pattern the game writes
        free           free but without the pattern: virgin or with old position
    """
    x, y, z = struct.unpack_from("<fff", data, off)
    marca = data[off + 12]
    modelo = struct.unpack_from("<h", data, off + 18)[0]
    pos_valida = all(math.isfinite(v) for v in (x, y, z))
    if data[off:off + PLAZA_LEN] == PLAZA_LIBRE:
        estado = "LIBRE (limpia)"
    elif modelo == 0:
        estado = "libre"
    elif pos_valida:
        estado = "ocupada"
    else:
        estado = "FANTASMA"
    return x, y, z, marca, modelo, estado


def es_fantasma(data, off):
    """Slot taken by a car that does not exist. This is the only thing that needs cleaning.

    WHAT A GHOST IS AND WHAT IT IS NOT
    -----------------------------------
    It was once believed that any slot without the clean pattern carried "remnants"
    and those remnants threw off the count. The three saves from
    `partidas/archivo/04-analisis-garaje` disprove that, and they are field truth:
    in `C-garaje-vacio.b`, with the garage emptied BY DRIVING THE CARS OUT, the game
    leaves slot 2 like this:

        model 0,  mark 2,  position (2503.2, -1693.7, 13.1)   <- the departing car's

    So **model 0 with the old position is written by the game itself** and is a normal
    empty slot. And a slot zeroed to 64 bytes is not a remnant either: that is how
    the 77 unused slots of a freshly started save come.

    The ghost is something else, and it was confirmed in-game (see PROJECT-MEMORY.md):
    **real model with NaN position**. The card says "slot taken" and the car is not
    anywhere in the world, so it cannot be extracted by driving. The two that broke
    CJ's garage were model 524 with NaN.
    """
    x, y, z = struct.unpack_from("<fff", data, off)
    modelo = struct.unpack_from("<h", data, off + 18)[0]
    return modelo != 0 and not all(math.isfinite(v) for v in (x, y, z))


def inspeccionar(path):
    data = Path(path).read_bytes()
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)
    print(f"=== {path} ===")
    print(f"  checksum: {'OK' if calc_checksum(data) == stored_checksum(data) else 'INVALID'}")
    for k, off in plazas(data):
        x, y, z, marca, modelo, estado = describir(data, off)
        pos = f"({x:8.1f},{y:9.1f},{z:7.1f})" if all(math.isfinite(v) for v in (x, y, z)) else "        (NaN)        "
        print(f"  slot {k}  {etiqueta(modelo):<26} "
              f"mark={marca}  {pos}  {estado}")


def limpiar(path, salida, forzar):
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(path).read_bytes()
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
    for k, off in plazas(data):
        antes = describir(data, off)
        if buf[off:off + PLAZA_LEN] == PLAZA_LIBRE:
            print(f"  slot {k}: already clean, not touching")
            continue
        buf[off:off + PLAZA_LEN] = PLAZA_LIBRE
        tocadas += 1
        print(f"  slot {k}: {antes[5]:<18} {etiqueta(antes[4]):<26} -> FREE (clean)")

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    assert len(buf) == len(data)

    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)

    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {tocadas} slot(s) rewritten · {cambiados} bytes changed in total")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, 29 blocks OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("save")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--output")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.clean:
        if not args.output:
            ap.error("--clean requires --output")
        limpiar(args.save, args.output, args.force)
    else:
        inspeccionar(args.save)


if __name__ == "__main__":
    main()

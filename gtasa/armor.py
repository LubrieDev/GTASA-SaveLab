#!/usr/bin/env python3
"""
Manages vehicle proof flags in garage slot records.

The field at offset +16 in the 64-byte CStoredCar record is NOT armor — it is a
set of proof/immunity flags. The filename `armor.py` is retained for compatibility.

    python armor.py <save> --inspect
    python armor.py <save> --armor --output NEW.b
    python armor.py <save> --armor --slot 0 --output NEW.b
    python armor.py <save> --unarmor --output NEW.b
    python armor.py <save> --value 0x01 --output NEW.b   # test a single bit

Proof flags (bitfield at offset +16):
    0x01 = bulletproof (BP)
    0x02 = fireproof (FP)
    0x04 = explosion-proof (EP)
    0x08 = damage-proof / collision-proof (DP/CP)
    0x10 = melee-proof (MP)
    0x1f = all-proof (AP)

The mask 0x1F isolates the five proof bits. Bits 5-7 (0x20, 0x40, 0x80) are
unrelated to proof flags and are preserved by the mask. Their meaning is
unknown/unconfirmed.

HOW THIS WAS FOUND
-------------------
Through CONTROLLED DIFFERENTIAL, the only thing that worked in this project.
The player submitted two saves from the same playthrough, with the SAME vehicle
(Patriot, model 470) parked in the SAME slot of the Grove Street garage, and only
one playable difference: one had proof flags and the other did not.

    A = partidas/originales/GTASAsf6-subido-05ago-patriot470-BLINDADO.b    proofed
    B = partidas/originales/GTASAsf5-subido-05ago-patriot470-SIN-BLINDAR.b unproofed

In block 3 (garages) 8 bytes change. Six are the three coordinates of the car (it
moved a few centimeters when parked again), and two remain. One of them, at the end
of the record, is this:

    slot 0 record, +16:   0x1f   ->   0x00
                           ^^         ^^
Byte +16 goes from 0x1f to 0x00, and the other three stay the same.

And in the ENTIRE file -- the 195000 bytes, the 31 blocks -- that is the ONLY byte
that makes the transition 0x1f -> 0x00. The state is NOT duplicated anywhere else,
unlike what happened with girlfriends (globals + copy in stats).

Corroboration across the 39 archived saves in the project:

    Patriot 470 proofed          +16 = 0x1f
    Patriot 470 unproofed        +16 = 0x00
    Freeway 463 (old saves
    from the same player)        +16 = 0x1f
    Cheetah 415 (100% save
    downloaded, from another)    +16 = 0x00
    empty and clean slot         +16 = 0x00

Beware a survey trap: in old saves slot 1 also shows 0x1f and no model. It is not
an independent sample -- it is a BYTE-FOR-BYTE COPY of slot 0 (same position, same
value). Counting it as a separate case would have inflated the evidence.

WHAT 0x1f MEANS -- HALF CONFIRMED
----------------------------------
CONFIRMED BY DOUBLE SAVE:

1. On the SAME car, +16 goes from 0x00 to 0x1f when proofed. It comes from the
   differential and from the player saying which was which.
2. WRITING IT WORKS. A save was generated putting 0x1f on the Patriot 470 that was
   at 0x00, the player loaded it on their phone and shot it with the minigun -- the
   weapon that does the most damage in the game -- and the car did NOT get destroyed.

So it is not just a field the game reads: it is the one that controls it.

WHAT THE MINIGUN EXACTLY CONFIRMS, AND WHAT IT DOES NOT. The minigun fires bullets,
so what is proven is BULLET IMMUNITY. A car whose health is not lowered by bullets
also never explodes, so not even the final explosion proves anything about explosion
immunity. Fire, explosions, collisions and melee remain UNPROVEN.

HYPOTHESIS, NOT CONFIRMED: that it is a bit field with one proof per bit.
0x1f = 0b00011111 is exactly 5 bits, and GTA San Andreas has exactly 5 vehicle
proofs (bullets, fire, explosions, collisions, melee). It fits well, but which
bit is which has not been checked.

THE BYTE IS NOT ONLY PROOF FLAGS
--------------------------------
It was initially believed that +16 was the entire proof flags byte, because in the
first six samples it only took values 0x00 or 0x1f. A Voodoo (model 412) that the
player parked later disproved that: it is 0x40, unproofed.

    Patriot 470 proofed      0x1f    00011111
    Patriot 470 normal       0x00    00000000
    Freeway 463 (old)        0x1f    00011111
    Cheetah 415 (100% other) 0x00    00000000
    Voodoo  412 new          0x40    01000000   <-- bit 6, never seen before
    Model   534 (Aug 6)      0xc0    11000000   <-- bits 6 AND 7, also never seen

THE MASK, CONFIRMED IN-GAME
---------------------------
The 534 is the proof that using a mask was correct and not a theoretical precaution.
It arrived with `0xc0` -- the two high bits set -- and was proofed by writing `0xdf`,
i.e. turning on the bottom five while leaving the top two as they were. **Two bytes,
and the car appeared proofed in the game.**

If `0x1f` had been written raw, as the first version of this file did, those two bits
would have been erased without knowing what they were. It did not happen.

Two models now have proof flags written and confirmed by the player: Patriot 470 and
534. What remains UNPROVEN is which bit is which proof: the only one confirmed in
the field is bullets, with the minigun.

Bit 6 cannot be proof flags: the car does not have it. So the byte carries at least
one other thing from the vehicle itself, unidentified.

PRACTICAL CONSEQUENCE, and the reason this module uses masks: writing 0x1f raw would
ERASE bit 6 of the Voodoo. Proofing turns on MASK bits and leaves the others as they
were; unproofing turns them off and also does not touch the rest. The first version
of this file wrote the entire byte, and with a single car in hand it seemed correct.

To find out which bit is which, there is `--value`: turn on ONE bit, play the game,
and see what proof appears. One bit per save. Changing several at once is the
method error that has been repeated most often in this project.

    --value 0x01   ->  test bit 0
    --value 0x02   ->  test bit 1     ... and so on up to 0x10

The neighboring bytes +14 and +15 also change with the car (0x30/0x00 for the Patriot,
0x43/0x02 for the Voodoo, 0x20/0x00 for the Cheetah). It fits that they are the two
paint colors, but that has NOT been confirmed and is not touched here.

KNOWN LIMITS
------------
This only touches cars STORED IN THE GARAGE. A vehicle that was driving around in the
world when saving lives in block 2 (Pools) and has not been searched for there: in
this differential the car was parked in both saves.
"""

import argparse
import struct
import sys
from pathlib import Path

from .editor import calc_checksum, stored_checksum, find_blocks, platform_warnings
from .garage import plazas, describir, PLAZA_LIBRE, PLAZA_LEN
from .vehicles import etiqueta

# The proof flags byte within the 64-byte CStoredCar record. It falls within what
# garage.py had documented as "+13 unknown dword": it is the low byte of the
# packed flags field at offset +16.
OFF_BLINDAJE = 16

MASCARA = 0x1F      # the five proof bits (BP/FP/EP/DP/MP)
BLINDADO = 0x1F     # all five set, as the game writes them
NORMAL = 0x00

# Names of GTA SA's five vehicle proofs, in the CANONICAL GAME ORDER.
# That bit n is proof n is THE HYPOTHESIS, not a fact: see the docstring.
INMUNIDADES = ["bullets", "fire", "explosions", "collisions", "melee"]


def leer(data, off):
    """The complete byte of the slot starting at `off`. Note: not just armor."""
    return data[off + OFF_BLINDAJE]


def aplicar(buf, off, valor):
    """Turns on the MASK bits requested by `valor` and respects all others.

    The bits outside the MASK belong to the car and we don't know what they are
    (bit 6 of the Voodoo). Overwriting them would be writing blindly, which is
    what this project does not do.
    """
    antes = buf[off + OFF_BLINDAJE]
    ahora = (antes & ~MASCARA) | (valor & MASCARA)
    buf[off + OFF_BLINDAJE] = ahora
    return antes, ahora


def describir_blindaje(valor):
    bajos = valor & MASCARA
    altos = valor & ~MASCARA
    if bajos == BLINDADO:
        etiqueta = "ARMORED"
    elif bajos == 0:
        etiqueta = "normal"
    else:
        bits = ", ".join(INMUNIDADES[i] for i in range(5) if bajos & (1 << i))
        etiqueta = f"partial ({bits})  <-- hypothesis"
    resto = f" [+0x{altos:02x} unrelated to proof flags]" if altos else ""
    return f"{etiqueta} (0x{valor:02x}){resto}"


def inspeccionar(path):
    data = Path(path).read_bytes()
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)
    print(f"=== {path} ===")
    for k, off in plazas(data):
        x, y, z, marca, modelo, estado = describir(data, off)
        print(f"  slot {k}  {etiqueta(modelo):<26} {estado:<16} "
              f"proofs {describir_blindaje(leer(data, off))}")


def escribir(path, valor, plaza, salida, forzar):
    origen = Path(path)
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = origen.read_bytes()
    avisos = platform_warnings(data)
    if avisos and not forzar:
        for w in avisos:
            print(f"  warning: {w}", file=sys.stderr)
        sys.exit("error: the source does not look like a mobile save (use --force)")
    if calc_checksum(data) != stored_checksum(data):
        sys.exit(f"error: {origen} has an invalid checksum before editing")

    buf = bytearray(data)
    cambios = []
    for k, off in plazas(buf):
        if plaza is not None and k != plaza:
            continue
        # An empty slot has no car to proof. Writing there would leave a flag hanging
        # in a record without a vehicle, which is exactly the kind of garbage that
        # broke the garage the previous time.
        if buf[off:off + PLAZA_LEN] == PLAZA_LIBRE:
            print(f"  slot {k}: empty and clean, not touching")
            continue
        modelo = struct.unpack_from("<h", buf, off + 18)[0]
        if modelo in (0, 524):
            print(f"  slot {k}: no car ({etiqueta(modelo)}), not touching")
            continue
        antes, ahora = aplicar(buf, off, valor)
        if antes == ahora:
            print(f"  slot {k}: already at 0x{antes:02x}")
            continue
        cambios.append((k, etiqueta(modelo), antes, ahora))

    if not cambios:
        print("  nothing to change; nothing written.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    assert len(buf) == len(data), "the size must not change"
    destino.write_bytes(buf)

    # Re-read from disk and re-validate as if it were an external file.
    check = destino.read_bytes()
    assert len(check) == len(data)
    assert calc_checksum(check) == stored_checksum(check), "checksum written incorrectly"
    find_blocks(check)
    assert not platform_warnings(check), platform_warnings(check)

    for k, coche, antes, ahora in cambios:
        print(f"  slot {k}  {coche:<26} 0x{antes:02x} -> 0x{ahora:02x}"
              f"   ({describir_blindaje(ahora)})")
    n = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {len(cambios)} slots · {n} bytes · wrote {destino}, checksum OK")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("save")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--armor", action="store_true", help="set proof flags to 0x1f (all-proof)")
    ap.add_argument("--unarmor", action="store_true", help="set proof flags to 0x00")
    ap.add_argument("--value", help="raw value, e.g. 0x01 to test a single bit")
    ap.add_argument("--slot", type=int, choices=range(4),
                    help="only that slot (default: all occupied)")
    ap.add_argument("--output")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.inspect or not (args.armor or args.unarmor or args.value):
        inspeccionar(args.save)
        return

    if sum(bool(x) for x in (args.armor, args.unarmor, args.value)) > 1:
        ap.error("--armor, --unarmor and --value are mutually exclusive")
    if not args.output:
        ap.error("--output is required: the original is never modified")

    if args.value:
        valor = int(args.value, 0)
        if not 0 <= valor <= 0xFF:
            ap.error("--value must fit in a byte")
    else:
        valor = BLINDADO if args.armor else NORMAL

    print(f"=== {args.save} ===")
    escribir(args.save, valor, args.slot, args.output, args.force)


if __name__ == "__main__":
    main()

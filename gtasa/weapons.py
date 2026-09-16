#!/usr/bin/env python3
"""
Inspect and edit weapons in a GTA SA Mobile save.

    python weapons.py <save> --inspect
    python weapons.py <save> --ammo minigun 30000 --output GTASAsf3.b

HOW THIS WAS FOUND
-------------------
Through field truth, not pattern searching. The player obtained the minigun, shot
until leaving it at an ugly number (487, which does NOT appear ONCE in the file) and
saved. Searching for 487 gave ONE single location, in block 2 (Pools):

    offset 62053: 38     <- minigun ID
    offset 62061: 487    <- the bullets
    offset 62065: 500

A round number would not have worked: 500 appears 100 times in the same file.

From there, moving forward and backward by 28 bytes, 13 consecutive records with
valid weapon IDs appear -- and the 13 slots match those of GTA SA (melee, pistols,
shotguns, submachine, assault, rifles, heavy, thrown, special, detonator). That
does not happen by chance.

    weapon table: 13 records of 28 bytes
        +0   int32   weapon ID (0 = empty slot)
        +4   int32   always 0 in what was observed
        +8   int32   bullets IN THE MAGAZINE (cap: the weapon's magazine size)
        +12  int32   TOTAL AMMO  <- this is the one to write
        +16  int32   timestamp: only has value in recently used weapons
        +20  int32   0 in everything observed
        +24  int32   0 in everything observed

WHICH FIELD IS THE AMMO: +12, NOT +8
-------------------------------------
For hours, +8 was written believing it was the ammo, and the game undid it. When
instantiating the weapon -- when equipping, or when switching weapons and returning --
it ALWAYS left it at the exact size of its magazine:

    pistol 34 (17x2)   sawed-off 4 (2x2)   MP5 30   M4 50
    sniper 1     minigun 500         molotov 1   extinguisher 500

Eight out of eight, with magazines different from each other, and the two doubled
exactly in the two weapons where the player is "Professional Killer" (dual wield).
It was not a cap that truncated: +8 IS the magazine and cannot exceed its size.

    +8   bullets in the magazine
    +12  TOTAL AMMO
    HUD: (+12 - +8) on the left, (+8) on the right  =  reserve and magazine

Three things delayed the diagnosis, and all three seemed confirmations:

1. Setting the minigun to 30000 in +8 showed "-29500-30000" on loading and seemed
   like a success. It was the opposite symptom: the HUD reading an impossible magazine.
2. It was confirmed that +12 does not change when firing and was labeled "constant,
   DO NOT TOUCH". It was true and irrelevant: it does not change when firing because
   what goes down is the magazine.
3. When writing 100000, four weapons kept the value and four reverted. A duplicate
   table that did not exist was sought. The player had only equipped four weapons;
   the others were never instantiated.

The data that resolved it was in the player's hands from the beginning: they said
the AK's ammo was not shown on screen because it exceeded 10000. The +12 values in
their save were 99971 in the sawed-off, 98590 in the MP5, 58933 in the M4 -- their
actual reserves.

Confirmed in-game: with +12 = 99999 the HUD does not show a number, which is exactly
what GTA SA does above 9999.

HEALTH AND ARMOR
----------------
They are in the same ped record, just BEFORE the weapons table: -8 for health and -4
for armor, both floats. Armor is 150 in the player's current saves -- same as their
transcription from the screen -- and 0 in older ones, when they did not yet wear a
vest.

The table is NOT at a fixed offset: block 2 grows with world entities (it has been
seen going from 5217 to 74765 bytes). It is located in each file by searching for 13
consecutive valid records.
"""

import argparse
import struct
import sys
from pathlib import Path

from .editor import calc_checksum, stored_checksum, find_blocks, platform_warnings

BLOQUE_POOLS = 2

# Health and armor live in the same ped record, just BEFORE the weapons table.
# Confirmed with field truth: armor is 150 in the player's current saves -- the same
# as their transcription from the statistics screen -- and 0 in older ones, when they
# did not yet wear a vest.
#
# Health comes out as 220 in ALL SEVEN analyzed saves, including the old ones. The most
# likely explanation is that saving at a safe house heals you, so a save with damage
# was never seen. That is why it is unknown whether the field is "current health" or
# "max health".
OFF_VIDA = -8
OFF_BLINDAJE = -4
RANURAS = 13
PASO = 28
OFF_ID, OFF_CARGADOR, OFF_TOTAL = 0, 8, 12

ARMAS = {
    0: "(empty)", 1: "brass knuckles", 2: "club", 3: "golf club", 4: "knife", 5: "bat",
    6: "shovel", 7: "pool cue", 8: "katana", 9: "chainsaw", 10: "dildo",
    11: "dildo 2", 12: "vibrator", 13: "vibrator 2", 14: "flowers", 15: "cane",
    16: "grenade", 17: "tear gas", 18: "molotov cocktail", 22: "pistol",
    23: "silenced pistol", 24: "Desert Eagle", 25: "shotgun", 26: "sawed-off",
    27: "combat shotgun", 28: "Micro Uzi", 29: "MP5", 30: "AK-47", 31: "M4",
    32: "Tec-9", 33: "rifle", 34: "sniper rifle", 35: "RPG",
    36: "heat-seeking RPG", 37: "flamethrower", 38: "minigun", 39: "satchel charges",
    40: "detonator", 41: "spray can", 42: "extinguisher", 43: "camera",
    44: "night vision goggles", 45: "thermal goggles", 46: "parachute",
}
POR_NOMBRE = {v.lower(): k for k, v in ARMAS.items() if k}

# In GTA SA each weapon has a fixed slot and each slot holds ONE at a time: equipping
# the sticky bomb replaces the molotov cocktails, because they share slot 8.
RANURA_DE = {
    0: 0, 1: 0,
    2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1,
    22: 2, 23: 2, 24: 2,
    25: 3, 26: 3, 27: 3,
    28: 4, 29: 4, 32: 4,
    30: 5, 31: 5,
    33: 6, 34: 6,
    35: 7, 36: 7, 37: 7, 38: 7,
    16: 8, 17: 8, 18: 8, 39: 8,
    41: 9, 42: 9, 43: 9,
    10: 10, 11: 10, 12: 10, 13: 10, 14: 10, 15: 10,
    44: 11, 45: 11, 46: 11,
    40: 12,
}

# No ammo: melee, equipment, and the detonator.
SIN_MUNICION = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                40, 43, 44, 45, 46}


def localizar_tabla(data):
    """Offset of the first record. Requires all 13 slots to be valid IDs."""
    offs = find_blocks(data)
    ini, fin = offs[BLOQUE_POOLS] + 5, offs[BLOQUE_POOLS + 1]
    candidatos = []
    for off in range(ini, fin - RANURAS * PASO, 4):
        ids = [struct.unpack_from("<i", data, off + k * PASO)[0] for k in range(RANURAS)]
        if all(v in ARMAS for v in ids) and sum(1 for v in ids if v) >= 5:
            candidatos.append((off, ids))
    if not candidatos:
        raise ValueError("weapons table not found in block 2")
    # If there were multiple, keep the one that starts first: the following ones are the
    # same table shifted by one slot.
    return candidatos[0][0]


def leer(data, off):
    return [struct.unpack_from("<i", data, off + k * 4)[0] for k in range(4)]


def inspeccionar(path):
    data = Path(path).read_bytes()
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)
    base = localizar_tabla(data)
    print(f"=== {path} ===")
    print(f"  checksum: {'OK' if calc_checksum(data) == stored_checksum(data) else 'INVALID'}")
    print(f"  weapons table at offset {base} (block {BLOQUE_POOLS})\n")
    print("  slot  weapon                       ammo          +12")
    for n in range(RANURAS):
        idw, _, mun, ref = leer(data, base + n * PASO)
        if not idw:
            print(f"    {n:<6}  {'(empty)':<26}")
            continue
        m = "-" if idw in SIN_MUNICION else f"{mun}"
        print(f"    {n:<6}  {ARMAS[idw]:<26} {m:>8} {ref:>9}")


def municion(path, arma, cantidad, salida, forzar):
    clave = arma.lower()
    if clave not in POR_NOMBRE:
        sys.exit(f"error: I don't know '{arma}'.\n"
                 f"valid: {', '.join(sorted(POR_NOMBRE))}")
    idw = POR_NOMBRE[clave]
    if idw in SIN_MUNICION:
        sys.exit(f"error: {ARMAS[idw]} does not use ammo")
    if not 0 <= cantidad <= 2_147_483_647:
        sys.exit("error: the amount must fit in a signed int32")

    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(path).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    base = localizar_tabla(data)
    buf = bytearray(data)
    tocadas = []
    for n in range(RANURAS):
        off = base + n * PASO
        if struct.unpack_from("<i", buf, off + OFF_ID)[0] != idw:
            continue
        antes_m = struct.unpack_from("<i", buf, off + OFF_CARGADOR)[0]
        # ONLY the ammo. +12 is a constant for the weapon type: see the header.
        struct.pack_into("<i", buf, off + OFF_CARGADOR, cantidad)
        tocadas.append((n, antes_m))

    if not tocadas:
        sys.exit(f"error: you don't have {ARMAS[idw]} equipped. Get one first: the script "
                 f"changes the ammo of a weapon you already have, it does not add one.")

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    assert len(buf) == len(data)
    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    localizar_tabla(check)

    for n, am in tocadas:
        print(f"  slot {n} ({ARMAS[idw]}): ammo {am}  ->  {cantidad}")
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed · wrote {destino}, checksum OK")


def municion_todas(path, cantidad, salida, forzar, igualar=False):
    """The same amount for all equipped weapons that use ammo.

    With igualar=True it also writes +12 with the same value. This is a HYPOTHESIS:
    the HUD calculates the left number as +12 minus +8, confirmed in three independent
    observations (pistol 435-34=401, minigun 500-487=13, and 500-30000=-29500 after
    editing). By making both equal, the HUD should display "0-<amount>", which is the
    state the game itself writes when picking up a weapon.

    What is NOT known is what +12 means. If it were "total ammo obtained", +12 minus
    +8 would be the spent ammo, and the sum of all weapons would give 262507 -- but
    the statistics screen says 88587 bullets fired. It does not add up. We know what
    the HUD calculates, not what the field is.
    """
    if not 0 <= cantidad <= 2_147_483_647:
        sys.exit("error: the amount must fit in a signed int32")
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(path).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    base = localizar_tabla(data)
    buf = bytearray(data)
    hechos = []
    for n in range(RANURAS):
        off = base + n * PASO
        idw = struct.unpack_from("<i", buf, off + OFF_ID)[0]
        if not idw or idw in SIN_MUNICION:
            continue
        antes = struct.unpack_from("<i", buf, off + OFF_CARGADOR)[0]
        antes_r = struct.unpack_from("<i", buf, off + OFF_TOTAL)[0]
        if antes == cantidad and not (igualar and antes_r != cantidad):
            continue
        struct.pack_into("<i", buf, off + OFF_CARGADOR, cantidad)
        if igualar:
            struct.pack_into("<i", buf, off + OFF_TOTAL, cantidad)
        hechos.append((n, ARMAS[idw], antes, antes_r))

    if not hechos:
        print("  nothing to change.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    assert len(buf) == len(data)
    destino.write_bytes(buf)

    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    localizar_tabla(check)

    for n, nombre, antes, antes_r in hechos:
        extra = f"   +12 {antes_r} -> {cantidad}" if igualar else f"   HUD: {antes_r - cantidad}-{cantidad}"
        print(f"  slot {n:<3} {nombre:<24} {antes:>7}  ->  {cantidad}{extra}")
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {len(hechos)} weapons · {cambiados} bytes changed · wrote {destino}, checksum OK")


def total_todas(path, cantidad, salida, forzar):
    """Writes TOTAL AMMO (+12) for all equipped weapons.

    WHY +12 AND NOT +8. For a long time +8 was written believing it was the ammo,
    and the game undid it: when instantiating the weapon it ALWAYS left it at the exact
    size of its magazine -- pistol 34 (17x2 with dual wield), sawed-off 4 (2x2), MP5
    30, M4 50, sniper 1, minigun 500, molotov 1, extinguisher 500. Eight out of eight,
    with magazines different from each other. That is not a cap that truncates: +8 IS
    the magazine and cannot exceed its size.

    The real ammo is in +12. It matches what the player saw on screen: they said the
    AK was not shown because it exceeded 10000 bullets, and the +12 values in their
    save are 99971 in the sawed-off, 98590 in the MP5, 58933 in the M4.

    The HUD displays (+12 - +8) on the left and (+8) on the right: reserve and magazine.
    """
    if not 0 <= cantidad <= 2_147_483_647:
        sys.exit("error: the amount must fit in a signed int32")
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(path).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    base = localizar_tabla(data)
    buf = bytearray(data)
    hechos = []
    for n in range(RANURAS):
        off = base + n * PASO
        idw = struct.unpack_from("<i", buf, off + OFF_ID)[0]
        if not idw or idw in SIN_MUNICION:
            continue
        antes = struct.unpack_from("<i", buf, off + OFF_TOTAL)[0]
        cargador = struct.unpack_from("<i", buf, off + OFF_CARGADOR)[0]
        if antes == cantidad:
            continue
        # The total cannot be less than what is already in the magazine.
        valor = max(cantidad, cargador)
        struct.pack_into("<i", buf, off + OFF_TOTAL, valor)
        hechos.append((n, ARMAS[idw], antes, valor, cargador))

    if not hechos:
        print("  nothing to change.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    localizar_tabla(check)

    for n, nombre, antes, valor, carg in hechos:
        print(f"  slot {n:<3} {nombre:<24} total {antes:>7} -> {valor:<7} "
              f"HUD: {valor - carg}-{carg}")
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {len(hechos)} weapons · {cambiados} bytes changed · "
          f"wrote {destino}, checksum OK")


def jugador(path, vida, blindaje, salida, forzar):
    """Changes health and/or armor. They are floats in the ped, just before the weapons."""
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --force)")

    data = Path(path).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    base = localizar_tabla(data)
    buf = bytearray(data)
    hechos = []
    for valor, off, etiqueta in ((vida, OFF_VIDA, "health"),
                                 (blindaje, OFF_BLINDAJE, "armor")):
        if valor is None:
            continue
        antes = struct.unpack_from("<f", buf, base + off)[0]
        struct.pack_into("<f", buf, base + off, float(valor))
        hechos.append((etiqueta, antes, float(valor)))

    if not hechos:
        print("  nothing to change.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    localizar_tabla(check)

    for etiqueta, antes, ahora in hechos:
        print(f"  {etiqueta:<10} {antes:>8.1f}  ->  {ahora:.1f}")
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed · wrote {destino}, checksum OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("save")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--ammo", nargs=2, metavar=("WEAPON", "AMOUNT"),
                    help="e.g. --ammo minigun 30000")
    ap.add_argument("--ammo-all", metavar="AMOUNT", dest="todas", type=int,
                    help="the same amount for all weapons that use ammo")
    ap.add_argument("--health", type=float)
    ap.add_argument("--armor", type=float)
    ap.add_argument("--total-all", metavar="AMOUNT", dest="total", type=int,
                    help="TOTAL AMMO (+12) for all weapons. This is the correct field")
    ap.add_argument("--equal-total", action="store_true", dest="igualar",
                    help="also writes +12 with the same amount, so the HUD "
                         "displays 0-N instead of a negative. This is a hypothesis: see the code")
    ap.add_argument("--output")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.health is not None or args.armor is not None:
        if not args.output:
            ap.error("--health/--armor require --output")
        jugador(args.save, args.health, args.armor, args.output, args.force)
    elif args.total is not None:
        if not args.output:
            ap.error("--total-all requires --output")
        total_todas(args.save, args.total, args.output, args.force)
    elif args.todas is not None:
        if not args.output:
            ap.error("--ammo-all requires --output")
        municion_todas(args.save, args.todas, args.output, args.force, args.igualar)
    elif args.ammo:
        if not args.output:
            ap.error("--ammo requires --output")
        try:
            cantidad = int(args.ammo[1])
        except ValueError:
            ap.error("the amount must be an integer")
        municion(args.save, args.ammo[0], cantidad, args.output, args.force)
    else:
        inspeccionar(args.save)


if __name__ == "__main__":
    main()

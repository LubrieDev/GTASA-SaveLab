"""
WEAPONS
-------
Gives weapons you don't have and/or sets ammo.

  GIVE = [(name, ammo), ...]   gives or replaces the weapon in its slot.
                                ONE SLOT, ONE WEAPON: overwrites whatever was there.
                                Weapons without ammo (melee, goggles...) receive
                                clip 0 and total 1 (the HUD shows them).
  AMMO_ALL = N                 writes the TOTAL (+12) for all weapons you carry.
                                Verified in-game: +12 is TOTAL and the clip (+8)
                                is NOT ammo.

Valid names: gtasa/weapons.py WEAPONS (e.g. "minigun", "satchel charges").

    python scripts/04_weapons.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import weapons as A

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_weapons.b"
GIVE = [("pistol", 999999), ("thermal goggles", None)]
AMMO_ALL = None   # int, or None to skip
FORCE = False
# ================================================

data = _core.load(SAVE)
base = A.localizar_tabla(data)
buf = bytearray(data)

for name, amount in GIVE:
    key = name.lower().strip()
    if key not in A.POR_NOMBRE:
        sys.exit(f"error: unknown weapon '{name}'.\n"
                 f"  valid: {', '.join(sorted(A.POR_NOMBRE))}")
    idw = A.POR_NOMBRE[key]
    slot = A.RANURA_DE.get(idw)
    if slot is None:
        sys.exit(f"error: I don't know which slot {A.ARMAS[idw]} goes in")
    off = base + slot * A.PASO

    before_id = struct.unpack_from("<i", buf, off + A.OFF_ID)[0]
    if before_id and before_id != idw:
        print(f"  warning: slot {slot} had {A.ARMAS[before_id]}; "
              f"{A.ARMAS[idw]} replaces it", file=sys.stderr)
    struct.pack_into("<i", buf, off + A.OFF_ID, idw)
    if idw in A.SIN_MUNICION:
        struct.pack_into("<i", buf, off + A.OFF_CARGADOR, 0)
        struct.pack_into("<i", buf, off + A.OFF_TOTAL, 1)
        print(f"  slot {slot:<3} {A.ARMAS[idw]:<24} (no ammo)")
    else:
        total = amount if amount is not None else 9999
        struct.pack_into("<i", buf, off + A.OFF_CARGADOR, 1)
        struct.pack_into("<i", buf, off + A.OFF_TOTAL, total)
        print(f"  slot {slot:<3} {A.ARMAS[idw]:<24} ammo {total:,}")

if AMMO_ALL is not None:
    if not 0 <= AMMO_ALL <= 2_147_483_647:
        sys.exit("error: AMMO_ALL must fit in a signed int32")
    for n in range(A.RANURAS):
        off = base + n * A.PASO
        idw = struct.unpack_from("<i", buf, off + A.OFF_ID)[0]
        if not idw or idw in A.SIN_MUNICION:
            continue
        clip = struct.unpack_from("<i", buf, off + A.OFF_CARGADOR)[0]
        before = struct.unpack_from("<i", buf, off + A.OFF_TOTAL)[0]
        value = max(AMMO_ALL, clip)
        if value != before:
            struct.pack_into("<i", buf, off + A.OFF_TOTAL, value)
            print(f"  total {A.ARMAS[idw]:<24} {before:>7}  ->  {value}"
                  f"   [HUD: {value - clip}-{clip}]")

if not GIVE and AMMO_ALL is None:
    sys.exit("error: set GIVE or AMMO_ALL")

check = _core.save(buf, OUTPUT, data, FORCE)
A.localizar_tabla(check)

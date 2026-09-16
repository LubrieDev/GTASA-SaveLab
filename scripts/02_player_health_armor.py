"""
PLAYER HEALTH AND ARMOR
-----------------------
Changes the player's current health and armor. They live in the ped record,
just before the weapon table (block 2), and are located via that table: they
are not fixed offsets.

Configure HEALTH and/or ARMOR (float; None = don't touch) and run:

    python scripts/02_player_health_armor.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import weapons as A

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_health.b"
HEALTH = 220.0            # current health (saving at home fills to max)
ARMOR = 150.0             # armor; 0 = no vest
FORCE = False
# ================================================

data = _core.load(SAVE)
base = A.localizar_tabla(data)
buf = bytearray(data)

changes = []
for value, off, label in ((HEALTH, A.OFF_VIDA, "health"),
                           (ARMOR, A.OFF_BLINDAJE, "armor")):
    if value is None:
        continue
    before = struct.unpack_from("<f", buf, base + off)[0]
    struct.pack_into("<f", buf, base + off, float(value))
    changes.append((label, before, float(value)))

if not changes:
    sys.exit("error: set at least HEALTH or ARMOR (None = don't touch)")

for label, before, now in changes:
    print(f"  {label:<10} {before:>8.1f}  ->  {now:.1f}")

check = _core.save(buf, OUTPUT, data, FORCE)
A.localizar_tabla(check)  # validate that block 2 is still recognizable

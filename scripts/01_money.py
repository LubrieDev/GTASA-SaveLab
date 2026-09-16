"""
MONEY
-----
Sets the amount of money for CJ and the HUD display. They must be set together:
if only one is changed, the screen and the save interior become out of sync.

Configure MONEY and run from the project root:

    python scripts/01_money.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import editor as E

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_money.b"
MONEY = 999999999      # in units: 1 = $1, max 2^31-1
FORCE = False          # True = overwrite OUTPUT if it already exists
# ================================================

if not 0 <= MONEY <= 2_147_483_647:
    sys.exit("error: money must fit in a signed int32")

data = _core.load(SAVE)
buf = bytearray(data)
offs = E.find_blocks(data)
pinfo = offs[E.PLAYERINFO_BLOCK]

for off, label in ((E.OFF_MONEY, "money"), (E.OFF_DISPLAY_MONEY, "money (HUD)")):
    before = struct.unpack_from("<i", buf, pinfo + off)[0]
    struct.pack_into("<i", buf, pinfo + off, MONEY)
    print(f"  {label:<16} {before:>12,}  ->  {MONEY:,}")

_core.save(buf, OUTPUT, data, FORCE)

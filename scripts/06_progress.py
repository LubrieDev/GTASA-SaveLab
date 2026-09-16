"""
GAME PROGRESS
-------------
Moves the progress bar in the save list. PROGRESS_MADE is calculated
from the total (float[1]) so the percentage is exact:

    PROGRESS_PCT = 100  ->  made = total   (100%)
    PROGRESS_PCT = 50   ->  made = total/2 (50%)

Does not touch any mission counter: only the displayed percentage.

    python scripts/06_progress.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import editor as E

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_progress.b"
PROGRESS_PCT = 100.0    # 0-100
FORCE = False
# ================================================

if not 0 <= PROGRESS_PCT <= 100:
    sys.exit("error: PROGRESS_PCT is a percentage 0-100")

data = _core.load(SAVE)
buf = bytearray(data)
base_stats = E.find_blocks(data)[E.STATS_BLOCK] + 5

done = struct.unpack_from("<f", buf, base_stats + 0)[0]
total = struct.unpack_from("<f", buf, base_stats + 4)[0]
target = total * PROGRESS_PCT / 100.0

struct.pack_into("<f", buf, base_stats + 0, target)
print(f"  PROGRESS_MADE  {done:g}  ->  {target:g}   "
      f"({PROGRESS_PCT:g}% of {total:g})")

_core.save(buf, OUTPUT, data, FORCE)

"""
PLAYER STATS
------------
Maxes out or sets the body stats from block 16 (Stats).

Options, one or more at a time:
  MAX_OUT = True      -> stamina, muscle, max health, sex appeal, driving skill,
                         respect and the 11 weapon skills to 1000. Fat goes to 0
                         (maxing fat is counterproductive, it goes to 0).
  FAT_PCT / MUSCLE_PCT -> percentage shown by the game (0-100). Written in
                         BOTH copies (stats + wardrobe end) so the screen and
                         CJ's body don't go out of sync.

NOTE: only identified and confirmed fields are touched. float[65..67] are NOT
touched (they are not flying/bikes/bike, see gtasa/editor.py), nor is RESPECT
maxed by shortcut when we don't know the screen formula: the stored value is
written.

    python scripts/03_player_stats.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import editor as E
from gtasa import wardrobe as R

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_stats.b"
MAX_OUT = True           # max the bars listed in gtasa.editor.MAXABLE
FAT_PCT = None           # 0-100, or None to skip
MUSCLE_PCT = None        # 0-100, or None to skip
FORCE = False
# ================================================

data = _core.load(SAVE)
buf = bytearray(data)

# fat/muscle ALWAYS go through sincroniza_cuerpo (two copies), and first:
# it is the anchor used to locate the wardrobe, it cannot be thrown off.
fat = 0.0 if MAX_OUT else None
muscle = None
if FAT_PCT is not None:
    if not 0 <= FAT_PCT <= 100:
        sys.exit("error: FAT_PCT is a percentage 0-100")
    fat = FAT_PCT * 10.0
if MUSCLE_PCT is not None:
    if not 0 <= MUSCLE_PCT <= 100:
        sys.exit("error: MUSCLE_PCT is a percentage 0-100")
    muscle = MUSCLE_PCT * 10.0

if fat is not None or muscle is not None:
    for name, idx, before, now in R.sincroniza_cuerpo(buf, fat, muscle):
        print(f"  [{idx:2d}] {E.FLOAT_STATS[idx]:<22} {before:9.2f} ({before/10:.0f}%)  "
              f"->  {now:.2f} ({now/10:.0f}%)  [body + stats]")

if MAX_OUT:
    base_stats = E.find_blocks(data)[E.STATS_BLOCK] + 5
    for idx in E.MAXABLE:
        off = base_stats + idx * 4
        before = struct.unpack_from("<f", buf, off)[0]
        if abs(before - 1000.0) <= 0.01:
            continue
        struct.pack_into("<f", buf, off, 1000.0)
        print(f"  [{idx:2d}] {E.FLOAT_STATS[idx]:<22} {before:9.2f}  ->  1000.00")

if not fat and not muscle and not MAX_OUT:
    sys.exit("error: enable MAX_OUT or set FAT_PCT/MUSCLE_PCT")

check = _core.save(buf, OUTPUT, data, FORCE)
R.localiza(check)  # the wardrobe anchor is still intact

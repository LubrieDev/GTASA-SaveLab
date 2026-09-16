"""
GIRLFRIENDS
-----------
Girlfriend state lives in THREE places (mask in global 1629, progress
in 1441+4n and the copy in block 16, which is what the list shows). All
three must be touched together, as gtasa/girlfriends.py does:

  RECOVER = ["denise", ...]   recovers lost girlfriends: mask bit + progress +
                               stats. Valid names are the 6: denise, michelle,
                               helena, barbara, katie, millie.
  PROGRESS_PCT = N            sets progress (0-100) for ALL girlfriends you have.
                               Does not activate the bit for ones you don't have.

DANGER: do NOT recalculate int[146] (GIRLFRIEND_COUNT): it is a playthrough
counter, the game increments it itself. Touching it here would be wrong.

    python scripts/05_girlfriends.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import editor as E
from gtasa import girlfriends as N

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_girlfriends.b"
RECOVER = ["millie"]
PROGRESS_PCT = None     # 0-100, or None
FORCE = False
# ================================================

data = _core.load(SAVE)
buf = bytearray(data)
offs = E.find_blocks(data)
b = offs[N.BLOQUE_SCRIPTS]
base_stats = offs[N.BLOQUE_STATS] + 5

def stat_i(idx):
    return struct.unpack_from("<i", buf, base_stats + idx * 4)[0]

def put_stat(idx, v):
    struct.pack_into("<i", buf, base_stats + idx * 4, v)

# --- recover -------------------------------------------------
for who in RECOVER:
    key = who.lower()
    if key not in N.NOVIAS:
        sys.exit(f"error: '{who}' does not exist. Valid: {', '.join(N.NOVIAS)}")
    off, bit, name, alive = N.NOVIAS[key]

    m = buf[b + N.MASCARA_OFF]
    if not (m >> bit) & 1:
        buf[b + N.MASCARA_OFF] = m | (1 << bit)
        print(f"  mask bit {bit}: 0x{m:02x}  ->  0x{buf[b + N.MASCARA_OFF]:02x}"
              f"   [{name}]")

    before_g = struct.unpack_from("<i", buf, b + off)[0]
    if before_g <= 0:
        struct.pack_into("<i", buf, b + off, alive)
        print(f"  {name}: global {off}  {before_g}  ->  {alive}")

    before_s = stat_i(N.STAT_PROGRESO + bit)
    if before_s <= 0:
        put_stat(N.STAT_PROGRESO + bit, alive)
        print(f"  {name}: stats int[{N.STAT_PROGRESO + bit}]  {before_s}  ->  {alive}")

# --- progress for all you already have -----------------------
if PROGRESS_PCT is not None:
    if not 0 <= PROGRESS_PCT <= 100:
        sys.exit("error: PROGRESS_PCT is a percentage 0-100")
    m = buf[b + N.MASCARA_OFF]
    k = 0
    for off, bit, name, _ in N.NOVIAS.values():
        if not (m >> bit) & 1:
            print(f"  {name}: you don't have her (bit {bit} off), skipping")
            continue
        before_g = struct.unpack_from("<i", buf, b + off)[0]
        before_s = stat_i(N.STAT_PROGRESO + bit)
        struct.pack_into("<i", buf, b + off, PROGRESS_PCT)
        put_stat(N.STAT_PROGRESO + bit, PROGRESS_PCT)
        print(f"  {name}: global {before_g} -> {PROGRESS_PCT}   "
              f"stats {before_s} -> {PROGRESS_PCT}")
        k += 1
    if not k:
        print("  (you have no girlfriends: PROGRESS_PCT touches nothing)")

if not RECOVER and PROGRESS_PCT is None:
    sys.exit("error: set RECOVER or PROGRESS_PCT")

_core.save(buf, OUTPUT, data, FORCE)

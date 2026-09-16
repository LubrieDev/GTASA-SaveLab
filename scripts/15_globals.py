"""
SCM GLOBALS (main script variables)
------------------------------------
Reads and writes main.scm global variables (block 1, 12303 int32 from +9).

  MODE = "view"      -> shows global[i] and its neighbors
  MODE = "write"     -> writes SET = {index: value, ...}
  MODE = "gym"       -> clears the daily limit date of the gym
                       (globals 6731/6732), which is what makes the game
                       answer "You have done enough exercise for today"

The numbering is NOT the same as PC main.scm (there are 49212 globals there,
not 43808): indices are located by differential, not by number. Useful
references already confirmed: girlfriends at 1441+4n and 1629 (mask);
gym at 6729..6732.

    python scripts/15_globals.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import globals as GL

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_globals.b"
MODE = "gym"           # "view" | "write" | "gym"
GLOBAL = 1441           # index to read (MODE="view")
SET = {1441: 100}       # {index: value, ...} (MODE="write")
FORCE = False
# ================================================

data, ini, g = GL.carga(SAVE)
buf = bytearray(data)

if MODE == "view":
    if not 0 <= GLOBAL < len(g):
        sys.exit(f"error: global[{GLOBAL}] out of range (there are {len(g)})")
    print(f"  {len(g)} globals in block 1, from byte {GL.INICIO}\n")
    for k in range(max(0, GLOBAL - 3), min(len(g), GLOBAL + 4)):
        mark = "->" if k == GLOBAL else "  "
        f = GL.como_float(g[k])
        extra = f"  = {f:g} as float" if abs(f) > 1e-6 and abs(f) < 1e9 else ""
        print(f"  {mark} global[{k:>5}]  byte {GL.INICIO + k * 4:>6}  "
              f"{g[k]:>12}{extra}")

elif MODE == "write":
    base = ini + GL.INICIO
    for i, v in SET.items():
        if not 0 <= i < len(g):
            sys.exit(f"error: global[{i}] out of range (there are {len(g)})")
        before = struct.unpack_from("<i", buf, base + i * 4)[0]
        struct.pack_into("<i", buf, base + i * 4, v)
        print(f"  global[{i:>5}]  byte {GL.INICIO + i * 4:>6}   "
              f"{before:>12}  ->  {v}")
    _core.save(buf, OUTPUT, data, FORCE)

elif MODE == "gym":
    before = GL.arreglar_gimnasio(buf)
    if before is None:
        sys.exit("  the gym is not blocked (no limit date set)")
    uso, _ = GL.gimnasio(bytes(buf))
    print(f"  daily limit (globals {GL.GIMNASIO_LIMITE[0]}/{GL.GIMNASIO_LIMITE[1]}): "
          f"{GL.fecha(before)}  ->  no date")
    print(f"  last visit (globals {GL.GIMNASIO_USO[0]}/{GL.GIMNASIO_USO[1]}): "
          f"{GL.fecha(uso)}  [left intact, does not block]")
    _core.save(buf, OUTPUT, data, FORCE)

else:
    sys.exit("error: MODE must be 'view', 'write' or 'gym'")

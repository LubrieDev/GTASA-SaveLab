"""
WARDROBE: COPY OR REMOVE CLOTHING / HAIR / TATTOOS
---------------------------------------------------
Names are HASHED (uint32), not as text: you cannot write "white shirt",
you must COPY the hash from a save that already has it equipped.

  MODE = "copy"    -> brings a part from SOURCE to the save
  MODE = "remove"  -> empties the part in the save (like taking off the hat)

PART is valid (gtasa/wardrobe.py MODELS/TEXTURES), e.g. torso, legs,
shoes, hair, hat, tattoos: arm_left_upper, back, chest_left, stomach,
lumbar... A slot moves model + texture together when touched.

VERIFIED IN-GAME: changed 5 slots at once (shirt, jeans, afro, tattoo,
remove the hat) and CJ appeared dressed exactly like that.

    python scripts/14_copy_wardrobe.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa import wardrobe as R

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_wardrobe.b"
MODE = "copy"             # "copy" or "remove"
SOURCE = "savefiles/base.b"  # save that has what you want (if MODE=copy)
PART = "torso"
FORCE = False
# ================================================

if MODE not in ("copy", "remove"):
    sys.exit("error: MODE must be 'copy' or 'remove'")

targets = R.ranuras(PART)
if not targets:
    sys.exit(f"error: '{PART}' is not a wardrobe part. "
             f"Valid: {', '.join(R.PARTES)}")

data = _core.load(SAVE)
buf = bytearray(data)
b = R.localiza(data)

if MODE == "copy":
    src = _core.load(SOURCE)
    s_b, s_models, s_textures = R.lee(src)
    changes = []
    for table, i in targets:
        value = s_models[i] if table == "modelos" else s_textures[i]
        changes.append((table, i, value))
else:
    changes = [(table, i, 0) for table, i in targets]

for table, i, value in changes:
    off = b + (i * 4 if table == "modelos" else R.N_MODELOS * 4 + i * 4)
    before = struct.unpack_from("<I", buf, off)[0]
    struct.pack_into("<I", buf, off, value)
    print(f"  {table[:-1]}[{i}]  {'from ' + SOURCE if MODE == 'copy' else 'empty'}"
          f": 0x{before:08x} -> 0x{value:08x}")

_core.save(buf, OUTPUT, data, FORCE)

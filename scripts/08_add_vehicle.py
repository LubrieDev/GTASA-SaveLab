"""
ADD A VEHICLE TO A GARAGE
-------------------------
Places a new car in an empty slot. Without X/Y/Z the car appears in the CENTER
of the garage (the default positions from gtasa/garages.py); with X/Y/Z, at
the coordinates you give.

Writes EXACTLY the byte pattern the game expects in an occupied slot:
position, mark 2, model at +18 and the 0xff tail. Nothing is invented.

MODEL is the ID (400..611): see the table with `python garages.py coches`.

    python scripts/08_add_vehicle.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import off_plaza, CASAS, N_GARAJES, N_PLAZAS
from gtasa.garage import describir, PLAZA_LEN
from gtasa.garages import POSICIONES_POR_DEFECTO
from gtasa.vehicles import etiqueta, nombre

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_add_vehicle.b"
GARAGE = 0
SLOT = 2                # base.b has slots 2 and 3 free at Grove Street
MODEL = 522             # NRG-500
X = None                # None = center of garage; otherwise free coordinate
Y = None
Z = None
FORCE = True
# ================================================

if not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")
if not 0 <= SLOT < N_PLAZAS:
    sys.exit(f"error: SLOT must be between 0 and {N_PLAZAS - 1}")
if nombre(MODEL) is None:
    sys.exit(f"error: {MODEL} is not a vehicle model (400..611)")

data = _core.load(SAVE)
off = off_plaza(data, GARAGE, SLOT)
x, y, z, marca, modelo_actual, estado = describir(data, off)
if estado == "ocupada":
    sys.exit(f"error: {CASAS[GARAGE][2]}, slot {SLOT} already has a car")
if estado == "FANTASMA":
    sys.exit(f"error: {CASAS[GARAGE][2]}, slot {SLOT} has a ghost; "
             f"clean it first with scripts/13_clean_ghost_slots.py")

if X is None:
    px, py, pz = POSICIONES_POR_DEFECTO[GARAGE]
else:
    px, py, pz = float(X), float(Y), float(Z)

buf = bytearray(data)

# Position
struct.pack_into("<fff", buf, off, px, py, pz)
# Mark (2 = occupied, as in real saves)
buf[off + 12] = 2
# Bytes +13..+17 (common pattern seen in real saves)
buf[off + 13] = 0x02
buf[off + 14] = 0x04
buf[off + 15] = 0x00
buf[off + 16] = 0x00
buf[off + 17] = 0x00
# Model
struct.pack_into("<h", buf, off + 18, MODEL)
# Tail: 0xff
for i in range(20, 24):
    buf[off + i] = 0xff

print(f"  {CASAS[GARAGE][2]}, slot {SLOT}: {etiqueta(MODEL)}")
print(f"    position ({px:.1f}, {py:.1f}, {pz:.1f})")

_core.save(buf, OUTPUT, data, FORCE)

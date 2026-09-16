"""
MOVE A VEHICLE IN A GARAGE (coordinates)
----------------------------------------
Changes the position (x, y, z) of the car saved in a slot. The game loads the
car EXACTLY at that position: inside the garage it appears inside, outside it
appears outside (verified in-game). Only moves a car that is already saved.

GARAGE (0..19) is the index from gtasa/houses.py CASAS: 0 = Johnson House
(Grove Street). SLOT (0..3). Run with the garage map:

    python houses.py mapa

    python scripts/07_move_vehicle.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import off_plaza, CASAS, N_GARAJES, N_PLAZAS
from gtasa.garage import describir
from gtasa.vehicles import etiqueta

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_move_vehicle.b"
GARAGE = 0
SLOT = 0
X, Y, Z = 2501.0, -1697.0, 12.9
FORCE = False
# ================================================

if not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")
if not 0 <= SLOT < N_PLAZAS:
    sys.exit(f"error: SLOT must be between 0 and {N_PLAZAS - 1}")

data = _core.load(SAVE)
off = off_plaza(data, GARAGE, SLOT)
x, y, z, marca, modelo, estado = describir(data, off)
if estado != "ocupada":
    sys.exit(f"error: {CASAS[GARAGE][2]}, slot {SLOT} is {estado}; "
             f"no car to move")

buf = bytearray(data)
struct.pack_into("<fff", buf, off, float(X), float(Y), float(Z))

print(f"  {CASAS[GARAGE][2]}, slot {SLOT}: {etiqueta(modelo)}")
print(f"    position ({x:.2f}, {y:.2f}, {z:.2f})  ->  ({X:.2f}, {Y:.2f}, {Z:.2f})")

_core.save(buf, OUTPUT, data, FORCE)

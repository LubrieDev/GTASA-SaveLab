"""
CHANGE THE VEHICLE MODEL IN A SLOT
-----------------------------------
Replaces the model (int16 at +18) of a saved car and EMPTIES its 10 upgrade
slots: the old car's upgrades don't work on the new one, and putting 8 pieces
from another model is exactly what crashed the game with the Rhino.

Does NOT touch: the position (appears where it was), the color, the proof
flags byte, or the tail. One change at a time, as recommended by
gtasa/houses.py cambiar_coche.

VERIFIED IN-GAME: CJ's garage Patriot was changed to an FBI Truck
(model 528) and it appeared in the garage, drivable.

MODEL is the ID (400..611): `python garages.py coches`.

    python scripts/10_change_vehicle_model.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import (off_plaza, CASAS, N_GARAJES, N_PLAZAS,
                          MODELO_OFF, MEJORAS_OFF, MEJORAS_N)
from gtasa.garage import describir
from gtasa.vehicles import etiqueta, nombre

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_change_model.b"
GARAGE = 0
SLOT = 0
MODEL = 528            # FBI Truck
FORCE = False
# ================================================

if not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")
if not 0 <= SLOT < N_PLAZAS:
    sys.exit(f"error: SLOT must be between 0 and {N_PLAZAS - 1}")
if nombre(MODEL) is None:
    sys.exit(f"error: {MODEL} is not a vehicle model (400..611)")

data = _core.load(SAVE)
off = off_plaza(data, GARAGE, SLOT)
x, y, z, marca, old, estado = describir(data, off)
if estado != "ocupada":
    sys.exit(f"error: {CASAS[GARAGE][2]}, slot {SLOT} is {estado}; "
             f"no car to change")

buf = bytearray(data)
struct.pack_into("<h", buf, off + MODELO_OFF, MODEL)
for i in range(MEJORAS_N):
    struct.pack_into("<H", buf, off + MEJORAS_OFF + 2 * i, 0xFFFF)

print(f"  {CASAS[GARAGE][2]}, slot {SLOT}")
print(f"    {etiqueta(old)}  ->  {etiqueta(MODEL)}")
print(f"    upgrades: emptied (the old car's don't apply)")
print(f"    stays at ({x:.1f}, {y:.1f}, {z:.1f})")

_core.save(buf, OUTPUT, data, FORCE)

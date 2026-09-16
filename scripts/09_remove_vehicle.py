"""
REMOVE A VEHICLE FROM A GARAGE
-------------------------------
Empties a slot: writes the exact empty slot pattern that the game leaves
(PLAZA_LIBRE from gtasa/garage.py). Does not touch cars in other slots.

GARAGE (0..19), SLOT (0..3). See `python houses.py mapa` for the index.

    python scripts/09_remove_vehicle.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import off_plaza, CASAS, N_GARAJES, N_PLAZAS
from gtasa.garage import describir, PLAZA_LIBRE, PLAZA_LEN
from gtasa.vehicles import etiqueta

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_remove_vehicle.b"
GARAGE = 0
SLOT = 1
FORCE = False
# ================================================

if not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")
if not 0 <= SLOT < N_PLAZAS:
    sys.exit(f"error: SLOT must be between 0 and {N_PLAZAS - 1}")

data = _core.load(SAVE)
off = off_plaza(data, GARAGE, SLOT)
x, y, z, marca, modelo, estado = describir(data, off)
if estado in ("LIBRE (limpia)", "libre"):
    sys.exit(f"error: {CASAS[GARAGE][2]}, slot {SLOT} is already free")

buf = bytearray(data)
buf[off:off + PLAZA_LEN] = PLAZA_LIBRE

print(f"  {CASAS[GARAGE][2]}, slot {SLOT}: {etiqueta(modelo)}  ->  FREE")

_core.save(buf, OUTPUT, data, FORCE)

"""
CLEAN GHOST SLOTS
-----------------
Searches for slots with a real model and NaN position (the car doesn't exist in
the world, the slot counts as occupied and CANNOT be cleared by playing) and
writes the empty slot pattern the game leaves. Does not touch real cars.

GARAGE = None -> all 20 garages; otherwise 0..19.
ALSO_FREE = True -> also normalize already-free slots that don't have the
exact pattern (cosmetic, not needed; see gtasa/garage.es_fantasma).

CONFIRMED IN-GAME (August): the three ghosts in the 100% save were cleaned and
Hashbury now fits 4 cars. See gtasa/houses.py limpiar.

    python scripts/13_clean_ghost_slots.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import off_plaza, CASAS, N_GARAJES, N_PLAZAS
from gtasa.garage import describir, es_fantasma, PLAZA_LIBRE, PLAZA_LEN
from gtasa.vehicles import etiqueta

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_clean_ghosts.b"
GARAGE = None           # None = all, or 0..19
ALSO_FREE = False
FORCE = False
# ================================================

if GARAGE is not None and not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")

data = _core.load(SAVE)
buf = bytearray(data)
touched = []

for g in (range(N_GARAJES) if GARAGE is None else [GARAGE]):
    for k in range(N_PLAZAS):
        off = off_plaza(data, g, k)
        x, y, z, marca, modelo, estado = describir(data, off)
        ghost = es_fantasma(data, off)
        if not ghost and not (ALSO_FREE and estado == "libre"):
            continue
        buf[off:off + PLAZA_LEN] = PLAZA_LIBRE
        touched.append((g, k, modelo, "GHOST" if ghost else estado))

if not touched:
    sys.exit("  no ghost slots; nothing written")

for g, k, modelo, what in touched:
    print(f"  {CASAS[g][2]:<32} slot {k}  {etiqueta(modelo):<26} "
          f"{what} -> FREE (clean)")

_core.save(buf, OUTPUT, data, FORCE)

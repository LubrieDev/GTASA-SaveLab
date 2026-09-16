"""
TUNE A SAVED VEHICLE
--------------------
Adds or removes upgrades (IDs 1000..1193) in the 10 upgrade slots of a slot
(offset +20..+40 of the record). Does not change the model.

SEVERE WARNING (see gtasa/houses.py tunear):
  - Only IDs from gtasa/vehicles.py UPGRADES (1000..1193), one per category: the
    game puts one part per slot and never two from the same category.
  - By default, the measured whitelist UPGRADES_SEEN is respected: combinations
    the game has already placed in real saves. Going outside it is what crashed
    the Rhino in the hangar (8 body kit pieces -> crash on load). With
    EVEN_IF_IT_CRASHES=True you skip that safety net: the worst case is a
    crash on load.
  - Nitro (1010) is inert on models that don't support it.

    python scripts/11_tune_vehicle.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import (off_plaza, CASAS, N_GARAJES, N_PLAZAS,
                          MEJORAS_OFF, MEJORAS_N)
from gtasa.garage import describir
from gtasa.vehicles import (etiqueta, MEJORAS, MEJORAS_VISTAS, SIN_MEJORA,
                            mejora, admite)

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_tune.b"
GARAGE = 2
SLOT = 0
UPGRADES = [1010]       # upgrade IDs (max 10). [] + REMOVE = True, or the list
REMOVE = False          # True = remove all upgrades from the car
EVEN_IF_IT_CRASHES = False  # skip the measured whitelist
FORCE = False
# ================================================

if not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")
if not 0 <= SLOT < N_PLAZAS:
    sys.exit(f"error: SLOT must be between 0 and {N_PLAZAS - 1}")
if not UPGRADES and not REMOVE:
    sys.exit("error: set UPGRADES or REMOVE = True")

if REMOVE:
    new = []
else:
    new = list(UPGRADES)
    if len(new) > MEJORAS_N:
        sys.exit(f"error: {MEJORAS_N} upgrades fit, you requested {len(new)}")
    unknown = [m for m in new if m not in MEJORAS]
    if unknown:
        sys.exit(f"error: not upgrade IDs (1000..1193): {unknown}")
    cats = [MEJORAS[m] for m in new]
    dupes = {c for c in cats if cats.count(c) > 1}
    if dupes:
        sys.exit(f"error: two upgrades for the same category: {sorted(dupes)}")

data = _core.load(SAVE)
off = off_plaza(data, GARAGE, SLOT)
x, y, z, marca, modelo, estado = describir(data, off)
if estado != "ocupada":
    sys.exit(f"error: {CASAS[GARAGE][2]}, slot {SLOT} is {estado}; "
             f"no car to tune")

if not REMOVE:
    foreign = [m for m in new if not admite(modelo, m)]
    if foreign and not EVEN_IF_IT_CRASHES:
        seen = MEJORAS_VISTAS.get(modelo)
        print(f"error: a {etiqueta(modelo)} has never been seen with "
              f"{', '.join(mejora(m) for m in foreign)}", file=sys.stderr)
        if seen:
            print(f"  what it does support: "
                  f"{', '.join(mejora(m) for m in sorted(seen))}", file=sys.stderr)
        else:
            print("  this model has never had ANY upgrade in the project's saves; "
                  "the mod shop probably offers none", file=sys.stderr)
        sys.exit("  use EVEN_IF_IT_CRASHES = True to try it anyway: with 8 pieces "
                 "on the Rhino the game crashed, with 1 nitro on the Patriot it did not")

buf = bytearray(data)
before = [struct.unpack_from("<H", buf, off + MEJORAS_OFF + 2 * i)[0]
          for i in range(MEJORAS_N)]
for i in range(MEJORAS_N):
    value = new[i] if i < len(new) else SIN_MEJORA
    struct.pack_into("<H", buf, off + MEJORAS_OFF + 2 * i, value)

print(f"  {CASAS[GARAGE][2]}, slot {SLOT}: {etiqueta(modelo)}")
print(f"    before: {[mejora(m) for m in before if m != SIN_MEJORA] or 'no upgrades'}")
print(f"    after:  {[mejora(m) for m in new] or 'no upgrades'}")

_core.save(buf, OUTPUT, data, FORCE)

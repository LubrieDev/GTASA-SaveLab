"""
VEHICLE PROOF FLAGS
-------------------
Sets or clears the proof/immunity flags (bitfield at +16 of the record of
each slot): 0x1f = bulletproof / fireproof / explosion-proof / damage-proof /
melee-proof.

Uses the MASK 0x1F from gtasa/armor.py: respects bits 5-7 (unknown, related
to the vehicle itself) and does not touch empty slots by default.

CONFIRMED IN-GAME: Patriot and Remington proofed withstood the minigun; the
flags live in the SLOT record, not the vehicle. UNCONFIRMED: when you park a
new car the game rewrites the record and may overwrite them (see gtasa/houses.py).

GARAGE = None -> all 20 garages; otherwise 0..19. INCLUDE_EMPTY = True ->
also touch empty slots.

    python scripts/12_vehicle_proofs.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _core
from gtasa.houses import off_plaza, CASAS, N_GARAJES, N_PLAZAS
from gtasa.garage import describir
from gtasa import armor as B
from gtasa.vehicles import etiqueta

# ==================== CONFIG ====================
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_proofs.b"
GARAGE = None           # None = all, or 0..19
ENABLE_PROOFS = True    # True = 0x1f, False = clear flags (0x00)
INCLUDE_EMPTY = False   # also touch empty slots (no practical effect)
FORCE = False
# ================================================

valor = B.BLINDADO if ENABLE_PROOFS else B.NORMAL
if GARAGE is not None and not 0 <= GARAGE < N_GARAJES:
    sys.exit(f"error: GARAGE must be between 0 and {N_GARAJES - 1}")

data = _core.load(SAVE)
buf = bytearray(data)
touched = 0

for g in (range(N_GARAJES) if GARAGE is None else [GARAGE]):
    for k in range(N_PLAZAS):
        off = off_plaza(data, g, k)
        estado = describir(data, off)[5]
        if estado != "ocupada" and not INCLUDE_EMPTY:
            continue
        antes, ahora = B.aplicar(buf, off, valor)
        if antes == ahora:
            continue
        modelo = struct.unpack_from("<h", buf, off + 18)[0]
        print(f"  {CASAS[g][2]:<32} slot {k}  "
              f"{etiqueta(modelo) if estado == 'ocupada' else '(' + estado + ')'}"
              f"   0x{antes:02x} -> 0x{ahora:02x}  "
              f"({B.describir_blindaje(ahora)})")
        touched += 1

if not touched:
    sys.exit("  nothing to change; nothing written")

_core.save(buf, OUTPUT, data, FORCE)

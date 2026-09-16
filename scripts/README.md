# Master Scripts

Ready-to-run scripts for common save operations. Each script has a **CONFIG**
block at the top (source save, output, parameters): edit, run, forget. All
writes go to a NEW file, never to the original.

## How to use

From the project root:

```bash
python scripts/01_money.py
```

Each script reads `SAVE`, validates it is a GTA SA Mobile save (platform check +
checksum), applies the operation, recalculates the checksum, writes to `OUTPUT`
and re-reads from disk to validate again. If `OUTPUT` already exists, it refuses
to overwrite unless `FORCE = True`.

## Index

| Script | Operation | Main config |
| ------ | --------- | ----------- |
| `01_money.py` | CJ money and HUD display | `MONEY` |
| `02_player_health_armor.py` | current health and armor | `HEALTH`, `ARMOR` |
| `03_player_stats.py` | max / set body stats | `MAX_OUT`, `FAT_PCT`, `MUSCLE_PCT` |
| `04_weapons.py` | give weapons and set ammo | `GIVE`, `AMMO_ALL` |
| `05_girlfriends.py` | recover girlfriends / set progress | `RECOVER`, `PROGRESS_PCT` |
| `06_progress.py` | game progress bar percentage | `PROGRESS_PCT` |
| `07_move_vehicle.py` | move a car's position in a garage | `GARAGE`, `SLOT`, `X`, `Y`, `Z` |
| `08_add_vehicle.py` | add a car to an empty slot | `GARAGE`, `SLOT`, `MODEL`, `X/Y/Z` |
| `09_remove_vehicle.py` | empty a slot | `GARAGE`, `SLOT` |
| `10_change_vehicle_model.py` | change the model of a car in a slot | `GARAGE`, `SLOT`, `MODEL` |
| `11_tune_vehicle.py` | add/remove upgrades (tuning) on a car | `GARAGE`, `SLOT`, `UPGRADES` |
| `12_vehicle_proofs.py` | vehicle proof flags on garage cars | `GARAGE`, `ENABLE_PROOFS`, `INCLUDE_EMPTY` |
| `13_clean_ghost_slots.py` | clean ghost slots (car with NaN) | `GARAGE`, `ALSO_FREE` |
| `14_copy_wardrobe.py` | copy/remove clothing, hair and tattoos | `MODE`, `SOURCE`, `PART` |
| `15_globals.py` | read/write SCM globals and fix the gym | `MODE`, `GLOBAL`, `SET` |

## Detailed usage

All examples below assume the command is run from the repository root. Change
the values in the script's `CONFIG` block before running it. `SAVE` is always
the input file, `OUTPUT` is the new file, and `FORCE = True` is required to
overwrite an existing output. The original input is never changed by default.

### 01 — Money

`01_money.py` writes CJ's money and the HUD copy together.

```python
SAVE = "savefiles/base.b"
OUTPUT = "savefiles/base_money.b"
MONEY = 999999999
FORCE = False
```

Both copies are updated because changing only one makes the save inconsistent.
The value must fit a signed 32-bit integer (`0..2147483647`).

```powershell
python scripts/01_money.py
```

### 02 — Health and armor

`02_player_health_armor.py` changes current health and armor. Set either value
to `None` to leave it unchanged.

```python
HEALTH = 220.0
ARMOR = 150.0
```

This changes CJ's current values, not maximum health or body stats.

### 03 — Player stats

`03_player_stats.py` can max the confirmed stats and/or set body percentages.

```python
MAX_OUT = True
FAT_PCT = 0       # None leaves fat unchanged
MUSCLE_PCT = 100  # None leaves muscle unchanged
```

Fat and muscle are written to both the stats block and wardrobe copy. `MAX_OUT`
sets fat to zero because maxing fat is not useful in-game. Unknown fields are
left untouched.

### 04 — Weapons and ammunition

`04_weapons.py` gives weapons and/or sets total ammo for weapons already held.

```python
GIVE = [("minigun", 99999), ("thermal goggles", None)]
AMMO_ALL = None
```

Weapon names must match the catalog in `gtasa/weapons.py`. Giving a weapon
overwrites the weapon currently occupying its slot. Weapons without ammo use
the game's no-ammo representation. `AMMO_ALL` changes total ammo, not the
magazine value.

### 05 — Girlfriends

`05_girlfriends.py` recovers girlfriends and/or changes the progress of every
girlfriend already active in the save.

```python
RECOVER = ["denise", "millie"]
PROGRESS_PCT = 100
```

Valid names are `denise`, `michelle`, `helena`, `barbara`, `katie`, and
`millie`. The script updates the mask, SCM global, and stats copy together.
It deliberately does not recalculate integer stat `146`.

### 06 — Progress bar

`06_progress.py` changes only the save-list progress bar.

```python
PROGRESS_PCT = 100.0
```

It calculates `PROGRESS_MADE` from the save's existing total and does not alter
mission counters.

### 07 — Move a vehicle

`07_move_vehicle.py` changes the saved position of one occupied garage slot.

```python
GARAGE = 0  # 0..19; see houses.py map
SLOT = 0    # 0..3
X, Y, Z = 2501.0, -1697.0, 12.9
```

Use `python houses.py map` to identify garage numbers. The game loads the car
at the exact coordinates written; the script does not change its model,
upgrades, colors, or proof flags.

### 08 — Add a vehicle

`08_add_vehicle.py` places a model in an empty slot.

```python
GARAGE = 0
SLOT = 2
MODEL = 522       # NRG-500; IDs are 400..611
X = Y = Z = None  # use the garage center
```

Use `python garages.py vehicles` for model IDs. The target must be empty and
not a ghost slot. Unsupported or invalid model IDs are rejected.

### 09 — Remove a vehicle

`09_remove_vehicle.py` replaces one slot with the exact clean-empty pattern.

```python
GARAGE = 0
SLOT = 1
```

It affects only that slot and refuses an already clean empty slot.

### 10 — Change a vehicle model

`10_change_vehicle_model.py` replaces the model of an occupied slot and clears
all ten upgrade slots.

```python
GARAGE = 0
SLOT = 0
MODEL = 528  # FBI Truck
```

Position, colors, proof flags, and the record tail are preserved. Clearing old
upgrades is intentional: upgrades from another model can crash the game.

### 11 — Tune a vehicle

`11_tune_vehicle.py` writes upgrade IDs into an occupied vehicle slot.

```python
GARAGE = 2
SLOT = 0
UPGRADES = [1010]
REMOVE = False
EVEN_IF_IT_CRASHES = False
```

Upgrade IDs are `1000..1193`, with at most one upgrade per category and ten
slots total. By default the measured whitelist in `gtasa/vehicles.py` rejects
combinations not seen in real saves. Set `REMOVE = True` with an empty list to
clear upgrades. `EVEN_IF_IT_CRASHES = True` disables the safety check and is
not recommended.

### 12 — Vehicle proof flags

`12_vehicle_proofs.py` applies or clears the five proof bits for occupied cars.

```python
GARAGE = None        # None = all 20 garages, or 0..19
ENABLE_PROOFS = True
INCLUDE_EMPTY = False
```

`ENABLE_PROOFS = True` writes mask `0x1f`; `False` clears those five bits.
Bits `0x20`, `0x40`, and `0x80` are preserved. Empty slots are skipped by
default because proofing a slot without a saved car has no practical effect.

```powershell
python scripts/12_vehicle_proofs.py
```

The master script writes a new file. To intentionally replace the input, set
`OUTPUT = SAVE` and `FORCE = True`, after making a backup.

### 13 — Clean ghost slots

`13_clean_ghost_slots.py` removes slots with a real model but NaN coordinates.

```python
GARAGE = None  # None = all garages, or 0..19
ALSO_FREE = False
```

Ghost slots are not real parked cars but occupy garage capacity. `ALSO_FREE`
only normalizes already-free slots with a nonstandard pattern; it is cosmetic.

### 14 — Copy wardrobe

`14_copy_wardrobe.py` copies or removes one clothing, hair, or tattoo part.

```python
MODE = "copy"              # "copy" or "remove"
SOURCE = "savefiles/base.b"
PART = "torso"
```

Wardrobe values are hashed uint32 values, not text names. In `copy` mode the
part is read from `SOURCE`; in `remove` mode its model and texture are set to
zero. Valid part names are listed in `gtasa/wardrobe.py`.

### 15 — SCM globals and gym

`15_globals.py` reads globals, writes selected globals, or clears the gym's
daily exercise limit.

```python
MODE = "view"       # "view", "write", or "gym"
GLOBAL = 1441       # used by view
SET = {1441: 100}   # used by write
```

Use `MODE = "view"` to inspect a global and nearby values, `MODE = "write"`
to write the entries in `SET`, or `MODE = "gym"` to clear globals `6731` and
`6732`. The mobile global numbering differs from PC; do not transfer PC
indices blindly.

## Notes by category

- **Cars/garages**: `python houses.py mapa` and `python garages.py coches`
  show the garage index and the model table (400..611). For tuning,
  IDs go from 1000 to 1193 and the measured vehicle whitelist is respected
  (see `gtasa/vehicles.py`); going outside it crashed the game
  (Rhino in the hangar). One change at a time: what each script does NOT
  touch is explained in its header.
- **Player**: stats go through `gtasa/editor.py` identified fields; fat and
  muscle are written in BOTH copies (stats + wardrobe) so the menu and
  CJ's body don't go out of sync. Unconfirmed fields are not touched.
- **Girlfriends/progress**: each girlfriend lives in three places (mask + global
  + block 16 copy); the scripts touch all three. Do not recalculate int[146].
- **Wardrobe**: names are hashed; only copied between saves.
- **Globals**: the mobile main.scm numbering differs from PC;
  confirmed indices (girlfriends, gym) are documented in
  `gtasa/globals.py`.

## Limits

- Only touches fields identified in the project; the list of confirmed fields
  and their confidence level is in `gtasa/*.py` and `docs/`.
- The scripts are a starting point: for combined operations, use
  `python gta.py audit` / `edit`, which applies everything in one pass.

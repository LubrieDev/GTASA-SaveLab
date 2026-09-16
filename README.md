# GTASA SaveLab

Tools and documentation for analyzing, researching, and editing **GTA San Andreas Mobile** save files.

---

## What it is

GTASA SaveLab is a collection of Python tools for inspecting and modifying GTA San Andreas Mobile save files (`.b` extension). It provides a command-line interface for auditing save contents and editing individual fields.

The project also includes reverse engineering documentation produced by analyzing the game binary (`libGame.so`, arm64-v8a) with ARM64 disassembly, differential analysis, and cross-referencing. This process reconstructed the save format, mapped data structures to specific offsets, and documented the loading flow the game uses at startup.

The save format is **variable-size** with **29 blocks** delimited by ASCII `BLOCK` markers. A `uint32` checksum (sum of all bytes except the last 4, masked to 32 bits) is stored in the last 4 bytes of the file. Each block has its own internal structure, and block boundaries shift depending on game state.

---

## What it does

- Audit save files and display detailed block maps
- Edit money, health, player armor, body stats, and player progress
- Manage weapons and ammunition
- Add, remove, and clean vehicles in all 20 garages
- Apply and remove vehicle proof flags (bulletproof, fireproof, etc.)
- Edit girlfriend relationships
- Copy clothing between saves
- Read and write script globals
- Manage properties and their garages
- Clone save files to different slots
- Run differential analysis across multiple saves

Editing operations write to a new output file rather than modifying the original. Written saves are recalculated with a valid checksum.

---

## Project structure

```
GTASA SaveLab/
├── gta.py              Main entry point (audit + edit)
├── armor.py            Vehicle proof flags tool
├── garage.py           CJ's garage (4 slots)
├── garages.py          All 20 garages
├── girlfriends.py      Girlfriend state
├── globals.py          SCM global variables
├── houses.py           Properties and garages
├── weapons.py          Weapon slots
├── wardrobe.py         Clothing, hair, tattoos
├── savefile.py         File layer (blocks + checksum)
├── vehicles.py         Vehicle catalog (212 models)
├── gtasa_editor.py     Save editor (money, progress)
├── expedition.py       Chain differential analysis
├── harvest.py          Cross-reference stat transcripts
├── scripts/            Ready-to-use master scripts (one operation each)
│   ├── README.md       Index and how to use them
│   └── *.py            Money, cars, tuning, girlfriends, wardrobe, globals
├── gtasa/              Package (implementation)
│   ├── analisis/       Analysis subpackage
│   └── ...             Module implementations
├── savefiles/          Pinned reference save files (test fixtures)
│   ├── base.b          Base reference save
├── tests/              Standard-library unittest suite
│   ├── test_savefile.py
│   ├── test_editor.py
│   ├── test_vehicles.py
│   ├── test_reference.py
│   └── _paths.py
├── .github/workflows/  CI (runs the suite on every push/PR)
└── docs/               This documentation
```

---

## Quick start

```bash
# Inspect a save file
python gta.py audit <save.b>

# Modify a save, writing output to a new file
python gta.py edit <save.b> --output NEW.b --money 999999999
```

Individual tools can also be run directly:

| Tool             | Purpose                                      |
| ---------------- | -------------------------------------------- |
| `gta.py`         | Unified CLI: audit and edit commands         |
| `armor.py`       | Apply/remove vehicle proof flags on garage slots |
| `garage.py`      | Inspect/edit CJ's garage (4 slots)           |
| `garages.py`     | Inspect/edit all 20 garages                  |
| `girlfriends.py` | View and modify girlfriend states            |
| `globals.py`     | Read/write SCM global variables              |
| `houses.py`      | Manage properties and attached garages       |
| `weapons.py`     | Inspect weapon slot contents and ammo        |
| `wardrobe.py`    | Manage clothing, hair, and tattoos           |
| `savefile.py`    | Low-level block and checksum operations      |
| `vehicles.py`    | Vehicle model catalog (212 models)           |
| `gtasa_editor.py`| High-level editor (money, body stats)        |
| `expedition.py`  | Chain differential analysis across saves     |
| `harvest.py`     | Cross-reference stat transcripts              |

---

## Master scripts

`scripts/` holds ready-to-run scripts, one per common operation, so you don't
have to write a throwaway tool each time. Each script has a **CONFIG** block at
the top (source save, output, parameters), writes to a new file and validates
the result. See [scripts/README.md](scripts/README.md) for the full index.

```bash
python scripts/01_money.py          # money
python scripts/07_move_vehicle.py   # move a car's position in a garage
python scripts/11_tune_vehicle.py   # tune a saved car
python scripts/15_globals.py        # read/write SCM globals
```

---

## Save file format

**Quick overview** (detailed documentation linked below):

- **Size**: variable (observed range: ~195 000 to ~260 000 bytes)
- **Structure**: 29 blocks, each preceded by the ASCII marker `BLOCK`
- **Checksum**: sum of all bytes except the last 4, masked to 32 bits, stored as `uint32` LE in the last 4 bytes (trailing garbage is included in the sum)
- **Mobile vs PC discrimination**: 49 212 SCM globals, SimpleVars section 433 bytes, player name encoded as UTF-16

For the full format reference, see [Save Format](docs/save-format.md).

---

## Reference files

The `savefiles/` directory contains the reference save files used by the test
suite. They are public (100% completion) saves, pinned on purpose so tests have
deterministic inputs:

| File            | Bytes | md5                              |
| --------------- | ----- | -------------------------------- |
| `base.b`        | 195000 | `f67201b9fd50a8118df86cd8fe698a62` |

The tests read them in memory as copies and never modify them. Because they are
test fixtures, they are excluded from the `*.b` `.gitignore` rule.

---

## Testing

The suite uses only the standard library; run it with:

```bash
python -m unittest discover -s tests -v
```

It covers the file layer (block traversal, checksum, version, resize, corruption
rejection), the editor (containment mapping, money, mobile/PC discrimination,
checksum helpers, CLI end-to-end through `gta.py`), vehicle slots (grid layout,
slot states, proof-flag masks, ghost detection) and the reference saves (mobile
discriminator, gym fix, wardrobe anchor, proofed Patriot).

`tests/_paths.py` points the suite at `savefiles/`. Tests never write to the
repository; modifications go to `tempfile` directories.

---

## Documentation

| Document                                            | Description                                  |
| --------------------------------------------------- | -------------------------------------------- |
| [Save Format](docs/save-format.md)                  | Format overview                              |
| [Block Map](docs/block-map.md)                      | The 29 blocks and their roles                |
| [Loading Flow](docs/loading-flow.md)                | What the game validates on load              |
| [Tools](docs/tools.md)                              | All tools with full CLI usage                |
| [Methodology](docs/methodology.md)                  | RE techniques, differential analysis, pitfalls |
| [Block Structures](docs/blocks/)                    | Per-block field reference                    |

---

## Requirements

- Python 3.8 or later
- No external dependencies (standard library only)

---

## Disclaimer

GTASA SaveLab is an independent project and is not affiliated with
or endorsed by Rockstar Games.

GTA San Andreas is a trademark of Rockstar Games.

This repository contains original tools, documentation, and research
for working with GTA San Andreas Mobile save files.

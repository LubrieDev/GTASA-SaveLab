# Tools

## Save Editors (gtasa/ package)

### gta.py — Main Entry Point

The all-in-one tool: `audit` (read-only inspection) and `edit` (write modifications) in a single pass.

```
python gta.py audit <save.b>                       inspect a save
python gta.py edit <save.b> --output NEW.b         modify a save
python gta.py clone <save.b> --output NEW.b --slot N  clone to another slot
```

Subcommands:
- `audit` — prints block map, money, stats, weapons, garages, girlfriends
- `edit` — applies modifications (see options below)
- `clone` — copies a save to another slot number

Spanish aliases are also accepted: `auditar`, `editar`, and `clonar`.

### armor.py — Vehicle Proof Flags (gtasa/ package)

Inspects and modifies the vehicle proof flags byte (+16) in garage slot records. The filename `armor.py` is retained for compatibility, but the underlying field is NOT armor — it is a set of proof/immunity flags. See `scripts/12_vehicle_proofs.py` for a reusable laboratory script.

```
python armor.py <save.b> --inspect
python armor.py <save.b> --armor --output NEW.b
python armor.py <save.b> --unarmor --output NEW.b
python armor.py <save.b> --armor --slot 0 --output NEW.b
python armor.py <save.b> --value 0x01 --output NEW.b
```

The proof flags byte is a bitfield:
- `0x01` = bulletproof (BP)
- `0x02` = fireproof (FP)
- `0x04` = explosion-proof (EP)
- `0x08` = damage-proof / collision-proof (DP/CP)
- `0x10` = melee-proof (MP)
- `0x1f` = all-proof (AP) — all five proofs enabled

Only bullet immunity has been confirmed in-game. The flags at bits 5-7 (0x20, 0x40, 0x80) are unrelated to proof flags and are preserved by the mask. Their meaning is unknown/unconfirmed.

### garage.py — CJ's Garage (4 Slots)

Inspects and cleans the 4-slot garage at CJ's house (block 3, payload + 39 + k*1280).

```
python garage.py <save.b> --inspect
python garage.py <save.b> --clean --output NEW.b
```

### garages.py — All 20 Garages

General tool for the 20 garages in the game.

```
python garages.py see <save.b> [--todo]
python garages.py add <save.b> --salida NEW.b --garaje N --plaza S --modelo ID
python garages.py remove <save.b> --salida NEW.b --garaje N --plaza S
python garages.py clean <save.b> --salida NEW.b [--garaje N]
python garages.py vehicles                 # vehicle ID table
```

Spanish aliases are `ver`, `anadir`, `quitar`, `limpiar`, and `coches`.

### girlfriends.py — Girlfriend State

Inspects and repairs girlfriend state: mask (global 1629), progress (globals 1441+4n), and stats copy (block 16 int[214+n]).

```
python girlfriends.py <save.b> --inspeccionar
python girlfriends.py <save.b> --recuperar denise --salida NEW.b
```

### globals.py — SCM Global Variables

Reads and writes main.scm global variables (block 1). 12303 int32 values starting at offset +9.

```
python globals.py view <save.b> --global N
python globals.py compare BEFORE.b AFTER.b
python globals.py inspect SAVE1.b SAVE2.b --globals 39,42,1234-1240
python globals.py write <save.b> --poner 1441=74 --salida NEW.b
```

### houses.py — Properties and Garages

20 houses with garages, bounding boxes, and purchased property flags.

```
python houses.py map                           # table of houses
python houses.py see <save.b>                  # what is parked in each
python houses.py check <save.b>                # validates against save
python houses.py properties <save.b>           # purchased houses
python houses.py clean <save.b> --salida NEW.b # remove ghost slots
```

Spanish aliases are `mapa`, `ver`, `comprobar`, `propiedades`, and `limpiar`.

### weapons.py — Weapon Slots

13 weapon slots × 28 bytes in block 2. Inspect, edit ammo, set fire type.

```
python weapons.py <save.b> --inspect
python weapons.py <save.b> --ammo minigun 30000 --output NEW.b
python weapons.py <save.b> --ammo-all 99999 --output NEW.b
python weapons.py <save.b> --health 200 --output NEW.b
python weapons.py <save.b> --armor 150 --output NEW.b
```

### wardrobe.py — Clothing, Hair, Tattoos

CPedClothesDesc in block 2: view, copy, and remove clothing parts.

```
python wardrobe.py view <save.b>
python wardrobe.py copy ORIGIN.b DEST.b --parte PART --salida NEW.b
python wardrobe.py remove <save.b> --parte PART --salida NEW.b
```

### savefile.py — File Layer

Block map, checksum validation, read/write of .b files.

```
python savefile.py <save.b> --mapa             # block map
```

### vehicles.py — Vehicle Catalog

Lookup table: 212 vehicle model IDs (400–611) to names.

```
python vehicles.py                             # print the table
```

### gtasa_editor.py — Save Editor (Legacy)

Shortcut to `gtasa.editor`. Provides money, stats, and progress editing.

```
python gtasa_editor.py <save.b> [options]
```

## Analysis Tools (gtasa/analisis/)

### expedition.py — Chain Differential Analysis

Compares N saves in N-1 pairs to isolate what each action changed. Uses noise baseline and frequency filtering.

```
python expedition.py --chain SAVE1.b SAVE2.b SAVE3.b ...
python expedition.py --star BASE.b CHANGE1.b CHANGE2.b ...
```

`--star` (default): each save is compared against the base. `--chain`: each save is compared against the previous one.

### harvest.py — Cross-Reference Stat Transcripts

Cross-references stat screen transcriptions (.md files) against .b saves to identify fields.

```
python harvest.py <transcript.md> <save.b>
```

## Binary Analysis Tools (external)

The following names refer to the separate reverse-engineering toolkit used to
produce the research notes. That toolkit is not included in this repository;
the commands below are historical references, not runnable GTASA SaveLab
commands.

### arm64.py — ARM64 Disassembler

Full ARM64 disassembler with symbol resolution, ELF parsing, logical immediate decoding, bit field analysis, and ADRP+LDR symbol resolution.

```
python arm64.py <symbol> [start] [end]
python arm64.py --search <text>
python arm64.py --who <symbol>
```

### shopping.py — SaveDataToWorkBuffer Tracer

Traces `*::Save` methods and lists every `_SaveDataToWorkBuffer` call with its size and source symbol. This is the universal entry point for mapping any block's structure.

```
python shopping.py
```

### ped.py — Ped Field Mapper

Generic field mapper for `*SaveStructure::Construct`. Follows data flow from a source register through loads, stores, and function calls.

```
python ped.py
```

### simple.py — SimpleVariables Field Mapper

Traces `CSimpleVariablesSaveStructure::Construct` to map block 0's fields.

```
python simple.py
```

### posteffects.py — PostEffects Field Mapper

Maps `CPostEffectsSaveStructure::CopyValues` for block 28.

```
python posteffects.py
```

### carga.py — Load-Side Analyzer

Lists all 29 `::Load` methods and determines whether loop bounds come from the file (resizable) or the binary (fixed).

```
python carga.py                # overview
python carga.py <class>        # trace specific class
```

### block_order.py — Block Order Determination

Traces `GenericSave` and `GenericLoad` to determine the exact call order of the 29 block handlers.

```
python block_order.py
```

### radar.py — Radar Block Analysis

Maps `CRadar::Save`/`Load` and validates 250 radar blip slots. Contains logical immediate and bit field decoders.

```
python radar.py
```

### Other block-specific tools

| Tool | Block | Purpose |
|---|---|---|
| `entry_exits.py` | 25 | Entry/exit stack parsing |
| `restart.py` | 8 | Respawn points |
| `radio.py` | 26 | Radio station data |
| `stunt_jumps.py` | 24 | Stunt jump validation |
| `set_pieces.py` | 17 | Police roadblock positions |
| `scripts.py` | 1 | CTheScripts non-globals |
| `pools.py` | 2 | Object pool anchoring |
| `minor_blocks.py` | 4,5,11,19,20,21,27 | Seven small blocks |
| `tags.py` | 20 | Tag manager references |
| `tail.py` | trailing | SaveBriefs analysis |
| `field_access.py` | — | Offset-to-function reverse lookup |
| `stat_ids.py` | — | Stat ID extraction |
| `position_scanner.py` | 2,3 | Map position search |

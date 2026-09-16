# Reverse Engineering Methodology

## Core principle

Everything in this project was obtained through **differential analysis**: two saves that differ in a single thing, and the bytes that change are the data.

Searching for patterns does not work and produces false positives. The garage block is 45% zeros and 14% `0xff` bytes: any 2-byte value hits by chance. Vehicle models that were *not* in the garage gave more matches than those that were.

**Without field truth, nothing gets written.**

## Differential analysis

The fundamental technique:

1. Take two saves from the same playthrough
2. Ensure they differ in exactly one thing
3. The bytes that change between them are the data for that thing

### Controlled comparison

The most reliable form: the same save state, one action performed, save again. Only the action's bytes change.

### Noise baseline

Two consecutive saves with nothing done isolate which regions change on their own (timers, position, counters). Subtracting them reduces candidate regions dramatically.

### Field truth anchors

Known values that anchor the analysis. Examples:
- Kart = model 571, NRG-500 = model 522 at known coordinates
- A specific weapon at exactly 487 rounds (a number that appears nowhere else in the file)
- A test going from 98% to 100% (yielding a single hit in 195000 bytes)

The key: use values that are **specific enough** to produce a unique hit. Round numbers produce hundreds of matches.

## Star vs. chain expedition

When mapping several things at once, how the saves are collected matters:

| Method | How it's played | What you get |
|---|---|---|
| **Chain** | Each save comes from the previous one | The differential mixes multiple changes |
| **Star** | Reload the base before each thing | Each save = base + one change |

Star expedition is generally more reliable because each differential isolates exactly one change. Chain expedition can work but requires careful interpretation because differentials compound.

**Before interpreting anything, you need to know which method was used**, because the same data means different things depending on the collection method.

## The minigun trick

Finding a specific value in a large binary file:

1. Perform an in-game action that produces a unique, non-round number
2. Save
3. Search for that number in the file
4. If it appears exactly once, you've found the field

Example: firing the minigun until the ammo reads 487 (a number that doesn't appear anywhere else in the file), then searching for 487 as int32 yields a single hit — the ammo field.

Round numbers fail: 500 appears 100+ times in the same file.

## The stats transcript trick

Cross-reference a stats screen transcription (every line read from the screen) against the save file:

1. Parse each value from the transcript (percentages, money, distances, counters)
2. Search for each value in the save
3. Unique hits are confirmed fields

This identified 106 fields in a single pass, at two confidence levels:
- **Level A**: value appears only once in the entire file — unassailable
- **Level B**: value appears multiple times, but only one falls in a valid slot of the stats block

## ARM64 binary analysis

The game binary (`libGame.so`, arm64-v8a) contains the save format as executable code. Key techniques:

### Tracing `SaveDataToWorkBuffer` calls

The `traza()` function traces a `*::Save` method and lists every `_SaveDataToWorkBuffer` call with its size and source symbol. This is the universal entry point for mapping any block's structure.

### ADRP+LDR pattern following

The game loads GOT (Global Offset Table) entries via ADRP+LDR. By following the page address (ADRP) and the offset (LDR), you can determine which global symbol each register holds at any point.

### Logical immediate decoding

ARM64 logical immediates (AND, ORR, EOR with bitmasks) use a complex encoding scheme. The `DecodeBitMasks` algorithm extracts the rotation and pattern to determine the actual mask value.

### Fixed-point coordinate decoding

Coordinates in some blocks use int16 fixed-point representation. The scale factor is visible in the binary as `scvtf ..., #N` — the N determines the number of fractional bits (divide by 2^N).

## Pitfalls

### The format is not aligned

The 5-byte `BLOCK` tag means fields fall on non-4-byte offsets. Any pattern scan must go byte-by-byte.

### Address order ≠ execution order

`CPools::Save` has a branch on `IsMissionSave` that skips half the function. The order of code in the binary is not the order it executes.

### The loop counter can be in 3 places

- On the **stack** (local variable)
- In a **global variable** (named symbol)
- In a **field of the object itself** (e.g., `this+17804` for CPathFind)

A detector that only checks one of these produces a wrong block map.

### The 9999 display threshold is display-only

The HUD doesn't show numbers above 9999, but the underlying value is preserved. Writing 99999 to a weapon's total ammo does NOT make it infinite — the clip field determines consumption.

### The magazine field cannot exceed its size

Writing a value larger than the weapon's magazine size to the clip field (`+8` in the weapon record) is silently overwritten by the game on load to the exact magazine size.

### Upgrades are not a free field

Only upgrades that a vehicle model actually supports are valid. Writing unsupported upgrades to a vehicle can crash the game (body parts on a tank) or be silently ignored (nitro on a military vehicle).

### Proof flags belong to the saved car, not the slot

When parking, the game writes the entire record from the vehicle. Proofing an empty slot does nothing; proofing a car that's already inside does. The proof flags byte is at offset +16 in the 64-byte CStoredCar record.

### PC saves are not convertible to mobile

The two platforms use different `main.scm` files. Global variable *n* on PC is not variable *n* on mobile. There is no shift that works for the entire file.

However, in the low globals region (~1000–4000), the two platforms align with a +4 byte offset at 85–92% match rate, providing a second independent sample for structures in that range.

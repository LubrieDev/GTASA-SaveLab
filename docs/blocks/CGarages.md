# Structure of the CGarages block (block 3)

Extracted from `CGarages::Save` @ `0x569C94` in `libGame.so` (972 bytes of code),
following each of its calls to `_SaveDataToWorkBuffer(void* data, int size)`.

Before writing anything, `CGarages::Save` calls
`CGarages::CloseHideOutGaragesBeforeSave()` — that is why the doors always appear
closed in the saved game.

## Layout

Offsets are relative to the **start of the data**, i.e. after the 5 bytes of the
`BLOCK` tag.

### Header — 39 bytes

| offset | size | field |
|---:|---:|---|
| 0 | 4 | `NumGarages` |
| 4 | 1 | `BombsAreFree` |
| 5 | 1 | `RespraysAreFree` |
| 6 | 1 | `NoResprays` |
| 7 | 4 | `CarsCollected` |
| 11 | 4 | `BankVansCollected` |
| 15 | 4 | `PoliceCarsCollected` |
| 19 | 4 | `CarTypesCollected[0]` |
| 23 | 4 | `CarTypesCollected[1]` |
| 27 | 4 | `CarTypesCollected[2]` |
| 31 | 4 | `CarTypesCollected[3]` |
| 35 | 4 | `LastTimeHelpMessage` |

### `aCarsInSafeHouse` — 5120 bytes (offset 39)

Array `[20][4]` of **64-byte** records (20 houses x 4 slots). The symbol
`CGarages::aCarsInSafeHouse` is 5120 bytes, which matches exactly.

**It is written by columns, not by rows.** The code consists of four loops of 20
iterations each, with step `0x100` (= 4 x 64) and bases `+0x00`, `+0x40`,
`+0x80`, `+0xC0`:

```
first   slot 0 of all 20 houses
then    slot 1 of all 20 houses
then    slot 2 of all 20 houses
then    slot 3 of all 20 houses
```

That is, the record for house `c` slot `p` is at:

```
39 + (p * 20 + c) * 64
```

and **not** at `39 + (c * 4 + p) * 64`. This is the easy mistake to make here.

#### The 64-byte record: `CStoredCar`

Extracted from `CStoredCar::StoreCar(CVehicle*)` @ `0x3F72E4`. The block writes it
verbatim, so the file layout matches the in-memory struct.

| offset | size | type | field |
|---:|---:|---|---|
| 0 | 4 | float | `X` |
| 4 | 4 | float | `Y` |
| 8 | 4 | float | `Z` |
| 12 | 4 | u32 | **installed upgrade flags** (`CVehicle+1208`) |
| 16 | 2 | u16 | packed flags (bits pointing to `CVehicle+100`, `+1208` and `+1562`) |
| 18 | 2 | u16 | **model** (`CVehicle+50`) |
| 20 | 30 | u16 x 15 | **upgrades / tuning**, `0xFFFF` = empty slot |
| 50 | 1 | u8 | **color 1** |
| 51 | 1 | u8 | **color 2** |
| 52 | 1 | u8 | color 3 |
| 53 | 1 | u8 | color 4 |
| 54 | 1 | u8 | **radio station** (`CVehicle+582`) |
| 55 | 1 | u8 | **extra 1** of the model (`CVehicle+1400`) |
| 56 | 1 | u8 | **extra 2** of the model (`CVehicle+1401`) |
| 57 | 1 | u8 | **bomb** (`CVehicle+1562`), **only written** if `CVehicle+1844` is 0 or 9 |
| 58 | 1 | u8 | remap / paint job (`GetRemapIndex()`), `0xFF` = none |
| 59 | 1 | u8 | **nitro** (`CVehicle+1518`) |
| 60 | 1 | i8 | orientation `X` |
| 61 | 1 | i8 | orientation `Y` |
| 62 | 1 | i8 | orientation `Z` |
| 63 | 1 | — | **padding, not written** |

The three orientation bytes come from the vehicle's rotation matrix converted to
integer and clamped to +/-127; they are not angles in degrees.

#### How the loose fields were identified

`CStoredCar::RestoreCar` @ `0x3F7560` confirms the round-trip: each field returns
to the same `CVehicle` offset it came from, and `+58` is restored by calling
`CVehicle::SetRemap`, confirming it as the paint job.

But those `CVehicle` offsets have no names on their own. To assign names,
**which other named functions in the binary touch the same offset** was used
for inference:

| offset | functions that use it | conclusion |
|---|---|---|
| `CVehicle+582` | `CPed::SetRadioStation` | radio station |
| `CVehicle+1208` | `AddVehicleUpgrade`, `SetVehicleUpgradeFlags`, `ClearVehicleUpgradeFlags` | upgrade flags |
| `CVehicle+1400/1401` | `CarHasRoof`, `IsOpenTopCar`, `AddExhaustParticles` | model extras |
| `CVehicle+1562` | `ActivateBomb`, `BlowUpCar`, `CWorld::UseDetonator` | bomb |
| `CVehicle+1518` | `CAutomobile::NitrousControl` (5 of 6 references) | nitro |

This is inference by usage, not a label from the binary. The evidence is
strong — `+1518` only appears in nitro control, `+582` only in the radio station —
but if you are going to write to one of these fields, verify it first with a
differential test.

#### Verification

In a reference save: 29 occupied slots out of 80, and the 29 models
fall within 411-562, all within the valid GTA SA vehicle range (400-611), none
outside.

The positions match the garages that contain them: house 0 slot 0 stores a car at
(2505.4, -1694.9, 13.55), a couple of meters from the `cjsafe` garage at
(2502.31, -1699.36, 12.43).

The upgrades come out as `0xFFFF` in all 15 slots of untuned cars, which is the
"no part" value, and byte `+63` is 0 in all 29 slots, consistent with `StoreCar`
not touching it.

**Watch out for NaN:** some slots may have a `NaN` position with orientation
`0,0,0` but valid model and colors. The game accepts them. If a script reads
those coordinates as float and operates on them, it will propagate `NaN` without
warning.

### Garages — `NumGarages` x 80 bytes (offset 5159)

One 80-byte record per garage. With `NumGarages = 50` that is 4000 bytes.

The record is built on the stack (`sp+8`) by copying fields from `CGarage` (244
bytes in memory; `CGarages::aGarages` is 12200 = 50 x 244). The bulk — bytes
4..67 — is a **literal copy of `CGarage[0..63]`**, a block of 16 floats.

| offset | size | source | field |
|---:|---:|---|---|
| 0 | 1 | `CGarage+80` | type |
| 1 | 1 | `CGarage+81` | door state (0 / 1 / 2) |
| 2 | 1 | `CGarage+82` | flags |
| 3 | 1 | — | **padding, not written** |
| 4 | 4 | `CGarage+0` | `X` position |
| 8 | 4 | `CGarage+4` | `Y` position |
| 12 | 4 | `CGarage+8` | `Z` lower bound |
| 16 | 16 | `CGarage+12` | 2x2 rotation matrix (`cos`, `sin`, `-sin`, `cos`) |
| 32 | 4 | `CGarage+28` | `Z` upper bound (ceiling) |
| 36 | 4 | `CGarage+32` | width |
| 40 | 4 | `CGarage+36` | depth |
| 44 | 8 | `CGarage+40` | `X` min / `X` max of the bounding rectangle |
| 52 | 8 | `CGarage+48` | `Y` min / `Y` max of the bounding rectangle |
| 60 | 4 | `CGarage+56` | door opening (0.0 - 1.0) |
| 64 | 4 | `CGarage+60` | second door opening |
| 68 | 8 | `CGarage+72` | name (ASCII, `__strcpy_chk` with n=8) |
| 76 | 1 | `CGarage+83` | type (second copy — see below) |
| 77 | 3 | — | **padding, not written** |

Bytes `+3` and `+77..79` are not written by anyone. `+3`
is stack garbage and `+77..79` are 0. Do not interpret
them as data.

### The two type fields

`+0` and `+76` come from different places in `CGarage` (offsets 80 and 83) and
**do not always agree**. In the 14 safehouse garages they have the same value; in
some mission garages they differ, e.g. `mul_lan` has `+0 = 19` and `+76 = 1`.

`CGarage` stores the current type and the original type, so they most likely
correspond to those two, but **it has not been determined which is which**. For
safehouses it does not matter; for a mission garage, check before writing.

### Coordinate verification

Reading `+4`, `+8`, `+12` as floats in a reference save:

| garage | X | Y | Z |
|---|---:|---:|---:|
| `cjsafe` (Johnson's house) | 2502.31 | -1699.36 | 12.43 |
| `beacsv` (Santa Maria Beach) | 319.33 | -1768.93 | 3.36 |
| `CEsafe1` (Mulholland) | 1352.58 | -636.66 | 108.14 |

They match the actual positions of those garages on the map. Across all 50
records, `+4` and `+8` fall within +/-2740 — the size of the San Andreas map — and
`+12` between -8 and 108, which is the height range. The `+16` matrix comes out
as `1,0,0,1` for axis-aligned garages and `0.945, 0.328, -0.328, 0.945` in
`CEsafe1`, which is rotated ~19 degrees.

## Arithmetic check

Block 3 example: offset 68945, size 9164 bytes.

```
9164 - 5 (tag)          = 9159
9159 - 39 (header)      = 9120
9120 - 5120 (safehouse) = 4000
4000 / 80               = 50 garages exactly
```

And `NumGarages` read from the file itself is **50**. The block matches to the byte
and ends exactly where block 4 starts.

## Cross-check against garage catalog

Reading the `+76` byte and the `+68` name from each record, the 14 safehouse
garages all match — name and number:

| name | `+76` |
|---|---:|
| `beacsv` | 17 |
| `vEsvgrg` | 18 |
| `cn2gar1` | 24 |
| `cn2gar2` | 25 |
| `burbdo2` | 26 |
| `blob69` | 27 |
| `blob7` | 28 |
| `burbdoo` | 29 |
| `blob6` | 30 |
| `carlas1` | 31 |
| `CEsafe1` | 32 |
| `sav1sfe` | 39 |
| `sav1sfw` | 40 |
| `svgsfs1` | 42 |

14 out of 14. The field cataloged as the first element of the
tuple is the **garage type** from byte `+76`.

Non-safehouse garages carry low, repeated types (`1`, `2`, `5`...: mission, bomb,
paint shop), while each safehouse has its own unique value between 16 and 45.
`cjsafe` = 16 is Johnson's house.

## Warning

`NumGarages` is 50 in a reference save, but **read it from the file** instead of assuming
it is fixed: the number of records that follow depends on that field. And the
offsets above are relative to the start of the block, which must be located by
counting `BLOCK` markers — the absolute offset from another save does not work.

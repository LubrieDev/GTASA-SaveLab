# The Load Side: What the Game Validates When Opening a Save

Extracted from `libGame.so` (arm64-v8a) using the ARM64 disassembler and load-side analysis tools.

See [Block Map](block-map.md) for the overall map.

## Summary for Editor Authors

| # | Rule |
|---|---|
| 1 | **The checksum is the only global validation**, and it is checked by the menu (not the loader). `sum(data[:-4]) & 0xFFFFFFFF == last 4 bytes as u32 LE`. |
| 2 | **The file must measure a multiple of 4 bytes.** Nothing else. Not 195000, not a multiple of 65000. |
| 3 | The 5-byte `BLOCK` markers **are validated block by block** with `strncmp`. |
| 4 | Each block must consume **exactly** what its `::Load` reads. There is no length field to adjust anything. |
| 5 | Whatever lies behind `SaveBriefs` **is never read**. |
| 6 | 12 of the 29 blocks carry the record count **within the file**: those can be lengthened or shortened. |
| 7 | **There is not a single upper-bound check.** A counter that is too large does not produce an error: it overflows the destination array. |

## Call Chain

```
Menu_LoadSlot / Menu_Resume / MainMenuScreen::OnResume
    -> CGenericGameStorage::CheckSlotDataValid(slot, bool)
           -> C_PcSave::GenerateGameFilename
           -> CGenericGameStorage::CheckDataNotCorrupt   <- checksum check
              (on failure: PcSaveHelper.error = 7, slot appears as corrupt)

CGame::InitialiseWhenRestarting
    -> CGenericGameStorage::GenericLoad(bool&)            <- does NOT check checksum
```

`CheckDataNotCorrupt` is also called from `C_PcSave::PopulateSlotInfo` and `Menu_PopulateSaves` (rendering the save list).

## The Checksum — `CheckDataNotCorrupt` @ `0x562ECC`

Reads the entire file in chunks and accumulates the sum of all bytes in 32 bits (vectorized loop processing 32 bytes at a time plus a scalar tail). At the end:

```python
checksum = sum(data[:-4]) & 0xFFFFFFFF
# == struct.unpack_from("<I", data, len(data) - 4)[0]
```

The sum covers ALL preceding bytes, including the trailing garbage. The last chunk must measure 4 bytes or more.

## File Size — `LoadWorkBuffer` @ `0x562CEC`

The only size restriction: the chunk `file_size mod 65000` must be a multiple of 4. Since 65000 is a multiple of 4, the rule simplifies to:

> **The file must measure a multiple of 4 bytes.** That is the only size restriction.

If the chunk is not a multiple of 4, `LoadWorkBuffer` returns 0, sets `ms_bFailed`, and the save is rejected with `PcSaveHelper.error = 5`.

## The 65000-Byte Buffer Is Transparent

When the requested amount does not fit in the remaining buffer, `_LoadDataFromWorkBuffer` copies what fits, calls itself recursively with the remainder, and refills via `LoadWorkBuffer`. **A record can cross the 65000-byte boundary without any problem.** The chunking is purely an I/O artifact.

## The Loop — `GenericLoad` @ `0x561F3C`

- 29 iterations (indices 0..28)
- Each iteration: read 5 bytes, validate with `strncmp` against `ms_BlockTagName`
- Bad tag: `ReportError(block-1, 2)`, aborts
- After the loop: `LoadBriefs` (no tag of its own), then `CFileMgr::CloseFile`
- **Does not verify that the file has been entirely consumed** — the 10427 trailing garbage bytes are harmless

## Which Blocks Can Be Resized

A block is resizable if its `::Load` reads the record count from the file and iterates that count.

| # | Block | Counter source | Type |
|---:|---|---|---|
| 1 | CTheScripts | ScriptSpace size | u32 |
| 2 | CPools | one per pool | u32 each |
| 3 | CGarages | NumGarages | u32 |
| 4 | CGameLogic | NumAfterDeathStartPoints | u32 |
| 5 | CPathFind | this+17804 | u32 |
| 8 | CRestart | NumberOfHospitalRestarts, NumberOfPoliceRestarts | u16 each |
| 10 | CTheZones | TotalNumberOfNavigationZones, etc. | u16 each |
| 12 | CTheCarGenerators | NumOfCarGenerators | u32 |
| 20 | CTagManager | ms_numTags | u32 |
| 22 | CShopping | ms_numPriceModifiers | u32 |
| 24 | CStuntJumpManager | on stack | u32 |
| 25 | CEntryExitManager | ms_entryExitStackPosn | u32 |

The remaining blocks have fixed size: 0, 6, 7, 9, 11, 13, 14, 15, 16, 17, 18, 19, 21, 23, 26, 27, 28.

### Counter locations vary

The counter can be:
- On the **stack** (CStuntJumpManager, CPools)
- In a **global variable** (CGarages::NumGarages, CTagManager::ms_numTags)
- In a **field of the object itself** (CPathFind at this+17804)

### Three that look variable and are not

- **CPickups (6)**: loop is for initialization, not data. Fixed.
- **CStreaming (18)**: loop of 26316 iterations hardcoded. Fixed.
- **CPedType (19)**: 640 bytes hardcoded. Fixed.

And one in the opposite direction: **CTheCarGenerators (12)** appeared fixed because `cmp x8, #0x1f3` is a range check on the index, not the loop bound. It is variable.

## No Upper-Bound Checks

In none of the `::Load` functions is the read counter compared against the destination array capacity. A badly placed counter does not produce a "corrupt save" — it produces a memory overflow. The limits must be enforced by the editor.

## Side Effects of Loading

Several `::Load` functions call their `Init`/`Initialise` before reading data. Fields that the block does not write are reset to defaults — there is no way to leave a field "untouched" by omitting it.

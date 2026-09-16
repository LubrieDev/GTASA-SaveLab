# Structure of the CStats block (block 16)

Extracted from `CStats::Save` @ `0x56D788` in `libGame.so`.

Before writing anything, `CStats::Save` touches two stats: it reads 176,
increments 177, and rewrites 176. These are play-time counters that update right
at save time, so **they change on their own between two saves even if nothing
happens**. If you compare two saves byte by byte, that pair will always appear as
a difference.

## Layout

Offsets relative to the start of the data, i.e. after the 5 bytes of the `BLOCK`
tag.

| offset | size | content |
|---:|---:|---|
| 0 | 328 | `StatTypesFloat` — 82 floats |
| 328 | 892 | `StatTypesInt` — 223 int32 |
| 1220 | 128 | `PedsKilledOfThisType` — 32 int32 |
| 1348 | 8 | `LastMissionPassedName` |
| 1356 | 56 | `FavoriteRadioStationList` — 14 floats |
| 1412 | 400 | `TimesMissionAttempted` |
| 1812 | 128 | 128 loose bytes: byte `+2` of each `StatMessage` entry, step 16 |

`328 + 892 + 128 + 8 + 56 + 400 + 128 = 1940`, which is the 1945 bytes of the
block minus the tag. Matches to the byte.

## How a stat is indexed

From `CStats::GetStatValue(unsigned short)` @ `0x4BAEB0`:

```
if (id <= 81)  ->  StatTypesFloat[id]              // direct float
else           ->  (float) StatTypesInt[id - 120]  // int32, converted with scvtf
```

In offsets within the block:

```
id 0..81     ->  +(id * 4)
id 120..342  ->  +328 + (id - 120) * 4
```

**IDs 82..119 do not exist.** It is a gap: the comparison sends any id > 81 to
the integer path, but subtracting 120 would give a negative index. Do not use
them.

## Identified IDs

Located by scanning the binary for `mov w0, #N` followed by a call to
`GetStatValue` / `SetStatValue` / `IncrementStat` / `ModifyStat`, and attributing
each use to the function that performs it. **133 IDs** emerge; these are the
useful ones:

### Body and skills (float)

| id | offset | meaning | evidence |
|---:|---:|---|---|
| 21 | +84 | **fat** | `GetCurrentCJMood` |
| 22 | +88 | **stamina** | `CCheat::StaminaCheat` |
| 23 | +92 | **muscle** | `GetCurrentCJMood` |
| 24 | +96 | max health | `CWidgetPlayerInfo::RenderHealthBar` |
| 69-78 | +276...+312 | **skill for the 10 weapons** | `CCheat::WeaponSkillsCheat` |

### Social (float)

| id | offset | meaning | evidence |
|---:|---:|---|---|
| **25** | +100 | **sex appeal** | `UpdateSexAppealStat` writes `StatTypesFloat[25]` |
| **64** | +256 | **respect** | `UpdateRespectStat` writes `StatTypesFloat[64]` |

These two did not come from the literal scan, because neither function passes
the ID as a parameter: they write **directly into the array**. They were located
by resolving the base register to `CStats::StatTypesFloat` via GOT and reading
the offset of the `str`:

```
UpdateSexAppealStat  +0x01c0   str s0, [x19, #100]   x19 = StatTypesFloat  -> id 25
UpdateRespectStat    +0x01e4   str s8, [x20, #256]   x20 = StatTypesFloat  -> id 64
```

This is the strongest evidence in the entire document: it is not inference by
usage, it is the instruction that writes the value.

Other stats touched by `CShopping::Buy` (clothing) that feed that calculation,
without individual identification: 13 (+52), 14 (+56), 30 (+120), 31 (+124), 55
(+220), 62 (+248), 20 (+80) and 200.

### Counters (int32)

| id | offset | who increments it |
|---:|---:|---|
| 120 | +328 | `CDarkel::RegisterKillNotByPlayer` |
| 121 | +332 | `CDarkel::RegisterKillByPlayer` |
| 125 | +348 | `BlowUpCar` (vehicles destroyed) |
| 127 | +356 | `CGarage::Update` |
| 129 | +364 | `CAutomobile::BurstTyre` |
| 131 | +372 | `CWanted::UpdateWantedLevel` |
| 135 | +388 | `CPlayerInfo::KillPlayer` |
| 136 | +392 | `DoGameSpecificStuffBeforeSave` (number of saves) |
| 144 | +424 | `CStuntJumpManager::Update` — **unique jumps found** |
| 145 | +428 | `CStuntJumpManager::Update` — **unique jumps completed** |

The last two are confirmed against block 24: counting the status bytes of its 70
records yields exactly these two values.

## Verification

**Against the file itself:** all 82 floats fall within reasonable ranges, with not
a single absurd value, and none of the 223 integers comes out negative. With a
wrong offset that does not happen.

**Across blocks:** `LastMissionPassedName` matches the same name
stored by `CSimpleVariables` in block 0. Consistent.

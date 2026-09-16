# Territories and gang wars

Two different locations in the file: the **global state** of the wars is in block
23, and the **per-zone territory** in the `ZoneInfoArray` of block 10.

## Block 23 — `CGangWars` (105 B)

From `CGangWars::Save` @ `0x56E0D8`. Offsets after the `BLOCK` tag:

| offset | size | content |
|---:|---:|---|
| 0 | 4 | size of the following struct (96) |
| 4 | 96 | `CGangWarsSaveStructure` |

`4 + 96 = 100` = the 105 bytes of the block minus the tag.

### `CGangWarsSaveStructure` (96 B)

Offsets relative to the struct:

| offset | size | field | value |
|---:|---:|---|---:|
| 0 | 1 | `bGangWarsActive` | 1 |
| 12 | 4 | unidentified | 168 |
| 16 | 4 | unidentified | 168 |
| 52 | 4 | `TimeTillNextAttack` | 1235937648 |
| 56 | 8 | unidentified | |
| 72 | 4 | `RadarBlip` | 0 |
| 76 | 1 | `bPlayerIsCloseby` | 1 |
| 88 | 1 | `bCanTriggerGangWarWhenOnAMission` | 0 |
| 89 | 1 | `bTrainingMission` | 0 |
| 92 | 4 | `ZoneInfoForTraining` | 324 |

The gaps not listed in the table are not written by `Construct`: they are padding.
As in other blocks, **do not interpret them as data**.

## Block 10 — `ZoneInfoArray` (378 × 17 B)

This is the array in `CTheZones.md`. It spans within block 10, and there is
**one entry per navigation zone**, in the same order as `NavigationZoneArray`.
That is:

```
ZoneInfo of zone z  ->  file offset  start_of_ZoneInfoArray + z*17
```

### The 17-byte record

| offset | size | content | confidence |
|---:|---:|---|---|
| 0 | 10 | **density/strength for each of the 10 gangs** | high |
| 10 | 5 | zone color (components) | medium |
| 15 | 1 | unidentified (27 distinct values, 0–39) | — |
| 16 | 1 | unidentified (15 in 352 of 378) | — |

The first 10 bytes match the 10 gang slots of GTA SA, and the pattern confirms it:
each zone with territory has **exactly one** of those ten positions set to non-zero,
and the position changes depending on the owning gang.

### Cross-check with known zones

```
zone   4  PARA     0 0 0 0 0 0 0 0 0 0 | 0  0   0  0  0 |  4 15
zone  19  CALT     0 0 0 0 0 0 10 0 0 0 | 0  0   0  0  0 |  5 15   <- gang 6
zone 116  ELCO1    0 0 0 0 0 0 0 40 0 0 | 0  0   0  0  0 |  6  9   <- gang 7
zone 203  SMB2     0 10 0 0 0 0 0 0 0 0 | 0 70 200  0 55 | 40 15   <- gang 1
```

`CALT` belongs to gang 6, `ELCO1` to gang 7 with strength 40, `SMB2` to gang 1. And
`SMB2` is the only one of the four with the color bytes filled in (70, 200, 55),
consistent with being a disputed territory painted on the radar.

## What is not here

Which gang each index 0 to 9 corresponds to, and the exact meaning of bytes 15 and
16. A differential test of conquering a known territory and seeing which array
position changes would resolve the gang index mapping.

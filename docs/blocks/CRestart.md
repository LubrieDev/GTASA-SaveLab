# Structure of the CRestart block (block 8)

Extracted from `CRestart::Save` @ `0x56C748` in `libGame.so`.
See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are the respawn points: hospitals on death and police stations on arrest.

## Layout

```
2 + 8×20 + 2 + 7×20 + 55 = 359   = 364 - 5 (tag)
```

Matches to the byte. The two lists are **variable-length**: as many points are
saved as indicated by the counter, not the 10 that fit in the in-memory array.

| offset | size | content |
|---:|---:|---|
| 0 | 2 | `NumberOfHospitalRestarts` (value: 8) |
| 2 | 8 × 20 | hospital points |
| 162 | 2 | `NumberOfPoliceRestarts` (value: 7) |
| 164 | 7 × 20 | police station points |
| 304 | 55 | miscellaneous fields |

In memory the arrays are of 10 (`HospitalRestartPoints` is 120 B = 10 × 12), so
**if you reserve 10 fixed records, everything after them shifts.**

## The record (20 bytes)

| offset | size | field |
|---:|---:|---|
| 0 | 12 | **position** X, Y, Z (3 uncompressed floats) |
| 12 | 4 | **heading** in degrees |
| 16 | 4 | **when to use it** (0, 1, or 2) |

It comes from the loop writing three times per point —12, 4, and 4 bytes— reading
from `HospitalRestartPoints`, `HospitalRestartHeadings`, and
`HospitalRestartWhenToUse`, which are the three symbols with those sizes (120, 40,
and 40 bytes for 10 entries).

### The points in a reference save

```
hospitals                                         heading   when
 0  ( 2027.77, -1420.52,  15.99)                   137.00   0
 1  ( 1180.85, -1325.57,  12.58)                   271.40   0
 2  ( 1244.44,   331.23,  18.55)                     7.55   1
 3  (-2199.72, -2308.07,  29.62)                   322.89   1
 4  (-2670.29,   616.44,  13.45)                   183.10   1
 5  ( -316.38,  1056.05,  18.73)                     1.60   2
 6  (-1514.82,  2527.12,  54.74)                     2.35   2
 7  ( 1578.45,  1770.68,   9.84)                    99.76   2

police stations
 0  ( 1550.68, -1675.49,  14.51)                    90.00   0
 1  (  632.23,  -571.71,  15.35)                   267.20   1
 2  (-2163.83, -2387.82,  29.62)                   134.21   1
 3  (-1605.79,   716.86,  11.02)                   355.30   1
 4  ( -212.19,   979.42,  18.32)                   278.05   2
 5  (-1393.07,  2633.12,  54.95)                    86.04   2
 6  ( 2337.08,  2453.80,  13.98)                    90.76   2
```

**The "when" field is the map progress**, and it is visible in the coordinates
themselves: the `0` values are all in Los Santos, the `1` values appear as the
countryside and San Fierro open up, and the `2` values are in Las Venturas and
the north. All 15 points have positions within the map and headings within 0–360.

## The final 55 bytes

| offset | size | field | value |
|---:|---:|---|---|
| 304 | 1 | `bOverrideRestart` | 0 |
| 305 | 12 | `OverridePosition` | (−2126.30, −440.60, 34.50) |
| 317 | 1 | `bFadeInAfterNextDeath` | 1 |
| 318 | 1 | `bFadeInAfterNextArrest` | 1 |
| 319 | 12 | `ExtraHospitalRestartCoors` | (−2570.51, 1139.58, 54.85) |
| 331 | 4 | `ExtraHospitalRestartRadius` | 1500.00 |
| 335 | 4 | `ExtraHospitalRestartHeading` | 160.00 |
| 339 | 12 | `ExtraPoliceStationRestartCoors` | (−1379.84, 2635.74, 54.43) |
| 351 | 4 | `ExtraPoliceStationRestartRadius` | 1500.00 |
| 355 | 4 | `ExtraPoliceStationRestartHeading` | 170.62 |

Both radii are 1500 and both headings fall within 0–360, which is the check that
confirms the assignment is correct.

## Three fields that exist and are NOT saved

`CRestart` has three more symbols in memory that the serializer **does not
write**:

```
CRestart::OverrideHeading                      (4 B)
CRestart::bOverrideRespawnBasePointForMission  (1 B)
CRestart::OverrideRespawnBasePointForMission  (12 B)
```

The curious case is `OverrideHeading`: it sits right after `OverridePosition` in
memory, and the serializer writes the position and skips to the next field. The
proof is arithmetic — the final 55 bytes match exactly without it, and with it
there would be 59.

**If you edit the forced respawn point, you can change where you appear but not
which direction you face**: that data does not travel in the save.

## Practical use

One of the few things left with direct practical utility. By changing the 20 bytes
of a hospital point you choose where you respawn on death; by setting
`bOverrideRestart` to 1 and any `OverridePosition`, you force a specific location.
Watch out for the "when" field: if you set a value that your save has not yet
reached, that point is not used.

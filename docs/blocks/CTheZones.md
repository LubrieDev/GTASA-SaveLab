# Structure of the CTheZones block (block 10)

Extracted from `CTheZones::Save` @ `0x5697BC` in `libGame.so`.

## Layout

Offsets relative to the start of the data, after the 5 bytes of the `BLOCK` tag.

| offset | size | content |
|---:|---:|---|
| 0 | 4 | `m_CurrLevel` |
| 4 | 2 | `TotalNumberOfNavigationZones` |
| 6 | 2 | `TotalNumberOfZoneInfos` |
| 8 | 2 | `TotalNumberOfMapZones` |
| 10 | `n × 32` | `NavigationZoneArray` |
| … | `i × 17` | `ZoneInfoArray` |
| … | `m × 32` | `MapZoneArray` |
| … | 100 | `ZonesVisited` |
| … | 4 | `ZonesRevealed` |

The three arrays are **variable-length**: you must read the three header counters
before you can jump to any of them.

### In a reference save

```
m_CurrLevel                  = 1
TotalNumberOfNavigationZones = 379
TotalNumberOfZoneInfos       = 378
TotalNumberOfMapZones        = 7
ZonesRevealed                = 100

4+2+2+2 + 379*32 + 378*17 + 7*32 + 100 + 4 = 18892   = 18897 - 5 (tag)
```

## The zone record (32 bytes)

Applies to both `NavigationZoneArray` and `MapZoneArray`.

| offset | size | field |
|---:|---:|---|
| 0 | 8 | **zone name** (ASCII) |
| 8 | 8 | **text label** / GXT key (ASCII) |
| 16 | 2 | `X1` (int16) |
| 18 | 2 | `Y1` |
| 20 | 2 | `Z1` |
| 22 | 2 | `X2` |
| 24 | 2 | `Y2` |
| 26 | 2 | `Z2` |
| 28 | 4 | level, index, and flags |

**These are two distinct name fields, not one repeated.** In most zones they
match, but not always: the map zone `VEGAS` carries `UNUSED` as its label.

The coordinates are **`int16`, not floats** — the entire map fits within ±3000.

### Verification

```
zone 0  'SAN_AND'  (-2999,-2999,-2000) .. (3000, 3000, 2000)   <- the entire map
zone 4  'PARA'     (-2741,   793,    0) .. (-2533, 1268,  200)  <- Paradiso, San Fierro
```

## `ZoneInfoArray`

These are 378 records of **17 bytes**, one per navigation zone and in the same
order, with gang densities and territory colors. Broken down in
`CGangWars.md`.

```
ZoneInfo of zone z  ->  file offset  start_of_ZoneInfoArray + z*17
```

`ZonesVisited` are 100 loose bytes and `ZonesRevealed` a counter.

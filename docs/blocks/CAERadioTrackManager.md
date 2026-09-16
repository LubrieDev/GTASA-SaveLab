# Structure of the CAERadioTrackManager block (block 26)

Extracted from `CAERadioTrackManager::Save` @ `0x56EAF8` in `libGame.so`.

This is the radio state: which tracks each station has queued, which it has
already played, and a handful of mission flags the game uses to decide what the
DJ talks about.

## Layout

```
14 × 272 + 28 = 3836   = 3841 - 5 (tag)
```

The serializer is a loop over the stations followed by a batch of loose bytes:

```
+0x02cc  cmp x20, #14        <- 14 stations
+0x02c4  add x21, x21, #0xa0 <- advance 160 B in one array
+0x02c8  add x22, x22, #0x3c <- and 60 B in another
+0x02d0  b.ne +0x40          <- return to start of body
```

| offset | size | content |
|---:|---:|---|
| 0 | 14 × 272 | one station per record |
| 3808 | 28 | global flags and counters |

## The station record (272 bytes)

| offset | size | content | confidence |
|---:|---:|---|---|
| 0 | 20 | 20 loose bytes (indices for IDs, advertisements, and DJ commentary) | medium |
| 20 | 32 | 8 × `int32` | medium |
| 52 | 160 | **history**: 40 × `int32`, `-1` if empty | high |
| 212 | 60 | **track list**: 15 × `int32`, `-1` if empty | high |

The two long arrays come from their own internal loops, not from counting by eye:

```
+0x0280  add x26, x26, #0x4 ; +0x0284  cmp x26, #160   -> 40 int32
+0x02b4  add x26, x26, #0x4 ; +0x02b8  cmp x26, #60    -> 15 int32
```

`20 + 32 + 160 + 60 = 272`.

## Validation: the ID bands are disjoint

The eleven stations with a track list have their 15 tracks in **ID bands that do
not overlap and grow station to station**:

```
stn  n  ID band           duplicates
  0  15  0..36               0
  1  15  188..217            0
  2  15  320..353            0
  3  15  473..497            2
  4  15  770..815            0
  5  15  951..980            0
  6  15  1064..1081          0
  7  15  1216..1244          0
  8  15  1363..1387          0
  9  15  1496..1525          0
 10  15  1657..1696          0
 11   0  (empty)
 12   0  (empty)
 13   0  (empty)
```

It is exactly what you expect from a global track table distributed by station.
**With the wrong step the bands would mix**: any displacement causes the values of
one station to fall within the range of the next. The eleven remain disjoint.

Furthermore, within each list **there are no duplicates** (except two in station
3): it is a shuffle of that station's tracks, not a list with repetitions.

And the three empty records at the end fit: San Andreas has **11 stations with
track lists**, plus the talk-only and the user stations, which have nothing to
shuffle.

The history at `+52` is a different thing: its 333 used entries are all between 66
and 134, a narrow range shared across all stations, so **they are not track
IDs**. The exact meaning of these entries has not been identified.

## The final 28 bytes

All have names in `.dynsym`, so there is nothing to guess here — it is the
serializer's write order:

| byte | field | value |
|---:|---|---:|
| 0 | `m_nStatsCitiesPassed` | 4 |
| 1–19 | `m_nStatsPassedCasino3`, `Casino6`, `Casino10`, `Cat1`, `Desert1`, `Desert3`, `Desert5`, `Desert8`, `Desert10`, `Farlie3`, `LAFin2`, `Mansion2`, `Ryder2`, `Riot1`, `SCrash1`, `Strap4`, `Sweet2`, `Truth2`, `VCrash2` | 1 |
| 20–22 | `m_nStatsStartedBadlands`, `Cat2`, `Crash1` | 1 |
| 23 | `m_nStatsLastHitGameClockDays` | 3 |
| 24 | `m_nStatsLastHitGameClockHours` | 7 |
| 25 | `m_nStatsLastHitTimeOutHours` | 168 |
| 26 | `m_nSpecialDJBanterPending` | 3 |
| 27 | `m_nSpecialDJBanterIndex` | 13 |

These are the missions the DJ can already mention in the news. The clock time
is within 0–23; the 168-hour "timeout" is 7 days.

## Practical use

Changing this block only alters which song plays next and what the DJ talks about.
The interesting thing about the block is that **it closes 3,841 bytes to the
byte** and that it leaves 28 named fields identified.

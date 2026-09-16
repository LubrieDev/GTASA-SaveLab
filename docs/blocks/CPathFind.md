# Structure of the CPathFind block (block 5)

Extracted from `CPathFind::Save` @ `0x56C3B0` in `libGame.so`. Payload 1,432 bytes.

## Layout

```
4 + 51 × 28 = 1432
```

| offset | size | content |
|---:|---:|---|
| 0 | 4 | number of zones (value: 51) |
| 4 | 51 × 28 | the zones |

## The zone record (28 bytes)

The record is **6 floats and 2 flags**:

| offset | size | field |
|---:|---:|---|
| 0 | 24 | bounding box: `x1, x2, y1, y2, z1, z2` |
| 24 | 1 | flag A |
| 25 | 1 | flag B |
| 26 | 2 | padding |

These are the zones where scripts have turned off car or pedestrian routes
(`CPathFind::SwitchRoadsOffInArea` and `SwitchPedRoadsOffInArea`), which is what
the two flags suggest.

## Validation

All **51 of 51** bounding boxes are well-formed — `min < max` on all three axes —
and with X and Y within the map. That `x1, x2, y1, y2` ordering is not the usual
one (the normal order would be `x1, y1, z1, x2, y2, z2`), and it is exactly
what the check distinguishes: with a by-vector read, no box satisfies `min < max`.

Flag distribution: `(0,1)` ×33, `(1,0)` ×14, `(1,1)` ×2, `(0,0)` ×2.

## Block size

1,437 bytes total: 5-byte `BLOCK` tag + 1,432 bytes of payload.

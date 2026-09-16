# Structure of the C3dMarkers block (block 27)

Extracted from `C3dMarkers::SaveUser3dMarkers` @ `0x56F470` in `libGame.so`.

## Layout

**5 markers × 28 bytes**, unrolled.

| offset | size | field |
|---:|---:|---|
| 0 | 4 | type or state |
| 4 | 12 | **position** X, Y, Z (3 × float32) |
| 16 | 12 | color and flags |

These are the markers the player places manually on the map.

### Example values

```
0  ( 1685.70, -2238.90,   14.00)
1  (-1421.50,  -287.20,   14.60)
2  (  344.00,   305.10,  999.66)   <- high z: it is an interior
```

## Alignment warning

**Watch out for alignment:** the position **does not start at offset 0** of the
record, but at 4. Read from 0, the first marker comes out as
`(0, 1685.70, -2238.90)`, which looks like a position but is not. All placed
markers fall within the map when read from `+4`, and the third is at
`z ≈ 1000`, which is an interior — the same case that already appeared in the
object pool of block 2.

## Block size

145 bytes total: 5-byte `BLOCK` tag + 140 bytes of payload.

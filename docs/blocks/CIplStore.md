# Structure of the CIplStore block (block 21)

Extracted from `CIplStore::Save` @ `0x56DD98` in `libGame.so`.

## Layout

```
4 + 255 = 259
```

| offset | size | content |
|---:|---:|---|
| 0 | 4 | 256 — the pool capacity |
| 4 | 255 | one status byte per IPL |

These are the map object groups (IPL files) that can be toggled on and off. In a
reference save 254 are 0 and one is 1.

## The off-by-one

**The off-by-one is real and verified**: the first `u32` says 256 and behind it
there are 255 bytes, not 256. The serializer's loop walks the pool with
`cmp x22, #256` but does not write the first entry.

## Block size

264 bytes total: 5-byte `BLOCK` tag + 259 bytes of payload.

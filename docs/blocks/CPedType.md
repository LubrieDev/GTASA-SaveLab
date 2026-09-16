# Structure of the CPedType block (block 19)

Extracted from `CPedType::Save` @ `0x56DA5C` in `libGame.so`. Payload 640 bytes.

## Layout

**32 ped types × 20 bytes** (`cmp #640` with 5 writes of 4 per iteration).

Each record is **5 `int32`**, which come from five calls to
`CAcquaintance::GetAcquaintances(i)`: the bitmasks of which ped types each type
respects, hates, fears, etc.

18 of the 32 types have some non-zero value. They are 32-bit masks
(`786496`, `113920`…), not counters.

## Block size

645 bytes total: 5-byte `BLOCK` tag + 640 bytes of payload.

## Note

The exact breakdown of what each of the five masks represents has not yet been
determined.

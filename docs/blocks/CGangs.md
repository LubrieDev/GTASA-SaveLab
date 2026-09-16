# Structure of the CGangs block (block 11)

Extracted from `CGangs::Save` @ `0x56D3DC` in `libGame.so`. Payload 160 bytes.

## Layout

**10 gangs × 16 bytes**, with the ten writes unrolled in the code.

| offset | size | field |
|---:|---:|---|
| 0 | 3 | forced ped models (`int8`, −1 = none) |
| 3 | 1 | padding |
| 4 | 12 | **3 weapon IDs** (`int32`) |

### Weapon assignments

```
gang 0: weapons [22, 28,  0]      gang 5: weapons [24,  0,  0]
gang 1: weapons [24, 29,  4]      gang 6: weapons [22, 30,  0]
gang 2: weapons [22,  0,  0]      gang 7: weapons [22, 28,  0]
gang 3: weapons [ 0,  0,  0]      gang 8: weapons [ 0,  0,  0]
gang 4: weapons [22, 28,  0]      gang 9: weapons [ 0,  0,  0]
```

## Validation

The IDs that appear are **4, 22, 24, 28, 29, and 30**, all within
the GTA SA weapon range and all recognizable — knife, Colt 45, Desert Eagle,
Micro SMG, MP5, and AK-47. It is the typical gang armament. With the record
misaligned the numbers come out nonsensical.

## Block size

165 bytes total: 5-byte `BLOCK` tag + 160 bytes of payload.

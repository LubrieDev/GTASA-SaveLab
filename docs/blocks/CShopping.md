# Structure of the CShopping block (block 22) — clothing

Extracted from `CShopping::Save` @ `0x56DF74` in `libGame.so`.

## Layout

Offsets relative to the start of the data, after the 5 bytes of the `BLOCK` tag.

| offset | size | content |
|---:|---:|---|
| 0 | 4 | `ms_numPriceModifiers` |
| 4 | `n × 8` | `ms_priceModifiers` — `n` entries of 8 bytes |
| 4 + n×8 | 4 | `ms_numBuyableItems` |
| 8 + n×8 | `m` | `ms_bHasBought` — **1 byte per purchasable garment** |

## This block is variable-sized

Unlike `CGarages` or `CStats`, here **the size depends on two counters that are
inside the block itself**. `CShopping::Save` reads `ms_numBuyableItems` at runtime
and passes it as the length to `_SaveDataToWorkBuffer`:

```
ldr  w1, [x20, #0]        ; w1 = ms_numBuyableItems
ldr  x0, [GOT] -> ms_bHasBought
bl   _SaveDataToWorkBuffer
```

That is: **do not hardcode the offset of `ms_bHasBought`**. You must read
`ms_numPriceModifiers` first, skip `n × 8` bytes, read `ms_numBuyableItems`, and
only then does the garment array begin.

The in-memory limits are `ms_priceModifiers` = 160 B (max 20 entries) and
`ms_bHasBought` = 560 B (max 560 garments), but what is saved is whatever the
counters say, not the symbol size.

## Verification

In a reference save, block 22 (589 bytes):

```
ms_numPriceModifiers = 4     ->  32 bytes of modifiers
ms_numBuyableItems   = 544   -> 544 bytes of ms_bHasBought
total = 4 + 32 + 4 + 544     = 584 = 589 - 5 (tag)   MATCHES
```

Of the 544 purchasable garments, **117 have the byte set to non-zero**, meaning
purchased.

## What stats buying clothing affects

`CShopping::Buy` @ `0x44F4E4` calls `CStats::ModifyStat` with these IDs:

```
62, 31, 13, 55, 30, 14, 200, and four times 20
```

None of them is sex appeal or respect directly: those two are recalculated
separately, in `CStats::UpdateSexAppealStat` and `CStats::UpdateRespectStat`.
The ones above are the intermediate counters that feed that calculation — money
spent on clothing, garments per category, and so on.

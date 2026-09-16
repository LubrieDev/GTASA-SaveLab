# Structure of the CEntryExitManager block (block 25)

Extracted from `CEntryExitManager::Save` @ `0x56E7B4` in `libGame.so`.
See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are interior entrances: shop doors, houses, and garages. The block **does
not store positions** — those come from the `.dat` and do not change — only the
state of each entry and how they are linked.

## Layout

```
4 + 2×1 + 376×6 + 2 = 2264   = 2269 - 5 (tag)
```

Matches to the byte.

| offset | size | content |
|---:|---:|---|
| 0 | 4 | `ms_entryExitStackPosn` (value: 1) |
| 4 | `posn × 2` | `ms_entryExitStack`, **only the used entries**, not all 16 in the array |
| 6 | 376 × 6 | one record per linked entry/exit |
| 2262 | 2 | `0xFFFF`, terminator |

The stack matters: `ms_entryExitStack` is 32 bytes in memory (16 `u16`), but the
serializer writes **only `stackPosn` entries**. If you reserve 32 fixed bytes,
everything after it shifts.

## The record (6 bytes)

The three fields come from the three writes in the loop, reading what each puts
into the buffer:

```
+0x00c8  strh w22, [x0]        <- w22 = index of the CEntryExit in the pool
+0x00e0  ldrh w8, [x23, #48]   <- x23 = the CEntryExit (64 B); +48 is its flags
+0x00ec  strh w8,  [x0]
+0x00b4  mov  w24, #65535      <- default "no link"
+0x010c  strh w24, [x0]        <- index of the next linked entry
```

| offset | size | field | confidence |
|---:|---:|---|---|
| 0 | 2 | **index in the pool** of entries/exits | high |
| 2 | 2 | **flags** (the `u16` at `CEntryExit+48`) | high |
| 4 | 2 | **linked index**, `0xFFFF` if none | high |

The pool element size is **64 bytes** (`add x21, x21, #0x40`) and the pool has
**455 slots** (`cmp x22, #455`). The 64 bytes match what already appeared in
[CRadar.md](CRadar.md), where `CRadar::Save` converts a
`CEntryExit` pointer to an index by dividing by 64.

## Validation

Everything is internal to the file, but it fits without slack:

- **The index field is exactly `0, 1, 2, … 375`**, without a single gap. The 376
  used pool slots are the first ones and are in order.
- All 376 indices are less than 455, the pool size.
- Of the 376 records, **67 have no link** (`0xFFFF`) and the other 309 point to
  an index between 0 and 370: **all fall within the array itself**. None goes
  out of bounds, which is what would happen with a misaligned record.
- The `0xFFFF` terminator is in the last two bytes of the block.
- The flags use bits 0–6, 8, 10, 12, 13 and 14. Bit 14 appears in 296 of the
  376 and bit 2 in 230; the rest are minority. None have been identified yet.

## Cross-check with CRadar

Each radar blip stores in its `+32` **the index of this pool plus one**, so the
blip indices would have to fall within the range here.

In a reference save, all 250 blips may have that field set to zero. None
is hooked to an interior entry, so there is nothing to cross-reference.

What is confirmed by two independent paths is the **64-byte size** of the pool
element: here by the loop step, and in `CRadar` by the divisor it uses to convert
the pointer to an index.

## What is not here

The positions of the entries, their names, and which interior they lead to **are
not stored in the save**: they come from the `.dat` loaded by
`CFileLoader::LoadEntryExit`. In the save only what changes is stored — the flags
and the links.

# Structure of the CStuntJumpManager block (block 24)

Extracted from `CStuntJumpManager::Save` @ `0x56E5C4` and
`CStuntJumpManager::AddOne` @ `0x4509D4` in `libGame.so`.
See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are the 70 unique stunt jumps of San Andreas: where each starts, where you
must land, where the camera is placed, and whether you have done it.

## Layout

`CStuntJumpManager::Save` writes two things:

```
+0x0034   _SaveDataToWorkBuffer(4)    <- CStuntJumpManager::m_iNumJumps
+0x00ac   _SaveDataToWorkBuffer(68)   <- one record per jump, in a loop
```

```
4 + 70 × 68 = 4764   = 4769 - 5 (tag)
```

Matches to the byte. `m_iNumJumps` is 70 in the file, the number of unique jumps
the game ships with.

| offset | size | content |
|---:|---:|---|
| 0 | 4 | `m_iNumJumps` |
| 4 | 70 × 68 | the jumps |

The loop walks the `mp_poolStuntJumps` pool and copies the record **whole and
untouched**: `ldr q0` / `ldp q1,q0` / `ldr q2` and one `ldr w8` for the last 4
bytes, `16 + 16 + 32 + 4 = 68`. There is no compression or reordering.

## The record (68 bytes)

The breakdown comes from `AddOne(const CBoundBox&, const CBoundBox&, const CVector&, int)`,
which creates them when loading the `.dat`:

| offset | size | field | confidence |
|---:|---:|---|---|
| 0 | 24 | **start box** — `CBoundBox`, 2 × `CVector` (min, max) | high |
| 24 | 24 | **landing box** — `CBoundBox` | high |
| 48 | 12 | **camera position** — `CVector` | high |
| 60 | 4 | **reward** (500 in all 70) | high |
| 64 | 1 | **completed** (0/1) | high |
| 65 | 1 | **found** (0/1) | high |
| 66 | 2 | padding, zero in all 70 | high |

The offsets come from following the arguments of `AddOne` one by one:

```
+0x008c  ldr  q0, [x0]      ; +0x0094  str  q0, [x9, #0]     box 1, bytes  0..15
+0x0088  ldr  x10,[x0,#16]  ; +0x0090  str  x10,[x9, #16]    box 1, bytes 16..23
+0x009c  ldr  q0, [x1]      ; +0x00a4  stur q0, [x9, #24]    box 2, bytes 24..39
+0x0098  ldr  x10,[x1,#16]  ; +0x00a0  str  x10,[x9, #40]    box 2, bytes 40..47
+0x00a8  ldr  x10,[x2]      ; +0x00b4  str  x10,[x9, #48]    camera, x and y
+0x00ac  ldr  w11,[x2,#8]   ; +0x00bc  stp  w11, w3,[x9,#56] camera z, and reward at +60
+0x00b0  strh wzr, [x9, #64]                                 state to zero
```

`AddOne` sets the state to zero with a 2-byte `strh`, and `Save` dumps it with a
4-byte `str`: that is why `+64` is a 4-byte field of which only the first two
bytes are used.

## Cross-validation with CStats

This is the strong one, because it does not depend on the reading of the block.

Counting the status bytes of the 70 records yields **21 found and 11 completed**.
And in block 16 ([CStats.md](CStats.md)):

```
stat 144 = 21     <- unique jumps found
stat 145 = 11     <- unique jumps completed
```

Two **consecutive** stats, with the exact two values, calculated from two
different blocks of the file that do not know about each other. With the record
misaligned by a single byte, both numbers change and cease to match.

Incidentally, this identifies what stats 144 and 145 are, which were previously
unnamed.

Which byte is which also comes from the data itself: the `+64` field values are
`0` (49 times), `0x0100` (10), and `0x0101` (11). **There is not a single
`0x0001`**, meaning no completed jump is not also found — which forces the low
byte to be "completed" and the high byte "found", and not the other way around.

All 1050 coordinates (70 × 15 floats) fall within the map.

## Practical use

Marking all 70 as completed means setting bytes `+64` and `+65` of each record
**and** adjusting stats 144 and 145 to 70. If you touch only one of the two, the
game shows a counter and a map that do not agree.

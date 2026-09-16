# Structure of the CSetPieces block (block 17)

Extracted from `CSetPieces::Save` @ `0x56D9B0`, `CSetPieces::AddOne` @ `0x44CA70`,
and `CSetPiece::Update` @ `0x44CBB4` in `libGame.so`.
See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are the ambushes: map locations where, if you pass through with the
appropriate wanted level, the game spawns cars or police officers from a spawn
point toward an objective.

## Layout

`CSetPieces::Save` writes two things and that is it:

```
+0x002c   _SaveDataToWorkBuffer(4)      <- CSetPieces::NumSetPieces
+0x005c   _SaveDataToWorkBuffer(6720)   <- CSetPieces::aSetPieces, the entire array
```

```
4 + 6720 = 6724   = 6729 - 5 (tag)
```

Matches to the byte on the first try. The array is **fixed**: all 210 records are
saved even if only the first `NumSetPieces` are in use.

| offset | size | content |
|---:|---:|---|
| 0 | 4 | `NumSetPieces` (how many are in use) |
| 4 | 6720 | 210 records of 32 bytes |

The 210 and 32 come from `AddOne`:

```
+0x000c  cmp   w9, #0xd1              <- 209
+0x0010  b.gt  ret                    <- indices 0..209
+0x002c  add   x10, x10, x9, lsl #5   <- 32 bytes per record
```

`210 × 32 = 6720`.

## The record (32 bytes)

| offset | size | field | confidence |
|---:|---:|---|---|
| 0 | 4 | **last generation**, in ms from `CTimer` | high |
| 4 | 4 | **corner 1** of the activation rectangle (x, y) | high |
| 8 | 4 | **corner 2** of the rectangle | high |
| 12 | 4 | **spawn 1** (x, y) | medium |
| 16 | 4 | **spawn 2** | medium |
| 20 | 4 | **target 1** (x, y) | medium |
| 24 | 4 | **target 2** | medium |
| 28 | 1 | **type** (1–8) | high |
| 29 | 3 | padding, always zero | high |

The six points are `CVector2D`, which is exactly what the signature of
`AddOne(uchar, CVector2D, CVector2D, CVector2D, CVector2D, CVector2D, CVector2D)`
asks for. `AddOne` writes them in two NEON bursts:

```
+0x0090  stur  q0, [x10, #4]     <- 16 B: the first 4 compressed points
+0x008c  stur  d1, [x10, #20]    <-  8 B: the last 2
+0x0044  strb  w0, [x10, #28]    <- the type
```

### The coordinates are int16 with 2 fractional bits

They are not floats or half-floats: they are fixed-point `int16`, **divided by
4**. The scale does not need to be guessed, it is in the converter of
`CSetPiece::Update`:

```
+0x0064  ldrsh w8, [x19, #4]
+0x0068  scvtf s2, w8, #2        <- convert to float with 2 fractional bits = /4
+0x006c  fcmp  s0, s2
```

Reading them as half-floats (`fp16`) does not hold: the first
value of record 0 would come out as `0.0158` and the second as `-1227.6`, which
are not a pair of coordinates.

### The rectangle and the cooldown

The four `int16` from `+4` to `+11` are each read **exactly once**, right after
`FindPlayerCoors` and compared with `fcmp` against the player's position: they are
the box that triggers the ambush. The other four points are read 11, 11, 6, and 5
times throughout `Update`, grouped in pairs — hence why they are presented as two
spawn/target pairs, but **which is which within each pair has not been
demonstrated**, it is only consistent with the read counts.

Field `+0` is a cooldown:

```
+0x0038  ldr   w8, [x19, #0]
+0x003c  cbz   w8, proceed          <- if never generated, go ahead
+0x0044  mov   w10, #40000
+0x0048  ldr   x9, [x9, #792]      <- &CTimer::m_snTimeInMilliseconds
+0x004c  add   w8, w8, w10         <- last time + 40 s
+0x0054  cmp   w9, w8
+0x0058  b.??  exit                <- not yet
```

**40,000 ms wait** between generations of the same ambush. `Update` writes `+0` in
six different places.

## Cross-validation

`NumSetPieces` = **209** of 210. The remaining record is entirely zero, and the 3
bytes of padding of all 210 records are zero: there is no leaked memory here,
because the array is initialized in full and saved as-is.

The 1254 coordinates (209 × 6 points), divided by 4:

```
X  -2829.0 ..  2893.0
Y  -2446.0 ..  2716.0
0 outside the map (+-3000)
```

The scale test rules out alternatives:

| scale | coordinates outside the map |
|---|---:|
| undivided | 1254 of 1254 |
| /2 | 1142 |
| **/4** | **0** |
| /8 | 0 |

The file alone cannot distinguish `/4` from `/8` — both fit in the map — and that
is why the `scvtf ..., #2` was needed. With `/8` all ambushes would be squeezed
into `±1450`, a central square; with `/4` they spread across the entire map, which
is what you expect from 209 ambushes.

Internal consistency check: of the 836 spawn and target points, **833 fall within
150 units of the center of their own rectangle**. With misaligned offsets this
breaks. The 3 outliers are all in the same record (11), where one value appears
with its sign flipped relative to its neighbors; it seems to be odd game data, not
a mapping error.

Distribution by type:

```
type 2: 80    type 3: 42    type 6: 22    type 5: 20
type 7: 18    type 4: 13    type 1: 11    type 8:  3
```

The type has not been identified. `Update` reads it with `ldrb` in three
places to decide whether to spawn a car or a pedestrian
(`CSetPiece::TryToGenerateCopCar` and `TryToGenerateCopPed`), but the branching
has not been followed.

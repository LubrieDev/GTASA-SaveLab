# Structure of the CRadar block (block 9)

Extracted from `CRadar::Save` @ `0x56CE20` and `CRadar::Load` @ `0x56CF94` in
`libGame.so`. See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are the map and radar icons: houses, shops, mission points, coordinate
markers placed by scripts.

## Layout

It is a **regular array without header**: 250 records of 40 bytes, one per blip
slot, saved or not.

```
250 × 40 = 10000   = 10005 - 5 (tag)
```

Matches to the byte. The block starts right where block 9 begins in the save
and ends right where block 10 begins.

Three independent confirmations of 250 in the binary:

| symbol | size | reasoning |
|---|---:|---|
| `CRadar::ms_RadarTrace` | 12000 B | 250 × 48 (the in-memory entry) |
| `CRadar::MapLegendList` | 500 B | 250 × 2 |
| `CRadar::RadarBlipSprites` | 512 B | 64 pointers → sprites 0–63 |

The `Save` loop is visibly unrolled:

```
+0x0024  mov   w23, #250            <- counter
+0x0028  ldr   x20, [x20, #144]     <- &CRadar::ms_RadarTrace
+0x0034  add   x20, x20, #0x30      <- advance 48 bytes per iteration
+0x00dc  mov   w0, #40
+0x00ec  bl    malloc               <- one 40-byte record per blip
+0x0128  bl    _SaveDataToWorkBuffer(40)
+0x0130  bl    free
```

## The record (40 bytes)

The in-memory entry is 48 bytes; the serializer copies field by field and omits
the struct padding.

| offset | size | field | source | confidence |
|---:|---:|---|---:|---|
| 0 | 4 | **color** (`m_nColour`) | trace +0 | high |
| 4 | 4 | **entity handle** | trace +4 | high |
| 8 | 4 | **X** (float) | trace +8 | high |
| 12 | 4 | **Y** (float) | trace +12 | high |
| 16 | 4 | **Z** (float) | trace +16 | high |
| 20 | 2 | **unique index** (generation counter) | trace +20 | high |
| 22 | 2 | *padding, never written* | — | — |
| 24 | 4 | **sphere radius** (float, always 1.0) | trace +24 | medium |
| 28 | 2 | **blip size** (`m_nBlipSize`) | trace +28 | high |
| 30 | 2 | *padding, never written* | — | — |
| 32 | 4 | **`CEntryExit` index + 1**, 0 if none | trace +32 | high |
| 36 | 1 | **sprite** (0–63) | trace +40 | high |
| 37 | 2 | **bitfield** (14 usable bits) | trace +41 | high |
| 39 | 1 | *padding, never written* | — | — |

The names come from `CRadar`'s setters, which write each offset directly. There is
no proximity matching:

```
CRadar::ChangeBlipColour(int, uint)      ->  str   w1, [x8, #0]
CRadar::SetEntityBlip(...)               ->  stp   w11, w1, [x8, #0]   (color, handle)
CRadar::SetCoordBlip(...)                ->  stp   s0, s1, [x8, #8]    (X, Y)
                                             str   s2, [x8, #16]       (Z)
CRadar::ChangeBlipScale(int, int)        ->  strh  w9, [x8, #28]
CRadar::SetBlipEntryExit(int, CEntryExit*) -> str  x1, [x8, #32]
CRadar::SetBlipSprite(int, int)          ->  strb  w1, [x8, #40]
```

Offset 37 goes **unaligned** (`sturh`), as is the case for the entire format.

## The bitfield (+37)

Only the lower 14 bits are saved: `and w21, w8, #0x3FFF`. Bits 14 and 15 exist
in memory, `ClearBlip` preserves them, and the save **does not touch them** — on
load, `Load` does `bfxil` of the 14 saved bits over the value left by
`Initialise`.

| bit(s) | meaning | who writes it |
|---:|---|---|
| 0 | brightness (`bright`), 1 by default | `ChangeBlipBrightness` |
| 1 | **slot in use** | `SetCoordBlip` / `SetEntityBlip` (`orr #3`) |
| 2 | short range | `SetShortRangeCoordBlip` (`orr #7`) |
| 3 | friendly | `SetBlipFriendly` |
| 4 | always visible when zooming | `SetBlipAlwaysDisplayInZoom` |
| 5 | faded (`fade`) | `SetBlipFade` |
| 6–7 | coordinate blip appearance | `SetCoordBlipAppearance` |
| 8–9 | **draw mode** (`eBlipDisplay`) | `ChangeBlipDisplay` |
| 10–13 | **blip type** (`eBlipType`) | `SetCoordBlip` / `SetEntityBlip` |
| 14–15 | not saved | — |

The positions come from decoding the logical immediates and the
`UBFIZ`/`BFI` of each setter, not from assuming the bitfield order in the struct.

The type occupies **4 bits starting at 10**, not 3 starting at 11. It is easy to
get wrong because `Save` only checks bits 11–13.

The enum matches the PC version:

| type | name | check |
|---:|---|---|
| 0 | `BLIP_NONE` | free slot |
| 1–3 | `BLIP_CAR`, `BLIP_CHAR`, `BLIP_OBJECT` | `SetEntityBlip` sets color 7 (`sub w11,w0,#1; cmp w11,#2; csel 7`) |
| 4 | `BLIP_COORD` | `SetCoordBlipAppearance` requires `bits10-13 == 4` |
| 5 | `BLIP_CONTACT_POINT` | — |

## Only coordinate blips survive

This is the important thing about the block and it is not visible in the file,
only in the code:

```
+0x009c  ldr   x8, [x8, #1624]      <- &IsMissionSave
+0x00a0  ldrb  w9, [x8, #0]
+0x00a8  tbz   w9, #0, +0xb4        <- normal save -> continues checking
+0x00b4  and   w9, w8, #0x3800      <- bits 11..13 = type >> 1
+0x00bc  cmp   w9, #0x1000          <- is type 4 or 5?
+0x00c0  b.eq  +0xd4                <- yes: saved as-is
+0x00c4  tbz   w8, #1, +0xd4
+0x00c8  and   w8, w8, #0xFFFFFFFD  <- no: clears "in use" bit IN THE COPY
+0x00d0  sturh w8, [x20, #41]
...
+0x013c  cbz   w26, +0x30
+0x0140  ldurh w8, [x20, #41]
+0x0144  orr   w8, w8, #0x2         <- and restores it in memory after writing
```

In a **normal save**, every blip whose type is not 4 or 5 is saved with the "in
use" bit cleared: on load it reappears as a free slot. That is, blips attached to
a car, pedestrian, or object do not survive saving, logically because the entity
does not either. In a **mission save** (`IsMissionSave != 0`) the filter is not
applied and all are saved.

The game clears the bit in the copy and re-enables it in memory after writing, so
saving does not erase blips from the current session.

## Old saves have 175 blips, not 250

`Load` decides how many records to read based on the slot version:

```
+0x0034  ldr   x8, [x8, #2248]      <- &CGenericGameStorage::m_currentSlotVersionNumber
+0x0038  mov   w9, #250
+0x004c  cmp   w8, #0x4
+0x0050  mov   w8, #175
+0x0058  csel  x21, x8, x9, lt      <- version < 4 ? 175 : 250
```

175 is the `MAX_RADAR_TRACES` from the PC version. `Save` always writes 250, so
the block is 10005 bytes in any mobile save; the 175 path only exists for reading
inherited saves.

## The blip handle that scripts see

All setters start the same way:

```
and   w8, w0, #0xFFFF          <- index in the array (low part)
madd  x10, x8, #48, base       <- &ms_RadarTrace[idx]
ldrh  w11, [x10, #20]
cmp   w11, w0, lsr #16         <- the unique index must match
b.ne  ret                      <- if not, the blip was reused: do nothing
ldurh w10, [x10, #41]
tbz   w10, #1, ret             <- and the slot must be in use
```

The handle is `(uniqueIndex << 16) | arrayIndex`. Field `+20` of the record is
that unique index, and that is why it must be saved: without it the handles
scripts have stored in globals would point to wrong blips after loading.

## Cross-validation

**153 blips in use, in slots 0–152; 97 free, all at the end.** Distribution:

| field | values |
|---|---|
| type | 4 (`BLIP_COORD`) ×100, 5 (`BLIP_CONTACT_POINT`) ×53 |
| draw mode | 3 ×109, 2 ×43, 0 ×1 |
| short range | yes ×152, no ×1 |
| color | 8 in all 153 (the constant `SetCoordBlip` loads) |
| entity handle | 0 in all 153 |
| radius | 1.0 in all 153 |
| sprite | 22 distinct sprites, max 63 |

That all 153 are type 4 and 5 is exactly what the `Save` filter predicts, and
that the color is 8 in all of them confirms that `+0` is the color:
`SetCoordBlip` does not compute it, it copies it from an 8-byte constant `(8, 0)`
loaded with a single `ldr d0`.

The strong cross-check is against another already-mapped block. Taking the
positions of the 50 garages from block 3
([CGarages.md](CGarages.md)) and searching for blips within
40 units:

```
35 of the ~40 real garages have a blip; 6 match to the centimeter
garage 11 ( 1021.8,-1018.7)  <->  blip  41 ( 1021.8,-1018.7)
garage 15 (-2728.5,  212.3)  <->  blip   0 (-2728.5,  212.2)
garage 18 (-1941.0,  251.7)  <->  blip 121 (-1941.0,  251.7)
garage 19 (-1908.9,  292.4)  <->  blip  44 (-1908.9,  292.3)
garage 33 ( 2382.3, 1044.0)  <->  blip 132 ( 2382.2, 1044.0)
garage 41 ( -103.6, 1112.4)  <->  blip  43 ( -103.6, 1112.4)
```

With the position at another offset none match.

## Traps of this block

**Bytes 22, 23, 30, 31, and 39 of each record are not written by anyone.** They
are padding from the 48-byte struct that the serializer does not fill in the
`malloc(40)`. In a reference save all 250 come out zero, but **it is not guaranteed**: the
40-byte chunk is reused on each loop iteration and retains whatever was there.
That is 1250 bytes per file that can differ in a differential without anything
having been touched.

**Free slots retain stale data.** `ClearBlip` only writes `+24`, `+28`, `+32`,
`+40`, and `+41`; the color, entity handle, and position remain as they were. In
a reference save there are free slots with colors like `0xFFC1BFFF` and positions of
blips that have already been deleted. **To know if a slot is occupied you must
check bit 1 (or the type), never whether the fields are zero.**

**The first field is 8 bytes copied at once** (`ldr d0` / `str d0`), but they are
two distinct `uint32` values: color and handle. Reading them as a `double` or as
a 64-bit pointer leads nowhere.

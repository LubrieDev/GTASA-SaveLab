# Structure of the CTheCarGenerators block (block 12)

Extracted from `CTheCarGenerators::Save` @ `0x56D0BC` in `libGame.so`.
See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are the cars that respawn at fixed locations on the map.

## Layout

Offsets relative to the start of the data, after the `BLOCK` tag.

| offset | size | content |
|---:|---:|---|
| 0 | 4 | number of generators **saved** |
| 4 | 1 | `ProcessCounter` |
| 5 | 1 | `GenerateEvenIfPlayerIsCloseCounter` |
| 6 | `n × 34` | generators: 2 B of index + 32 B of data |
| … | 4 | `m_SpecialPlateHandler` |
| … | `15 × 16` | custom license plates |

In a reference save:

```
4 + 1 + 1 + 208*34 + 4 + 15*16 = 7322   = 7327 - 5 (tag)
```

Matches to the byte, and the block ends at 136253, right where block 13 starts.

## Not all generators are saved

The loop **filters**: it checks two bytes of each in-memory array entry and only
writes the one that passes both tests.

```
+0x00a4  add   x20, x20, #0x20     <- walks the array in steps of 32
+0x00b0  ldurb w8, [x20, #-1]
+0x00b4  cbnz  w8, next            <- if != 0, not saved
+0x00b8  ldrb  w8, [x20, #0]
+0x00bc  cbz   w8, next            <- if == 0, not saved
+0x00d4  strh  w21, [x0]           <- saves the INDEX in the array
+0x00d8  _SaveDataToWorkBuffer(2)
+0x00fc  _SaveDataToWorkBuffer(32) <- and the 32 B of data
```

That is why each record starts with its index: **the file is sparse**. In a
reference save the indices go from 35 to 242, strictly increasing, with 208 entries saved
from a larger array.

**Practical consequence:** you cannot index by position in the file. To reach
generator `k` you must walk the records reading the index of each one.

## The record (2 + 32 bytes)

| offset | size | field | confidence |
|---:|---:|---|---|
| 0 | 2 | **index in the array** (u16) | high |
| 2 | 2 | **vehicle model** (int16) | high |
| 4 | 2 | −1 constant (second model, unused?) | medium |
| 6 | 30 | **unidentified** | — |

The model is confirmed: **205 of the 208 records have an int16 in `+2` within the
GTA SA vehicle range (400–611)**. With a wrong offset this does not come out.

The remaining 30 bytes have not been resolved. Reading the position as three
floats and as three `int16` (as `CTheZones` stores them) at the 27 possible
offsets, and the best case gives 148 of 208 — not enough to assert it. There are
several constant values across records (`10000`, `4608`, `0xFFFFFFFF`, `256`) that
point to timers and flags, but they have not been identified.

## Custom license plates

The 15 records of 16 bytes at the end are directly readable:

```
136013  33 00 00 00 | " SHERM  "
136029  34 00 00 00 | "GROVE4L "
136045  63 00 00 00 | "HOMEGIRL"
136061  64 00 00 00 | "  NOS   "
```

Format: **4 bytes of index + 8 ASCII characters + 4 zero bytes**. The text is
justified to 8 characters with spaces.

# GTA San Andreas Mobile Save Format

## Overview

The save file is a sequence of blocks. Each block is preceded by the 5-byte ASCII literal `BLOCK`. The file has no global header beyond the first block's tag. The last 4 bytes of the file are a checksum.

| Property | Value |
|---|---|
| Size | Variable (observed 195000 and 260000 bytes) |
| Blocks | 29 (delimited by `BLOCK` markers) |
| Checksum | uint32 LE = `sum(data[:-4]) & 0xFFFFFFFF` |
| Platform | Android (arm64-v8a) |

## The 65000-byte buffer

The game reads and writes the save through a 65000-byte work buffer. The file is effectively 3 dumps of this buffer. Actual data ends at offset 184573; everything after is stale remnants from previous buffer fills. The file size must be a multiple of 4 bytes — this is the only size restriction.

## Checksum algorithm

```python
def calc_checksum(data: bytes) -> int:
    return sum(data[:-4]) & 0xFFFFFFFF

def verify(data: bytes) -> bool:
    return calc_checksum(data) == struct.unpack_from("<I", data, len(data) - 4)[0]
```

The checksum covers ALL preceding bytes, including the trailing garbage. It is validated by the menu (not the loader). The binary implementation processes 32 bytes at a time in a vectorized loop, then handles the scalar tail.

## Platform discrimination

A PC save passes the same checksum algorithm. Distinguish platforms by:

| Property | Mobile | PC |
|---|---|---|
| Script globals | **49212** | **43808** |
| Block 0 (SimpleVars) size | 433 bytes | 317 bytes |
| Save name encoding | UTF-16 | ANSI |

Size and block count vary between saves on the same platform and are NOT reliable discriminators.

The two platforms use different `main.scm` files, so global variable *n* on mobile is not the same as global *n* on PC. They are not convertible. However, in the low globals region (~1000–4000), the two platforms align with a +4 byte offset at 85–92% match rate.

## Format version

The uint32 at offset 0 of block 0 (byte 5 of the file) is a CRC-32 of the literal `"GTASA%d"` for N = 0…4, computed with `CKeyGen::GetKey` (reflected CRC-32, init 0xFFFFFFFF, no final complement).

| Value in file | Version |
|---|---|
| `0x131AECDA` | 0 |
| `0x641DDC4C` | 1 |
| `0xFD148DF6` | 2 |
| `0x8A13BD60` | 3 |
| `0x147728C3` | **4** (current) |

Version effects:
- ≤ 1: save is rejected
- 2: data fence markers interleaved between fields
- ≥ 3: block 28 (CPostEffects) is read
- ≥ 4: CRadar saves 250 blips (below that, 175)

## Block structure

Each block starts with the 5-byte `BLOCK` tag, followed by the block's data. There is no length field — the size is determined by the reader field by field. The 29 blocks are traversed in execution order by `GenericSave`/`GenericLoad` in the binary.

12 of the 29 blocks are variable-sized (they carry the record count within the file). The other 17 have fixed sizes imposed by the binary.

See [Block Map](block-map.md) for the complete table.

## What the game validates on load

See [Loading Flow](loading-flow.md) for full details. Summary:

1. Checksum is the only global validation (checked by menu, not loader)
2. File must measure a multiple of 4 bytes
3. The 29 `BLOCK` markers are validated block by block with `strncmp`
4. Each block must consume exactly what its `::Load` reads
5. There is not a single upper-bound check — a bad counter overflows the destination array

## Record boundaries

The 5-byte `BLOCK` tag means fields can fall on non-4-byte offsets. Any scan for patterns must go byte-by-byte. The format is NOT aligned.

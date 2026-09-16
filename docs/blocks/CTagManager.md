# Structure of the CTagManager block (block 20)

Extracted from `CTagManager::Save` @ `0x56DCA0` in `libGame.so`.

## Layout

```
4 + 100 = 104
```

| offset | size | content |
|---:|---:|---|
| 0 | 4 | `ms_numTags` (value: 100) |
| 4 | 100 | the **alpha** of each tag, one byte |

The 100 tags of San Andreas. In a reference save: 95 at `255` and five at `240`,
`232`, `232`, `240`, and `248`.

## Tag completion threshold

The threshold comes from the code, not from assumption: `CTagManager::UpdateNumTagged`
walks the tags reading the `+8` byte of each 16-byte descriptor and counts those
with **alpha ≥ 229** (`cmp w12, #229`). Tags at or above this threshold count as completed.

## Block size

109 bytes total: 5-byte `BLOCK` tag + 104 bytes of payload.

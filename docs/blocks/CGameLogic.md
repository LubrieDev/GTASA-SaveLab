# Structure of the CGameLogic block (block 4)

Extracted from `CGameLogic::Save` @ `0x56C1B0` in `libGame.so`. Payload 11 bytes.

## Layout

| offset | size | field | value |
|---:|---:|---|---:|
| 0 | 4 | `NumAfterDeathStartPoints` | 0 |
| 4 | 1 | `bPenaltyForDeathApplies` | 0 |
| 5 | 1 | `bPenaltyForArrestApplies` | 0 |
| 6 | 1 | `GameState` | 0 |
| 7 | 4 | `TimeOfLastEvent` | 514962609 |

```
4 + 1 + 1 + 1 + 4 = 11
```

## This block is variable-sized

After `TimeOfLastEvent` there is a loop that
writes 12 + 4 bytes per respawn point, but `NumAfterDeathStartPoints` is 0 and it
never runs. In a save where it has a different value, this block is larger than
16 bytes.

## Block size

16 bytes total: 5-byte `BLOCK` tag + 11 bytes of payload (when `NumAfterDeathStartPoints` is 0).

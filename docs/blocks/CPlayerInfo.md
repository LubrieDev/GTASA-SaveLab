# Structure of the CPlayerInfo block (block 15) — money

Extracted from `CPlayerInfo::Save` @ `0x56D604` in `libGame.so`.

## Layout

The block consists of two writes: a `u32` with the size, and a 40-byte struct
(the binary calls it `CPlayerInfoSaveStructure`).

| offset in data | size | content |
|---:|---:|---|
| 0 | 4 | struct size (40) |
| 4 | 40 | `CPlayerInfoSaveStructure` |

`4 + 40 = 44` = the 49 bytes of the block minus the tag. Matches.

## The 40-byte struct

Offsets relative to the start of the struct. The "source" column is the offset
within `CPlayerInfo` in memory.

| offset | size | source | field |
|---:|---:|---|---|
| 0 | 4 | `+240` | **money** |
| 4 | 2 | `+364` | camera (`CCamera::Init`, `AvoidTheGeometry`) |
| 6 | 1 | `+280` | player state (`CGameLogic::Update`) |
| 7 | 1 | — | **padding** |
| 8 | 4 | `+368` | unidentified float |
| 12 | 4 | `+244` | **money shown on HUD** |
| 16 | 1 | `+384` | energy / hunger (`WorkOutEnergyFromHunger`) |
| 17 | 3 | — | **padding** |
| 20 | 8 | `+248` | two unidentified `u32` |
| 28 | 8 | `+392` | unidentified |
| 36 | 1 | `+400` | state (`ArrestPlayer`, `CGameLogic::Update`) |
| 37 | 1 | — | **padding** |
| 38 | 2 | `+402` | unidentified |

Bytes 7, 17-19, and 37 are not written by anyone and may contain stack garbage —
do not interpret them as data.

## There are two money fields and both must be edited

```
struct+0   = CPlayerInfo+240   actual money
struct+12  = CPlayerInfo+244   HUD money
```

The first is modified by collectibles (`CPickups::PickedUpOyster`,
`PickedUpHorseShoe`, `PictureTaken`) and the game logic. The second is read by
`CWidgetPlayerInfo::Draw`, i.e. the HUD: it is the value visible on screen that
animates upward to reach the actual value.

**If you edit only one, the HUD and the actual balance become desynchronized.**

## Unidentified

The fields at `+8`, `+20`, `+28`, and `+38` are saved and restored, but have not
been determined. The source offsets in `CPlayerInfo` are not touched by
any named function descriptive enough to deduce it. If any of them are needed,
it comes out with a differential test.

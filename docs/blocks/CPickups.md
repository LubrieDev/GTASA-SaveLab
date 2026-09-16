# Structure of the CPickups block (block 6)

Extracted from `CPickups::Save` @ `0x56C4D0` in `libGame.so`.

## Layout

Offsets relative to the start of the data, after the 5 bytes of the `BLOCK` tag.

| offset | size | content |
|---:|---:|---|
| 0 | 19840 | `aPickUps` — **620 records of 32 bytes** |
| 19840 | 2 | `CollectedPickUpIndex` |
| 19842 | 1 | `DisplayHelpMessage` |
| 19843 | 80 | `aPickUpsCollected` — 20 × u32 |

`620 × 32 + 2 + 1 + 20 × 4 = 19923` = the 19928 bytes of the block minus the
tag.

The number 620 is a literal in the code (`mov w21, #620`); it is not a counter
read from the file. The step in memory is 36 bytes per entry
(`add x20, x20, #0x24`), of which 32 are saved: `CPickup+8..11` **is not
written**.

## The 32-byte record

| offset | size | field | confidence |
|---:|---:|---|---|
| 0 | 4 | value (float) — amount in money pickups | high |
| 4 | 4 | always 0 in reference saves | — |
| 8 | 4 | the same value, as integer | medium |
| 12 | 12 | **unidentified** — see below | — |
| 24 | 2 | **model ID** | high |
| 26 | 2 | counter (ammo or respawn timer?) | low |
| 28 | 1 | **pickup type** | high |
| 29 | 1 | flags | medium |
| 30 | 2 | always 0 | — |

### Model (+24) and type (+28) — verified

Of the 620 records: **350 have a model in the weapon range (321–372)** and 134 in
the pickup object range (1240–1320). The most frequent are 1212 (money, 134),
1242 (armor, 50), 1247 (49) and 325 (39).

The two fields are consistent with each other, which confirms the reading:

| type | count | models that appear |
|---:|---:|---|
| 15 | 382 | 321, 322, 325, 326, 331, 333… (all weapons) |
| 0 | 179 | mix of weapons and 953 |
| 3 | 19 | 1240 (health), 1277 |
| 8 | 11 | 1212 (money) |
| 16 | 10 | 1274 (money bag) |
| 5 | 6 | 1240, 1242 (health and armor) |

Type 16 always appears with model 1274 and with values in `+0` of 2000, 5000 and
8000: those are the money bundles on the map. Type 15 is the standard weapon
pickup.

## Pickups do NOT store position

The position of a pickup is set by the map or the script that
created it, and the save only needs to store its **state** (what it is, whether
it has been picked up, how much remains).

The 12 bytes of `+12..23` are not interpretable data: they change in an apparently
random way between records and do not fit as float, integer, or coherent pointer.
Do not touch them.

## This is not CJ's inventory

This block contains **the weapons scattered on the map**, not the ones the player
is carrying. CJ's inventory lives in `CPed`, which is serialized inside
`CPools::SavePedPool` — block 2.

If what you want is to give ammo to the player, this is not the block.

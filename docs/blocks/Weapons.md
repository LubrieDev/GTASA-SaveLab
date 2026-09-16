# CJ's weapon inventory (within block 2)

It is in the **ped pool**, not in `CPickups`. Full path from the binary:

```
CPools::Save
  -> CPools::SavePedPool          @ 0x567A38
       -> virtual call vtable+200 on each CPed
            -> CPlayerPed::Save   @ 0x564E80   (CJ; CPed::Save for the rest)
                 -> CPedSaveStructure::Construct(CPed*)  @ 0x564080
```

## Ped pool header

At the beginning of the block 2 data (after the `BLOCK` tag):

| offset | size | field |
|---:|---:|---|
| 0 | 4 | number of peds saved |
| 4 | 4 | ped reference (`GetPedRef`) |
| 8 | 4 | model index (0 for CJ) |
| 12 | 4 | ped type |
| 16 | 4 | size of the following struct |
| 20 | variable | `CPedSaveStructure` |

If the model is in the range **290–299**, a 9-byte model name is inserted between
the type and the struct. For CJ (model 0) it does not appear.

For CJ, `CPlayerPed::Save` adds another `4 + 136` bytes with
`CPlayerPedDataSaveStructure` after the ped struct.

## `CPedSaveStructure` (420 bytes in a reference save)

| offset | size | source | field |
|---:|---:|---|---|
| 0 | 8 | — | unidentified |
| 8 | 4 | — | unidentified |
| 12 | 4 | `CPed+20` | unidentified |
| 16 | 4 | `CPed+1708` | unidentified |
| 20 | 4 | `CPed+1716` | unidentified |
| **24** | **364** | `CPed::m_aWeapons` | **13 weapon slots × 28 B** |
| 388 | 1 | `CPed+1352` | |
| 389 | 1 | `CPed+2268` | |
| 390 | 1 | `CPed+75` | |
| 392 | 4 | `CPed+2302` | |
| 396 | 2 | `CPed+2301/2302` | |

`388 − 24 = 364 = 13 × 28`, which is exactly `CWeapon m_aWeapons[13]`.

## `CWeapon` — 28 bytes per slot

| offset | size | field |
|---:|---:|---|
| 0 | 4 | **weapon type** (0–46) |
| 4 | 4 | state |
| 8 | 4 | **clip ammo** |
| 12 | 4 | **total ammo** |
| 16 | 12 | rest (zero in the read slots) |

## Verification

Reading 13 slots, with weapons starting at a located offset:

| slot | type | clip | total | weapon |
|---:|---:|---:|---:|---|
| 0 | 1 | 0 | 1 | brass knuckles |
| 1 | 4 | 0 | 6 | knife |
| 2 | 22 | 34 | 99999 | 9mm pistol |
| 3 | 26 | 4 | 99999 | sawed-off |
| 4 | 29 | 30 | 99999 | MP5 |
| 5 | 31 | 50 | 99999 | M4 |
| 6 | 34 | 1 | 99999 | sniper rifle |
| 7 | 38 | 500 | 99999 | minigun |
| 8 | 39 | 1 | 50 | explosives |
| 9 | 42 | 500 | 99999 | fire extinguisher |
| 10 | 0 | 0 | 0 | *(empty)* |
| 11 | 45 | 0 | 1 | thermal goggles |
| 12 | 40 | 0 | 0 | detonator |

**The 13 types fall within the valid range 0–46**, and the slot order matches the
GTA SA categories: melee, knife, pistol, shotgun, submachine gun, rifle, sniper,
heavy, explosives, spray, projectiles, goggles, detonator. With a misplaced offset
neither check passes.

## Formulas

```
weapon in slot n:
    type     ->  weapons_start + n*28
    clip     ->  weapons_start + n*28 + 8
    total    ->  weapons_start + n*28 + 12
```

**Do not use a hardcoded offset.** You must locate block 2 by
counting `BLOCK` markers and computing the pool header size. The pool header is
fixed size *only as long as there is a single saved ped and its model is not in
290–299*; if the ped count at offset +0 is not 1, the weapons offset changes.

## Ammo behavior

- `+12` (total ammo) is **a cap, not a counter**: it is not consumed when
  firing. Writing any value is sufficient for infinite ammo.
- `+8` (clip ammo) is reset to the weapon's magazine size on load. Writing
  beyond the magazine size has no effect — the game enforces the cap.
- For throwables (e.g. explosives), the HUD displays `+12` directly since they
  have no clip mechanism.

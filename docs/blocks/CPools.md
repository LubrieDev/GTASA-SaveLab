# CPools block (block 2) — partial mapping

Extracted from `CPools::Save` @ `0x5677A4`. **This document is intentionally
incomplete**: see the final section.

## Block composition

`CPools::Save` does not write a struct: it orchestrates others. This is the exact
order in which the block content is dumped:

| # | what |
|---:|---|
| 1 | `CPools::SavePedPool` |
| 2 | `CPools::SaveVehiclePool` |
| 3 | `CPools::SavePedTasks` |
| 4 | `CPedGroups::Save` |
| 5 | `CDecisionMakerTypes::m_bIsActive` (20 B) |
| 6 | `CDecisionMakerTypes::ScriptReferenceIndex` (40 B) |
| 7 | `CDecisionMakerTypes::m_types` (20 B) |
| 8 | `CDecisionMakerTypes::m_pPedDecisionTypes` (variable size) |
| 9 | `CUserDisplay::OnscnTimer` (64 B) |
| 10 | 272 B block, unidentified |
| 11 | `CPedScriptedTaskRecord::Save` |
| 12 | `CAudioEngine::Save` |
| 13 | `CCarCtrl::CarDensityMultiplier` (4 B) |
| 14 | `CCarCtrl::bAllowEmergencyServicesToBeCreated` (1 B) |
| 15 | `CPopulation::PedDensityMultiplier` (4 B) |
| 16 | `CPools::SaveObjectPool` |
| 17 | `currentSaveFenceCount` (2 B) |
| 18 | `CPopulation::m_bDontCreateRandomGangMembers` (1 B) |
| 19 | 2 B, unidentified |
| 20 | `CPopulation::m_bOnlyCreateRandomGangMembers` (1 B) |
| 21 | `CTheScripts::SaveAfter` |

Useful fact: `CPedGroups::Save`, `CAudioEngine::Save`, and
`CPedScriptedTaskRecord::Save` **are not standalone blocks** — they execute inside
`CPools`. That is why they do not appear in the 25-case list of the `GenericSave`
`switch`.

## WARNING: the block content changes depending on the save type

The table above is the order in the binary, **not what is always in the file**.
`CPools::Save` starts like this:

```
+0x0018  bl   CPools::SavePedPool
+0x001c  bl   CPools::SaveVehiclePool
+0x0024  x21 = &IsMissionSave
+0x0028  ldrb w8, [x21]
+0x002c  cmp  w8, #1
+0x0030  b.ne +0x198          <-- jumps straight to SaveObjectPool
+0x0034  bl   CPools::SavePedTasks
         ...
+0x0198  bl   CPools::SaveObjectPool
```

**If `IsMissionSave` is not 1, elements 3 through 15 of the table are not
written.** `SavePedTasks`, `CPedGroups::Save`, the four `CDecisionMakerTypes`
arrays, `CUserDisplay::OnscnTimer`, the 272 B block,
`CPedScriptedTaskRecord::Save`, `CAudioEngine::Save`, and the
`CCarCtrl`/`CPopulation` densities are all skipped.

The same flag is checked again at `+0x01a4`, `+0x01c8`, and `+0x0220` to skip
sections at the end, and `SaveVehiclePool` also queries it in its prologue.

### Practical consequence

A normal save and a mission save have **different layouts** in this block. Two
effects:

1. Any tool that traverses block 2 must read `IsMissionSave` before deciding what
   to expect.
2. In a differential, comparing a normal save against a mission save will make the
   entire block show up as a difference. It is not a signal.

In a normal save the block ends with the object pool. Elements 17 through
21 of the table (the fence, `m_bDontCreateRandomGangMembers`, the 2 unidentified
bytes, `m_bOnlyCreateRandomGangMembers`, and `CTheScripts::SaveAfter`) **are also
not written** in a normal save.

The proof is arithmetic: the last `CObjectSaveStructure` ends at the last byte
of the block. Nothing else fits after it.

## External structure of the pools

Both the ped pool and the vehicle pool follow the same pattern: a 4-byte counter
followed by one record per entity.

```
SavePedPool:      u32 number of peds,      then one record per ped
SaveVehiclePool:  u32 number of vehicles,  then one record per vehicle
```

Each ped record includes a 9-byte model name copied from
`CModelInfo::ms_modelInfoPtrs`.

The step between vehicle pool entries in memory is **3176 bytes**
(`mov w26, #3176`).

## Why this is not finished

The other documented blocks could be mapped byte by byte because their serializer
is linear: a fixed sequence of `_SaveDataToWorkBuffer` calls with constant sizes.
`CPools` is not like that:

- **The records are variable-length.** The content of a vehicle depends on its
  class (`CAutomobile`, `CBike`, `CBoat`, `CHeli`, `CPlane`...), and each branch
  writes different fields.
- **There are cross-references.** `SaveVehiclePool` repeatedly calls
  `CPools::GetPedRef` and `GetVehicleRef` to convert pointers to indices, and
  stores those indices. They are not flat data, they are links between entities.
- **The total size depends on the game state**: how many cars and peds were alive
  at the time of saving.

Giving fixed offsets here would be making them up. To truly map it you would need
to walk `SaveVehiclePool` (1976 bytes of code) branch by branch.

## `CVehicleSaveStructure` — struct mapped, location NOT

`CVehicleSaveStructure::Construct(CVehicle*)` @ `0x564424` builds a **128-byte**
struct:

| offset | size | source | field |
|---:|---:|---|---|
| 0 | 72 | — | matrix (`CMatrixSerialize::operator=`) |
| 72 | 1 | `CVehicle+1552` | who created the vehicle (`SetVehicleCreatedBy`) |
| 73 | 4 | `CVehicle+1396..1399` | **colors 1-4** |
| 78 | 2 | `CVehicle+1436` | alarm (`ProcessCarAlarm`) |
| 80 | 1 | `CVehicle+1516` | floatability / state |
| 84 | 4 | `CVehicle+1536` | control (`ProcessControl`) |
| 88 | 4 | `CVehicle+1544` | control (`ProcessControlInputs`) |
| 92 | 4 | `CVehicle+1548` | control (`ProcessAI`) |
| 96 | 8 | `CVehicle+1384` | unidentified |
| **104** | **4** | `CVehicle+1588` | **HEALTH** |
| 108 | 4 | `CVehicle+1668` | ped exiting the vehicle |
| 112 | 4 | `CVehicle+100` | entity flags |
| 116 | 4 | `CVehicle+176` | physics (`ApplyCollision`, `ApplyFriction`) |
| 120 | 4 | `CVehicle+180` | physics (`FlyingControl`) |
| 124 | 4 | `CVehicle+196` | unidentified |

The health is identified unambiguously: `CVehicle+1588` is touched by
`CAutomobile::VehicleDamage`, `CVehicle::InflictDamage`, `CBike::VehicleDamage`,
and `CPlane::VehicleDamage`. The colors at `+73` match those of `CStoredCar` in
block 3, reinforcing the reading.

**The vehicle pool may be empty in a reference save.** If the pool is empty,
there are no `CVehicleSaveStructure` records to verify against. A save with
vehicles placed in the world is needed to anchor the structure.

### What is needed to close this

A save game **with vehicles placed in the world**: park two or three recognizable
cars outside a garage, with different colors and damage, and save. That way the
pool is no longer empty and can be anchored by the colors at `+73` and the health
at `+104`, which are already identified.

Meanwhile, with the structure known but without an anchor, writing to this block
would be blind. **If what you are looking for is a specific car, it is in block 3**
(see below).

## The object pool IS mapped, and anchored

`CPools::SaveObjectPool` writes a `u32` with the number of objects followed by a
**64-byte record per object**:

```
u32 = number of objects
number_of_objects x 64 bytes   <- the records
```

The block ends with the last object, to the byte.

The record:

| offset | size | content |
|---:|---:|---|
| 0 | 4 | object reference (pool index, **unique among the objects**) |
| 4 | 4 | **model ID** |
| 8 | 4 | struct size = **52** (constant, this is the anchor) |
| 12 | 52 | `CObjectSaveStructure` |

`CObjectSaveStructure` (from `Construct(CObject*)` @ `0x563EA4`):

| offset | size | field |
|---:|---:|---|
| 0 | 12 | **position X, Y, Z** — 3 **uncompressed** floats |
| 12 | 9 | **rotation** — 9 x normalized `int8` (127 = 1.0) |
| 24 | 1 | `CObject+417` |
| 26 | 2 | `CObject+418` |
| 28 | 4 | `CObject+436` |
| 32 | 8 | `CObject+40` |
| 46 | 1 | `CObject+416` |
| 47 | 2 | `CObject+424/425` |
| 49 | 1 | `CObject+100` |
| 50 | 2 | `CObject+468` |

**`CCompressedMatrixNotAligned` does not compress the position**, only the
rotation: it leaves the 3 floats as-is and reduces the three orientation vectors
to 9 signed bytes. That is why positions appear as raw floats in the file.

### Verification

The counter, the 52-byte markers at a 64-byte step, and the sum reaching exactly
the end of the block all validate the structure. All positions should fall within
reasonable map coordinates. The model IDs should be within the object range.
The references should be **distinct from each other**, as pool indices should be.

The `127, 0, 0, 0, 127, 0, 0, 0` pattern is the normalized identity: an object
with this rotation is not rotated.

**Watch out for the Z coordinate:** some objects may be at `z ~ 1909`, all in the
same location. It is not an alignment error: they are **interior** objects, which
in GTA SA live in the same coordinate space but at high altitude. A validation
that restricts `z` to street-level values would mark them as false positives.

## The ped pool IS mapped

`SavePedPool` is approachable when there is only one saved ped (the player).
That is where **the weapon inventory** comes from, documented separately.

**If what you are looking for is the proof flags or tuning of a specific car, check
block 3 first**: cars saved in garages are in `aCarsInSafeHouse`, with a fixed
structure already documented in the CGarages block documentation. This block only
contains vehicles that were loose in the world at save time.

See `gtasa/armor.py` for the proof flags field (offset +16 in the 64-byte CStoredCar
record) and `scripts/12_vehicle_proofs.py` for a reusable laboratory script.

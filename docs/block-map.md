# Save File Block Map

Obtained by reverse engineering `libGame.so` (arm64-v8a), extracted from the `split_config.arm64_v8a.apk` of the official `com.rockstargames.gtasa` package. This is not derived from diffs: it is the exact order the game itself executes.

## Binary mechanism

`CGenericGameStorage::GenericSave(int)` @ `0x5617E0`:

```
+0x00ac   adrp/ldr  ms_BlockTagName            <- only site that writes the tag
+0x00dc   bl        _SaveDataToWorkBuffer      <- writes the 5 bytes "BLOCK"
+0x00e4   cmp       w27, #0x1c
+0x00f8   ldrb      w10, [x26, x8]             <- jump table @ 0x2677C4 (1-byte entries)
+0x0100   br        x9                         <- case base @ 0x5618E4
...
+0x0270   add       w27, w27, #1
+0x0274   cmp       w27, #0x1d                 <- 29 iterations (indices 0..28)
+0x027c   bl        SaveBriefs                 <- outside the loop, no tag of its own
```

`ms_BlockTagName` is referenced only twice in the entire binary: here and in `GenericLoad`. The number of `BLOCK` markers equals the number of loop iterations.

## The 29 blocks

| # | hex | size | serializer | description |
|---:|---|---:|---|---|
| 0 | 0x0000000 | 433 | **CSimpleVariables** | name, clock, weather — [details](blocks/CSimpleVariables.md) |
| 1 | 0x00001B1 | variable | **CTheScripts** | globals + threads — [globals](blocks/CTheScripts.md), [threads](blocks/CTheScripts-Threads.md) |
| 2 | 0x000F170 | variable | **CPools** | ped pool, vehicle pool — [details](blocks/CPools.md) |
| 3 | 0x0010D51 | variable | **CGarages** | 20 garages × 4 slots — [details](blocks/CGarages.md) |
| 4 | 0x001311D | 16 | **CGameLogic** | [details](blocks/CGameLogic.md) |
| 5 | 0x001312D | variable | **CPathFind** | pathfinding data — [details](blocks/CPathFind.md) |
| 6 | 0x00136CA | 19928 | **CPickups** | [details](blocks/CPickups.md) |
| 7 | 0x00184A2 | 5 | *(empty)* | gap from PC version |
| 8 | 0x00184A7 | variable | **CRestart** | respawn points — [details](blocks/CRestart.md) |
| 9 | 0x0018613 | 10005 | **CRadar** | map icons — [details](blocks/CRadar.md) |
| 10 | 0x001AD28 | variable | **CTheZones** | zones — [details](blocks/CTheZones.md) |
| 11 | 0x001F6F9 | 165 | **CGangs** | [details](blocks/CGangs.md) |
| 12 | 0x001F79E | variable | **CTheCarGenerators** | car generators — [details](blocks/CTheCarGenerators.md) |
| 13 | 0x002143D | 5 | *(empty)* | gap from PC version |
| 14 | 0x0021442 | 5 | *(empty)* | gap from PC version |
| 15 | 0x0021447 | 49 | **CPlayerInfo** | money — [details](blocks/CPlayerInfo.md) |
| 16 | 0x0021478 | 1945 | **CStats** | statistics — [details](blocks/CStats.md) |
| 17 | 0x0021C11 | 6729 | **CSetPieces** | police roadblocks — [details](blocks/CSetPieces.md) |
| 18 | 0x002365A | 26321 | **CStreaming** | model flags — [details](blocks/CStreaming.md) |
| 19 | 0x0029D2B | 645 | **CPedType** | [details](blocks/CPedType.md) |
| 20 | 0x0029FB0 | variable | **CTagManager** | graffiti tags — [details](blocks/CTagManager.md) |
| 21 | 0x002A01D | 264 | **CIplStore** | [details](blocks/CIplStore.md) |
| 22 | 0x002A125 | variable | **CShopping** | clothing data — [details](blocks/CShopping.md) |
| 23 | 0x002A372 | 105 | **CGangWars** | [details](blocks/CGangWars.md) |
| 24 | 0x002A3DB | variable | **CStuntJumpManager** | unique jumps — [details](blocks/CStuntJumps.md) |
| 25 | 0x002B67C | variable | **CEntryExitManager** | interior entrances — [details](blocks/CEntryExits.md) |
| 26 | 0x002BF59 | 3841 | **CAERadioTrackManager** | radio — [details](blocks/CAERadioTrackManager.md) |
| 27 | 0x002CE5A | 145 | **C3dMarkers** | [details](blocks/C3dMarkers.md) |
| 28 | 0x002CEEB | 357 | **CPostEffects** | [details](blocks/CPostEffects.md) |

Offsets are from a reference save (195000 bytes). **The order is fixed; the offsets are not** — they depend on the size of each block, which varies between saves.

## File tail

| From | To | Content |
|---:|---:|---|
| 184400 | 184572 | **SaveBriefs** — 173 B, no tag of its own |
| 184573 | 194995 | **Garbage**: remnants of previous buffer dumps |
| 194996 | 194999 | Checksum (4 bytes) |

The actual data ends at offset 184573. The file measures 195000 because it consists of 3 dumps of a 65000-byte buffer.

## Empty blocks

Cases 7, 13 and 14 write the tag and nothing else. They are gaps in the enum inherited from the PC version whose subsystems are not saved on mobile.

## Variable-sized blocks

12 of the 29 blocks carry the record count within the file: 1, 2, 3, 4, 5, 8, 10, 12, 20, 22, 24 and 25. Their `::Load` iterates that count, so adding or removing records is legitimate.

The remaining 17 have fixed sizes imposed by the binary.

## How a block is mapped

Decompile its serializer and read the `_SaveDataToWorkBuffer` calls field by field. All symbols are still unstripped in `.dynsym` (~22700 exported), so disassemblers recognize them directly.

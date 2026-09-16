# CTheScripts block (block 1) — the non-globals region

Continuation of the CTheScripts globals documentation, covering the header and
`ScriptSpace`. Extracted from `CTheScripts::Save` @ `0x56A79C`
(3352 bytes of code, the largest serializer in the game).

## Where it starts

```
block 1 data = block_data_start
  +0        u32 = ScriptSpace size   (e.g. 49212)
  +4         ScriptSpace              (e.g. 49212 B)  <- the globals, already mapped
  +(4 + size) the rest                (e.g. 12154 B)  <- this
```

## Breakdown of the 12,154 bytes (example)

```
  2314   fixed header (arrays and scalars)
     14   unidentified
  9536   32 script threads x 298 B
   274   CScriptResourceManager::Save
    16   IsOddJob, mission text name, missionReplaySetting
 -----
 12154
```

Matches to the byte. Offsets relative to the start of the rest (**+0 = first
byte after ScriptSpace**).

## Fixed header (+0 to +2313)

| offset | size | content |
|---:|---:|---|
| 0 | 1400 | `ScriptsForBrains`, 70 records of 20 |
| 1400 | 4 | `OnAMissionFlag` |
| 1404 | 4 | `LastMissionPassedTime` |
| 1408 | 400 | loop of 25 x 16 |
| 1808 | 160 | loop of 20 x 8 |
| 1968 | 80 | loop of 20 x 4 |
| 2048 | 80 | `ScriptConnectLodsObjects`, 10 x 8 |
| 2128 | 160 | `ScriptAttachedAnimGroups`, 8 x 20 |
| 2288 | 1 | `bUsingAMultiScriptFile` |
| 2289 | 1 | `bPlayerHasMetDebbieHarry` |
| 2290 | 4 | `MainScriptSize` |
| 2294 | 4 | `LargestMissionScriptSize` |
| 2298 | 2 | `NumberOfMissionScripts` |
| 2300 | 2 | `NumberOfExclusiveMissionScripts` |
| 2302 | 4 | `LargestNumberOfMissionScriptLocalVariables` |
| 2306 | 4 | `SaveStreamedScripts` |
| 2310 | 4 | `SaveGameStateType` |

The loop sizes come from their comparisons in the binary:

```
+0x0108  cmp x21, #1400    -> ScriptsForBrains: 1400 / 20 = 70 records
+0x017c  mov w24, #25      -> 25 iterations of 16 bytes
+0x02b8  cmp x23, #160     -> 160 / 8  = 20 iterations
+0x0370  cmp x21, #80      ->  80 / 4  = 20 iterations
```

**The validation is that the scalars land exactly where the sum of the loops
predicts**, and they come out with credible values.

## Script threads (from +2328 onward)

**32 threads, 298 bytes each.** Each record begins with a 256-byte image of the
`CRunningScript`, and **the thread name is the first 8 bytes**, in ASCII and
terminated by `\0`:

```
   0  +  2328  'main'       8  +  4712  'psave1'   16  +  7096  'impnd_l'
   1  +  2626  'oddveh'     9  +  5010  'help'     17  +  7394  'tri'
   2  +  2924  'r3'        10  +  5308  'colls'    18  +  7692  'apcheck'
   3  +  3222  'gym'       11  +  5606  'cranes'   19  +  7990  'hj'
   4  +  3520  'shoot'     12  +  5904  'buy_pro'  20  +  8288  'intman'
   5  +  3818  'bloodr'    13  +  6202  'valet_l'  21  +  8586  'gfagnt'
   6  +  4116  'hotr'      14  +  6500  'adplane'  22  +  8884  'ms_skip'
   7  +  4414  'kicks'     15  +  6798  'trainsl'  23  +  9182  'mob_ran'
  24  +  9480  'trucks'    27  + 10374  'bikes'    30  + 11268  'impexpm'
  25  +  9778  'trace'     28  + 10672  'psch'     31  + 11566  'impexpc'
  26  + 10076  'bschoo'    29  + 10970  'quarrys'
```

These are recognizable San Andreas script names (`gym`, `bschoo` from the driving
school, `impexpm` from import/export, `quarrys` from the quarry), which confirms
that the offset and step are correct.

The record is 256 (image) + 42 (tail). The serializer writes the image in one
go and then nine `u32`, one `u16`, and one `u32`:

```
+0x0890..+0x08fc   builds 256 B in a stack buffer by copying from CRunningScript
+0x0950            _SaveDataToWorkBuffer(256)
+0x0978..+0x0af8   nine 4-byte writes
+0x0b88            2   (depends on IsMissionSave)
+0x0bcc            4   (index into CTheScripts::StreamedScripts)
```

`9 x 4 + 2 + 4 = 42`. The 42-byte tail and the 256-byte image beyond the name
have not been fully broken down field by field.

### The 14 bytes before the first thread

Just before the first thread there are 14 bytes that have not been attributed
to any code write. They have exactly the same shape as the last 14 bytes
of the tail of each thread:

```
gap    +2314 : 5f 00 ff ff ff ff 00 00 00 00 00 00 00 fa
thread 0 +2612 : 5d 00 ff ff ff ff 00 00 00 00 00 00 00 fa
thread 1 +2910 : 5c 00 ff ff ff ff 00 00 00 00 00 00 00 fa
thread 2 +3208 : 5b 00 ff ff ff ff 00 00 00 00 00 00 00 fa
```

The first `u16` counts backward (95, 93, 92, 91...). The likely explanation is
that the compiler **rotated the loop**: `CTheScripts::Save` enters the body through
`+0x0b0c`, not from its start (`+0x088c` is a `b +0xb0c`), so the first pass
skips the image and the initial writes and only writes the tail. This is
consistent with the byte shape and with the sum closing.

## The tail (to the end)

| offset | size | content |
|---:|---:|---|
| 11864 | 274 | `CScriptResourceManager::Save` |
| 12138 | 4 | `IsOddJob` |
| 12142 | 8 | loaded mission text name (`CText::GetNameOfLoadedMissionText`) |
| 12150 | 4 | `missionReplaySetting` |

`CScriptResourceManager::Save` (@ `0x56A34C`) is variable-length — it contains
`strlen` loops — so the 274 bytes are what it occupies in a reference save, not a
constant.

## What is not saved: the `DataFence`

`CTheScripts::Save` has a 2-byte write at `+0x081c` that **does not appear in the
file**, because it is inside a debugging mechanism:

```
+0x07d4  ldrb  w22, [x21]        <- &UseDataFence
+0x07d8  cmp   w22, #1
+0x07dc  b.ne  +0x82c            <- in the retail version it always skips
```

If you count it, there are 2 extra bytes and nothing that follows adds up.

## What remains unmapped

- The breakdown of the 42 tail bytes of each thread.
- The 256 bytes of the `CRunningScript` image beyond the name.
- The contents of the three loops at +1408, +1808, and +1968 (how large
  they are and how many iterations they run are known, not what they contain).
- The 20-byte record of `ScriptsForBrains` (the name is at `+11`).

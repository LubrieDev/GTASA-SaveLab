# Structure of the CTheScripts block (block 1) — the globals

Extracted from `CTheScripts::Save` @ `0x56A79C` in `libGame.so` (3352 bytes of
code, the largest serializer in the game).

## Header and globals

The first two writes in the block are:

```
+0x0050   _SaveDataToWorkBuffer(&size, 4)          <- u32: ScriptSpace size
+0x0094   _SaveDataToWorkBuffer(ScriptSpace, size)  <- the entire globals space
```

| offset in data | size | content |
|---:|---:|---|
| 0 | 4 | `ScriptSpace` size in bytes |
| 4 | *that size* | `CTheScripts::ScriptSpace` |

## The formula

```
global $g  ->  file offset  (block_1_data_start) + 4 * g
```

More generally:

```
block_1_start  +  5 (BLOCK tag)  +  4 (size field)  +  4 * g
```

## Where the "-9" comes from

The 9-byte offset is exactly the 5 bytes of the `BLOCK` tag plus the 4 bytes of
the size field. It is the header before `ScriptSpace` begins.

Verified: byte 1441 relative to the start of the block is file offset
`block_start + 1441`, and `block_data_start + 4 * 358` matches. It is global
`$358`, to the byte.

So the formula is:

```
byte b relative to start of block  ->  global  (b - 9) / 4
```

## Why the PC numbering does not work

`ScriptSpace` is a literal copy of the `main.scm` variable area. Global indices
depend on how that `main.scm` is compiled, and the mobile version's is not the
PC's. The formula above is correct in both; what changes is what each index stores.

## The first globals are garbage

`ScriptSpace` starts with the `main.scm` header itself, not with data:

```
02 00 01 3C C0 00 00 73 ...
```

`02 00` is the `GOTO` opcode, `01` the parameter type, and `3C C0 00 00` = 49212 —
the jump that skips over the variable area, and which matches the declared size.
That is, `$0` and `$1` **are not variables**, they are instruction bytes. Do not
interpret or write them.

## What remains of the block

After `ScriptSpace` there are the remaining bytes with the
rest: `ScriptsForBrains`, `OnAMissionFlag`, `LastMissionPassedTime`,
`InvisibilitySettingArray`, `VehicleModelsBlockedByScript`,
`ScriptConnectLodsObjects`, `ScriptAttachedAnimGroups`, `MainScriptSize`,
`NumberOfMissionScripts`, `CurrentScriptName` (256 B),
`LocalVariablesForCurrentMission` (4096 B), the active scripts, and
`CScriptResourceManager::Save`.

This is already mapped in the thread documentation: 2314 bytes of
fixed header, 32 script threads of 298 bytes each, and a 290-byte tail. The sum
closes to the byte.

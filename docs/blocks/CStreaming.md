# Structure of the CStreaming block (block 18)

Extracted from `CStreaming::Save` @ `0x566078` in `libGame.so`.

It is the largest block in the file after the globals, and it is the simplest of
all: **a flat array of one byte per model**.

## Layout

```
26316 bytes, one per model. The index IS the model ID.
```

`26316 × 1 = 26316` = the 26,321 bytes of the block minus the tag.

## The code

```
+0x001c  mov   w21, #26316          <- number of models, literal
+0x002c  add   x20, x9, #0x10       <- x9 = ms_aInfoForModel
loop:
+0x0050  ldrb  w8, [x20, #0]
+0x0054  strb  w22, [sp, #4]        <- w22 = 255, default value
+0x0058  cmp   w8, #1
+0x005c  b.ne  write               <- if not 1, save 255
+0x0060  ldurb w8, [x20, #-10]      <- if 1, save this other byte
write:
+0x0040  bl    _SaveDataToWorkBuffer(sp+4, 1)
+0x0048  add   x20, x20, #0x14      <- step of 20 B in memory (CStreamingInfo)
```

That is: for each model, **`0xFF` is saved unless its streaming state is 1**, in
which case another byte from the same structure is saved.

## Verification

```
distinct values in the block: 5
   255 -> 25261 models    (default, not persisted)
     0 ->   931
     8 ->   108
    10 ->     8
     2 ->     8

marked models (!= 0xFF): 1055 of 26316
```

Only five distinct values in 26 KB, and `0xFF` dominates: it is exactly what the
code predicts.

### Cross-validation with other blocks

The marked models match what the save has stored in other blocks. Examples:

- **Model 0** (CJ) marked — the only ped saved in the block 2 pool.
- **Models 470 and 520** marked — they are two of the cars parked in garages
  (house 0 slot 0, and houses 13/14 slot 1).
- 22 models marked in the weapon range (321–372) and 27 in the pickup object
  range (1200–1320), consistent with blocks 2 and 6.

That models saved in one block appear marked in another is the signal that both
readings are correct.

## What the byte means

`0xFF` is "no persisted state". The values 0, 2, 8, and 10 are model streaming
flags — presumably things like *required by mission* or *do not unload*. The exact
meaning of each bit would require looking at who reads `ms_aInfoForModel+6` in
the rest of the binary.

If you are going to touch this block: it is a flat array indexed by model ID, so
writing is trivial, but changing these flags alters which models the game keeps
loaded. It is not a block where editing blindly has visible or predictable
effects.

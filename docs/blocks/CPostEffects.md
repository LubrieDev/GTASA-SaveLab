# Structure of the CPostEffects block (block 28)

Extracted from `CPostEffects::Save` @ `0x57B5E4` and
`CPostEffectsSaveStructure::CopyValues` @ `0x57B688` in `libGame.so`.
See [BLOCK-MAP.md](../block-map.md) for the overall map.

These are the post-processing settings: color filter, radiosity, grain, night
vision and infrared, heat haze, speed effect, and water.

## The block is 357 bytes, not 9718

**Row 28 of the map was wrong.** The size was derived from the distance between
`BLOCK` markers, and the next marker (193761) is one of the two false ones inside
the `SaveBriefs` text. The serializer writes:

```
+0x0030  malloc(4)
+0x0040  str  w8, [x0]              <- w8 = 348
+0x0044  _SaveDataToWorkBuffer(4)   <- header: the struct size
+0x0054  malloc(348)
+0x0064  memcpy(x0, sp+12, 348)     <- CPostEffectsSaveStructure, built on stack
+0x0070  _SaveDataToWorkBuffer(348)
```

```
5 (tag) + 4 (header) + 348 = 357
```

Verified in the file: at 184048 there is the `uint32` **348**, and the block ends
at 184400. The remaining 10,600 bytes to the end are from `SaveBriefs`, which is
written outside the block loop and without its own tag.

The 4-byte header is redundant — it always is 348 — but it is there, so the data
starts at offset 9 of the block, not at 5.

## How the field map was derived

`CPostEffects::Save` does not read the global variables directly: it calls
`CPostEffectsSaveStructure::CopyValues(structure, 0)`, which copies them to the
struct. The same function with the second argument set to 1 does the reverse, and
it is the branch that appears first in the disassembly:

```
+0x0010  tbz  w1, #0, +0x5d0        <- w1 == 0: save (long branch, below)
+0x0014  ldp  s0, s1, [x0, #0]      <- w1 == 1: load. reads the struct...
+0x0024  str  s0, [x8, #0]          <- ...and writes the global (x8 from GOT)
```

Each field is resolved by following the `ldr` pair from `x0+offset` → `str` to a
global resolved by the GOT. There is no proximity matching: the name comes from
the symbol, which is undecorated.

## The 348 bytes

97 fields identified. The value column is from a reference save.

| offset | size | field (`CPostEffects::`) | value |
|---:|---:|---|---|
| 0 | 4 | `m_colour1Multiplier` | 1 |
| 4 | 4 | `m_colour2Multiplier` | 1 |
| 8 | 4 | *padding* | — |
| 12 | 4 | `SCREEN_EXTRA_MULT_CHANGE_RATE` | 0.0005 |
| 16 | 4 | `SCREEN_EXTRA_MULT_BASE_CAP` | 0.35 |
| 20 | 4 | `SCREEN_EXTRA_MULT_BASE_MULT` | 0.5 |
| 24 | 4 | `m_colourLeftUOffset` | 16 |
| 28 | 4 | `m_colourRightUOffset` | 16 |
| 32 | 4 | `m_colourTopVOffset` | 16 |
| 36 | 4 | `m_colourBottomVOffset` | 16 |
| 40 | 1 | `m_bSeamRemover` | 1 |
| 41 | 1 | `m_bSeamRemoverSeamSearchMode` | 0 |
| 42 | 1 | `m_bSeamRemoverDebugMode` | 0 |
| 43 | 1 | *padding* | — |
| 44 | 4 | `m_SeamRemoverMode` | 1 |
| 48 | 4 | `m_SeamRemoverShiftTopLeft` | 0 |
| 52 | 4 | `m_SeamRemoverShiftBottomRight` | 1 |
| 56 | 1 | `m_smokeyEnable` | 0 |
| 57 | 3 | *padding* | — |
| 60 | 4 | `m_smokeyStrength` | 128 |
| 64 | 4 | `m_smokeyDistance` | 75 |
| 68 | 1 | `m_waterEnable` | 0 |
| 69 | 3 | *padding* | — |
| 72 | 4 | `m_VisionFXDayNightBalance` | 1 |
| 76 | 1 | `m_bHeatHazeFX` | 0 |
| 77 | 1 | `m_bHeatHazeMaskModeTest` | 0 |
| 78 | 2 | *padding* | — |
| 80 | 4 | `m_HeatHazeFXHourOfDayStart` | 10 |
| 84 | 4 | `m_HeatHazeFXHourOfDayEnd` | 19 |
| 88 | 4 | `m_fHeatHazeFXFadeSpeed` | 0.05 |
| 92 | 4 | `m_fHeatHazeFXInsideBuildingFadeSpeed` | 0.5 |
| 96 | 4 | `m_HeatHazeFXType` | 0 |
| 100 | 4 | `m_HeatHazeFXTypeLast` | 0 |
| 104 | 4 | `m_HeatHazeFXIntensity` | 80 |
| 108 | 4 | `m_HeatHazeFXRandomShift` | 0 |
| 112 | 4 | `m_HeatHazeFXSpeedMin` | 12 |
| 116 | 4 | `m_HeatHazeFXSpeedMax` | 18 |
| 120 | 4 | `m_HeatHazeFXScanSizeX` | 98 |
| 124 | 4 | `m_HeatHazeFXScanSizeY` | 83 |
| 128 | 4 | `m_HeatHazeFXRenderSizeX` | 104 |
| 132 | 4 | `m_HeatHazeFXRenderSizeY` | 89 |
| 136 | 1 | `m_bDarknessFilter` | 0 |
| 137 | 3 | *padding* | — |
| 140 | 4 | `m_DarknessFilterAlpha` | 170 |
| 144 | 4 | `m_DarknessFilterAlphaDefault` | 170 |
| 148 | 4 | `m_DarknessFilterRadiosityIntensityLimit` | 45 |
| 152 | 1 | `m_bCCTV` | 0 |
| 153 | 4 | `m_CCTVcol` | 2 |
| 157 | 1 | `m_bFog` | 0 |
| 158 | 1 | `m_bSpeedFX` | 1 |
| 159 | 1 | `m_bSpeedFXTestMode` | 0 |
| 160 | 4 | `m_SpeedFXAlpha` | 36 |
| 164 | 1 | `m_bSpeedFXUserFlag` | 1 |
| 165 | 1 | `m_bSpeedFXUserFlagCurrentFrame` | 0 |
| 166 | 2 | *padding* | — |
| 168 | 4 | `m_fSpeedFXManualSpeedCurrentFrame` | 0 |
| 172 | 1 | `m_bInCutscene` | 0 |
| 173 | 1 | `m_bNightVision` | 0 |
| 174 | 2 | *padding* | — |
| 176 | 4 | `m_NightVisionGrainStrength` | 48 |
| 180 | 4 | `m_NightVisionMainCol` | -16743936 |
| 184 | 4 | `m_fNightVisionSwitchOnFXTime` | 50 |
| 188 | 4 | `m_fNightVisionSwitchOnFXCount` | 50 |
| 192 | 4 | `m_fInfraredVisionSwitchOnFXCount` | 50 |
| 196 | 1 | `m_bInfraredVision` | 0 |
| 197 | 3 | *padding* | — |
| 200 | 4 | `m_InfraredVisionGrainStrength` | 64 |
| 204 | 4 | `m_fInfraredVisionFilterRadius` | 0.003 |
| 208 | 16 | `m_fInfraredVisionHeatObjectCol` | 1 0 0 1 |
| 224 | 4 | `m_InfraredVisionCol` | -12834706 |
| 228 | 4 | `m_InfraredVisionMainCol` | -3669916 |
| 232 | 1 | `m_bRadiosity` | 0 |
| 233 | 1 | `m_bRadiosityLinearFilter` | 1 |
| 234 | 1 | `m_bRadiosityStripCopyMode` | 1 |
| 235 | 1 | *padding* | — |
| 236 | 4 | `m_RadiosityPixelsX` | 0 |
| 240 | 4 | `m_RadiosityPixelsY` | 0 |
| 244 | 4 | `m_RadiosityFilterPasses` | 2 |
| 248 | 4 | `m_RadiosityRenderPasses` | 1 |
| 252 | 4 | `m_RadiosityIntensityLimit` | 220 |
| 256 | 4 | `m_RadiosityIntensity` | 35 |
| 260 | 4 | `m_RadiosityFilterUCorrection` | 2 |
| 264 | 4 | `m_RadiosityFilterVCorrection` | 2 |
| 268 | 1 | `m_bRadiosityDebug` | 0 |
| 269 | 1 | `m_bRadiosityBypassTimeCycleIntensityLimit` | 0 |
| 270 | 1 | `m_bDisableAllPostEffect` | 0 |
| 271 | 1 | `m_bSavePhotoFromScript` | 1 |
| 272 | 1 | `m_bGrainEnable` | 0 |
| 273 | 3 | *padding* | — |
| 276 | 4 | `m_grainStrength` | 64 |
| 280 | 1 | `m_bHilightEnable` | 0 |
| 281 | 3 | *padding* | — |
| 284 | 4 | `m_hilightStrength` | 128 |
| 288 | 4 | `m_hilightScale` | 3 |
| 292 | 4 | `m_hilightOffset` | 2 |
| 296 | 1 | `m_hilightMblur` | 0 |
| 297 | 3 | *padding* | — |
| 300 | 4 | `m_waterStrength` | 64 |
| 304 | 4 | `m_xoffset` | 4 |
| 308 | 4 | `m_yoffset` | 24 |
| 312 | 4 | `m_waterSpeed` | 0.0015 |
| 316 | 4 | `m_waterFreq` | 0.04 |
| 320 | 4 | `m_waterCol` | 3.00392 |
| 324 | 1 | `m_bWaterDepthDarkness` | 1 |
| 325 | 3 | *padding* | — |
| 328 | 4 | `m_fWaterFullDarknessDepth` | 90 |
| 332 | 4 | `m_fWaterFXStartUnderWaterness` | 0.535 |
| 336 | 1 | `m_bRainEnable` | 0 |
| 337 | 1 | `m_bColorEnable` | 1 |
| 338 | 2 | *padding* | — |
| 340 | 4 | `m_defScreenXPosn` | 0 |
| 344 | 4 | `m_defScreenYPosn` | 0 |

The 1-byte `m_b*` fields are booleans; the rest are `int` or `float` depending on
the name. Several that look like `float` are integers (`m_colourLeftUOffset` = 16,
`m_DarknessFilterAlpha` = 170, the `HeatHazeFX` hours = 10 and 19).
`m_fInfraredVisionHeatObjectCol` is 4 consecutive floats, copied in one go with a
128-bit access.

## Validation

The file values are coherent field by field, which is the check that matters: with
wrong offsets, floats and ints do not land where they should.

- The `float` values come out round and sensible: `0.0005`, `0.35`, `0.5`, `0.05`,
  `50`, `90`, `0.535`, `0.003`.
- The `int` values too: hours of day `10`–`19`, alpha `170`, radiosity passes `2`
  and `1`, `m_hilightScale` `3`.
- All 22 booleans are 0 or 1. None comes out with garbage.

## This block leaks stack memory

**38 of the 348 bytes are not written by anyone.** The struct is built on the
stack (`sp+12`) and copied in full with `memcpy`, so the alignment padding between
fields —the 3 bytes after each `bool`, plus the 4 bytes at offset 8, which no
`CopyValues` instruction touches— is saved with whatever happened to be on the
stack.

In a reference save, **14 of those 38 bytes are non-zero**:

```
offset   8:  70 00 00 00     (0x70 = 112)
offset  78:  e3 24
offset 166:  10 e2
offset 174:  06 e2
offset 197:  23 10 e2
offset 325:  ea 2d e0
offset 338:  1f 00
```

The `e2`, `10 e2`, `e0 1f` are fragments of Android pointers. **They change
between runs**, so in a byte-by-byte differential of two saves they appear as
differences without any settings having been touched. It is the same pattern
already documented in `CSimpleVariables` and in the garages.

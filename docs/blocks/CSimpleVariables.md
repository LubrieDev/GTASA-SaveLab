# Structure of the CSimpleVariables block (block 0)

Extracted from `CSimpleVariablesSaveStructure::Construct` @ `0x56369C` in
`libGame.so`, following the data flow register by register (the symbols are loaded
through the GOT and the compiler reuses registers, so matching "symbol → offset"
by eye gives wrong results).

## Header and name

| offset | size | field |
|---:|---:|---|
| 0 | 4 | format version number (`GetCurrentVersionNumber`) |
| 4 | 48 | **save name**, UTF-16LE (GXT), 24 characters |
| 52 | 48 | last mission passed name (GXT), from `CStats::LastMissionPassedName` |

## Clock and time

| offset | size | field |
|---:|---:|---|
| 228 | 4 | `CClock::ms_nLastClockTick` |
| 232 | 1 | month |
| 233 | 1 | day |
| 234 | 1 | hour |
| 235 | 1 | minute |
| 236 | 1 | `CClock::CurrentDay` |
| 237–240 | 4 | month/day/hour/minute **stored** (`ms_Stored_*`) |
| 241 | 1 | `bClockHasBeenStored` |
| 244 | 1 | `CCheat::m_bHasPlayerCheated` |
| 248 | 4 | **play time in ms** (`CTimer::m_snTimeInMilliseconds`) |
| 260 | 4 | `CTimer::ms_fTimeStepNonClipped` (float) |
| 264 | 4 | frame counter |

## Weather

| offset | size | field |
|---:|---:|---|
| 268 | 2 | `CWeather::OldWeatherType` |
| 270 | 2 | `CWeather::NewWeatherType` |
| 272 | 2 | `CWeather::ForcedWeatherType` (65535 = none) |
| 276 | 4 | `InterpolationValue` |
| 280 | 4 | `WeatherTypeInList` |
| 284 | 4 | `CWeather::Rain` (float) |

## World and state

| offset | size | field |
|---:|---:|---|
| 204 | 1 | `CGame::bMissionPackGame` |
| 208 | 4 | `CGame::currLevel` |
| 288 | 4 | `TheCamera` (field) |
| 292 | 4 | `TheCamera` (field) |
| 296 | 4 | `CGame::currArea` (current interior) |
| 300, 308 | 1 | `MobileSettings::settings` |
| 304 | 4 | `CTimeCycle::m_ExtraColour` |
| 312 | 4 | `m_ExtraColourInter` |
| 316 | 4 | `m_ExtraColourWeatherType` |
| 320 | 4 | `CWaterLevel::m_nWaterConfiguration` |
| 324 | 1 | `gbLARiots` |
| 325 | 1 | `gbLARiots_NoPoliceCars` |
| 328 | 4 | `CWanted::MaximumWantedLevel` |
| 332 | 4 | `CWanted::nMaximumWantedLevel` |
| 336–338 | 3 | `CLocalisation`: French / German / `nastyGame` |

## Menu and settings

| offset | size | field |
|---:|---:|---|
| 384 | 1 | `gbCineyCamMessageDisplayed` |
| 385 | 1 | `CMBlur::BlurOn` |
| 386–392, 404, 412–414 | 1 each | fields of `FrontEndMenuManager` |
| 416 | 4 | `gMobileMenu` |
| 420–422 | 3 | `CPlayerPed::bHasDisplayedPlayerQuitEnterCarHelpText` and neighbors |
| 424 | 4 | `CPIndex` |

## WARNING: this block leaks memory

The gaps that `Construct` does not write **are not zero**: they contain remnants
of the process memory. For example, the range `struct+100..203` may contain
64-bit Android pointers:

```
struct+196:  14 58 D3 FB 70 00 00 00   00 F8 2D E0 00 00 00 00
```

Those are addresses like `0x70fbd35814`, not save data.

**This directly affects any differential method.** If you compare two saves byte
by byte, that range will always show as a difference even if nothing has changed
in the game, because it changes with the memory map of each execution. It
is not a signal, it is noise — and the worst kind, because it looks like data.

The safe ranges of the block are those documented above. Everything else between
offset 52 and 203, and between 338 and 384, should be ignored.

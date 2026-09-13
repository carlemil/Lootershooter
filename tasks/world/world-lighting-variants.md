# MEDIUM — Day and dusk lighting variants (rain: stretch)

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-terrain-blockout, world-kits-import

## Files
- `world/lighting/env_day.tres` (new)
- `world/lighting/env_dusk.tres` (new)
- `world/lighting/lighting_variant.gd` (new)
- `world/maps/mekong/mekong.tscn` (modify)
- `tests/test_lighting_variant.gd` (new)

## Issue
The map has default editor lighting: flat, no sky, no shadow direction, nothing to distinguish one match from the next. The plan wants a day and a dusk variant chosen per match (dusk changes sight-lines and makes the flashlight and flare gun worth their price), with monsoon rain as a later stretch addition that masks audio and lowers bot perception.

## Fix
- `world/lighting/lighting_variant.gd`, autoload-free `Node` script on a `LightingVariant` node inside `mekong.tscn`: `apply(variant: String)` where variant is `"day"` or `"dusk"`. The **server picks the variant from the match seed** at match start and broadcasts it with `phase_changed`, so every client sees the same sky — never a client-side setting.
- `env_day.tres`: `WorldEnvironment` resource with a Poly Haven CC0 HDRI sky (clear tropical midday), sun `DirectionalLight3D` at ~65° elevation, shadow distance 250 m with 4 splits, mild fog 800 m, tonemap Filmic, brightness tuned so interiors are readably darker than outdoors without needing a flashlight.
- `env_dusk.tres`: low sun ~8° elevation with a warm orange HDRI, long shadows, denser and warmer fog at 400 m, roughly 2 EV darker overall. Bump `bot-perception`'s `visibility_mult` to 0.75 in dusk (read from the variant, not hardcoded in the bot).
- Expose `get_ambient_light_level() -> float` (1.0 day, 0.6 dusk, 0.4 rain) as the single number the bot perception and any gameplay lighting checks read, so adding a variant later needs no gameplay changes.
- Bake `LightmapGI` only for the tunnel interiors and bunkers (static, dark, worth it); everything else is realtime with SDFGI off (too expensive at this scale) and a `ReflectionProbe` in the town.
- **Stretch — monsoon rain:** `env_rain.tres` plus a `rain.tscn` particle/shader overlay, `get_ambient_light_level() == 0.4`, an audio bus that attenuates distant gunshots and footsteps (feeding `audio-gunshots-propagation`'s distance tiers), and `visibility_mult` 0.55 for bots. Ship day and dusk first; do not block this task's completion on rain — implement it only after `audio-gunshots-propagation` exists, and leave the variant registered but unselectable until then.

## Acceptance
- GUT test `tests/test_lighting_variant.gd`: `apply("day")` then `get_ambient_light_level() == 1.0`; `apply("dusk")` → 0.6; an unknown variant falls back to `"day"` and pushes a warning. Two matches with the same seed select the same variant; different seeds can differ (assert the selection is a pure function of the seed).
- Open `mekong.tscn` and switch variants in the editor: day reads as bright tropical midday with crisp shadows; dusk has long shadows, a visibly lower sun and warm fog, and a flashlight makes a real difference indoors.
- Both variants keep ≥ 60 fps at 1080p in the town on a mid-range GPU.
- Rain (stretch) is present in the file as a registered variant but not selected by the seed until enabled; nothing else in the task depends on it.

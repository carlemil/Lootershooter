# MEDIUM — Settings: rebinds, FOV, sensitivity, audio, accessibility

**Category:** ui
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M9
**Depends on:** ui-hud, move-fp-camera-arms, audio-gunshots-propagation

## Files
- `client/ui/settings/settings_screen.tscn` (new)
- `client/ui/settings/settings_screen.gd` (new)
- `client/ui/settings/rebind_row.gd` (new)
- `client/settings.gd` (new — autoload)
- `tests/test_settings.gd` (new)

## Issue
Every input is hardcoded, FOV and mouse sensitivity cannot be changed, audio has one volume, and the colourblind minimap palette the plan lists under accessibility has nowhere to be toggled from. HUD, minimap and audio tasks all read "the settings singleton" that does not exist yet, so each of them is currently forced to hardcode values.

## Fix
- `client/settings.gd`: autoload `Settings`. Loads/saves `user://settings.cfg` with `ConfigFile`. Sections: `input` (action → event serialisation), `video` (fov, ui_scale, vsync, resolution_scale, fps_cap), `audio` (master, sfx, music, voice, ambience volumes in dB), `gameplay` (sensitivity, ads_sensitivity_multiplier, toggle_ads, toggle_crouch, toggle_sprint, minimap_north_up), `accessibility` (colourblind_mode: off/protan/deutan/tritan, subtitles, hud_contrast, reduce_shake). Emits `setting_changed(section, key, value)`; every consumer reacts to that signal instead of polling.
- Defaults live in one dictionary in `settings.gd`; a missing or corrupt config file falls back to defaults without crashing, and unknown keys are dropped on save.
- `rebind_row.gd`: click a row to capture the next `InputEventKey` / `InputEventMouseButton` / `InputEventJoypadButton`, write it with `InputMap.action_erase_events` + `action_add_event`, and persist the serialised event. Detect and warn on conflicts (highlight both rows, allow the duplicate but flag it). `Esc` cancels the capture. A Reset-to-default button per row and for the whole list.
- Actions to expose at minimum: move ×4, sprint, crouch, prone, jump/vault, lean L/R, dive, fire, ADS, reload, fire-mode, interact, use-item, throwable slots, weapon slots 1–5, wrist store, inventory, map, ping, scoreboard, push-to-talk placeholder.
- FOV slider 70–110 (applies to the first-person camera and, scaled, the viewmodel FOV so arms do not distort). Sensitivity 0.05–2.0 with a separate ADS multiplier and a per-scope-magnification option so a 4× scope does not feel 4× twitchier.
- Audio tab: five buses (Master, SFX, Music, Ambience, UI) mapped straight onto `AudioServer` bus volumes in dB; a "test gunshot" button that plays one distance-tiered sample so the player can set levels against the real thing.
- Accessibility: colourblind mode swaps the zone/hot-zone/team/ping palette used by `ui-hud` and `ui-minimap-fullmap` via a `Settings.palette()` accessor (one palette table, three remaps); subtitles toggle for callouts and important audio cues; `reduce_shake` scales camera shake and recoil kick visuals only — never the actual recoil, which is server-relevant.
- The settings screen is reachable from the main menu and from an in-match pause overlay that does *not* pause the world (server-authoritative match keeps running); pressing Esc in-match shows Settings / Leave match.

## Acceptance
- GUT test `tests/test_settings.gd`:
  - `test_defaults_on_missing_file`: with no `settings.cfg`, `Settings.get_value("video","fov")` returns the default 90 and no error is pushed.
  - `test_roundtrip`: setting FOV to 103 and sensitivity to 0.42, saving, reloading, and reading returns the same values.
  - `test_rebind_applies`: rebinding `fire` to `KEY_Z` makes `InputMap.action_has_event("fire", z_event)` true and removes the old event.
  - `test_corrupt_config`: a truncated `settings.cfg` loads defaults and rewrites a valid file.
  - `test_palette_remap`: `Settings.palette()` in `deutan` mode returns a different zone colour than `off`, and the same number of entries.
- Manual: change FOV, sensitivity and the fire key mid-session and confirm they apply immediately and survive a client restart; switch colourblind mode and see the minimap zone colours change.

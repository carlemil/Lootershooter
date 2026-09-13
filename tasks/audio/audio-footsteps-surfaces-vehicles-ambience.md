# MEDIUM — Footsteps by surface, vehicle audio, jungle and rain ambience

**Category:** audio
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M9
**Depends on:** audio-gunshots-propagation, move-controller-base, veh-base-vehiclebody, world-terrain-blockout

## Files
- `client/audio/footstep_player.gd` (new)
- `client/audio/vehicle_audio.gd` (new)
- `client/audio/ambience_controller.gd` (new)
- `data/audio.json` (modify)
- `tests/test_footstep_surfaces.gd` (new)

## Issue
Beyond gunshots the world is silent: you cannot hear someone flanking through a hut, an engine approaching (audible at 250 m per the plan), or the difference between standing in a rice paddy and on a road. Footsteps also need to match the hearing model bots use — sprint 35 m, walk 20 m, crouch 8 m, prone silent — or players and bots will be operating on different information.

## Fix
- Surface detection: on each footstep the movement controller raycasts down and reads the surface from (a) the Terrain3D splat/control map index for terrain, or (b) a `surface` metadata string on the collider for props and buildings. Surfaces: `dirt`, `grass`, `mud`, `paddy_water`, `gravel`, `road`, `wood`, `bamboo`, `concrete`, `metal`, `foliage`, `water_deep`.
- `data/audio.json` gains `footsteps: {<surface>: {samples: [...], base_db, loudness_m_mult}}`. Water and mud are loud (`loudness_m_mult` 1.3), grass and foliage moderate, wood creaks, concrete and metal are sharp and carry.
- `client/audio/footstep_player.gd`: plays the local player's steps as 2D/close 3D and remote players' steps as `AudioStreamPlayer3D` through the `audio_director` pool. Step cadence comes from the movement controller's stride, not a timer, so it matches the animation. Stance scaling: sprint `+3 dB`, walk 0, crouch `-8 dB`, prone silent (and no `SoundEvent` at all). Landing from a fall, vaulting and the sprint-dive each get their own one-shot.
- The same step emits the server-side `SoundEvent` with `loudness_m` of 35 (sprint) / 20 (run/walk) / 8 (crouch) / 0 (prone), multiplied by the surface's `loudness_m_mult` and by 0.7 in rain — the client sound and the bot hearing range must come from one table in `data/audio.json`, read by both sides.
- `client/audio/vehicle_audio.gd`: per replicated vehicle, an engine loop whose pitch maps from `rpm_norm` in the vehicle snapshot section (`veh-net-sync`) over a 0.7–1.8 pitch range, plus a load layer that fades in with throttle. Start/stop one-shots on `engine_started` / `engine_stopped`, a horn one-shot, tire skid tied to lateral slip, a `tire_popped` blowout bang, impact thumps scaled by collision impulse, and the explosion. Max audible distance 250 m (scooter and sampan 120 m, `quiet` flag in `data/vehicles.json`), with the same distance low-pass as gunshots.
- Occupants hear an interior mix: engine louder, low-passed wind, exterior world attenuated by 4 dB.
- `client/audio/ambience_controller.gd`: a biome-driven ambience bed, crossfading over 2 s as the listener moves between `jungle`, `paddy`, `town`, `river`, `plantation` (biome sampled from the same terrain control map, at 4 Hz not per frame). Each bed has a day and a dusk variant; add sparse randomised one-shots (birds, insects, distant dogs, a temple bell in town) placed within 30 m of the listener.
- Rain: a global rain bed plus a heavier "under cover" variant when the listener is inside; applies the `-3 dB` global and extra low-pass from `audio-gunshots-propagation`, and raises the ambience bed so quiet cues genuinely get masked.
- All playback allocates from the `audio_director` pool and routes to the `Ambience` or `SFX` bus so the settings screen's volume sliders apply.

## Acceptance
- GUT test `tests/test_footstep_surfaces.gd`:
  - `test_surface_lookup`: a raycast hit on a collider with `surface = "bamboo"` selects the bamboo sample set; an unmapped surface falls back to `dirt` without error.
  - `test_stance_loudness`: emitted `SoundEvent.loudness_m` is 35 sprinting on dirt, 20 walking, 8 crouched, and no event is emitted while prone.
  - `test_surface_multiplier`: sprinting in `paddy_water` yields `loudness_m == 35 * 1.3`; the same step in rain yields that value × 0.7.
  - `test_single_source_of_truth`: the loudness values used by `footstep_player.gd` and by the bot hearing path both read from `data/audio.json` (assert the same dictionary reference/values).
- Manual: walk from a road into a paddy and into a hut and hear three distinct materials; a sedan is clearly audible approaching at ~250 m and a scooter is not until ~120 m; standing in the jungle at dusk in rain, footsteps at 15 m are noticeably harder to hear than in clear weather.

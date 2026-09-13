# MEDIUM — Gunshot distance tiers, supersonic crack, delayed report

**Category:** audio
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M9
**Depends on:** gun-weapon-base, bot-perception, net-snapshot-sync

## Files
- `client/audio/gunshot_player.gd` (new)
- `client/audio/audio_director.gd` (new)
- `data/audio.json` (new)
- `tests/test_gunshot_audio.gd` (new)

## Issue
Sound is the primary information channel in an FPS and there is none: every shot either plays one sample at one volume or nothing at all. The plan requires distance tiers, a supersonic crack that arrives before the muzzle report, and a report delayed by the real travel time at 343 m/s — at 600 m (the plan's gunshot hearing range) that is a 1.75 s gap, which is what lets a player tell "close" from "far" and locate a sniper.

## Fix
- `shared/net/sound_event.gd` (from `bot-perception`) is already broadcast server-side for every shot. The server sends clients a compact `shot_audio {pos, dir, weapon_id, suppressed, tick}` event; the client does all the tiering and delay locally. Do not send per-listener audio decisions from the server.
- `client/audio/gunshot_player.gd`: on a `shot_audio` event compute `d = listener.distance_to(pos)`.
  - Pick a tier from `data/audio.json` `gunshot_tiers`: `close` (0–40 m), `mid` (40–150 m), `far` (150–400 m), `distant` (400–800 m). Each tier names its own sample set per weapon class (pistol, smg, shotgun, carbine, rifle, ar, lmg, sniper, launcher) plus a tail/reverb sample — a distant shot is a different recording, not the close one turned down.
  - Volume: `db = base_db - 20 * log10(max(d, 1) / ref_dist)` clamped to the tier's floor, with an extra `-occlusion_db` (default 6 dB, 12 dB through two occluders) from a single raycast listener→source. Low-pass cutoff falls with distance (20 kHz at 10 m → 1.2 kHz at 600 m) via an `AudioEffectLowPassFilter` on the SFX bus send.
  - Report delay: schedule playback at `d / 343.0` seconds (speed of sound). Use a timer/queue in `audio_director.gd`, not `await` chains per shot, and drop queued reports older than 3 s (the shooter is long gone).
- Supersonic crack: if the cartridge's muzzle velocity from `data/cartridges.json` exceeds 343 m/s (all rifle rounds; .45 ACP at 260 and 9×18 at 320 do not) and the listener is within 15 m of the bullet's path segment, play the crack immediately at `time_of_closest_approach = along_track_distance / muzzle_velocity`, before the report. This is what makes "being shot at" audible and directional.
- Suppressed weapons: use the `suppressed` sample set, `loudness_m` 180 instead of 600, no crack for subsonic loads, and the crack still plays for supersonic rounds through a suppressor (physically correct and tactically important).
- `client/audio/audio_director.gd`: owns a pool of ~24 `AudioStreamPlayer3D`s with priority stealing (closest and newest win), the delayed-report queue, and the bus routing to the `SFX` bus from `ui-settings-keybinds`. Every other audio task allocates through this pool — no scene-local one-shot players.
- Rain (from `world-lighting-variants`) applies a global `-3 dB` and an extra low-pass to distant tiers, matching the bot-perception masking multiplier of 0.7, so what the player hears and what a bot hears degrade together.
- Indoor/outdoor: a simple reverb bus switched by whether the listener is inside a building volume — one `AudioEffectReverb`, two presets, no acoustic simulation.

## Acceptance
- GUT test `tests/test_gunshot_audio.gd` (pure maths, headless):
  - `test_report_delay`: a shot at 343 m schedules its report at 1.0 s ± 0.01; at 686 m, 2.0 s.
  - `test_tier_selection`: distances 10 / 90 / 300 / 600 m select `close / mid / far / distant`.
  - `test_falloff`: 100 m is ~20 dB quieter than 10 m for the same weapon.
  - `test_crack_only_supersonic`: a 7.62×39 shot (715 m/s) passing 8 m from the listener produces a crack; a .45 ACP shot (260 m/s) on the same path does not.
  - `test_stale_reports_dropped`: a queued report older than 3 s is discarded rather than played.
- Manual: two clients 500 m apart on the test map — the listener hears the crack first and the report roughly 1.5 s later, a suppressed shot is inaudible past ~200 m, and firing inside the temple is audibly reverberant.

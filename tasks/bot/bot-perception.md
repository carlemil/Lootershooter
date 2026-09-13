# HIGH — Bot vision cone, occlusion and hearing events

**Category:** bot
**Priority:** HIGH
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-input-adapter, gun-weapon-base, veh-base-vehiclebody

## Files
- `server/bots/bot_perception.gd` (new)
- `server/bots/perception_events.gd` (new)
- `shared/net/sound_event.gd` (new)
- `tests/test_bot_perception.gd` (new)

## Issue
A bot with no perception is either omniscient or blind, and both read as fake. The plan specifies a 110° view cone with occlusion raycasts, hearing at 600 m for gunshots, 250 m for vehicles and 20 m for footsteps, and a prone-in-paddy-water rule that makes a player invisible beyond 40 m. None of that exists, and there is no shared sound event that both the client audio system and the bot ears can consume.

## Fix
- `shared/net/sound_event.gd`: `class_name SoundEvent` with `kind` (`GUNSHOT`, `SUPPRESSED_GUNSHOT`, `VEHICLE`, `FOOTSTEP`, `EXPLOSION`, `SAFE_CRACK`, `VAULT`), `position: Vector3`, `source_peer: int`, `loudness_m: float`, `tick: int`. Emitted server-side by weapons, vehicles, the movement controller and the safe cracker. The client audio tasks consume the same struct — do not invent a second sound type.
- Default `loudness_m`: gunshot 600, suppressed gunshot 180, explosion 800, vehicle 250 (scooter/sampan 120), footstep 20 (sprint 35, crouch 8, prone 0), vault 15, safe crack 120. Rain (from `world-lighting-variants`) multiplies `loudness_m` by 0.7 and bot hearing by 0.7 (masking rule from plan 3.10).
- `server/bots/perception_events.gd`: server-only autoload. `emit_sound(event: SoundEvent)` fans the event out to every `BotPerception` within `loudness_m`, no allocation per listener beyond the hit list. Keep a 1 s ring of recent events for late-ticking bots.
- `server/bots/bot_perception.gd`: per-bot component, ticked at 10 Hz (not 30 Hz — perception is the expensive part of the 33 ms budget), staggered across bots by `peer_id % 3`.
  - Vision: for each candidate actor within `max_view_dist` (250 m, 400 m with binoculars), reject if the angle between the bot's look direction and the actor exceeds 55° (110° full cone); then one raycast from the bot's eye marker to the actor's chest and, if that fails, to the head — two rays max per candidate.
  - Detection is not binary: accumulate `awareness` per target at `rate = base_rate * size_factor * (1 - dist/max_view_dist) * stance_factor * motion_factor`, decaying at 0.5/s when unseen. `awareness >= 1.0` promotes the target to `known`. Stance factors: standing 1.0, crouched 0.7, prone 0.45. Moving targets get ×1.6, sprinting ×2.0.
  - Paddy rule: if the target is prone AND inside an `Area3D` in group `"paddy_water"` AND distance > 40 m, vision is skipped entirely regardless of cone or ray.
  - Ghillie wrap gadget multiplies `rate` by 0.5; a flare (from the flare gun) sets `rate` ×2 inside its radius.
- Hearing: a received `SoundEvent` inserts or refreshes a `heard` memory `{position, kind, tick}` with positional noise of `dist * 0.05` metres (so distant gunshots give a direction, not a pinpoint), and raises `awareness` for a known target at that position. Memory entries expire after 12 s.
- Public read API for the brain: `get_known_enemies() -> Array[Dictionary]` each `{peer_id, last_pos, last_seen_tick, confidence, distance, visible_now}`; `get_recent_sounds(kind := -1)`; `can_see(peer_id) -> bool`.
- Difficulty knobs (from `data/bots.json`): `perception_mult` scales `rate` and `max_view_dist`; easy 0.6, normal 1.0, hard 1.4.

## Acceptance
- GUT test `tests/test_bot_perception.gd`:
  - `test_cone_limits`: a target at 50° off the look axis is a vision candidate; the same target at 60° is not.
  - `test_occlusion`: with a wall collider between bot and target, `awareness` stays 0 after 2 s of ticks.
  - `test_paddy_prone_invisible`: a prone target in a `paddy_water` area at 45 m is never seen; the same target at 35 m is seen.
  - `test_hearing_ranges`: a `GUNSHOT` at 550 m registers a `heard` memory, at 650 m it does not; a `FOOTSTEP` at 25 m does not, at 15 m it does.
- Run `godot --headless -s addons/gut/gut_cmdln.gd -gexit` — all green.

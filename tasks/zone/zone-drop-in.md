# HIGH — Orbit pick, reentry, freefall and parachute

**Category:** zone
**Priority:** HIGH
**Status:** TODO
**Milestone:** M5
**Depends on:** zone-match-loop, move-controller-base, net-input-stream

## Files
- `shared/drop/drop_state.gd` (new)
- `server/match/drop_controller.gd` (new)
- `client/ui/orbit/orbit_map.tscn` (new)
- `client/ui/orbit/orbit_map.gd` (new)
- `tests/test_drop_state.gd` (new)

## Issue
Players currently have to be teleported onto the map. The design opens every match on an orbital screen where the team leader picks a drop point within 20 s (teammates cluster within 150 m), followed by a 5 s uncontrolled reentry capsule, a steerable freefall at up to 60 m/s with 15 m/s of lateral drift, and a parachute that opens automatically at 300 m or manually any time above it. It is a pure state machine — no orbital physics.

## Fix
- `shared/drop/drop_state.gd`, `class_name DropState` (`RefCounted`, deterministic, no nodes): `enum { REENTRY, FREEFALL, CHUTE, LANDED }` and `step(delta, input: Vector2, open_chute: bool)` advancing `position: Vector3` and `velocity: Vector3`.
  - `REENTRY`: 5 s, input ignored, falls on a fixed rail from the spawn altitude (start at 2000 m).
  - `FREEFALL`: vertical speed accelerates toward a terminal `60.0 m/s`; `input` (the look/move vector) tilts the dive and produces lateral speed up to `15.0 m/s`, ramping in over ~0.5 s so it feels like a body, not a plane. Diving straight down reaches terminal faster; levelling off trades descent for glide.
  - `CHUTE`: entered on `open_chute` or automatically when `position.y <= 300.0` above ground. Descent clamps to `6.0 m/s`, lateral up to `12.0 m/s`, turn rate limited.
  - `LANDED` when the ground is reached; hands control back to the normal `CharacterBody3D` controller with zero fall damage from a chute landing.
  - All constants as `const` at the top of the script and referenced by the tests.
- `server/match/drop_controller.gd` (server only): runs `DropState` authoritatively for every player (humans and bots) from the same input packets as normal movement — no separate netcode path. Snapshots position/velocity like any other player state; the client predicts with the identical `DropState`.
- Drop point: the team leader's pick is validated server-side to be inside the map bounds; on `REENTRY` start each teammate is placed at the pick offset by a deterministic ring of up to 150 m (seeded by match seed + player index) so a squad lands together but not stacked.
- No pick made when the 20 s ORBIT timer expires → the server picks for that team: a uniformly random point inside the initial safe circle using the match RNG.
- `client/ui/orbit/orbit_map.tscn`: top-down map of the 2 km world with the initial safe circle, hot-zone-free, a 20 s countdown, click to place the marker (leader only; teammates see it live), and a confirm button. Non-leaders get a "waiting for leader" state.
- Show altitude, horizontal speed and distance-to-marker on the HUD during freefall so players can judge the glide.

## Acceptance
- GUT test `tests/test_drop_state.gd`:
  - `REENTRY` ignores input and lasts exactly 5.0 s before switching to `FREEFALL`.
  - In `FREEFALL`, vertical speed never exceeds 60.0 m/s and lateral speed never exceeds 15.0 m/s for any input, including a max-magnitude input held for 60 s.
  - Falling from 2000 m with no manual open enters `CHUTE` at `y <= 300` (assert within 0.5 m of the auto threshold) and thereafter descends at ≤ 6.0 m/s.
  - A manual open at 900 m enters `CHUTE` immediately and still reaches `LANDED`.
- Open `client/ui/orbit/orbit_map.tscn` and run: the 20 s countdown ticks, clicking places a marker, the confirm button sends one pick; letting it expire still lands the player inside the initial circle.

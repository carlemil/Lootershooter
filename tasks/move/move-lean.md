# MEDIUM — Lean left/right with wall check

**Category:** move
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M2
**Depends on:** move-stances

## Files
- `shared/player/lean.gd` (new)
- `shared/player/movement.gd` (modify)
- `client/player/fp_camera.gd` (modify)
- `tests/shared/test_lean.gd` (new)

## Issue
Q/E leaning is core to corner fighting in a game where a single 7.62 hit matters, and the design explicitly makes leaning block sprint. Nothing implements it: `PlayerState.lean` exists but is never written, so the head never moves, hitboxes never shift and the server has no way to know a player is exposed around a corner. Leaning must also refuse to push the head through a wall, and that refusal must be identical on client and server or the predicted camera will disagree with where the server thinks the head is.

## Fix
- `shared/player/lean.gd`, `class_name Lean`, static, with constants: `MAX_ANGLE_DEG = 18.0`, `MAX_OFFSET = 0.45` (metres of lateral head travel), `LEAN_SPEED = 6.0` (units of lean per second, so full lean in ~0.17 s), `RETURN_SPEED = 9.0`.
- `static target_from_input(input: InputFrame) -> float`: `BTN_LEAN_L` → −1, `BTN_LEAN_R` → +1, both or neither → 0.
- `static step(state: PlayerState, body: CharacterBody3D, input: InputFrame, delta: float) -> void`:
  1. `target = target_from_input(input)`, zeroed when `state.stance == Stance.PRONE` (you cannot lean while prone) or when the player is airborne.
  2. Wall check: from the head position, cast a ray (or a small sphere shape-cast, radius 0.2) `MAX_OFFSET * abs(target)` along the body's right vector (signed by `target`); the allowed magnitude is the hit fraction. Clamp `target` to that fraction so leaning into a wall stops short instead of clipping.
  3. Move `state.lean` toward `target` at `LEAN_SPEED` (toward 0 at `RETURN_SPEED`), clamped to −1..1.
  4. Apply the pose: offset the `Head` node by `right * state.lean * MAX_OFFSET` and roll it by `-state.lean * MAX_ANGLE_DEG`. Do this on the **`Head` node**, which carries the head hitbox, so a leaning player is genuinely more exposed and the server's rewound hitboxes reflect it.
- Movement coupling in `Movement.step`: `abs(state.lean) > 0.1` disables the sprint branch (plan 3.5) and multiplies the target speed by `LEAN_SPEED_MULT = 0.8`.
- `state.lean` is in the public snapshot (quantised to one signed byte) so remote players visibly lean and lag-comp rewinds the leaned head pose.
- Client: `client/player/fp_camera.gd` reads `state.lean` (predicted locally) for the camera roll — it must never compute its own lean value, or prediction and server diverge.
- ADS interaction: leaning does not cancel ADS; the extra sway from leaning is a `gun-weapon-base` concern, expose `Lean.amount(state)` for it.

## Acceptance
- GUT file `tests/shared/test_lean.gd`:
  - `test_lean_reaches_full()` — holding `BTN_LEAN_R` for 0.2 s of ticks gives `state.lean == 1.0` (clamped, `assert_almost_eq` 0.001).
  - `test_lean_blocked_by_wall()` — with a `StaticBody3D` 0.2 m to the player's right, `state.lean` settles at ≤ 0.45 (0.2 / 0.45) and the head's world x never passes the wall plane.
  - `test_prone_cannot_lean()` — in PRONE with `BTN_LEAN_L` held for 1 s, `state.lean` stays 0.0.
  - `test_lean_blocks_sprint()` — with `state.lean = 1.0`, `Movement.speed_for` with `BTN_SPRINT` returns `RUN_SPEED * 0.8`, not `SPRINT_SPEED`.
- Manual: peek a corner in the blockout — the camera and the third-person head both swing out, and a teammate watching sees the lean at the same angle.

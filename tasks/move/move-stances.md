# HIGH — Stances: crouch and prone with collider and camera blending

**Category:** move
**Priority:** HIGH
**Status:** TODO
**Milestone:** M2
**Depends on:** move-controller-base

## Files
- `shared/player/stance.gd` (new)
- `shared/player/movement.gd` (modify)
- `shared/player/player.gd` (modify)
- `tests/shared/test_stance.gd` (new)

## Issue
`Movement.step` already branches on `state.stance`, but nothing ever changes it, so everybody is permanently standing: no crouch-walk, no prone/crawl, and no hiding prone in flooded paddies — which the design leans on for both stealth and bot perception rules. Stance also changes the capsule, and standing up under a low ceiling must be refused on the server, not just visually blocked on the client, or players will clip into geometry after reconciliation.

## Fix
- `shared/player/stance.gd`, `class_name Stance`, static functions and constants:
  - `enum { STAND, CROUCH, PRONE }` mirrored on `PlayerState.stance` (store the int, not a string — it goes over the wire).
  - Capsule heights: `HEIGHT_STAND = 1.8`, `HEIGHT_CROUCH = 1.2`, `HEIGHT_PRONE = 0.6`; camera (Head) heights `EYE_STAND = 1.65`, `EYE_CROUCH = 1.05`, `EYE_PRONE = 0.35`.
  - Transition times: stand↔crouch `0.25 s`, crouch↔prone `0.45 s`, stand↔prone `0.65 s` (goes through crouch). During a transition the player keeps moving but the target speed is multiplied by `TRANSITION_SPEED_MULT = 0.5`.
  - `static desired_stance(current: int, input: InputFrame, was_pressed: Dictionary) -> int`: `BTN_CROUCH` toggles STAND↔CROUCH (hold-to-crouch is a client setting, but the *frame* carries the resulting intent so the server sees one rule); `BTN_PRONE` toggles PRONE from anything; pressing crouch while prone goes to CROUCH, not STAND.
  - `static can_stand_up(body: CharacterBody3D, target_height: float) -> bool`: shape-cast the target capsule upward from the current feet position and return false on any collision with world geometry (exclude other players so bodies cannot trap each other permanently). Called on **both** sides so prediction and server agree.
  - `static apply(state: PlayerState, body: CharacterBody3D, delta: float) -> void`: advances `state.stance_blend` (0..1) toward the target, resizes the `CollisionShape3D` capsule `height` and re-centres its `position.y` to `height / 2`, and sets the `Head` node's local `y` by lerping the eye heights with the same blend — one blend value drives both, so hitbox and camera never disagree.
- Speed rules folded into `Movement.step` step 3: PRONE uses `PRONE_SPEED` (0.8 m/s), CROUCH uses `CROUCH_SPEED` (1.8 m/s), and **sprint is impossible** in CROUCH or PRONE (the sprint branch requires `stance == STAND`).
- Going prone while sprinting is the dive (`move-dive`) — here, just make sure a prone request while airborne is deferred until landing, not applied mid-air.
- Store the blend in `PlayerState.stance_blend: float` and include it in the public snapshot (one quantised byte) so remote players' capsules and animations match what the server used for hit detection.
- Paddy water / concealment rules are `world-paddies-plantation-jungle` and `bot-perception`; expose `Stance.is_prone(state)` for them to query rather than duplicating the enum comparison.

## Acceptance
- GUT file `tests/shared/test_stance.gd`:
  - `test_crouch_toggle()` — a frame with `BTN_CROUCH` from STAND gives CROUCH; the same frame again gives STAND.
  - `test_prone_speed_cap()` — in PRONE with full forward input, `Movement.speed_for` returns 0.8 within 0.01, and the sprint button does not change it.
  - `test_capsule_and_eye_match_blend()` — mid-transition (`stance_blend == 0.5`, STAND→CROUCH) the capsule height is within 0.01 of 1.5 and the Head y within 0.01 of 1.35.
  - `test_blocked_standup()` — with a ceiling 1.3 m above the floor, `can_stand_up` for the 1.8 m capsule returns false and the stance stays CROUCH after `apply`.
  - `test_transition_times()` — STAND→PRONE takes 0.65 s of ticks to reach `stance_blend == 1.0` (±1 tick).
- Manual: crouch and prone change eye height smoothly, standing under a table is refused on both client and server (no rubber-band), and a prone player's capsule visibly fits under a 0.8 m gap.

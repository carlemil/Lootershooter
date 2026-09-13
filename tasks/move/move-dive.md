# MEDIUM — Sprint dive to prone with no-aim window

**Category:** move
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M2
**Depends on:** move-stances, move-stamina

## Files
- `shared/player/dive.gd` (new)
- `shared/player/movement.gd` (modify)
- `tests/shared/test_dive.gd` (new)

## Issue
The movement list includes a sprint-to-prone dive, and the design gives it a deliberate cost: 25 stamina and 0.3 s where you cannot aim. Without it, breaking contact in open rice paddies has no skill expression, and the dive is also a movement the bots must be able to read (a diving target is briefly helpless). None of the state, timing or costs exist yet.

## Fix
- `shared/player/dive.gd`, `class_name Dive`, static. Constants: `COST_STAMINA = 25.0`, `LAUNCH_SPEED = 6.5` (horizontal), `LAUNCH_UP = 2.0` (vertical), `DURATION = 0.75` (airborne + slide), `NO_AIM_SECONDS = 0.3`, `SLIDE_FRICTION = 8.0`, `COOLDOWN = 1.5`.
- Trigger, checked in `Movement.step` before the normal branches: `BTN_DIVE` (or `BTN_PRONE` pressed while sprinting — treat both as the same intent so a player who just slams prone at speed gets the dive) **and** `state.stance == Stance.STAND` **and** currently sprinting (speed ≥ `SPRINT_SPEED * 0.8`) **and** `state.stamina >= COST_STAMINA` **and** `input.tick >= state.dive_cooldown_tick`.
- On trigger:
  - Charge 25 stamina once, keyed on `state.dive_tick = input.tick` so a replay during reconciliation cannot double-charge.
  - `velocity = forward * LAUNCH_SPEED + Vector3.UP * LAUNCH_UP`.
  - `state.stance = Stance.PRONE` immediately (the capsule shrinks as the dive starts — that is the point of the move), with `stance_blend` driven at the dive's own rate rather than the normal 0.65 s transition.
  - `state.no_aim_until_tick = input.tick + round(NO_AIM_SECONDS * NetConstants.TICK_RATE)` (9 ticks at 30 Hz).
  - `state.dive_until_tick = input.tick + round(DURATION * TICK_RATE)`; `state.dive_cooldown_tick = dive_until_tick + round(COOLDOWN * TICK_RATE)`.
- While `input.tick < state.dive_until_tick`: gravity applies normally, input movement is ignored (no air-steering out of a dive), and once grounded the horizontal velocity decays with `SLIDE_FRICTION` so the dive ends in a short slide.
- Aiming: `gun-weapon-base` must consult `state.no_aim_until_tick` — expose `static can_aim(state, tick) -> bool` here and have the weapon code call it rather than comparing ticks itself. Firing from the hip during the window is allowed (with full spread); ADS is not.
- Landing in water (`move-swim`) or on a slope steeper than `MAX_SLOPE_DEG` ends the dive early and drops to a normal prone.
- Diving is blocked while mantling, on a ladder, in a vehicle, or while the wrist store is raised.

## Acceptance
- GUT file `tests/shared/test_dive.gd`:
  - `test_dive_costs_25_stamina_once()` — stamina 100 before, 75 after the trigger tick; replaying the same input frame 5 times (simulating reconciliation) still leaves 75.
  - `test_dive_requires_sprint_and_stamina()` — at walking speed the dive does not trigger; at sprint with stamina 20 it does not trigger and stamina is unchanged.
  - `test_no_aim_window()` — `Dive.can_aim(state, dive_tick + 8)` is false, `can_aim(state, dive_tick + 9)` is true.
  - `test_dive_ends_prone()` — after `DURATION` of ticks the player is on the floor, `stance == PRONE`, horizontal speed under 0.5 m/s.
  - `test_cooldown()` — triggering again 1.0 s after the dive ended is refused; 1.5 s after, it is allowed.
- Manual: sprint across open ground and dive — the camera drops, the player slides, the ADS input is ignored for ~0.3 s, and a second dive is refused until the cooldown clears.

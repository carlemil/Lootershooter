# HIGH — Shared CharacterBody3D controller: walk, run, sprint, gravity, slopes

**Category:** move
**Priority:** HIGH
**Status:** TODO
**Milestone:** M2
**Depends on:** net-prediction-reconcile

## Files
- `shared/player/movement.gd` (new)
- `shared/player/move_config.gd` (new)
- `shared/player/player.gd` (modify)
- `tests/shared/test_movement.gd` (new)

## Issue
`Player.apply_input()` is still a stub, so neither the server sim nor client prediction actually moves anyone. The movement maths must live in `shared/` and be fully deterministic — same input, same tick delta, same result on both sides — or reconciliation will fight itself every tick. It also has to be a plain function over state, not a node reading globals, so prediction can replay it 32 times in one frame.

## Fix
- `shared/player/move_config.gd`, `class_name MoveConfig`, all `const` (these are tuning numbers, not weapon data, so they stay in code):
  - `WALK_SPEED = 3.0`, `RUN_SPEED = 5.0`, `SPRINT_SPEED = 7.0`, `CROUCH_SPEED = 1.8`, `PRONE_SPEED = 0.8` (all m/s).
  - `ACCEL_GROUND = 40.0`, `ACCEL_AIR = 8.0`, `FRICTION = 12.0`, `GRAVITY = 9.81`, `MAX_SLOPE_DEG = 46.0`, `STEP_HEIGHT = 0.4`, `AIR_CONTROL = 0.3`.
  - `BACKWARD_MULT = 0.75`, `STRAFE_MULT = 0.9` — you are slower going backwards and sideways.
- `shared/player/movement.gd`, `class_name Movement` — **static** functions only, no member state:
  - `static step(state: PlayerState, input: InputFrame, delta: float, body: CharacterBody3D) -> void` is the single entry point, called by the server sim, by client prediction/replay, and by bots.
  - Order inside `step`, fixed and documented (changing it changes the sim):
    1. Apply `look_yaw`/`look_pitch` from the input to `state` (already clamped by `InputFrame.sanitize`).
    2. Compute `wish_dir` = the input `move` rotated by `look_yaw`, then normalised; apply `BACKWARD_MULT`/`STRAFE_MULT` to the target speed.
    3. Choose the target speed: `PRONE_SPEED`/`CROUCH_SPEED` by stance (from `move-stances`), else `SPRINT_SPEED` when `BTN_SPRINT` is held **and** forward input > 0.5 **and** stamina > 0 **and** not leaning (plan 3.5: leaning blocks sprint), else `RUN_SPEED`, and `WALK_SPEED` when the walk modifier is held.
    4. Accelerate the horizontal velocity toward `wish_dir * target_speed` with `ACCEL_GROUND` (or `ACCEL_AIR * AIR_CONTROL` when airborne), and apply `FRICTION` when `wish_dir` is zero and grounded.
    5. Apply gravity to `velocity.y` (`-GRAVITY * delta`) when not on floor.
    6. `body.velocity = state.velocity`; `body.move_and_slide()`; write `body.velocity` and `body.global_position` back into `state` — the body is the collision oracle, the state is the truth carried over the network.
  - Slopes: set `body.floor_max_angle = deg_to_rad(MAX_SLOPE_DEG)`, `body.floor_snap_length = 0.3`, `body.floor_stop_on_slope = true`, `body.up_direction = Vector3.UP`. Steeper than 46° = slide down, no climbing.
  - Step-up: rely on `body.floor_block_on_wall = false` plus a `motion_mode = MOTION_MODE_GROUNDED` and a 0.4 m `safe_margin`-based step; if Godot's built-in step-up proves insufficient, implement an explicit shape-cast step: cast up `STEP_HEIGHT`, forward, then down, and accept the result only if the landing normal is within `MAX_SLOPE_DEG`.
  - `static speed_for(state, input) -> float` exposed separately so tests and the stamina task can query the intended speed without running physics.
- Determinism rules, enforced here: no `randf()`, no `Time.get_ticks_msec()`, no `Input.*`, no `get_process_delta_time()` — `delta` is always `NetConstants.TICK_DELTA` in the authoritative path.
- Wire `Player.apply_input(input, delta)` to call `Movement.step(state, input, delta, self)` and emit `input_applied(input.tick)`.
- Sprint consumes stamina, but the drain itself belongs to `move-stamina`; here, only *read* `state.stamina > 0` as the gate and leave a `# see move-stamina` comment.

## Acceptance
- GUT file `tests/shared/test_movement.gd` (uses a real `CharacterBody3D` in a bare `Node3D` scene with a large `StaticBody3D` floor):
  - `test_forward_reaches_run_speed()` — 30 ticks of full forward input at `TICK_DELTA` gives horizontal speed within 0.05 of 5.0 m/s and displacement within 0.1 m of 5.0 m after 1 s of steady state.
  - `test_sprint_is_faster()` — with `BTN_SPRINT` and stamina 100, steady-state speed is within 0.05 of 7.0 m/s; with stamina 0 it falls back to 5.0 m/s.
  - `test_backward_is_slower()` — `move = Vector2(0, -1)` steady speed is within 0.05 of `5.0 * 0.75`.
  - `test_determinism()` — run the same 120-input sequence twice from the same start; final positions are bit-identical (`assert_eq`, not `almost_eq`).
  - `test_gravity_and_floor()` — dropped from 5 m, the body lands and `velocity.y` settles to ~0 with `is_on_floor()` true.
- Manual: walking around a blockout, a 0.4 m curb can be stepped onto, a 46°+ slope cannot be climbed, and the local player's motion is immediate with no jitter against a 150 ms-latency server.

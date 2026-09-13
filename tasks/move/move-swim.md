# MEDIUM — Water volumes, swimming, holster and drop-pack

**Category:** move
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M2
**Depends on:** move-stances

## Files
- `shared/player/swim.gd` (new)
- `world/components/water_volume.tscn` (new)
- `world/components/water_volume.gd` (new)
- `shared/player/movement.gd` (modify)
- `tests/shared/test_swim.gd` (new)

## Issue
The map is riverine: canals, paddies and a river cut across every route, and the design says water means slow movement, no sprint, holstered weapons and the option to dump a heavy backpack to swim faster. Today water is not represented at all, so players would walk along the canal bed with a rifle up. Wading (paddies, shallow) and swimming (canals, deep) need to be distinct because prone in shallow paddy water is a concealment mechanic elsewhere in the design.

## Fix
- `world/components/water_volume.tscn`: an `Area3D` in group `"water"` with a `BoxShape3D` (or convex shape), plus exported `surface_y: float` and `flow: Vector3 = Vector3.ZERO` (gentle current, used by the river). The script `water_volume.gd` only exposes `surface_y` and `flow` — no per-frame logic; the player queries it.
- `shared/player/swim.gd`, `class_name Swim`, static. Constants: `WADE_DEPTH = 0.7` (hip), `SWIM_DEPTH = 1.4` (chest), `SWIM_SPEED = 1.6`, `SWIM_SPEED_NO_PACK = 2.2`, `WADE_SPEED_MULT = 0.55`, `BUOYANCY = 6.0`, `WATER_DRAG = 3.0`, `SURFACE_SNAP = 0.15`.
- `static water_state(body, areas) -> Dictionary` → `{"in_water": bool, "depth": float, "surface_y": float, "mode": NONE|WADE|SWIM}`, where `depth = surface_y - feet_y`, `WADE` when `depth >= WADE_DEPTH`, `SWIM` when `depth >= SWIM_DEPTH`.
- Rules applied in `Movement.step` when `mode != NONE`:
  - **WADE**: normal ground movement with the target speed × `WADE_SPEED_MULT`; sprint disabled; prone allowed (this is the paddy-hiding case); weapons stay up.
  - **SWIM**: gravity replaced by buoyancy toward `surface_y` (`velocity.y += (surface_y - head_y) * BUOYANCY * delta`, damped by `WATER_DRAG`); horizontal movement at `SWIM_SPEED` (or `SWIM_SPEED_NO_PACK` when no backpack is equipped); stance forced to `STAND`; jump, dive, mantle, lean and ADS all disabled; `state.weapon_holstered = true` so `gun-weapon-base` refuses to fire.
  - Entering SWIM sets `state.holster_until_tick` on exit so there is a 0.8 s re-equip delay when you climb out — you are vulnerable leaving the water.
- **Drop pack**: `BTN_INTERACT` while swimming drops the equipped backpack as a world pickup (hook into `econ-inventory`'s drop path; for now emit `signal backpack_dropped(unique_id)` and leave a `# TODO(econ-inventory)` for the actual item spawn) and switches the speed to `SWIM_SPEED_NO_PACK`.
- Exiting water: when `depth` falls below `WADE_DEPTH` on ground with a walkable normal, restore normal movement; if the bank is too steep, allow a mantle out via `Traversal.find_ledge` from the swim state.
- Stamina: swimming drains at `SPRINT_DRAIN * 0.5` (5/s) through `Stamina.charge` — expose it as a continuous drain in `Stamina.step` rather than a new system. At 0 stamina the swim speed halves (you do not drown; drowning is out of scope).
- `flow` adds `flow * delta` to the position while in SWIM mode, so the river pushes downstream.
- Bots read `Swim.water_state` too — no separate bot water logic.

## Acceptance
- GUT file `tests/shared/test_swim.gd` (a water `Area3D` with `surface_y = 2.0` over a floor at y = 0):
  - `test_mode_by_depth()` — feet at 1.5 (depth 0.5) → `NONE`; feet at 1.2 (depth 0.8) → `WADE`; feet at 0.4 (depth 1.6) → `SWIM`.
  - `test_wade_speed()` — in WADE with full forward input, steady speed is within 0.05 of `5.0 * 0.55`.
  - `test_swim_speed_and_pack()` — in SWIM with a backpack, steady speed within 0.05 of 1.6; after `backpack_dropped`, within 0.05 of 2.2.
  - `test_swim_holsters_and_blocks()` — entering SWIM sets `weapon_holstered == true`, and `BTN_SPRINT`/`BTN_JUMP`/`BTN_PRONE` produce no sprint, no vertical impulse and no stance change.
  - `test_buoyancy_settles_at_surface()` — dropped into deep water from 5 m, after 3 s of ticks the head y is within `SURFACE_SNAP` of `surface_y`.
- Manual: swim a canal in the blockout — the weapon lowers, sprint is refused, dropping the pack visibly speeds you up, and climbing out has a short re-equip delay.

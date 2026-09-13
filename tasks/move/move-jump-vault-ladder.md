# MEDIUM — Jump, vault/mantle (<=1.5 m) and ladder climbing

**Category:** move
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M2
**Depends on:** move-stances

## Files
- `shared/player/traversal.gd` (new)
- `shared/player/movement.gd` (modify)
- `world/components/ladder.tscn` (new)
- `world/components/ladder.gd` (new)
- `tests/shared/test_traversal.gd` (new)

## Issue
The map is full of paddy dikes, sandbag walls, stilt-house platforms, watchtowers and bunker lips, and right now a player can only walk on what a 0.4 m step-up reaches. The design specifies jumping, mantling obstacles up to 1.5 m, and ladders — and bots will later need navigation links at exactly the same places, so the vault rule has to be a shared, queryable function rather than something buried in the controller. Vaulting also cancels ADS, which matters for combat feel.

## Fix
- `shared/player/traversal.gd`, `class_name Traversal`, static, constants: `JUMP_VELOCITY = 4.5` (≈1.0 m apex), `MANTLE_MAX_HEIGHT = 1.5`, `MANTLE_MIN_HEIGHT = 0.5`, `MANTLE_DEPTH = 0.6` (required flat ledge depth), `MANTLE_DURATION = 0.55`, `MANTLE_REACH = 0.9`, `LADDER_SPEED = 2.2`, `COYOTE_TIME = 0.1`.
- **Jump**: in `Movement.step`, on `BTN_JUMP` with `body.is_on_floor()` (or within `COYOTE_TIME` of leaving the floor) and `stance == STAND` and stamina ≥ 8: set `velocity.y = JUMP_VELOCITY`, mark `state.jump_tick = input.tick` (used by `move-stamina` to charge the −8 cost exactly once per jump, never per tick). Crouch/prone: pressing jump first stands the player up instead of jumping.
- **Mantle detection**, `static find_ledge(body, state) -> Dictionary` returning `{"ok": bool, "target": Vector3, "height": float}`:
  1. Forward ray at chest height (`1.2 m`) up to `MANTLE_REACH` — must hit a surface whose normal is near-vertical-wall (`abs(normal.y) < 0.4`).
  2. From `hit.position + forward * 0.3 + up * MANTLE_MAX_HEIGHT`, cast **down** `MANTLE_MAX_HEIGHT`; the hit is the ledge top. Reject if `ledge_height - feet_y` is outside `MANTLE_MIN_HEIGHT..MANTLE_MAX_HEIGHT` or the ledge normal is steeper than `MoveConfig.MAX_SLOPE_DEG`.
  3. Clearance: capsule-cast the crouched capsule at the ledge target; reject if it collides (no mantling into a crawlspace you do not fit in).
  - Deterministic and side-effect free so both sides and `world-navmesh-bake` can call it.
- **Mantle execution**: a scripted, non-physics move — set `state.mantle_until_tick`, `state.mantle_from`, `state.mantle_to`; while active, `Movement.step` ignores input movement and lerps the body along a two-segment path (up, then forward) over `MANTLE_DURATION`, with `velocity` zeroed and gravity off. On completion the player ends crouched if headroom is tight, else standing. Because it is a pure function of `(from, to, start_tick, current_tick)`, prediction replays it identically.
- Mantling sets `state.ads_blocked_until_tick` so ADS is cancelled and cannot restart until the mantle ends (plan 3.5).
- **Ladders**: `world/components/ladder.tscn` is an `Area3D` in the group `"ladder"` with a `Marker3D` `Top`, a `Marker3D` `Bottom` and an exported `climb_normal: Vector3`. `Traversal.ladder_step(state, body, input, area, delta)`: while overlapping and facing within 60° of `-climb_normal`, gravity is off, vertical velocity = `input.move.y * LADDER_SPEED`, horizontal motion is locked to the ladder axis, jump detaches with a small push off the normal, and reaching `Top` snaps the player onto the platform. Sprint and ADS are disabled on a ladder.
- Add a `navigation_link` marker pair to both the ladder scene and a `vault_link` helper so `world-navmesh-bake` and `bot-navigation` reuse the same geometry instead of re-deriving it.

## Acceptance
- GUT file `tests/shared/test_traversal.gd` (physics scene with boxes of known heights):
  - `test_jump_apex()` — from rest, a jump reaches 0.95–1.10 m above the start and returns to the floor.
  - `test_mantle_accepts_1_2m()` — a 1.2 m box in front returns `ok == true` with `height` within 0.02 of 1.2; after `MANTLE_DURATION` of ticks the player stands on top (y within 0.05 of 1.2).
  - `test_mantle_rejects_1_8m()` — a 1.8 m box returns `ok == false` and the player does not move vertically.
  - `test_mantle_rejects_no_clearance()` — a 1.0 m ledge with a ceiling 0.5 m above it returns `ok == false`.
  - `test_ladder_climb()` — inside the ladder area with full forward input for 1 s, the player rises within 0.1 m of 2.2 m and horizontal position stays within 0.05 m of the ladder axis.
- Manual: vault a sandbag wall and a paddy dike, climb a watchtower ladder and step off at the top, and confirm ADS drops during the vault and can be re-aimed after.

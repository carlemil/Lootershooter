# HIGH — 200 ms hitbox history ring and rewind API

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-snapshot-sync

## Files
- `server/net/lagcomp.gd` (new)
- `server/net/lagcomp_registry.gd` (new)
- `tests/server/test_lagcomp.gd` (new)

## Issue
A client shoots at what it sees, which is roughly 100 ms of interpolation delay plus half the round trip behind the server's present. If the server resolves hits against present-time hitboxes, players will miss targets they clearly hit. The plan calls for a 200 ms history ring on the server that can rewind every player's hitboxes to the tick the shooter actually saw, run the shot there, and restore. The kill cam (`polish-killcam-stats`) reads the same ring.

## Fix
- `server/net/lagcomp.gd`, `class_name LagComp` — a pure ring buffer, no nodes, so it unit-tests headless:
  - Capacity `SIZE = ceil(NetConstants.LAGCOMP_MS / 1000.0 * NetConstants.TICK_RATE) + 2` (200 ms at 30 Hz = 6 ticks, +2 slack = 8). Store per entry: `tick: int`, and per player `{position, look_yaw, look_pitch, stance, alive}` — hitbox *poses*, not full `PlayerState`.
  - `record(tick: int, players: Dictionary)` writes one entry, overwriting the oldest.
  - `get_at(tick: int) -> Dictionary` returns the entry for that exact tick; if the tick falls between two recorded ticks (it will, because snapshots are 20 Hz and clients aim between them), **interpolate** position linearly and angles with `lerp_angle` between the two bracketing entries.
  - `clamp_tick(requested: int, now: int) -> int` clamps a request to `[now - SIZE + 1, now]` and returns the clamp — a client asking to rewind 2 s gets 200 ms, never more. Expose `was_clamped` so anti-cheat can count it.
  - `oldest_tick()` / `newest_tick()`.
- `server/net/lagcomp_registry.gd`: a `Node` on the server that calls `LagComp.record(tick, poses)` once per server tick after the sim step, and offers the rewind sandwich:
  - `rewind_to(tick: int, exclude_id: int) -> void` — moves every registered player's hitbox nodes (the `HitboxRoot` from `net-player-spawn`) to the historic pose. The shooter is excluded so it is never rewound against itself.
  - `restore() -> void` — puts every hitbox back to the present pose. Always call it in the same frame; wrap the shot resolution so an early `return` cannot skip it.
  - `with_rewind(tick, exclude_id, callable)` helper that does rewind → call → restore, and is the only public way the gun code is allowed to use it.
  - Rewind moves **hitboxes only**, never the `CharacterBody3D` position or velocity — the player's own movement sim must not see the rewind.
- The tick a shot rewinds to is `min(client_reported_fire_tick, server_tick)` after `clamp_tick`; never trust a raw client tick.
- Dead or disconnected players are removed from the registry on the same tick they die; a rewind must skip entries whose `alive` is false at that historic tick (you cannot hit a corpse-tick).
- Record cost: 20 players × 8 entries × ~40 bytes is trivial — use plain Dictionaries, do not optimise.

## Acceptance
- GUT file `tests/server/test_lagcomp.gd`:
  - `test_ring_capacity()` — recording 50 ticks leaves `newest_tick() == 49` and `oldest_tick() == 42` (SIZE 8); `get_at(30)` returns empty.
  - `test_exact_tick_lookup()` — a player recorded at `(10, 0, 0)` on tick 5 comes back exactly at tick 5.
  - `test_interpolates_between_ticks()` — positions `(0,0,0)` at tick 4 and `(2,0,0)` at tick 6; a fractional request midway (tick 5, recorded absent) returns `(1,0,0)` within 0.001 m, and `lerp_angle` handles a yaw pair of 3.0 → −3.0 rad without spinning the long way.
  - `test_clamp_rejects_old_request()` — `now = 100`, requested tick 40 → clamped to 93 with `was_clamped == true`.
  - `test_rewind_then_restore_is_identity()` — record 8 ticks of motion, `rewind_to(now - 5)`, `restore()`, and every hitbox transform equals its pre-rewind transform within 0.0001.
- Manual: with a client on 150 ms simulated latency, firing at a strafing bot registers hits where the crosshair was, and the server log shows rewinds of 4–6 ticks with `was_clamped == false`.

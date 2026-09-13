# MEDIUM — Throwables: frag, F1, smoke, concussion, Molotov

**Category:** gun
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-hitzones-damage

## Files
- `shared/weapons/throwable.gd` (new)
- `server/combat/throwable_manager.gd` (new)
- `client/player/throw_arc.gd` (new)
- `data/items.json` (modify)
- `tests/shared/test_throwable.gd` (new)

## Issue
The store sells M67 frags, F1s, M18 smoke, Mk3A2 concussion and Molotovs at $150–400 with four throwable slots on the player, but nothing can be thrown. Grenades are the main tool for clearing bunkers and tunnels and for breaking a camped hot zone, and bots need them too.

## Fix
- Data per throwable in `data/items.json`: `"slot": "throwable"`, `"fuse_s"`, `"damage"`, `"radius"`, `"falloff"` (`linear`|`quadratic`), `"effect"` (`frag`|`smoke`|`concussion`|`fire`), `"cookable"` (bool), `"bounce"` (restitution), `"weight"`, `"duration_s"` (smoke/fire).
- `shared/weapons/throwable.gd`, `class_name Throwable`, static and deterministic:
  - `static throw_velocity(power: float, look_dir: Vector3, stance: int) -> Vector3` — `power` 0..1 from the hold duration, mapping to 8–22 m/s, plus a fixed upward bias; prone throws are weaker (×0.6).
  - `static simulate(pos, vel, delta, space_state) -> Dictionary` — a stepped projectile with gravity and bounce (restitution from data, friction on contact), returning the new state and any collision. Same fixed 30 Hz step as everything else so the client's arc preview matches the server's flight.
  - `static explode(item, position, players, space_state) -> Array` — for each player within `radius`, a line-of-sight ray (cover blocks blast), `damage * falloff(distance)` applied via `Damage.compute` with zone `"chest"` and no energy falloff. Concussion applies a screen/audio effect and a 1.5 s aim penalty instead of damage. Smoke spawns a persistent volume. Fire spawns a damage-over-time area (`8 HP/s` inside, `duration_s`).
- **Cooking**: holding fire after pulling the pin starts the fuse on the *server* at the tick of the pull. Releasing throws with the remaining fuse. Holding past the fuse detonates in hand. The client predicts the timer visually but the server's pull tick is authoritative.
- `server/combat/throwable_manager.gd` (server only): owns live throwables, steps them each tick, handles the fuse, calls `explode`, emits `throwable_spawned` / `throwable_exploded` events to clients for VFX/audio. A grenade is a networked entity only as an event plus position updates at snapshot rate — do not make it a full replicated node.
- Smoke: an `Area3D` volume that grows over 2 s and lasts `duration_s`. It must block **bot vision** (`bot-perception` raycasts test the group `"smoke"`) — that is the point of buying it.
- `client/player/throw_arc.gd`: renders the predicted arc while the throw is held, by calling the same `Throwable.simulate` with the local look direction and a `PhysicsRayQueryParameters` sweep — one code path, no separate preview maths.
- Throwables come from the four throwable slots; consuming one decrements the inventory stack via `econ-inventory`.

## Acceptance
- GUT file `tests/shared/test_throwable.gd`:
  - `test_arc_matches_simulation()` — the client-side preview points and the server simulation over 60 ticks agree within 0.01 m at every step.
  - `test_fuse_timing()` — an M67 with `fuse_s = 4.0` thrown at tick 0 explodes at tick 120 ±1; cooked for 2 s, it explodes at tick 60 ±1.
  - `test_cook_too_long_kills_thrower()` — holding past the fuse detonates at the thrower's position and applies damage to the thrower.
  - `test_damage_falloff_and_cover()` — a player at the blast centre takes full damage; at `radius * 0.5` with linear falloff, half; behind a `StaticBody3D` wall at 2 m, zero.
  - `test_smoke_blocks_vision()` — a ray from A to B through an active smoke volume reports blocked; after `duration_s` it does not.
- Manual: cook a frag and land it in a bunker, pop smoke across a paddy and watch a bot lose track of you, and throw a Molotov into a doorway to deny it.

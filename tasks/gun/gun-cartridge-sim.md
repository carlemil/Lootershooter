# HIGH — Projectile stepper: gravity, drag, per-tick raycast

**Category:** gun
**Priority:** HIGH
**Status:** TODO
**Milestone:** M3
**Depends on:** infra-data-loader, net-lagcomp-history

## Files
- `shared/ballistics/projectile.gd` (new)
- `shared/ballistics/ballistics.gd` (new)
- `server/combat/projectile_manager.gd` (new)
- `tests/shared/test_ballistics.gd` (new)

## Issue
Every weapon in this game fires a simulated projectile, not a hitscan: per-cartridge muzzle velocity (5.56×45 at 990 m/s down to .45 ACP at 260 m/s), gravity drop and quadratic drag all matter at the ranges this map allows. Nothing simulates a bullet yet, so there is no way to resolve a shot at all. Projectiles live server-side only; clients get a tracer event and render visuals themselves.

## Fix
- `shared/ballistics/projectile.gd`, `class_name Projectile extends RefCounted`: `origin`, `position`, `prev_position`, `velocity`, `cartridge_id`, `shooter_id`, `spawn_tick`, `energy_j`, `pellet_index`, `penetrations_used`, `alive`.
- `shared/ballistics/ballistics.gd`, `class_name Ballistics`, static and deterministic (no `randf()`; any spread comes in pre-computed from a seeded RNG):
  - `static spawn(cartridge: Dictionary, origin: Vector3, dir: Vector3, shooter_id: int, tick: int) -> Projectile` — `velocity = dir.normalized() * cartridge.muzzle_velocity`, `energy_j = 0.5 * (mass_g / 1000.0) * v²`.
  - `static step(p: Projectile, delta: float) -> void` — `p.prev_position = p.position`; drag `p.velocity -= p.velocity.normalized() * (cartridge.drag_k * p.velocity.length_squared()) * delta`; gravity `p.velocity.y -= 9.81 * delta`; `p.position += p.velocity * delta`; recompute `energy_j` from the new speed.
  - `static energy_fraction(p) -> float` = current energy / muzzle energy, used by damage and penetration.
  - `static max_range_reached(p) -> bool` — true past 1500 m travelled or below 10 % muzzle energy.
- `server/combat/projectile_manager.gd` (server only), one instance on the match node:
  - Holds `Array[Projectile]`; `fire(weapon_id, cartridge_id, origin, dir, shooter_id, fire_tick)` creates one projectile per pellet (shotguns: 8 pellets for `12ga_buck`, each with its own seeded spread offset).
  - Each server tick, for each live projectile: `Ballistics.step(p, NetConstants.TICK_DELTA)`, then a **segment raycast** from `prev_position` to `position` via `PhysicsDirectSpaceState3D.intersect_ray`, excluding the shooter. This segment sweep is what makes a 990 m/s round hit a 0.35 m-wide target despite moving 33 m per tick.
  - Hits are handed to `gun-hitzones-damage` (players) or `gun-penetration-ricochet` (world); the projectile dies when neither continues it.
  - The whole tick's worth of projectile stepping runs **inside** `LagCompRegistry.with_rewind(fire_tick, shooter_id, ...)` for the first tick of a projectile's life; after that it runs against present-time geometry (world geometry does not move).
  - Emits `tracer` events (`origin`, `dir`, `speed`, `cartridge_id`) to clients in range — `gun-tracers-fx` renders them.
- Budget guard: cap live projectiles at 400; drop the oldest and log when exceeded.

## Acceptance
- GUT file `tests/shared/test_ballistics.gd` (pure maths, no physics world — step the projectile and measure the trajectory):
  - `test_drop_at_100m_556()` — 5.56×45 fired perfectly level: at 100 m downrange, drop is between 0.04 m and 0.09 m.
  - `test_drop_at_300m_556()` — same round at 300 m: drop is between 0.45 m and 0.75 m, and time of flight is between 0.31 s and 0.40 s.
  - `test_drop_at_100m_45acp()` — .45 ACP (260 m/s) at 100 m drops between 0.65 m and 0.95 m (a much slower, loopier round).
  - `test_drag_reduces_speed()` — after 300 m, the 7.62×39 projectile's speed is strictly below 715 m/s and above 500 m/s, and `energy_fraction` is between 0.45 and 0.85.
  - `test_determinism()` — two identical spawns stepped 60 times land on bit-identical positions.
- Manual: fire at a 300 m target on the blockout — the round visibly drops and must be held over.

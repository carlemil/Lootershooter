# MEDIUM — Material penetration and shallow-angle ricochet

**Category:** gun
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-cartridge-sim

## Files
- `shared/ballistics/materials.gd` (new)
- `shared/ballistics/penetration.gd` (new)
- `world/components/surface_material.gd` (new)
- `server/combat/projectile_manager.gd` (modify)
- `tests/shared/test_penetration.gd` (new)

## Issue
Stilt-house walls are thin wood and bamboo, town blocks are brick and concrete, and outposts are sheet metal and sandbags — but every surface currently stops every bullet dead. The design fixes the table (wood 0.6, bamboo 0.7, sheet metal 0.4, brick 0.1, concrete 0), allows at most one wall per round, and ricochets at incidence under 15° with a 30 % chance keeping 40 % energy.

## Fix
- `world/components/surface_material.gd`: a tiny script attached to `StaticBody3D`/`CSG` colliders exposing `@export var material_id: String = "concrete"`. Lookup helper `static of(collider) -> String` returns `"concrete"` when absent, so unmarked geometry is always safe (bullet-proof), never accidentally permeable.
- `shared/ballistics/materials.gd`, `class_name Materials`: `const PEN = {"wood": 0.6, "bamboo": 0.7, "sheet_metal": 0.4, "brick": 0.1, "concrete": 0.0, "sandbag": 0.05, "foliage": 0.95, "water": 0.2, "glass": 0.85}` plus `const HARD = ["concrete", "brick", "sheet_metal", "steel"]` for the ricochet rule and `static pen_factor(id) -> float`.
- `shared/ballistics/penetration.gd`, `class_name Penetration`, static and deterministic (the 30 % ricochet roll takes a **seeded** `RandomNumberGenerator` argument — never `randf()`):
  - `static resolve(p: Projectile, hit: Dictionary, material_id: String, rng: RandomNumberGenerator) -> Dictionary` returning `{"action": "stop"|"penetrate"|"ricochet", "new_velocity": Vector3, "new_energy": float, "exit_point": Vector3}`.
  - Order: compute `incidence_deg = 90.0 - rad_to_deg(acos(abs(dir.dot(normal))))` (angle from the surface plane).
    1. **Ricochet** first: material in `HARD` and `incidence_deg < 15.0` and `rng.randf() < 0.30` → reflect the direction about the normal, keep 40 % of the energy (`new_velocity = reflected * sqrt(0.4) * speed`), do **not** count it as a penetration.
    2. **Penetrate**: `remaining = energy_fraction * pen_factor(material)`; penetrate when `remaining > 0.15` **and** `p.penetrations_used == 0` (max one wall). Find the exit point by raycasting backwards from a point 0.5 m past the entry along the direction; reject walls thicker than 0.5 m. New energy = `energy * pen_factor * (1.0 - thickness_m)`; increment `penetrations_used`.
    3. Otherwise `"stop"`.
  - `foliage` is a special case: it never counts toward `penetrations_used` (you can shoot through a bamboo thicket) but each leaf hit costs 5 % energy and deflects the direction by up to 0.3° using the seeded RNG.
- Wire it into `projectile_manager.gd`: on a world hit, call `Penetration.resolve` with the match RNG **derived per shot** (`rng.seed = hash(match_seed, shooter_id, fire_tick, pellet_index)`) so the server and any replay produce the same ricochet. Continue the projectile from `exit_point` on penetrate/ricochet, otherwise kill it and emit an impact event for `gun-tracers-fx`.
- Penetrating a player limb (from `gun-hitzones-damage`) uses the same one-wall budget with a pen factor of 0.5.

## Acceptance
- GUT file `tests/shared/test_penetration.gd` (seeded RNG so the 30 % roll is deterministic):
  - `test_concrete_always_stops()` — full-energy 7.62×51 at 90° into `concrete` → `"stop"` regardless of the RNG seed.
  - `test_wood_penetrates_with_energy_loss()` — full-energy 5.56 into 0.1 m `wood` → `"penetrate"` with `new_energy` between 50 % and 60 % of the original.
  - `test_one_wall_max()` — a projectile with `penetrations_used = 1` into `wood` → `"stop"`.
  - `test_ricochet_at_10_degrees()` — `brick`, incidence 10°, seed chosen so the roll passes → `"ricochet"`, the reflected direction's dot with the normal is positive, and `new_energy` is 40 % ±1 % of the original.
  - `test_no_ricochet_at_30_degrees()` — `brick`, incidence 30°, any seed → never `"ricochet"`.
  - `test_low_energy_stops()` — `energy_fraction = 0.1` into `wood` → `"stop"`.
- Manual: shoot through a stilt-house wall and hit a bot behind it; shoot a concrete wall at a glancing angle and see sparks skip along it.

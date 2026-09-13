# MEDIUM — Vehicle catalog: sedan, pickup, scooter, sidecar, Lambro, tractor

**Category:** veh
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M7
**Depends on:** veh-base-vehiclebody, world-kits-import

## Files
- `data/vehicles.json` (modify)
- `world/vehicles/sedan.tscn` (new)
- `world/vehicles/pickup.tscn` (new)
- `world/vehicles/scooter.tscn` (new)
- `world/vehicles/sidecar_bike.tscn` (new)
- `world/vehicles/lambro.tscn` (new)
- `world/vehicles/tractor.tscn` (new)
- `server/world/vehicle_spawner.gd` (new)
- `tests/test_vehicle_catalog.gd` (new)

## Issue
`vehicle_base.gd` exists but nothing instances it. The plan's six civilian vehicles each have distinct handling and seat layouts (sedan 4 seats / 90 km/h, pickup 2 cab + 3 exposed bed, scooter 1 + pillion / 55 km/h / quiet, motorcycle + sidecar 3 seats with a firing gunner, Lambro three-wheeler 1 + 4 cargo slow and tanky, tractor very slow with high HP and offroad grip) and none of them exist as scenes or data. Vehicles also need to be placed deterministically from the match seed so loot layout and replays stay reproducible.

## Fix
- Fill `data/vehicles.json` with six records using the `vehicle_base.gd` schema. Target values: sedan `max_speed_kmh 90, hp 900, seats 4 (1 driver + 3 passenger, none exposed), offroad_grip 0.5`; pickup `85, hp 1000, 2 cab + 3 bed exposed, offroad_grip 0.7`; scooter `55, hp 300, driver + pillion exposed, quiet true, engine_db low`; sidecar_bike `70, hp 450, driver + pillion + sidecar gunner (exposed, type "gunner")`; lambro `45, hp 1400, driver + 4 cargo exposed, offroad_grip 0.5`; tractor `28, hp 2000, driver only, offroad_grip 1.0`.
- One scene per vehicle: `Vehicle` root with `vehicle_id` set, mesh from the imported CC0 kit (Kenney *Car Kit* for sedan/pickup/tractor, Quaternius *Ultimate Vehicles* for scooter/motorcycle), a `CollisionShape3D` convex hull, four (three for Lambro, two for bikes) `VehicleWheel3D` nodes with `use_as_traction`/`use_as_steering` set per layout, and `Marker3D` seat + exit markers named to match the JSON `marker` keys.
- Tire hurtboxes: one `Area3D` per wheel in the `hitbox` layer named `tire_0..n`, routed to `Vehicle.apply_damage(amount, name)`.
- Gunner seats: the sidecar seat marker parents a `Node3D` aim pivot clamped to ±120° yaw relative to the bike, so the gunner fires the weapon they already hold through the normal `gun-weapon-base` path — no vehicle-specific weapon.
- `server/world/vehicle_spawner.gd`: server-only. Reads `Marker3D`s in group `"vehicle_spawn"` placed by the world tasks, each with metadata `tiers` (e.g. `["sedan","scooter"]`). Uses the match-seed RNG (`polish` determinism rule) so a given seed always produces the same layout. Spawns ~35 vehicles, weighted towards roads for sedan/Lambro and hamlets for scooter/tractor. Spawned via `MultiplayerSpawner`.
- Start fuel is randomised 25–100 from the same seeded RNG.
- All six get added to group `"vehicles"` by `vehicle_base.gd` — no per-scene code.

## Acceptance
- GUT test `tests/test_vehicle_catalog.gd`:
  - `test_all_six_present`: `data/vehicles.json` contains exactly the ids `sedan, pickup, scooter, sidecar_bike, lambro, tractor`.
  - `test_scene_matches_data`: for each id, loading `world/vehicles/<id>.tscn` yields a node whose seat markers count equals `seats.size()` in JSON.
  - `test_seed_determinism`: `VehicleSpawner.plan_spawns(seed=1234)` called twice returns identical id/position arrays; with `seed=9999` at least one differs.
- In editor: run the test map, drive each vehicle — sedan tops out near 90 km/h, tractor near 28 km/h, scooter engine loop is audibly quieter, sidecar gunner can fire while the bike moves.

# LOW — Sampan canal boat (stretch)

**Category:** veh
**Priority:** LOW
**Status:** TODO
**Milestone:** M7
**Depends on:** veh-base-vehiclebody, veh-net-sync, world-rivers-bridge-tunnels

## Files
- `shared/vehicles/boat_base.gd` (new)
- `world/vehicles/sampan.tscn` (new)
- `data/vehicles.json` (modify)
- `tests/test_boat_base.gd` (new)

## Issue
The river and canal network from `world-rivers-bridge-tunnels` is currently a movement penalty only — swimming is slow and forces holstering, so water is pure denial with no counterplay. A sampan (4 seats, canals and river) is the plan's suggested stretch vehicle and gives the waterways a fast, quiet flank route. It is explicitly optional: ship it only after the six-vehicle catalog works.

## Fix
- `shared/vehicles/boat_base.gd`: `class_name Boat extends RigidBody3D` (not `VehicleBody3D` — no wheels). Reads the same `data/vehicles.json` record shape as `Vehicle` so the store, spawner and audio treat it identically; add keys `buoyancy_points` (array of marker names) and `water_drag`.
- Buoyancy: for each `Marker3D` in `buoyancy_points`, if the marker's global Y is below the water surface Y (queried from the `Area3D` water volume it overlaps), apply an upward force proportional to submerged depth × `buoyancy_force`, plus `water_drag` on linear and angular velocity. Four points give pitch/roll for free. Server-only, as with all vehicle physics.
- Throttle/steer: driver input `input_vector.y` → forward force at the stern marker, `input_vector.x` → yaw torque scaled down with speed. Max speed 30 km/h; `quiet: true`, `engine_db` low — the long-tail motor is audible at 120 m rather than the 250 m of a car.
- Out of water (all buoyancy points above the surface): kill the throttle and let it beach — no land driving.
- Seats: 1 driver at the stern + 3 passengers, all `exposed: true`, so occupants can shoot; reuse `Vehicle`'s seat enter/exit API verbatim by sharing a `seat_manager.gd` helper rather than duplicating it.
- Damage and sinking: `apply_damage` shares the base API; at `hp <= 0` the boat scuttles — disable buoyancy, sink over 3 s, occupants are force-exited into swim state (`move-swim`).
- Spawn: add `tiers: ["sampan"]` markers along the canal and river banks in the world scene, picked up by the existing `vehicle_spawner.gd` with no spawner changes.
- Replication reuses `veh-net-sync` unchanged — a boat is in group `"vehicles"` and its transform rides the same snapshot section.

## Acceptance
- GUT test `tests/test_boat_base.gd`:
  - `test_buoyancy_rises`: a boat spawned 1 m under the water plane has net upward force > 0 and settles within ±0.1 m of the surface after 2 s of simulated steps.
  - `test_no_throttle_on_land`: with every buoyancy point above the water Y, full throttle produces zero forward force.
  - `test_sink_ejects`: `apply_damage(hp)` force-exits all occupants into swim state.
- Manual: drive the sampan down a canal under the bridge — passengers can fire, the motor is audible at ~120 m but not at 250 m, beaching stops it.

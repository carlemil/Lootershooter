# MEDIUM — Base vehicle: seats, fuel, damage, tires

**Category:** veh
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M7
**Depends on:** net-player-spawn, move-controller-base, gun-hitzones-damage

## Files
- `shared/vehicles/vehicle_base.gd` (new)
- `shared/vehicles/vehicle_base.tscn` (new)
- `shared/vehicles/seat.gd` (new)
- `data/vehicles.json` (new)
- `tests/test_vehicle_base.gd` (new)

## Issue
There is no vehicle at all: a 2 km × 2 km map with a 15-minute match and a zone shrinking from 1200 m to 40 m is not crossable on foot. We need one arcade `VehicleBody3D` base that every catalog entry (sedan 90 km/h down to tractor) configures from `data/vehicles.json`, with seats, fuel 0–100, shootable tires and hookable engine audio at 250 m. Physics must be server-owned so the same server-authoritative rule that covers players covers vehicles.

## Fix
- `shared/vehicles/vehicle_base.gd`: `class_name Vehicle extends VehicleBody3D`. Exported `vehicle_id: String`; on `_ready()` load its record from `DataLoader.vehicles[vehicle_id]` (autoload from `infra-data-loader`).
- JSON keys per vehicle: `id`, `display_name`, `mass_kg`, `max_speed_kmh`, `engine_force`, `brake_force`, `steer_max_deg`, `steer_speed`, `hp`, `fuel_capacity`, `fuel_burn_per_km`, `seats` (array of `{name, type: "driver"|"passenger"|"gunner", exposed: bool, marker: String}`), `tire_hp`, `offroad_grip`, `engine_db`, `quiet` (bool), `model_path`.
- Driving in `_physics_process` on the server only (`multiplayer.is_server()`): map the driver's input struct — `input_vector.y` → `engine_force`, `input_vector.x` → `steering` lerped at `steer_speed`, `buttons & Buttons.JUMP` → handbrake. Clamp speed to `max_speed_kmh / 3.6`. Never read raw client physics state.
- Fuel: `fuel: float` 0–100, drained by `fuel_burn_per_km * distance_this_tick`; at 0 engine_force is forced to 0. `refuel(amount)` server-only (fuel can from the store).
- Seats: `Marker3D` children named per the JSON `marker`. `request_enter(peer_id, seat_index)` / `request_exit(peer_id)` are server-side functions called from the player's interact action; on enter, reparent/hide the player body, set `PlayerState.vehicle = self` and `seat_index`; on exit place the player at the seat's exit marker with a clear-space check. Exposed seats keep the player's hurtboxes active and let them fire; `driver` seats holster.
- Damage: `apply_damage(amount, hit_part)` server-only. `hit_part == "tire_<n>"` decrements that wheel's `tire_hp`; a popped tire sets its `VehicleWheel3D` friction slip high and caps speed to 40% and pulls steering to that side. `hp <= 0` → `exploded` signal, 300 damage in a 5 m radius, occupants killed, wreck left behind.
- Signals: `engine_started`, `engine_stopped`, `tire_popped(index)`, `exploded`, `seat_changed(seat_index, peer_id)`. Client audio (`audio-footsteps-surfaces-vehicles-ambience`) subscribes; nothing audio-related lives in this script.
- Register every vehicle in group `"vehicles"` so bot hearing (`bot-perception`, 250 m) and the minimap can query them.
- Collisions: vehicle vs player above 25 km/h deals `speed_kmh * 1.5` damage to the player, server-side.

## Acceptance
- GUT test `tests/test_vehicle_base.gd`:
  - `test_fuel_drain`: a vehicle with `fuel_burn_per_km = 5.0` driven 2 km of simulated distance ends at `fuel == 90.0`.
  - `test_empty_tank_kills_throttle`: with `fuel = 0.0`, applying full throttle leaves `engine_force == 0.0`.
  - `test_popped_tire_caps_speed`: `apply_damage(tire_hp, "tire_0")` emits `tire_popped(0)` and `max_speed_effective()` is 40% of `max_speed_kmh`.
  - `test_seat_occupancy`: `request_enter(1, 0)` then `request_enter(2, 0)` returns false for the second call; `request_exit(1)` frees the seat.
- Run `godot --headless -s addons/gut/gut_cmdln.gd -gexit` — all green.

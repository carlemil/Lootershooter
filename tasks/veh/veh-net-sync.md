# MEDIUM — Server-owned vehicle physics and occupant sync

**Category:** veh
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M7
**Depends on:** veh-base-vehiclebody, net-snapshot-sync, net-prediction-reconcile

## Files
- `server/net/vehicle_replication.gd` (new)
- `client/net/vehicle_interpolator.gd` (new)
- `shared/vehicles/vehicle_base.gd` (modify)
- `shared/net/messages.gd` (modify)
- `tests/test_vehicle_net.gd` (new)

## Issue
`vehicle_base.gd` simulates on the server but clients see nothing: a driven car is invisible or frozen for everyone else. With 20 players at a 30 Hz server tick and 20 Hz snapshots, vehicle transforms must ride the existing snapshot path, not a second ad-hoc channel, and the driver needs enough local smoothing that steering does not feel like 150 ms of lag while the server stays authoritative.

## Fix
- Add a `vehicles` section to the snapshot in `shared/net/messages.gd`: per active vehicle `{id: int, pos: Vector3, basis_quat: Quaternion, lin_vel: Vector3, steer: float, rpm_norm: float, fuel_q: int (0-100 byte), tire_flags: int (bitmask), occupants: PackedInt32Array}`. Only vehicles with a non-zero velocity or an occupant change are included in a snapshot; parked ones are sent once and on change.
- `server/net/vehicle_replication.gd`: collects group `"vehicles"` each snapshot tick, applies distance-based visibility (skip vehicles > 400 m from a given peer unless that peer is an occupant), and hands the section to the existing snapshot writer.
- `client/net/vehicle_interpolator.gd`: attached to each replicated vehicle on the client. Buffers the last 3 snapshots and renders at `now - interpolation_delay` (reuse the player interpolation delay constant). Non-driver clients never run `VehicleBody3D` physics — set `freeze = true` on the client and drive the transform from the buffer.
- Driver-side smoothing: the local driver predicts only the visual transform — apply the last authoritative transform then extrapolate by `lin_vel * time_since_snapshot`, and blend towards the next authoritative transform over 100 ms. No client physics stepping, no reconciliation replay (vehicle physics is not deterministic enough); a hard divergence > 2 m snaps.
- Occupants: when `occupants` changes, the client reparents the passenger models to the seat markers and switches the local player's camera to the seat view. The `seat_changed` signal fires client-side from the interpolator so HUD/audio can react.
- Enter/exit stays a server RPC: client calls `rpc_id(1, "request_enter", vehicle_id, seat_index)`, server validates distance ≤ 3 m to the seat marker, seat empty, and player not already seated, then broadcasts. Rate-limit the request to 5/s per peer (feeds `polish-anticheat-sanity`).
- Lag compensation: push each vehicle's transform into the existing 200 ms history ring from `net-lagcomp-history` so shots at a moving car and its tires rewind like player hitboxes.

## Acceptance
- GUT test `tests/test_vehicle_net.gd`:
  - `test_snapshot_roundtrip`: encoding then decoding a vehicle section preserves position within 0.01 m and the tire bitmask exactly.
  - `test_parked_vehicles_omitted`: a vehicle with zero velocity and unchanged occupants is absent from the second consecutive snapshot.
  - `test_enter_rejected_when_far`: `request_enter` from a peer 10 m away returns false and does not change occupancy.
  - `test_visibility_cull`: a vehicle 500 m from a peer is excluded, the same vehicle is included when that peer is an occupant.
- Manual: two clients + one server locally with 150 ms simulated latency — the passenger sees the car move smoothly with no visible rubber-banding; shooting a moving car's tire at range registers.

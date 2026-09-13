# MEDIUM — Smuggler truck road event worth $2500

**Category:** zone
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M5
**Depends on:** zone-match-loop, econ-kill-drop, world-terrain-blockout

## Files
- `server/match/smuggler_truck.gd` (new)
- `world/events/smuggler_truck.tscn` (new)
- `data/zone.json` (modify)
- `tests/test_smuggler_truck.gd` (new)

## Issue
The plan replaces the usual airdrop with a ground event: a civilian truck spawns on a road mid-match carrying $2500, drives a fixed route, and can be hijacked (driven off and looted) or simply destroyed for the cash. Nothing generates a mid-match contested objective on the roads, so the road network built by `world-terrain-blockout` gets no gameplay use.

## Fix
- Add to `data/zone.json`: `"smuggler": {"spawn_time_s": 420, "cash": 2500, "speed_kmh": 40, "hp": 1200, "announce_radius_m": 400}`.
- `server/match/smuggler_truck.gd` (server only): at t = 7:00, pick a road `Path3D` from the `roads` group whose end point lies inside the current safe circle, using the match RNG (deterministic). Spawn `smuggler_truck.tscn` as a `PathFollow3D`-driven body at the path start.
- The truck drives the spline at 40 km/h, ignoring players, until it reaches the path end, where it despawns after 30 s if never engaged. Announce it on every minimap at spawn with a distinct icon and a kill-feed line ("Smuggler truck spotted").
- Two ways to take it, both ending in cash on the ground rather than instantly in a wallet:
  - **Destroy**: the truck has 1200 HP and takes damage from bullets/launchers; at 0 it explodes (damaging anyone within 6 m) and drops a `cash_bag` (reuse `shared/loot/cash_bag.gd`) with the full $2500 and the standard 90 s decay.
  - **Hijack**: a player interacting at the driver door while the truck is stopped or under 15 km/h takes control (it becomes a normal drivable vehicle once `veh-base-vehiclebody` exists; until then, interacting stops it and drops the bag). Any occupant leaving with the truck keeps the cash attached to the vehicle until it is destroyed or the cargo is looted from the bed (5 s channel, same rules as a safe).
- Engine noise is loud — reuse the noise event bus with `"vehicle"` at 250 m so bots and players hear it coming.
- Only one truck per match; if the chosen road has no point inside the safe circle at 7:00, fall back to the road nearest the circle center.

## Acceptance
- GUT test `tests/test_smuggler_truck.gd` with a synthetic `Path3D`:
  - Spawns exactly once at t≈420 s; a second call at t=600 spawns nothing.
  - Same seed picks the same road twice; a different seed may differ.
  - Applying 1200 damage destroys it and creates exactly one cash bag with `amount == 2500` and `lifetime == 90`.
  - Reaching the path end without being engaged despawns it 30 s later, leaving no bag.
- In a local session: the truck icon appears on the minimap at 7:00, the truck follows the road spline at a steady speed, and destroying it leaves a lootable $2500 bag.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

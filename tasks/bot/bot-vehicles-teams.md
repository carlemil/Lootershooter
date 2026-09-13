# MEDIUM — Bot driving, squad follow and revives

**Category:** bot
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-navigation, veh-catalog, veh-net-sync, zone-teams-dbno, world-navmesh-bake

## Files
- `server/bots/bot_driver.gd` (new)
- `server/bots/bot_squad.gd` (new)
- `server/bots/actions/drive.gd` (modify)
- `server/bots/actions/revive_teammate.gd` (modify)
- `tests/test_bot_driver.gd` (new)

## Issue
Bots walk everywhere on a 2 km map while the zone shrinks from 1200 m to 40 m in 15 minutes, so they arrive late or die outside; the vehicles from M7 sit unused. In team modes bots also ignore each other — they do not cluster, do not share a drop point, and leave knocked teammates to bleed out, which makes duo/squad matches feel like five solo bots wearing the same colour.

## Fix
- `server/bots/bot_driver.gd`: drives through `BotAgent` inputs only. Follows the road spline graph from `world-navmesh-bake` (`RoadGraph.find_route(from, to) -> Array[Vector3]`), not the pedestrian navmesh. Pure-pursuit steering: pick the lookahead point at `clamp(speed_ms * 1.2, 8, 30)` m along the route, steer toward it (`input_vector.x`), throttle to a target speed of `min(vehicle_max, 60 km/h)` reduced to 30 km/h on corners sharper than 25° and 20 km/h offroad.
- Obstacle handling: a forward `shapecast` 15 m ahead; on a hit, brake and, if blocked for 2 s, reverse for 1 s then re-route. Stuck twice in 10 s → exit the vehicle and walk (the brain will rescore).
- `drive.gd`: enter the nearest vehicle within 60 m with a free driver seat (via the normal server `request_enter` path, distance ≤ 3 m), drive to a point within 80 m of the destination, then exit and walk. Abandon driving if the destination is within 150 m, if fuel hits 0, or if two tires are popped. Passengers: a squad-follower bot whose squad leader is driving takes a passenger seat instead of a second vehicle.
- Threat response while driving: at `< 25 %` vehicle HP or when taking fire from a known enemy, stop and bail out on the side away from the threat.
- `server/bots/bot_squad.gd`: per-squad coordinator (one instance per bot squad, not per bot). Holds `leader_peer`, a shared `objective` (zone point / hot zone / loot cluster) and a contact board — enemy sightings shared between squad members with a 1.5 s "callout" delay so squads are not a hive mind.
- Squad follow: non-leader bots keep a slot offset (a ring of 8–15 m around the leader, per-member fixed angle), and their `move_to_zone`/`loot` scores get a penalty proportional to `distance_to_leader / 60` so they regroup. `squad_follower` profile weights this hardest. Drop picks (from `zone-drop-in`) use the leader's chosen spot, teammates clustered within the 150 m the plan allows.
- `revive_teammate.gd`: path to the DBNO teammate, throw smoke if a known enemy is within 60 m, hold the revive interact for the full duration, abort if health drops below 30% or an enemy closes within 15 m. Score already set at 0.95 in the brain; this task fills `tick()`.
- Focus fire: when the contact board holds an enemy that two squad members can see, apply a ×1.25 `engage` score so squads commit together instead of trickling in.

## Acceptance
- GUT test `tests/test_bot_driver.gd`:
  - `test_pure_pursuit_steering`: a lookahead point 20 m ahead and 5 m to the right produces a positive `input_vector.x` under 1.0; dead ahead produces ≈ 0.
  - `test_corner_slowdown`: a route with a 40° bend caps the throttle target at 30 km/h.
  - `test_bail_on_low_hp`: vehicle HP at 20% triggers an exit request within 1 s.
  - `test_squad_regroup`: a follower 90 m from its leader scores `move_to_zone` lower than the same bot 10 m away (the follow penalty applies).
  - `test_callout_delay`: an enemy seen by one member is absent from a teammate's known list for 1.5 s, then present.
- Manual: a squad of 4 bots drives one pickup to the zone, dismounts together, and one revives a knocked member under smoke.

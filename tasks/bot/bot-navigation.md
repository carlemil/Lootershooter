# HIGH — Navmesh movement, nav links and cover points

**Category:** bot
**Priority:** HIGH
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-input-adapter, bot-utility-brain, world-navmesh-bake

## Files
- `server/bots/bot_navigator.gd` (new)
- `server/bots/cover_points.gd` (new)
- `server/bots/actions/move_to_zone.gd` (modify)
- `server/bots/actions/flank.gd` (modify)
- `server/bots/actions/camp.gd` (modify)
- `tests/test_bot_navigation.gd` (new)

## Issue
The brain picks destinations but nothing turns a destination into per-tick `input_vector` and `look` values, so bots cannot cross the 2 km map, use the vault/ladder/tunnel `NavigationLink3D`s baked by `world-navmesh-bake`, or take cover during `flank`/`camp`. Pathing must also be cheap: up to 20 bots repathing inside a 33 ms server tick budget.

## Fix
- `server/bots/bot_navigator.gd`: wraps a `NavigationAgent3D` per bot. `set_destination(pos)`, `stop()`, `is_arrived()`, `distance_remaining()`. Repath at most every 0.5 s, or immediately when the destination moves more than 5 m; use `NavigationServer3D.map_get_path` async via the agent's own callbacks, never a synchronous full-map query per tick.
- Per tick, convert `get_next_path_position()` into inputs: desired direction in the bot's local frame → `set_move(Vector2(local.x, -local.z).normalized())`; travel `look` yaw follows the path direction, smoothed, but is overridden by `bot-combat` whenever a target is being aimed at (combat owns `look`, navigation owns `move`, and the navigator must not fight it — expose `travel_look_yaw()` and let the agent decide).
- Gait: `press(SPRINT)` when `distance_remaining() > 25 m`, stamina > 35 and no enemy visible; release below stamina 15 so bots obey the same 100-point pool and −10/s sprint drain as humans. Crouch when `camp` or when an enemy is known within 60 m.
- Nav links: when `get_current_navigation_path_index()` enters a link owned by a node in group `"nav_link_vault"` / `"nav_link_ladder"` / `"nav_link_tunnel"`, run the matching traversal — vault taps `JUMP` at the link entry; ladder holds forward with `look` pitched up until the exit marker; tunnel just walks but sets a flag so the bot does not try to shoot through geometry. Timeout each traversal at 6 s and repath on failure.
- Stuck detection: if the bot moved < 1 m in 2 s while `move` is non-zero, nudge — pick a random 90° sidestep for 0.6 s, then repath; after three failures, teleport-free fallback is to mark the destination unreachable for 20 s and let the brain rescore.
- `server/bots/cover_points.gd`: server-only. At match start, sample cover candidates from static geometry near the navmesh — for each of a grid of navmesh points (every 8 m in built-up areas, from `Marker3D`s in group `"cover"` where the world tasks placed them), store `{position, normal}`. Query API `best_cover(from_pos, threat_pos, max_dist) -> Vector3` scores candidates by: within `max_dist`, occluded from `threat_pos` (one raycast), and not increasing distance to the bot's current objective. Cache the grid; do at most 12 raycasts per query.
- `flank.gd` uses `best_cover` plus a path that keeps the last-known enemy position out of line-of-sight, aiming to arrive within 40 m off the enemy's flank (±60–120° from their facing). `camp.gd` picks cover with sightlines onto the nearest loot cluster or zone approach and holds. `move_to_zone.gd` targets a point at `zone_radius * 0.6` from the wandering centre, not the exact centre, so bots do not funnel into one spot.
- Perf guard: cap global repaths to 8 per tick with a round-robin queue; bots that miss their slot keep following the existing path.

## Acceptance
- GUT test `tests/test_bot_navigation.gd`:
  - `test_path_to_input`: with a path node 10 m directly ahead, the emitted `input_vector` is within 0.05 of `(0, 1)`; 10 m to the bot's right gives ≈ `(1, 0)`.
  - `test_sprint_gate`: distance 100 m and stamina 80 presses SPRINT; stamina 10 releases it.
  - `test_stuck_recovery`: a bot blocked by a collider for 2 s emits a sidestep input and requests a repath.
  - `test_cover_occluded`: `best_cover` never returns a point with clear line of sight to the threat when an occluded candidate exists within range.
  - `test_repath_budget`: 20 bots all requesting a repath in one tick issue at most 8 `NavigationServer3D` path requests.
- Manual (headless with `bot_debug`): a bot spawned at a map corner reaches the zone centre, using at least one vault and one ladder link on the way, without getting stuck.

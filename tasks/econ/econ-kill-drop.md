# MEDIUM — Kill drops a cash bag with $300 bounty, 90 s decay

**Category:** econ
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-cash-state, gun-hitzones-damage

## Files
- `shared/loot/cash_bag.tscn` (new)
- `shared/loot/cash_bag.gd` (new)
- `server/economy/kill_drop.gd` (new)
- `tests/test_kill_drop.gd` (new)

## Issue
Killing a player currently yields nothing, so there is no incentive to fight and no way for a poor player to catch up. The design says a death drops a bag holding all of the victim's unspent cash plus a flat $300 bounty, the bag lasts 90 s and then vanishes, and a knocked (DBNO) player drops nothing until they are finished.

## Fix
- `server/economy/kill_drop.gd` (server only): listens for the `player_died(victim_peer, killer_peer)` signal from the damage system. Ignores `player_knocked` entirely — DBNO drops nothing.
- On death: `var amount := CashService.get_stats(victim_peer).cash + BOUNTY` with `const BOUNTY := 300`; `CashService.charge(victim_peer, cash, "death")` to zero the victim (the bounty is minted, not taken from anyone), then spawn `cash_bag.tscn` at the corpse position raised 0.3 m and dropped to the nearest navmesh/ground point so it never spawns inside geometry.
- `shared/loot/cash_bag.gd`: `Area3D`, `@export var amount: int`, `@export var lifetime := 90.0`. Counts down on the server; `queue_free()` at 0. Replicate `time_left` at low rate so the client can fade/flash the bag in its last 15 s.
- Pickup is instant on interact, server-validated (within 2.5 m, alive, bag not already taken) → `CashService.grant(peer_id, amount, "bag")`. Teammates and enemies may both take it; no ownership lock.
- Fire a `kill_feed` entry carrying the bag amount so `ui-hud` can show "+$N" and a world marker visible to the killer's team for 10 s.
- A player who dies while outside the zone or to the zone (`killer_peer == 0`) still drops a bag with the bounty — the bounty is for the corpse, not the killer.
- Bag pickup is also how bots get rich; no separate bot path (bots use the same interact input).

## Acceptance
- GUT test `tests/test_kill_drop.gd`:
  - Victim with $1200 dies → bag `amount == 1500`, victim's cash is 0.
  - Victim with $0 dies → bag `amount == 300`.
  - A `player_knocked` signal spawns no bag; the following `player_died` spawns exactly one.
  - Advancing 90.1 s frees the bag; picking it up at 89 s grants the full amount and frees it.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

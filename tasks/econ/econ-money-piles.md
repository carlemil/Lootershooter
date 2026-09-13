# HIGH — Money piles spawned from tiered building markers

**Category:** econ
**Priority:** HIGH
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-cash-state, infra-data-loader, net-player-spawn

## Files
- `shared/loot/loot_tiers.gd` (new)
- `server/economy/money_spawner.gd` (new)
- `shared/loot/money_pile.tscn` (new)
- `shared/loot/money_pile.gd` (new)
- `data/loot_tiers.json` (new)
- `tests/test_money_spawner.gd` (new)

## Issue
Money is the only loot in the game, but nothing places it in the world. The design calls for ~300 piles per match drawn from `Marker3D` groups placed by the world tasks, with tier values hamlet house $50–150, town building $100–300, outpost $200–500, and ~40% of the total world value concentrated in the town and outposts. The layout must be identical on server and any replay, so it has to come from the seeded match RNG, not `randf()`.

## Fix
- `data/loot_tiers.json`: one object per tier keyed by the marker group name — `{"loot_hamlet": {"min": 50, "max": 150, "weight": 1.0}, "loot_town": {"min": 100, "max": 300, "weight": 2.0}, "loot_outpost": {"min": 200, "max": 500, "weight": 2.5}}`. No amounts in scripts; loaded through the `infra-data-loader` autoload.
- `shared/loot/loot_tiers.gd`: thin accessor over the loaded JSON — `tier_names()`, `roll(tier, rng) -> int` using `rng.randi_range(min, max)`.
- `server/economy/money_spawner.gd` (server only): `populate(root: Node3D, seed: int, target_count := 300)`.
  - Collect markers per tier with `get_tree().get_nodes_in_group(tier_name)`.
  - Seed a `RandomNumberGenerator` with the match seed; sort each marker array by node path before use so iteration order is deterministic regardless of scene-tree traversal.
  - Pick `target_count` markers by tier weight (weighted sample without replacement — one pile per marker max), roll a value per pile, spawn `money_pile.tscn` at the marker's global transform.
  - Log the summed value per tier and assert town + outpost ≥ 38% and ≤ 45% of total; if the world's marker mix cannot hit it, push-warning with the actual split so the world tasks can add markers.
- `shared/loot/money_pile.gd`: `Area3D` with `@export var amount: int`, an interact prompt ("Take $N", hold not required), and a `pick_up(peer_id)` that runs **server-side only**, calls `CashService.grant(peer_id, amount, "pile")`, then `queue_free()`. Guard against double pickup with an `_taken` bool.
- Replicate piles with a `MultiplayerSpawner` under the world root with distance visibility (the plan's interest-management rule); the client instantiates the same scene for visuals and sends only `request_pickup(pile_path)`.
- Server validates the pickup: pile still exists, not taken, and the requesting player is within 2.5 m of it.

## Acceptance
- GUT test `tests/test_money_spawner.gd` using a synthetic scene of `Marker3D`s (20 `loot_hamlet`, 20 `loot_town`, 10 `loot_outpost`):
  - `populate(root, 12345, 40)` spawns exactly 40 piles, no marker used twice.
  - Two runs with seed 12345 produce the same ordered list of `(marker_path, amount)`; seed 99999 produces a different one.
  - Every hamlet pile amount is within 50–150 inclusive, every outpost pile within 200–500.
  - `pick_up` grants the exact amount once; a second call grants nothing.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

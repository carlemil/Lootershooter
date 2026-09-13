# MEDIUM — Bot looting routes and wrist-store purchases by profile

**Category:** bot
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-utility-brain, bot-navigation, econ-money-piles, econ-store-catalog, econ-inventory

## Files
- `server/bots/bot_economy.gd` (new)
- `server/bots/actions/loot.gd` (modify)
- `server/bots/actions/buy.gd` (modify)
- `data/bots.json` (modify)
- `tests/test_bot_economy.gd` (new)

## Issue
Cash is the only loot and the store is the whole game loop, so a bot that does not loot or buy stays on its $800 starting cash with the default loadout and stops being a credible opponent after the first two minutes. The `loot` and `buy` actions currently score but do nothing. Bots also need to crack safes, pick up kill-drop bags ($300 bounty plus the victim's cash, decaying in 90 s), and spend in a profile-flavoured order.

## Fix
- `server/bots/bot_economy.gd`: per-bot component with a loot memory and a shopping list.
- Looting: maintain `loot_targets` — money pile / cash bag / safe nodes within 150 m, from the server's loot registry (never a scene-wide scan per tick; subscribe to the spawner's signals and keep a local list). Score each by `value_estimate / (path_distance + 20)` with a ×1.5 bias for the building-tier priors in `data/bots_learned.json` (see `bot-learned-sampling`) and ×2.0 for kill bags whose 90 s decay leaves > 25 s.
- `loot.gd` `tick()`: navigate to the chosen target via `BotNavigator`, then hold the interact button for the pickup duration. Safes take 5 s and are loud — only crack one when no enemy has been known within 120 m for 8 s, and abort (release interact) if perception promotes an enemy mid-crack.
- Building sweep: inside a building, walk the `Marker3D` loot points of that building in nearest-first order rather than pathing to each from outside, with a 25 s per-building cap so bots do not vacuum a hamlet while the zone closes.
- Buying: `buy.gd` opens the wrist store through the same input button as a human, respects the 1.5 s raise time, and issues purchase requests through the server-side purchase validation from `econ-store-catalog` (no direct inventory writes). While the store is up the bot keeps walking but does not fire — same rule as a player.
- Shopping list order per profile, stored in `data/bots.json` under `profiles.<name>.buy_priority` as an ordered array of item category names, e.g. rusher `["assault_rifle","armor","healing","throwable","ammo","attachment"]`, camper `["sniper","armor","healing","gadget","ammo"]`, looter `["backpack","carbine","healing","armor","ammo"]`, opportunist `["smg","healing","throwable","armor"]`, squad_follower `["carbine","healing","armor","ammo"]`.
- Purchase rule: walk the priority list, buy the most expensive affordable item in the first category where the bot has a gap, but always keep a reserve — `reserve = 300` for rusher, `800` for camper/looter — so bots are not perpetually broke. Always top up ammo for held weapons before buying a new gun. Refuse anything that fails the inventory fits-check (the server will refuse anyway; don't spam requests).
- Rich-bounty awareness: a bot carrying > $3000 gets its `buy` score boosted 1.5× (it knows it is marked), matching the economy pressure the marker is meant to create.
- Emit a `bot_purchase` telemetry line for `bot-learning-recorder` on every successful buy.

## Acceptance
- GUT test `tests/test_bot_economy.gd`:
  - `test_loot_priority`: given a $150 pile 40 m away and a $1200 kill bag 80 m away with 60 s left, the bag is chosen.
  - `test_safe_aborts_on_contact`: an enemy promoted to known during a safe crack releases interact before the 5 s completes.
  - `test_buy_respects_reserve`: a camper with $1000 and an empty rifle slot does not buy a $900 sniper (reserve 800); with $1800 it does.
  - `test_buy_order_by_profile`: with $2500 and an empty loadout, rusher buys an assault rifle first, camper buys a sniper first.
  - `test_no_direct_inventory_write`: a purchase that fails server validation leaves the bot's inventory unchanged.
- Run `godot --headless -s addons/gut/gut_cmdln.gd -gexit` — all green.

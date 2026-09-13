# HIGH — Item catalog, prices and server-side purchase validation

**Category:** econ
**Priority:** HIGH
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-cash-state, econ-inventory, infra-data-loader

## Files
- `data/items.json` (new)
- `data/prices.json` (new)
- `server/economy/store_service.gd` (new)
- `tests/test_store_service.gd` (new)

## Issue
The wrist store has nothing to sell and no rule for what a purchase costs or whether it is allowed. Prices must live in data (plan §3.3: pistols 200–300, SMGs 600–800, assault rifles 1800–2500, LMGs 3200–3800, snipers 2600–4000, launchers 2000–4500, throwables 150–400, armor 400–1200, backpacks 200–600, healing 50–600, boosters 100–300, gadgets 150–800, attachments 150–1200, ammo 20–80, vehicle items 50–100), and the server must be the only thing that decides a buy succeeds — a client that sends `buy("m60")` with $0 must be refused.

## Fix
- `data/items.json`: one entry per item id → `{"name", "kind", "category", "weight_kg", plus kind-specific keys ("cartridge" for guns, "capacity_kg" for backpacks, "tier" for armor/helmets, "heal" / "duration_s" for consumables)}`. Cover every row of plan §3.3. Weapon *stats* stay in `data/weapons.json` (M3); `items.json` carries only inventory/economy facts and the `weapon_id` link.
- `data/prices.json`: flat `{ "<item_id>": <int dollars> }`, values inside the plan's per-category bands. Kept separate from `items.json` so balance passes (`polish-playtest-balance`) touch one small file.
- `server/economy/store_service.gd` (server only, `class_name StoreService`), single entry point:
  - `@rpc("any_peer", "call_remote", "reliable") func buy(item_id: String) -> void` — the client sends nothing but the id; the peer comes from `multiplayer.get_remote_sender_id()`.
  - Validate in order and return the first failure via `purchase_result(item_id, ok, reason)` back to that peer only: `"unknown_item"` (not in items.json/prices.json), `"store_closed"` (wrist device not raised, or player dead/knocked/parachuting), `"no_cash"` (`price > balance`), then `inventory.can_fit(item_id)` → `"no_free_slot"` / `"over_capacity"`.
  - Only after all checks: `CashService.charge(peer, price, "purchase")` and `inventory.add(item_id)`. If `add` somehow fails after the charge, refund and log an error — never leave a player charged without the item.
  - Rate limit to 10 buys/second per peer; excess is dropped and counted for `polish-anticheat-sanity`.
- `price_of(item_id) -> int` and `catalog_by_category() -> Dictionary` are shared read-only helpers the client UI uses to draw cards; the client never computes affordability as anything but a grey-out hint.
- Add a loader schema test hook: every id in `prices.json` exists in `items.json` and vice versa; every gun item's `weapon_id` exists in `weapons.json`.

## Acceptance
- GUT test `tests/test_store_service.gd`:
  - Every key of `prices.json` exists in `items.json` and every key of `items.json` has a price (no orphans).
  - Player with $800 buying an M16A1 (1800–2500) is refused with `"no_cash"` and balance stays 800.
  - Player with $3000 buying an M16A1 succeeds once; balance drops by exactly `price_of("m16a1")` and the rifle is in a primary slot. A third rifle purchase fails with `"no_free_slot"` and is **not** charged.
  - Prices per category fall inside the plan's bands (assert min/max per category).
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

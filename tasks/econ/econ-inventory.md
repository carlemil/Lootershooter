# HIGH — Slot + weight inventory with backpack tiers

**Category:** econ
**Priority:** HIGH
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-cash-state, infra-data-loader

## Files
- `shared/inventory/inventory.gd` (new)
- `shared/inventory/slots.gd` (new)
- `tests/test_inventory.gd` (new)

## Issue
There is nowhere to put a purchased item. The store's whole buy flow depends on a "does it fit?" answer, and `move-stamina` needs a total carried weight. The design fixes the slot layout — primary ×2, sidearm, melee, throwables ×4, gadget ×2, armor, helmet, backpack — with loose consumables and ammo limited by the backpack tier's weight capacity.

## Fix
- `shared/inventory/slots.gd`: `enum Slot { PRIMARY_1, PRIMARY_2, SIDEARM, MELEE, THROW_1..THROW_4, GADGET_1, GADGET_2, ARMOR, HELMET, BACKPACK }` plus `const SLOT_KINDS := {...}` mapping each slot to the item `kind` string it accepts (`"primary"`, `"sidearm"`, `"melee"`, `"throwable"`, `"gadget"`, `"armor"`, `"helmet"`, `"backpack"`). Everything else (`"consumable"`, `"ammo"`, `"attachment"`) is loose cargo.
- `shared/inventory/inventory.gd`, `class_name Inventory`, a plain `RefCounted` so it is testable headless and usable identically on client and server:
  - `slots: Dictionary` (Slot → item_id or `""`), `cargo: Dictionary` (item_id → count).
  - `capacity_kg() -> float` = `BASE_CAPACITY` (no backpack) plus the equipped backpack's `capacity_kg` from `data/items.json`. Tiers per plan: Satchel / Rucksack / ALICE pack.
  - `weight_kg() -> float` sums every equipped item's `weight_kg` plus cargo `count * weight_kg`. Equipped gear counts toward the stamina weight but **not** against backpack capacity — only cargo does.
  - `can_fit(item_id) -> Dictionary` returning `{ok: bool, reason: String}` with reasons `"no_free_slot"`, `"over_capacity"`, `"unknown_item"`. This single function is the authority used by the store, pickups and bots.
  - `add(item_id) -> bool` (calls `can_fit`, then places into the first free matching slot or increments cargo), `remove(item_id) -> bool`, `equipped_in(slot)`, `to_dict()` / `from_dict()` for replication.
  - Removing a backpack while cargo exceeds the smaller capacity is refused (`"would_overflow"`); dropping a pack to swim (`move-swim`) drops its cargo with it.
- All item data (kind, weight_kg, capacity_kg, stack limits) comes from `data/items.json` via the loader — no stats in this script.
- Each `PlayerState` owns one `Inventory`; the server holds the authoritative copy, the client a mirror refreshed from `to_dict()` after every server-accepted change.

## Acceptance
- GUT test `tests/test_inventory.gd` (using a small fixture items dict injected into the loader):
  - Two primaries fit; the third returns `{ok=false, reason="no_free_slot"}`.
  - Five throwables: the fifth is refused (4 slots).
  - With no backpack, adding cargo past `BASE_CAPACITY` returns `"over_capacity"`; equipping the ALICE pack then lets it fit.
  - Unequipping a backpack that would overflow returns `false` and leaves the inventory unchanged.
  - `weight_kg()` of a known loadout equals the hand-computed sum.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

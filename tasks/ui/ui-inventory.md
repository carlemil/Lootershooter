# MEDIUM — Inventory screen: slots, weight, drag/drop, attachments

**Category:** ui
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M9
**Depends on:** econ-inventory, gun-attachments, ui-hud

## Files
- `client/ui/inventory/inventory_screen.tscn` (new)
- `client/ui/inventory/inventory_screen.gd` (new)
- `client/ui/inventory/slot_control.gd` (new)
- `client/ui/inventory/weight_bar.gd` (new)
- `tests/test_inventory_ui.gd` (new)

## Issue
`econ-inventory` holds slots (primary ×2, sidearm, melee, throwables ×4, gadget ×2, armor, helmet, backpack) plus backpack-tier capacity for consumables and ammo, with weight scaling stamina drain — but there is no way to see or rearrange any of it. Players also cannot fit or remove attachments bought from the wrist store, so scopes and suppressors are unusable.

## Fix
- `client/ui/inventory/inventory_screen.tscn`: `Tab`-toggled full screen (rebindable). Three columns — equipped slots (left, laid out as a character silhouette), backpack contents grid (centre), and the attachment panel for the currently selected weapon (right). Reuse `lootershooter_theme.tres` from `ui-hud`.
- `slot_control.gd`: one `Control` per slot handling `_get_drag_data` / `_can_drop_data` / `_drop_data`. `_can_drop_data` asks the *shared* inventory rules (`Inventory.can_place(item, slot)` from `econ-inventory`) — do not duplicate slot-type or weight logic in the UI.
- Every mutation is a request to the server: `rpc_id(1, "inventory_move", from_slot, to_slot, count)`. The UI shows an optimistic preview and reverts if the server's next inventory sync disagrees. Drops and splits (right-click to split a stack) go through the same call.
- `weight_bar.gd`: current / capacity from the backpack tier (Satchel / Rucksack / ALICE), with the stamina-drain multiplier printed next to it (e.g. "sprint drain ×1.3") so the weight/stamina link from `move-stamina` is visible rather than mysterious. Bar turns red when over capacity — the server refuses the pickup anyway.
- Item tooltips: name, weight, value, and for weapons the cartridge, RPM, muzzle velocity and fitted attachments, pulled from `data/weapons.json` / `data/items.json` via the data loader.
- Attachment panel: one socket row per weapon (`optic`, `muzzle`, `underbarrel`, `magazine`, `bayonet`), drag an attachment in or out; show the stat deltas (ADS time, recoil, sway, mag size) before committing. Fitting is a server request like any other move.
- Quick actions: double-click to equip/unequip, `Ctrl+click` to drop, number keys to swap the highlighted weapon into the primary slot. Hovering the ground-loot list (items within 3 m) allows direct drag into the inventory.
- Opening the inventory does not pause the game, does not stop movement, and holsters nothing — it is a screen overlay with a dimmed background, and the player remains vulnerable (same rule as the wrist store).
- Controller/keyboard navigation must work without a mouse (focus neighbours set on every slot) for the accessibility baseline.

## Acceptance
- GUT test `tests/test_inventory_ui.gd` (scene instanced headless with a fake inventory):
  - `test_can_drop_delegates`: dropping a rifle onto the helmet slot is rejected because `Inventory.can_place` says so — assert the UI calls the shared rule rather than deciding itself.
  - `test_optimistic_revert`: a move the server rejects returns the item to its original slot on the next sync.
  - `test_weight_bar`: 24 kg in a 20 kg ALICE pack shows over-capacity styling and the correct drain multiplier text.
  - `test_attachment_delta`: fitting a suppressor shows the expected ADS-time and loudness deltas from `data/items.json`.
- Manual: with a live server, press Tab mid-match, drag a rifle between primary slots, fit a scope, drop a grenade to the ground and pick it back up; movement still responds while the screen is open.

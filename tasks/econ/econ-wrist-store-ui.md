# HIGH — 3D wrist store with SubViewport UI and 1.5 s raise

**Category:** econ
**Priority:** HIGH
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-store-catalog, econ-inventory, move-fp-camera-arms

## Files
- `client/ui/wrist_store/wrist_device.tscn` (new)
- `client/ui/wrist_store/wrist_device.gd` (new)
- `client/ui/wrist_store/store_screen.tscn` (new)
- `client/ui/wrist_store/store_screen.gd` (new)
- `tests/test_wrist_store_state.gd` (new)

## Issue
Players can earn cash but cannot spend it. The store is a diegetic wrist device, openable anywhere: raising it takes 1.5 s, lowers the weapon, and the player can still walk while it is up. None of that exists — there is no wrist mesh, no SubViewport UI, and no client-side buy button wired to `StoreService.buy`.

## Fix
- `wrist_device.tscn`: a `Node3D` parented to the first-person arms rig (`move-fp-camera-arms`) holding the wrist mesh (kitbash from Kenney *Input Prompts*/*UI Pack* on a simple box until modelled) with a `SubViewport` (768×512, `update_mode = UPDATE_WHEN_VISIBLE`) rendered onto a `MeshInstance3D` quad via a `ViewportTexture` on an unshaded material.
- `wrist_device.gd` state machine: `LOWERED → RAISING (1.5 s) → RAISED → LOWERING (1.5 s)`. Toggle on the `store` action (default `B`). Transitions:
  - On `RAISING`, call the weapon system's `holster()` so the gun lowers; firing and ADS are blocked for the whole raised period.
  - Movement stays fully enabled (walk/run allowed; **sprint is blocked** like leaning, per plan §3.5's precedent — document that choice in a comment).
  - Sprinting, taking damage, being knocked, or the parachute state force an immediate `LOWERING`.
  - Mouse is captured for look the whole time; the SubViewport UI is driven by a virtual cursor moved with the mouse and confirmed with the fire button (no pointer release, so the player can still fight-or-flight).
- `store_screen.gd` inside the SubViewport: left column = category tabs from `StoreService.catalog_by_category()`; right = item cards (name, price, weight, kind icon from Kenney *Game Icons*). Each card shows a fit hint computed locally from the mirrored `Inventory.can_fit()` and greys out when `price > cash`, but the **button always sends `StoreService.buy(item_id)`** and the card state is refreshed only from the server's `purchase_result` / `cash_changed`.
- Show the server's rejection reason as a one-line toast ("No room in inventory", "Not enough cash") — never fabricate a client-side refusal.
- Header strip shows live cash and `weight_kg / capacity_kg`.
- Keep the state machine in a pure, node-free inner class or a plain script with injected time so it can be unit-tested headless (the visuals are not tested).

## Acceptance
- GUT test `tests/test_wrist_store_state.gd`: the raise state machine reaches `RAISED` only after 1.5 s of accumulated time; a sprint input at 1.0 s aborts back to `LOWERED`; `is_store_open()` is `true` only in `RAISED`, which is what `StoreService` checks for `"store_closed"`.
- Open `client/ui/wrist_store/wrist_device.tscn` in the editor and run the scene: the wrist mesh raises over ~1.5 s, the SubViewport UI is legible at 1080p, and the tabs list every category in `data/prices.json`.
- In a local two-instance session (`tools/run-local-server.ps1`): press `B`, buy a pistol with $800 → cash drops by the pistol price, the weapon appears in the sidearm slot, and buying an M60 shows the "Not enough cash" toast with no cash change.
- Walking works while the device is raised; the weapon is visibly lowered and cannot fire.

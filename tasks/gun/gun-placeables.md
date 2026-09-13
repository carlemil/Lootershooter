# MEDIUM — Placeables: claymore, tripwire trap, toe-popper mine

**Category:** gun
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-throwables

## Files
- `shared/weapons/placeable.gd` (new)
- `server/combat/placeable_manager.gd` (new)
- `world/components/placeable.tscn` (new)
- `data/items.json` (modify)
- `tests/server/test_placeable.gd` (new)

## Issue
The store lists M18A1 Claymores, tripwire grenade traps and toe-popper mines at $400–700, and the design leans on them for cheap area denial around tunnels and hot zones. None exist, so there is no way to hold ground while looting or to punish a predictable route.

## Fix
- Data in `data/items.json` per placeable: `"slot": "throwable"` (they occupy throwable slots), `"place_time_s"`, `"arm_time_s"`, `"trigger"` (`directional`|`tripwire`|`pressure`), `"damage"`, `"radius"`, `"arc_deg"` (claymore ≈ 60), `"range"`, `"detectable"` (bool — can it be spotted and shot), `"hp"`.
- `shared/weapons/placeable.gd`, `class_name Placeable`, static:
  - `static can_place(space_state, origin, normal, trigger) -> Dictionary` — claymores need a surface within 1.5 m ahead, tripwires need two anchor points 1–4 m apart, pressure mines need a walkable floor normal. Returns `{"ok", "position", "basis"}`.
  - `static in_trigger_volume(p: Dictionary, placeable) -> bool` — directional: inside `arc_deg` and `range` **with line of sight**; tripwire: the segment between the anchors is crossed; pressure: within 0.5 m of the mine on the ground.
- `server/combat/placeable_manager.gd` (server only, authoritative):
  - Placement consumes the inventory item after `place_time_s` (interruptible), then the device is `arming` for `arm_time_s` before it can trigger — an unarmed device never kills its owner during placement.
  - Each tick, test every armed device against every player in range (cheap: devices are few; use a squared-distance pre-filter). Owner and teammates **do** trigger their own devices — no friendly immunity; this is a Vietnam trap game — but `friendly_fire` config still gates the damage.
  - On trigger: apply damage through the same `Throwable.explode` path (directional variants restrict the arc), emit an event for FX/audio, and destroy the device.
  - Devices are damageable: `detectable` ones have `hp` and a small hitbox, so shooting a claymore destroys it (small secondary explosion for the claymore, silent removal for a tripwire).
  - Devices persist for the rest of the match or until their owner dies + 60 s, then despawn (prevents a dead player's minefield ending the match).
- Replicate as spawned entities with visibility by distance (only within ~80 m) so an enemy claymore is not revealed by the network traffic; teammates always see their squad's devices marked.

## Acceptance
- GUT file `tests/server/test_placeable.gd`:
  - `test_arming_delay()` — a claymore placed at tick 0 with `arm_time_s = 2.0` does not trigger for a player standing in its arc at tick 30, and does at tick 61.
  - `test_directional_arc()` — a player 5 m in front inside 60° triggers it; the same distance at 90° off-axis does not; directly behind does not.
  - `test_line_of_sight_required()` — a player inside the arc but behind a wall does not trigger it.
  - `test_tripwire_crossing()` — walking through the segment between the two anchors triggers; walking parallel 1 m away does not.
  - `test_shooting_destroys()` — dealing `hp` damage to a claymore removes it and no player damage is applied beyond the secondary blast radius.
- Manual: claymore a tunnel entrance, walk a bot into it, then shoot a second claymore from range and see it destroyed.

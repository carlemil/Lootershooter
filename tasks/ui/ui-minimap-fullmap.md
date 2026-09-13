# HIGH — Minimap, full map, zone wander preview, hot zones, pings, bounties

**Category:** ui
**Priority:** HIGH
**Status:** TODO
**Milestone:** M9
**Depends on:** ui-hud, zone-shrinking-circle, zone-hot-zones, econ-rich-bounty, world-terrain-blockout

## Files
- `client/ui/map/minimap.tscn` (new)
- `client/ui/map/minimap.gd` (new)
- `client/ui/map/full_map.tscn` (new)
- `client/ui/map/full_map.gd` (new)
- `client/ui/map/ping_system.gd` (new)
- `shared/net/ping_message.gd` (new)
- `tests/test_map_projection.gd` (new)

## Issue
The zone is the match: a circle shrinking continuously from 1200 m to 40 m over 15:00 whose centre *wanders* along a noise path, telegraphed 30 s ahead. Without a map the player cannot see it, cannot see the 2–3 live hot zones paying up to $8/s at centre, cannot see rich-bounty pulses, and teams have no ping system — the plan calls ping out as required for teams without voice.

## Fix
- Shared projection helper (put it in `client/ui/map/minimap.gd` as a static or a tiny `MapProjection` class both scenes use): world XZ (−1024..1024) → map UV. One implementation only; both maps and the compass import it.
- `minimap.tscn`: top-right, ~220 px round or square (setting), rendered from a pre-baked top-down map texture of the 2 km terrain (export once from the world scene; do not render a live `SubViewport` camera — that costs frame time every frame). Rotates with the player yaw by default, north-up when the setting says so; player arrow always centred. Zoom levels 150 m / 300 m / 600 m cycled with a key.
- Drawn layers, in order: terrain texture, roads, zone circle (current radius), next-zone preview circle (the wander target 30 s ahead, dashed), hot zones (pulsing filled circles, alpha ∝ current pot), teammates + their DBNO state, pings, rich-bounty markers, local player arrow.
- Zone data comes from the server's zone state in the snapshot (`center`, `radius`, `next_center`, `next_radius`, `time_to_next`) — the client must not re-derive the noise path. The Radio gadget reveals the wander direction 60 s ahead instead of 30 s: toggle that from the item's state flag, not by a separate widget.
- Rich bounty: for any player with > $3000, the server broadcasts a pulse marker every 20 s containing only a position (no identity); render it as a fading ring on both maps for ~4 s.
- `full_map.tscn`: toggled with `M`, full-screen, pannable with drag and zoomable with the wheel (0.5×–4×), same layers plus a distance ruler and a "you are here" crosshair. `Esc`/`M` closes. Opening the map does not pause or block movement input.
- `ping_system.gd` + `shared/net/ping_message.gd`: middle-mouse (rebindable) casts a ray from the camera; the hit point is sent to the server as `{pos, kind}` where kind is `GOING_THERE`, `ENEMY`, `LOOT`, `DANGER` (wheel menu on hold). Server validates a max of 4 pings per 10 s per player and rebroadcasts to the sender's team only. Pings live 12 s, render in the world as a clamped screen-edge marker and on both maps, and carry the teammate's colour.
- Full-map markers are clickable to place a ping at that world position (same rate limit).
- Colourblind mode swaps the zone/hot-zone/team palette via the settings singleton.

## Acceptance
- GUT test `tests/test_map_projection.gd`:
  - `test_projection_corners`: world `(-1024, -1024)` maps to UV `(0, 0)` and `(1024, 1024)` to `(1, 1)` within 0.001; `(0,0)` maps to `(0.5, 0.5)`.
  - `test_rotation`: with player yaw 90°, a point due world-north renders to the left of the rotating minimap's centre.
  - `test_ping_rate_limit`: five ping requests within 10 s from one peer accept four and reject the fifth.
  - `test_zone_preview_uses_server_values`: the preview circle radius equals the snapshot's `next_radius`, not a locally computed one.
- Manual: join a live match — the minimap circle visibly shrinks and its centre drifts, the dashed preview leads it by 30 s, hot zones pulse and fade as the pot grows, `M` opens a pannable full map, a ping shows for a teammate and not for an enemy, and a $3500 player produces a pulse ring every 20 s.

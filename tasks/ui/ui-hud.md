# HIGH — HUD: health, stamina, cash, ammo, compass, killfeed, team panel

**Category:** ui
**Priority:** HIGH
**Status:** TODO
**Milestone:** M9
**Depends on:** net-snapshot-sync, move-stamina, econ-cash-state, gun-reload-mags, zone-teams-dbno

## Files
- `client/ui/hud/hud.tscn` (new)
- `client/ui/hud/hud.gd` (new)
- `client/ui/hud/compass_strip.gd` (new)
- `client/ui/hud/killfeed.gd` (new)
- `client/ui/hud/team_panel.gd` (new)
- `client/ui/theme/lootershooter_theme.tres` (new)
- `tests/test_hud_bindings.gd` (new)

## Issue
The client renders a world with no readouts: a player cannot see health, the 100-point stamina pool, cash on hand, ammo in the magazine, the zone timer against the 15:00 cap, or who just died. In team modes there is no way to see that a teammate is knocked. This is the last blocker to a playable vertical slice alongside the minimap and server browser.

## Fix
- `client/ui/hud/hud.tscn`: a `CanvasLayer` with anchored containers — bottom-left health + stamina bars, bottom-right ammo block, top-centre compass strip, top-left zone/match timer, right edge killfeed, left edge team panel, cash readout above health. Build the theme from the Kenney *UI Pack* nine-slices and *Game Icons* (CC0) into `lootershooter_theme.tres`; no per-control inline styling.
- `hud.gd` binds to the local `PlayerState`'s signals — `health_changed`, `stamina_changed`, `cash_changed`, `ammo_changed`, `armor_changed` — and never polls in `_process` except for the timer and compass. HUD is client-only and read-only; it must not send anything to the server.
- Health bar 0–100 with an armor pip row above it (vest tier + durability, helmet icon greys out when broken). Stamina bar 0–100 that turns amber below 30 (the ADS sway threshold) and hides after 3 s at full.
- Cash: `$1,234` formatted, flashing green on gain and red on drain; when cash > $3000 show the rich-bounty icon so the player knows they are marked on everyone's minimap every 20 s.
- Ammo block: `mag / reserve`, the fire-mode glyph (semi/burst/auto/bolt), and the PUBG-style partial-mag count from `gun-reload-mags`. Greys during reload with a thin progress arc.
- `compass_strip.gd`: a 360° strip with N/NE/E/... ticks and 3-digit bearings, driven by the camera yaw. Renders ping and teammate markers clamped to the strip edges. Redraw only when yaw changes by more than 0.2°.
- `killfeed.gd`: consumes a `kill_event {killer_name, victim_name, weapon_id, headshot, killer_is_local, victim_is_local}` RPC broadcast by the server. Max 5 entries, 6 s each, fade out; weapon icon from the item atlas; local player's kills highlighted.
- `team_panel.gd`: one row per teammate — name, colour, health bar, DBNO state with a bleed-out countdown, disconnected/dead states, and a small vehicle/seat icon when they are in a vehicle. Hidden entirely in solo.
- Zone timer shows `mm:ss` to the 15:00 cap plus a shrink indicator; turns red and pulses while the local player is outside the circle (−$20/s and −2 HP/s scaling with distance).
- Everything scales with a `ui_scale` setting and respects the colourblind palette added in `ui-settings-keybinds` — read both from the settings singleton, do not hardcode colours.

## Acceptance
- GUT test `tests/test_hud_bindings.gd` (headless, instancing the scene without a server):
  - `test_health_binding`: emitting `health_changed(37)` sets the health bar value to 37.
  - `test_cash_format`: cash 1234 renders `$1,234`; cash 3500 makes the bounty icon visible, 2999 hides it.
  - `test_killfeed_cap`: pushing 8 kill events leaves exactly 5 rows.
  - `test_stamina_warning`: stamina 29 sets the amber modulate; 31 does not.
- Manual: run the client against a local server — take damage, sprint to drain stamina, pick up cash, fire and reload, step outside the zone, and watch each readout respond; at 1280×720 and 2560×1440 nothing overlaps or clips.

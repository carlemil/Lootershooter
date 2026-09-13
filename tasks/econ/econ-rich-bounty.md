# MEDIUM — Rich bounty marker above $3000

**Category:** econ
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-cash-state

## Files
- `server/economy/rich_bounty.gd` (new)
- `client/ui/minimap/bounty_marker.gd` (new)
- `tests/test_rich_bounty.gd` (new)

## Issue
Hoarding cash is currently risk-free, so a player can sit on $6000 and never touch the store, which kills the buy loop the economy is built around. The design's pressure valve: anyone carrying more than $3000 is broadcast to every minimap as a pulsing marker, refreshed every 20 s.

## Fix
- `server/economy/rich_bounty.gd` (server only): a 20.0 s `Timer` that scans every alive `PlayerState`, collects those with `cash > 3000`, and broadcasts `bounty_positions(Array[Dictionary])` with `{peer_id, position, cash_band}` to all clients.
- Send a **cash band**, not the exact amount: `"rich"` (3000–6000) / `"loaded"` (>6000). Exact balances stay private.
- Snapshot the position at the moment of the tick only — no continuous tracking. The marker is a 20-second-old breadcrumb, which is the intended tension; document that in a comment so nobody "fixes" it into a wallhack.
- Exclude the carrier from their own broadcast list only for the "hunted" warning styling — they still see a marker on themselves plus a HUD warning "You are marked" so they know to spend.
- Teammates of a marked player see the marker but not the warning.
- A player who drops below $3000 (spent it, died) is omitted from the next tick; death removes them immediately by re-running the scan on `player_died`.
- `client/ui/minimap/bounty_marker.gd`: draws a pulsing icon on the minimap and full map at the broadcast position, alpha-decaying over the 20 s until the next update so a stale marker visibly ages out. Colourblind-safe shape difference (ring vs. dot) between `"rich"` and `"loaded"`, not colour alone.

## Acceptance
- GUT test `tests/test_rich_bounty.gd`:
  - A player at $2999 is absent from the broadcast; at $3001 present with band `"rich"`; at $6500 band `"loaded"`.
  - The scan fires at 20 s intervals, not per frame (count emissions over 61 s == 3).
  - A marked player who dies is removed from the very next broadcast without waiting the full 20 s.
- In a local session, exceeding $3000 shows the "You are marked" HUD warning and the marker pulses on a second client's minimap and fades over 20 s.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

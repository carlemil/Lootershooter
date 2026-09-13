# MEDIUM — Lobby, team select, orbit drop pick, end scoreboard

**Category:** ui
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M9
**Depends on:** ui-server-browser, ui-minimap-fullmap, zone-match-loop, zone-drop-in, zone-teams-dbno

## Files
- `client/ui/menu/lobby.tscn` (new)
- `client/ui/menu/lobby.gd` (new)
- `client/ui/menu/team_select.gd` (new)
- `client/ui/orbit/orbit_screen.tscn` (new)
- `client/ui/orbit/orbit_screen.gd` (new)
- `client/ui/menu/scoreboard.tscn` (new)
- `client/ui/menu/scoreboard.gd` (new)
- `tests/test_orbit_pick.gd` (new)

## Issue
The server's match loop already runs lobby → warm-up → orbit → drop → 15:00 match → results → lobby, but the client shows none of those states: a joining player has no lobby, no team select, no way to pick a drop point on the orbit screen (team leader picks, teammates cluster within 150 m, 20 s timer) and no results screen. The match-flow states exist server-side with no front end.

## Fix
- `lobby.tscn`: player list with names, team colours and ready state; match countdown (starts when ≥2 players or on the host timer); bot fill count; map name and mode; a Ready button and a Leave button. Driven by a `lobby_state` RPC from the server — the client never decides readiness or team composition itself.
- `team_select.gd`: pick or create a team (1–4 depending on mode), or Auto-fill. Sends `rpc_id(1, "request_team", team_id)`; the server validates size and mode and broadcasts. Show which teams are full. Solo mode hides the panel.
- Warm-up screen (`client/ui/lobby/warmup_screen.tscn`, new): shown during `WARMUP`; loads the world, runs the shader pre-warm pass from `zone-match-loop`, then sends `client_ready` and shows "waiting for other players" with a count.
- `orbit_screen.tscn`: the full-map texture from `ui-minimap-fullmap` (reuse `MapProjection`; do not write a second projection), a 30 s countdown, the current zone-free map with hot-zone spawn hints off (they are not known yet), and other players' picked spots for your own team only.
  - Team leader clicks a point → `rpc_id(1, "request_drop_point", pos)`. The server clamps it to the map bounds and the flight path. Teammates see the leader's marker and their own auto-cluster position within the 150 m allowance; a non-leader clicking sees "leader picks" feedback.
  - A small readout of the reentry timeline (reentry 5 s, no control → freefall, up to 60 m/s, 15 m/s lateral → chute auto at 300 m) so first-time players know what is about to happen.
- In-flight HUD (part of `orbit_screen.gd`, shown during the drop state): altitude, horizontal speed, distance to the picked point, and a chute prompt that turns from "manual chute" to "auto at 300 m". It reads the state machine's replicated phase — it does not run the state machine.
- `scoreboard.tscn`: end-of-match results — placement, winning team highlighted, then per-player rows with kills, damage, cash earned, cash spent, cash on hand (the 15:00 tiebreak), distance travelled, hot-zone seconds. Sort by placement then cash. A "Back to lobby" button and a countdown to the next match on the same server.
- Mid-match `Tab`-equivalent scoreboard: the same scene in a compact mode showing teams alive, players alive, and your team's stats — bound to a separate key from the inventory `Tab`.
- All screens are `CanvasLayer`s under one `client/ui/ui_root.gd` state switcher driven by the replicated match state, so exactly one screen is visible per match phase.

## Acceptance
- GUT test `tests/test_orbit_pick.gd`:
  - `test_pick_clamped`: a drop request at world `(3000, 0, 0)` is clamped inside the ±1024 m map bounds.
  - `test_leader_only`: a non-leader's `request_drop_point` is rejected and the team's marker is unchanged.
  - `test_cluster_within_150`: teammate auto-cluster positions are all within 150 m of the leader's pick.
  - `test_scoreboard_sort`: three fake results sort by placement, and a tie at 15:00 orders by cash on hand.
- Manual: run a full local match — lobby shows players and bots and counts down, team select assigns a squad, the orbit screen accepts a pick with a 30 s timer, the flight readout updates during freefall and chute, and the scoreboard lists the correct winner and cash figures before returning to lobby.

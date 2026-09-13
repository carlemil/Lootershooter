# HIGH — Match loop: lobby → orbit → drop → match → results → lobby

**Category:** zone
**Priority:** HIGH
**Status:** TODO
**Milestone:** M5
**Depends on:** net-server-bootstrap, zone-shrinking-circle, econ-cash-state

## Files
- `server/match/match_loop.gd` (new)
- `shared/match/match_phase.gd` (new)
- `server/match/results.gd` (new)
- `tests/test_match_loop.gd` (new)

## Issue
`net-server-bootstrap` left a state skeleton but no actual match: no seed, no phase timings, no win condition, no results, no return to lobby. The container is supposed to loop forever — lobby, 20 s orbit pick, 5 s reentry, freefall, the match, results, lobby. There is **no hard time cap and no cash tiebreak**: the circle closes to radius 0 at 15:00 and the outside-damage ramp ends the match by attrition. The only win condition is last team alive.

## Fix
- `shared/match/match_phase.gd`: `enum Phase { LOBBY, ORBIT, REENTRY, FREEFALL, MATCH, RESULTS }` plus `ORBIT_S = 20.0`, `REENTRY_S = 5.0`, `CIRCLE_CLOSE_S = 900.0`, `RESULTS_S = 20.0`. Note in a comment that `CIRCLE_CLOSE_S` is the circle's closing time and the HUD clock — **not** a match timeout. Shared so the client names the same phases.
- `server/match/match_loop.gd` (server only), the single owner of phase transitions:
  - `LOBBY`: wait for ≥ 2 human players or a host timer; ask the bot filler to top up to the configured target (default 20) before leaving lobby.
  - Generate `match_seed := randi()` **once** when leaving lobby, broadcast it, and hand it to `ZoneService`, `HotZoneService` and `MoneySpawner` — one seed drives zone wander, hot zones and loot layout so replays reproduce.
  - `ORBIT` 20 s → `REENTRY` 5 s → `FREEFALL` (ends per player on landing; the phase ends when the last player has landed or a 60 s safety timeout) → `MATCH`.
  - `MATCH` has **no end timer**. Evaluate the end condition after every death (and as a cheap once-per-second safety net): `alive_teams().size() <= 1`. One team left → that team wins and the loop moves to `RESULTS`. Zero teams left (a simultaneous wipe, e.g. two players' zone ramps expiring on the same tick) → record a **draw** with no winner and still go to `RESULTS`; never hang waiting for a winner that cannot exist.
  - Keep a display clock counting up from 0 and broadcast it; past 900 s it keeps counting ("circle closed" state on the HUD). Do not branch on it — the circle at radius 0 plus `ZoneMath.damage_per_s` reaching 100%/s after ~60 s outside is what resolves the match, typically within a minute of the close.
  - `RESULTS` 20 s showing the scoreboard, then reset everything (`CashService.reset_match()`, despawn loot/bags/hot zones, respawn players in lobby) and return to `LOBBY`. No process restart between matches — assert no leaked nodes by counting world-root children before and after.
  - Broadcast `phase_changed(phase, phase_end_unix_ms, match_seed)` reliably; clients drive countdowns from the end timestamp so a dropped packet doesn't desync the clock. `MATCH` carries a null/zero end timestamp because it has no scheduled end.
- `server/match/results.gd`: one scoreboard row per player — `{name, team, kills, cash_on_hand, cash_earned, cash_spent, distance_m, hot_zone_time_s, placement}` from `CashService.get_stats` and the damage system. **Cash is a displayed stat only** and never affects placement; sort by placement (team elimination order), then kills, then cash for presentation.
- Solo mode: every player is their own team, so the same last-team-alive rule works unchanged.
- **Death is final for the round.** There is no respawn path in `MATCH`: a `DEAD` player stays dead until `RESULTS`, keeps their peer slot, and receives snapshots as a spectator (see `zone-teams-dbno`). A peer that connects during `ORBIT`..`MATCH` is accepted into the slot list as `SPECTATOR` (never spawned into the world, no cash, no team) and becomes a normal lobby player at the next `LOBBY`. Bots never fill a slot vacated by a dead or disconnected human mid-match.

## Acceptance
- GUT test `tests/test_match_loop.gd` driving the loop with an injected clock and fake players:
  - Phase order and durations: ORBIT exactly 20 s, REENTRY exactly 5 s.
  - Killing all but one team at t = 120 s moves immediately to `RESULTS` with that team as winner.
  - **No timer end:** with two teams still alive at t = 1200 s (past the 900 s circle close) the phase is still `MATCH` — the loop has not ended the match and has not picked a cash winner.
  - Wiping the last two teams on the same tick yields `RESULTS` with `winner == null` and a draw flag, not a hang.
  - Two consecutive matches: `match_seed` differs, and after the second `LOBBY` transition every player's cash is 800 and no loot nodes remain.
  - A player killed at t = 60 s is still `DEAD` at t = 600 s with no body in the world; a peer joining at t = 200 s is `SPECTATOR`, has no `PlayerState` in the sim, and is `LOBBY`-eligible after `RESULTS`.
  - The results rows carry `cash_on_hand` but placement is unaffected by it: a losing team with more cash still places below the surviving team.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

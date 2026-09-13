# MEDIUM — Teams, knock-down, revive and spectate

**Category:** zone
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M5
**Depends on:** zone-match-loop, econ-kill-drop, gun-hitzones-damage

## Files
- `shared/match/team.gd` (new)
- `server/match/dbno_service.gd` (new)
- `client/ui/spectate/spectator_cam.gd` (new)
- `tests/test_dbno.gd` (new)

## Issue
Team modes (duo/trio/squad, 1–4) exist only as a lobby label. Death is final for the round (no respawns; the dead spectate until results), so in team modes a downed player should go DBNO rather than die outright — crawling, bleeding out, revivable by a teammate — and, importantly for the economy, a knocked player drops **no** cash bag until they are actually finished. After a real death the player needs something to do: spectate a living teammate, then the match.

## Fix
- `shared/match/team.gd`: `team_id` on `PlayerState`, `team_size` from the lobby mode (1 = solo → DBNO disabled entirely), helpers `teammates_of(peer)` and `alive_teams()` used by `match_loop`'s win check.
- `server/match/dbno_service.gd` (server only):
  - Lethal damage in a team mode with ≥ 1 living teammate → state `KNOCKED` instead of `DEAD`: HP set to a `bleed_hp = 100`, bleeding `-4 HP/s` (faster per subsequent knock in the same life: ×1.5 per knock, capped ×3), movement limited to a slow crawl, no weapons, no store, no interacts.
  - Lethal damage with no living teammate, or bleed-out to 0, or a finisher hit → `DEAD`, which is what fires `player_died` for `econ-kill-drop`. Assert in a comment and a test that no bag spawns on knock.
  - `revive(target_peer)`: a teammate channels 8.0 s within 2 m; cancels on the reviver taking damage, moving out of range, or being knocked (progress resets to 0). On success the target stands with 30 HP and their knock counter kept.
  - Credit the kill to the peer who landed the knock if the victim bleeds out or is finished within 30 s of the knock; otherwise the finisher gets it.
  - When the last living member of a team is knocked, immediately convert every knocked member to `DEAD` (team wipe) — each drops its own bag.
- `client/ui/spectate/spectator_cam.gd`: on `DEAD`, attach to a living teammate's first-person camera, cycle with fire/aim keys, show their HUD; when no teammate is alive, free-look camera over the match until `RESULTS`. Spectating never grants input authority — the spectator sends no input packets.
- HUD: DBNO indicator per teammate with bleed timer, revive prompt with a channel bar, and a "knocked" vignette for the victim.

## Acceptance
- GUT test `tests/test_dbno.gd`:
  - Squad mode, victim takes lethal damage with a living teammate → state `KNOCKED`, no cash bag exists, `player_died` not emitted.
  - Bleed at 4 HP/s from 100 reaches `DEAD` at 25.0 s; exactly one bag then spawns with the victim's cash + $300.
  - Revive channel interrupted at 7.9 s leaves the target knocked with progress 0; a full 8.0 s channel restores 30 HP.
  - Solo mode: lethal damage goes straight to `DEAD` with no knocked state.
  - Knocking the last living member of a team converts all knocked members to `DEAD` and spawns a bag per member.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

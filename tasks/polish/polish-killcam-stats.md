# MEDIUM — Kill cam from 5 s of server history, plus match stats

**Category:** polish
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M10
**Depends on:** net-lagcomp-history, zone-teams-dbno, ui-lobby-orbit-scoreboard, polish-anticheat-sanity

## Files
- `server/match/kill_history.gd` (new)
- `client/ui/killcam/killcam.tscn` (new)
- `client/ui/killcam/killcam.gd` (new)
- `server/match/match_stats.gd` (new)
- `tests/test_kill_history.gd` (new)

## Issue
When you die you see a black screen and have no idea what happened — whether you were flanked, shot through a wall, or hit by someone you never saw. The server already keeps a 200 ms hitbox ring for lag compensation, but nothing keeps the ~5 s of coarse state a kill cam needs, and the end scoreboard has no stats source beyond whatever each screen scrapes together.

## Fix
- `server/match/kill_history.gd`: server-only. A ring buffer of coarse world snapshots at 10 Hz covering 6 s (60 frames) — per player `{peer, pos, yaw, pitch, stance, health, weapon_id, firing}`, plus tracer events `{origin, dir, speed, tick}` and damage events. Coarse on purpose: this is a replay aid, not the lag-comp buffer, and must cost well under 1 ms per second of match time.
- On a kill, the server extracts the killer's and victim's last 5 s from the ring plus everyone within 100 m of either, and sends that slice to the victim only (never to living opponents — it must not leak enemy positions mid-match). Compress with the existing snapshot encoder.
- `client/ui/killcam/killcam.gd`: plays the slice back from the killer's viewpoint, interpolating the 10 Hz frames, with a scrub bar, pause, and a 0.5× slow-motion toggle. Overlay shows killer name, weapon, distance, hit zone and damage per hit. The world itself is already loaded — reuse the live scene, hide live players during playback, and drive ghost proxies from the slice.
- Show it after the death screen, skippable with a key, and never during DBNO (in team modes the kill cam waits until the player is actually finished, so it cannot be used to scout while a teammate is reviving). Solo mode plays it immediately.
- `server/match/match_stats.gd`: accumulates per player `{kills, knocks, assists (damage ≥ 20% within 10 s of the kill), damage_dealt, damage_taken, headshots, shots_fired, shots_hit, cash_earned, cash_spent, cash_on_hand, distance_m, vehicle_distance_m, hot_zone_seconds, revives, survival_time, placement}`. It is the single source for the end scoreboard from `ui-lobby-orbit-scoreboard` and for the telemetry `"end"` line.
- Accuracy is `shots_hit / shots_fired` computed server-side from the ballistics results, not claimed by the client.
- Persist each finished match's stats block as one JSON line in `learn/<date>.jsonl` with `"type": "stats"` so `polish-playtest-balance` can consume it with the same reader as everything else.
- Memory guard: cap the ring at 60 frames × 20 players and reuse preallocated arrays; a kill-cam slice is built on demand and freed after sending.

## Acceptance
- GUT test `tests/test_kill_history.gd`:
  - `test_ring_length`: after 10 s of simulated 10 Hz pushes the ring holds exactly 60 frames, the oldest being 6 s old.
  - `test_slice_contents`: a slice for a kill at tick T contains frames covering T−5 s to T, includes killer and victim, and excludes a player 300 m away.
  - `test_no_leak`: the slice is addressed only to the victim's peer id.
  - `test_stats_accuracy`: 10 shots fired with 4 hits yields `accuracy == 0.4`; an assist is credited for 25% damage dealt 6 s before the kill and not for damage 15 s before.
- Manual: die to a bot in a local match — the kill cam shows the bot's approach and shot from its viewpoint, scrub and slow-mo work, skipping returns to spectate; in squad mode nothing plays until you are finished. The end scoreboard numbers match the kill cam's damage figures.

# MEDIUM — Performance pass: 20 players + bots at 30 Hz, client 60 fps

**Category:** polish
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M10
**Depends on:** bot-utility-brain, bot-navigation, bot-perception, veh-net-sync, ui-minimap-fullmap, world-paddies-plantation-jungle

## Files
- `server/profiling/tick_profiler.gd` (new)
- `tools/perf_soak.ps1` (new)
- `client/profiling/frame_stats.gd` (new)
- `tests/test_tick_budget.gd` (new)

## Issue
A full match is 20 slots, most of them bots, each running perception raycasts, a utility scorer, navigation and an aim model, on top of ballistics, lag-comp history, snapshots and vehicle physics. The server tick is 30 Hz, so everything must fit in 33 ms or the server falls behind and every client feels it. Nothing measures any of this today, so the first time it matters will be the first 20-bot match.

## Fix
- `server/profiling/tick_profiler.gd`: server-only autoload enabled with `--profile`. Times labelled phases per tick — `input`, `movement`, `ballistics`, `bots_perception`, `bots_brain`, `bots_nav`, `bots_aim`, `vehicles`, `zone_econ`, `lagcomp`, `snapshot`, `recorder` — using `Time.get_ticks_usec()`. Keeps a rolling 300-tick window and reports mean, p95 and max per phase plus total. Logs a line every 10 s and writes a summary JSON at match end.
- Budget targets for 20 slots (17 bots) at 30 Hz, total ≤ 33 ms with headroom: input+movement ≤ 4 ms, ballistics ≤ 3 ms, all bot phases combined ≤ 12 ms, vehicles ≤ 3 ms, lag-comp + snapshot ≤ 6 ms, everything else ≤ 3 ms. p95 total ≤ 20 ms; max total ≤ 33 ms with zero missed ticks over a 15-minute match.
- Known levers to apply, measuring after each (do not apply blindly):
  - Bot perception is the big one: keep it at 10 Hz staggered by `peer_id % 3`, cap candidates by a squared-distance prefilter before any raycast, and reuse one `PhysicsRayQueryParameters3D` object rather than allocating per query.
  - Brain at 5 Hz staggered; navigation repaths capped at 8 per tick with a round-robin queue (already specified in `bot-navigation` — verify it holds under load).
  - Lag-comp history stores only hitbox transforms, preallocated, no per-tick array growth.
  - Snapshot: skip parked vehicles and distance-cull loot; verify delta compression actually shrinks packets (log bytes/tick, target < 8 KB/s per client).
  - Telemetry recorder flushes off the critical path and drops a batch rather than blocking (already specified — verify).
- `tools/perf_soak.ps1`: launches a headless server with `--bots=20 --profile --record` and runs a full 15-minute match with no human clients, then prints the phase table and pass/fail against the budgets. This is the repeatable benchmark; run it before and after any bot or netcode change.
- `client/profiling/frame_stats.gd`: an F3 overlay with fps, frame time, draw calls, vertices, and the ping/jitter to the server. Client target 60 fps at 1080p on mid hardware — the main costs will be foliage instancing (use Terrain3D LODs and a hard instance-distance cap), the viewmodel, and the minimap (confirm it is a baked texture, not a live `SubViewport` camera).
- Fix what the numbers show, not what looks slow. Record the before/after table in the task's commit message.

## Acceptance
- GUT test `tests/test_tick_budget.gd`:
  - `test_profiler_phases`: all 12 phase labels are recorded and their sum is within 5% of the measured total tick time.
  - `test_budget_assertion`: a synthetic run with a 40 ms tick is reported as a missed tick; a 20 ms tick is not.
  - `test_perception_stagger`: over 3 consecutive ticks with 18 bots, no tick runs perception for more than 7 bots.
- `tools/perf_soak.ps1` on a 15-minute 20-bot headless match: p95 total tick ≤ 20 ms, max ≤ 33 ms, zero missed ticks, bot phases combined ≤ 12 ms mean, per-client snapshot bandwidth < 8 KB/s.
- Client: 60 fps or better at 1080p in the jungle biome with 20 entities visible, verified on the F3 overlay.

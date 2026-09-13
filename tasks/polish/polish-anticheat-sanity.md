# MEDIUM — Server-side sanity checks: speed, teleport, fire rate, input rate

**Category:** polish
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M10
**Depends on:** net-input-stream, net-prediction-reconcile, net-lagcomp-history, gun-weapon-base, econ-store-catalog

## Files
- `server/anticheat/sanity.gd` (new)
- `server/anticheat/violation_log.gd` (new)
- `server/net/input_router.gd` (modify)
- `data/anticheat.json` (new)
- `tests/test_anticheat_sanity.gd` (new)

## Issue
The server is authoritative for movement, damage and economy, but it currently accepts whatever input arrives: a modified client can send 200 inputs per second, claim a position jump, fire faster than the weapon's RPM, or spam purchase and enter-vehicle requests. The plan's anti-cheat basics are exactly these four checks plus a per-match seed, and they are cheap because the server already simulates everything — it just has to notice when the client's claims disagree.

## Fix
- `server/anticheat/sanity.gd`: server-only, called from `input_router.apply_input()` before the input is simulated. Thresholds live in `data/anticheat.json` so tuning needs no code change.
- **Input rate**: a per-peer token bucket sized for the 30 Hz tick with burst tolerance (max 45 inputs/s sustained, burst 20). Excess inputs are dropped, not queued. Duplicate or out-of-order `tick` values are dropped; a `tick` more than 20 ahead of the server tick is rejected (clients must not run ahead).
- **Speed**: after simulating, compare the resulting position delta against `max_speed_for_state * dt * 1.15` (state = stance, stamina, weight, in-vehicle, water, on a slope). A breach does not kick — the server *corrects*, snapping the player back to the last valid position and sending a forced reconciliation. Count the breach.
- **Teleport**: any single-tick delta beyond `teleport_threshold_m` (default 8 m, exempting legitimate teleports — vehicle enter/exit, nav-link traversal, respawn — which must call `Sanity.allow_warp(peer, reason)` for that tick).
- **Fire rate**: per weapon, enforce `60.0 / rpm` between accepted `fire` messages with a 15 ms grace for jitter; reject extra shots outright (no bullet, no recoil) rather than clamping. Also reject firing while reloading, while the wrist store is raised, while in a driver seat, or with an empty magazine — the server already knows all four.
- **Request spam**: rate-limit non-movement RPCs per peer — purchase 10/s, interact 10/s, enter-vehicle 5/s, ping 4/10 s, inventory move 20/s, chat 3/s. Over the limit, drop and count.
- **Look rate**: clamp per-tick yaw/pitch delta to the same constant bots use (`bot-input-adapter`) — a shared `MAX_TURN_RATE`, so an aimbot's instant snaps become impossible for humans and bots alike.
- `server/anticheat/violation_log.gd`: accumulates `{peer, kind, count, worst_value, first_tick}`. Escalation: log at 1, warn the peer at 5 of a kind within 30 s, kick at 20, and always write the summary to the telemetry JSONL (`bot-learning-recorder`) so false positives are visible in the data before anyone is banned. Never kick on a single breach — latency and packet loss produce isolated ones.
- Per-match seed: the server generates it, uses it for all loot/vehicle/zone RNG, and only publishes derived state — never the seed itself — so a client cannot precompute the layout or the zone wander path.
- Every check must be O(1) per input; the whole sanity pass must stay under 0.5 ms per tick for 20 players.

## Acceptance
- GUT test `tests/test_anticheat_sanity.gd`:
  - `test_input_rate_limit`: 100 inputs pushed in one simulated second accept at most 45 and count the rest as violations.
  - `test_speed_correction`: an input that would move a walking player 5 m in one 33 ms tick is corrected back to the last valid position (max ≈ 0.19 m) and logs one `speed` violation.
  - `test_teleport_exempt`: a 30 m warp with `allow_warp(peer, "vehicle_exit")` set logs nothing; the same warp without it logs a `teleport` violation.
  - `test_fire_rate`: a 600 RPM weapon accepts shots 100 ms apart and rejects a second shot at 40 ms; the rejected shot produces no damage event.
  - `test_escalation`: 20 violations of one kind within 30 s triggers a kick; 4 do not.
- Perf: with 20 simulated peers at 30 Hz, the sanity pass measures under 0.5 ms per tick in the headless profile output.

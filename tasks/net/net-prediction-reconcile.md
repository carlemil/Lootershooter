# HIGH — Client-side prediction and server reconciliation

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-snapshot-sync

## Files
- `client/net/prediction.gd` (new)
- `shared/net/tick_clock.gd` (new)
- `tests/shared/test_prediction.gd` (new)
- `tests/helpers/fake_link.gd` (new)

## Issue
With snapshots arriving at 20 Hz and inputs travelling to a 30 Hz server, the local player would feel a full round-trip of input lag if it simply displayed the last snapshot. The local player must move immediately on its own input, then correct silently when the server's authoritative state for that tick disagrees. The correction must be exact: same movement code, same tick delta, same order, or the client will visibly rubber-band. This is the piece that has to survive 150 ms of simulated latency.

## Fix
- `shared/net/tick_clock.gd`, `class_name TickClock`: converts wall time to tick numbers at `NetConstants.TICK_RATE`, and holds the client's estimated **server tick** = last received snapshot tick + half RTT in ticks + 1 tick of buffer. It nudges (never jumps) by ±1 tick when the estimate drifts more than 2 ticks, so the input stream stays just ahead of the server.
- `client/net/prediction.gd`:
  - Owns `pending: Array[InputFrame]` — every frame sent and not yet acked, in ascending tick order.
  - Each client tick: build the input frame, append to `pending`, call `Player.apply_input(frame, NetConstants.TICK_DELTA)` locally, send it.
  - On `snapshot_applied(tick, acked_input_tick, states)`:
    1. Discard every pending frame with `tick <= acked_input_tick`.
    2. Read the authoritative local `PlayerState` out of the snapshot.
    3. Compare it with the locally predicted state that was recorded for `acked_input_tick` (keep a parallel `predicted_history: Dictionary[tick -> PlayerState]`, capped at 64 entries).
    4. If position differs by more than `RECONCILE_EPSILON = 0.02 m` or velocity by more than 0.1 m/s: snap the player to the authoritative state, then **replay** every remaining pending frame through `Player.apply_input` with `NetConstants.TICK_DELTA`, rewriting `predicted_history` as it goes.
    5. If the error is under the epsilon, do nothing — no smoothing, no correction (avoids constant micro-jitter).
  - Large corrections (> 1.0 m, e.g. teleport, spawn, vehicle exit) snap hard and clear `pending` entirely.
  - Optionally smooth sub-epsilon visual error by offsetting the **camera/mesh** by the residual and decaying it to zero over 100 ms; never offset the collision body.
  - Guard: cap the replay at 32 frames; if `pending` is longer, snap and drop, and log a warning (the connection is beyond playable).
- Determinism requirements, enforced by convention and by the tests: `Player.apply_input` must not read `Engine.get_process_delta_time()`, must not call `randf()`, and must not read `Input` directly — every input arrives in the `InputFrame`.
- `tests/helpers/fake_link.gd`: a test double that queues messages with a configurable one-way delay in ticks and an optional drop probability driven by a **seeded** `RandomNumberGenerator`, then delivers them when `advance(ticks)` is called. Used to simulate 150 ms latency (≈5 ticks each way) headlessly with no sockets.

## Acceptance
- GUT file `tests/shared/test_prediction.gd`, driving two `Player` instances (one "client", one "server") through `fake_link.gd`:
  - `test_no_latency_no_correction()` — 0 ms delay, 60 ticks of constant forward input: the client never triggers a replay (`reconcile_count == 0`) and both positions match within 0.001 m.
  - `test_150ms_latency_converges()` — 5-tick each-way delay, 120 ticks of forward-then-strafe input: after the last snapshot is applied, client and server positions agree within 0.02 m.
  - `test_replay_after_divergence()` — force the server to reject one input (simulate a wall the client did not know about) so the authoritative position differs by 0.5 m: the client snaps and replays, and `reconcile_count == 1`, with the final positions matching within 0.02 m.
  - `test_packet_loss_20pct_converges()` — seeded 20 % drop over 300 ticks: final divergence stays under 0.05 m and no replay exceeds 32 frames.
- Manual: with the server on localhost plus `--delay 150` (or a network simulator), strafing feels immediate and no rubber-banding is visible while walking into walls.

# HIGH — 20 Hz delta-compressed snapshots

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-input-stream

## Files
- `server/net/snapshot_writer.gd` (new)
- `client/net/snapshot_reader.gd` (new)
- `shared/net/snapshot.gd` (new)
- `client/net/remote_interpolator.gd` (new)
- `tests/shared/test_snapshot_delta.gd` (new)

## Issue
The server simulates at 30 Hz but must send state at 20 Hz, delta-compressed, along with the last input tick it processed for each client — that acked tick is what prediction and reconciliation key off. Right now nothing leaves the server, so clients see no one. With 20 players the full state must stay small enough that 20 players × 20 Hz is comfortable, which means short keys, quantised floats and sending only changed fields.

## Fix
- `shared/net/snapshot.gd`, `class_name Snapshot`:
  - `static encode_full(states: Array[PlayerState], tick: int, acked_input_tick: int) -> Dictionary` → `{"t": tick, "a": acked_input_tick, "f": 1, "p": {unique_id: player_dict}}`.
  - `static encode_delta(prev: Dictionary, curr: Dictionary) -> Dictionary` → same shape with `"f": 0` and, per player, only the keys whose value changed; players absent from `curr` appear in a `"rm": [ids]` array; new players carry all keys.
  - `static apply_delta(base: Dictionary, delta: Dictionary) -> Dictionary` reconstructs the full state. `encode/apply` must round-trip exactly — this is the one function every desync bug will point at, so it gets the most tests.
  - Quantisation helpers used inside the player dict: position to mm (`int(round(v * 1000.0))` per axis), angles to `int(round(a * 10000.0))`, health/stamina to `int(round(v * 10.0))`. Decoding reverses it. Quantise **before** the delta comparison, otherwise float noise defeats the compression.
- `server/net/snapshot_writer.gd`:
  - Runs every `TICK_RATE / SNAPSHOT_RATE` = every 1.5 ticks — implement as an accumulator so snapshots go out on ticks 0, 2, 3, 5, 6, … averaging 20 Hz, not by skipping every other tick.
  - Per connected peer keeps `last_acked_snapshot_tick` and a ring of the last 32 sent snapshot payloads. The delta baseline is the peer's last acked snapshot; if none is acked within 1 s or the baseline has fallen out of the ring, send a **full** snapshot (`"f": 1`).
  - `acked_input_tick` per peer comes from that peer's `InputReceiver.last_applied_tick`.
  - Private fields (cash, stamina, exact health, inventory) are included only in the receiving peer's own player entry and its teammates'; everyone else gets the public subset (`PlayerState.to_snapshot(false)`).
  - Send with `@rpc("authority", "call_remote", "unreliable")` `client_snapshot(payload)` on channel `CH_SNAPSHOT`; the client acks by piggybacking `last_snapshot_tick` on its next input packet (no separate ack RPC).
- `client/net/snapshot_reader.gd`:
  - Keeps the last confirmed full state, applies deltas, drops any snapshot with `t <=` the last applied tick (unreliable delivery can reorder), and re-requests nothing — a lost delta simply resolves when the next full snapshot arrives.
  - Emits `signal snapshot_applied(tick, acked_input_tick, states)`; `net-prediction-reconcile` consumes it.
- `client/net/remote_interpolator.gd`: for every non-local player, buffer the last 3 snapshots and render at `now - 100 ms` (two snapshot intervals), lerping position and `slerp`ing the yaw between the two bracketing snapshots; extrapolate for at most 100 ms when the buffer starves, then freeze. The local player is never interpolated — it is predicted.
- Bandwidth guard: log a warning if an encoded snapshot payload exceeds 1200 bytes (one MTU-safe datagram).

## Acceptance
- GUT file `tests/shared/test_snapshot_delta.gd`:
  - `test_full_then_delta_roundtrip()` — encode a full snapshot of 3 players, move one by `(0.5, 0, 0)`, encode the delta, `apply_delta(full, delta)` equals the freshly-encoded full state key-for-key.
  - `test_delta_omits_unchanged()` — with only player 2 moving, the delta's `p` dict has exactly one key, and that entry has no `h` (health) key.
  - `test_removed_player_in_rm()` — dropping player 3 puts `3` in `delta["rm"]` and `apply_delta` removes it.
  - `test_quantisation_precision()` — position `(1.2345, 0, -7.6543)` survives the round trip to within 0.001 m; yaw 1.23456 to within 0.0002 rad.
- Manual: two clients moving around see each other move smoothly (no stutter at 20 Hz thanks to the 100 ms interpolation delay), and the server log's average snapshot size for 20 players is under 1200 bytes.

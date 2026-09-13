# HIGH — Client→server input packets with tick numbers and rate limiting

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-player-spawn

## Files
- `shared/net/input_frame.gd` (new)
- `client/net/input_sender.gd` (new)
- `server/net/input_receiver.gd` (new)
- `tests/server/test_input_receiver.gd` (new)

## Issue
The server is authoritative, which means the only thing a client may send about its own movement is `{input_vector, look, buttons, tick}` — no position, no velocity, no "I hit them". There is no input channel at all yet, and without tick numbers on each frame neither prediction nor lag compensation can line client and server up. A naive channel also lets a client flood the server or replay old ticks, so rate limiting and tick sanity are part of this task, not a later hardening pass.

## Fix
- `shared/net/input_frame.gd`, `class_name InputFrame extends RefCounted`:
  - Fields: `tick: int`, `move: Vector2` (x = strafe, y = forward, each clamped to −1..1 and the vector length clamped to 1), `look_yaw: float`, `look_pitch: float` (clamped to ±PI/2), `buttons: int` (bitmask).
  - `const BTN_FIRE = 1 << 0`, `BTN_AIM = 1 << 1`, `BTN_SPRINT = 1 << 2`, `BTN_JUMP = 1 << 3`, `BTN_CROUCH = 1 << 4`, `BTN_PRONE = 1 << 5`, `BTN_LEAN_L = 1 << 6`, `BTN_LEAN_R = 1 << 7`, `BTN_RELOAD = 1 << 8`, `BTN_INTERACT = 1 << 9`, `BTN_STORE = 1 << 10`, `BTN_DIVE = 1 << 11`.
  - `to_array() -> Array` / `static from_array(a) -> InputFrame` using a compact positional array `[tick, move.x, move.y, yaw, pitch, buttons]`, not a Dictionary — this is the highest-frequency message in the game.
  - `pressed(mask) -> bool`, and `static sanitize(frame) -> InputFrame` applying every clamp above. Sanitising happens **on the server**, on receipt, before anything reads the frame.
- `client/net/input_sender.gd`:
  - Samples `Input` each client frame into an `InputFrame` with the client's current predicted tick.
  - Sends at the server tick rate (30 Hz), not per render frame: accumulate and emit on the 30 Hz boundary.
  - Each packet carries the **last 3 input frames** (the new one plus two redundant older ones) in one `@rpc("any_peer", "call_remote", "unreliable_ordered")` `server_input(frames: Array)` on channel `NetConstants.CH_INPUT`, so a single dropped UDP packet does not cost a tick. Unreliable is correct here — resending stale input is worse than losing it.
  - Keeps a local ring of unacked frames for `net-prediction-reconcile` to replay.
- `server/net/input_receiver.gd`, `class_name InputReceiver` — pure logic class, one instance per player, no RPC inside so it unit-tests headless:
  - `accept(frames: Array, now_tick: int, now_msec: int) -> Array[InputFrame]` returns the frames to actually apply, in ascending tick order, after:
    1. **Rate limit**: at most `NetConstants.TICK_RATE * 2` accepted frames per rolling second per player (a 60/s token bucket refilled by `now_msec`). Overflow frames are dropped and `rejected_rate` is incremented.
    2. **Duplicate/stale**: drop any frame with `tick <= last_applied_tick`.
    3. **Future clamp**: drop any frame with `tick > now_tick + 6` (200 ms of lead) — a client cannot run ahead of the server by more than the lag-comp window; increment `rejected_future`.
    4. **Sanitise**: `InputFrame.sanitize` on every surviving frame.
  - Exposes counters `rejected_rate`, `rejected_future`, `rejected_stale` and `last_applied_tick` — `polish-anticheat-sanity` later reads these.
  - **Gap filling**: if the accepted frame's tick is more than 1 past `last_applied_tick`, repeat the last applied frame for the missing ticks (up to 6) so the simulation never stands still on packet loss; return those repeats in the array flagged `is_repeat = true`.
- Server side: the `server_input` RPC looks the sender's `InputReceiver` up by `multiplayer.get_remote_sender_id()`, never by a peer id in the payload.
- Bots call `InputReceiver.accept` too — `bot-input-adapter` hands bot-generated `InputFrame`s into the *same* function, so bots cannot exceed the rate limit or bypass sanitising either.

## Acceptance
- GUT file `tests/server/test_input_receiver.gd`:
  - `test_stale_ticks_dropped()` — after accepting tick 10, feeding ticks 8, 9, 10 returns an empty array and `rejected_stale == 3`.
  - `test_future_ticks_dropped()` — `now_tick = 100`, frame tick 120 → dropped, `rejected_future == 1`; tick 106 → accepted.
  - `test_rate_limit()` — 200 frames with distinct ascending ticks inside one simulated second yield at most 60 accepted and `rejected_rate > 0`.
  - `test_gap_fill()` — last applied 10, then a frame at tick 14 → returns 4 frames (11, 12, 13 repeats + 14), the repeats carrying the previous frame's `move` and `buttons`.
  - `test_sanitize_clamps_move()` — a frame with `move = Vector2(9, 9)` is clamped to length 1.0 (`assert_almost_eq(accepted[0].move.length(), 1.0, 0.001)`).
- Manual: with a connected client, the server log's per-second input counter sits at ~30 accepted frames per player and 0 rejections under normal play.

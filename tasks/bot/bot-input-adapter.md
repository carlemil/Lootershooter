# HIGH — Bots feed the same input struct as human clients

**Category:** bot
**Priority:** HIGH
**Status:** TODO
**Milestone:** M8
**Depends on:** net-input-stream, net-player-spawn, move-controller-base

## Files
- `server/bots/bot_agent.gd` (new)
- `server/bots/bot_manager.gd` (new)
- `server/match/match_loop.gd` (modify)
- `tests/test_bot_input_adapter.gd` (new)

## Issue
Bots fill a 20-slot match up to the configured target, so most of the lobby is usually AI. If bots move or shoot through their own code path, the netcode grows a second branch that is untested by real play and becomes a cheating vector the anti-cheat checks cannot see. The plan's hard rule is that a bot is a server-side thing that produces exactly `{input_vector, look, buttons, tick}` and nothing else — the same struct `net-input-stream` receives from a client.

## Fix
- `server/bots/bot_agent.gd`: `class_name BotAgent extends Node`. Holds `peer_id: int` (negative pseudo-id, e.g. `-1..-20`, so it can never collide with an ENet peer), `player_state: PlayerState`, `profile: Dictionary`, `difficulty: String`, and a `current_input: Dictionary`.
- Public write API used by every later bot task: `set_move(vec: Vector2)`, `set_look(basis_or_yaw_pitch: Vector2)`, `press(button: int)`, `release(button: int)`, `tap(button: int)` (held for one tick). These only mutate `current_input`; no bot code may touch `PlayerState`, velocity, health, cash or the weapon directly.
- Each server tick (30 Hz) `BotAgent.emit_input(tick)` stamps `tick` and pushes the struct into the *same* server-side function that handles a received client input packet — factor that out of `net-input-stream` as `InputRouter.apply_input(peer_id, input)` if it is currently inline, and call it from both paths.
- `look` is rate-limited the same way a human's is: clamp per-tick yaw/pitch delta to the max turn rate used by the anti-cheat sanity check, so a bot can never snap instantly. Aim smoothing itself belongs to `bot-combat`; this task only enforces the clamp.
- `server/bots/bot_manager.gd`: autoloaded on the server only. `fill_to(target: int)` spawns `BotAgent`s plus a normal `PlayerState` through the same `MultiplayerSpawner` used for humans, assigning a name from a name pool and a profile from `data/bots.json`. `release_slot()` despawns the lowest-priority bot when a human joins mid-lobby. Config: `--bots=<n>` CLI arg, default fill to 20.
- Bots have no client, so snapshot writing must skip their peer ids (negative) — add that guard in the snapshot sender rather than special-casing bots elsewhere.
- `match_loop.gd`: call `BotManager.fill_to()` at lobby countdown, and drive `BotAgent.think()` (a no-op stub in this task, implemented in `bot-utility-brain`) once per tick before inputs are emitted.
- Add an assertion/`push_error` in `PlayerState` mutation setters if the caller stack is under `server/bots/` — cheap guard that keeps the single-path rule honest.

## Acceptance
- GUT test `tests/test_bot_input_adapter.gd`:
  - `test_input_struct_shape`: `BotAgent.emit_input(42)` produces a dictionary with exactly the keys `input_vector, look, buttons, tick` and `tick == 42`.
  - `test_same_router`: a bot's forward input and a simulated human packet with the identical struct produce the same `PlayerState.velocity` after one tick.
  - `test_look_clamped`: requesting a 180° yaw change in one tick yields a delta no larger than the max turn rate constant.
  - `test_fill_to`: `fill_to(20)` with 3 humans present creates 17 bot agents with distinct negative peer ids.
- Run `godot --headless -s addons/gut/gut_cmdln.gd -gexit` — all green.

# HIGH — Headless server bootstrap and match-loop skeleton

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** infra-data-loader, infra-dockerfile

## Files
- `server/server_main.gd` (new)
- `server/match_loop.gd` (new)
- `server/scenes/server_main.tscn` (new)
- `client/scenes/main.tscn` (new)
- `client/client_main.gd` (new)
- `shared/net/net_constants.gd` (new)
- `tests/server/test_match_loop.gd` (new)
- `project.godot` (modify)

## Issue
The Docker entrypoint runs `server.x86_64 --headless -- --port=7777 --registry=http://registry:8080`, but nothing parses those arguments, opens an ENet host or drives a match. One container must be one match instance that loops lobby → 15:00 match → results → lobby, with up to 20 slots. The tick rate is fixed at 30 Hz and must come from one place so client, server and tests agree.

## Fix
- `shared/net/net_constants.gd`, `class_name NetConstants`, all `const`, read once from `ProjectSettings` at the top of the file: `TICK_RATE = 30`, `TICK_DELTA = 1.0 / 30.0`, `SNAPSHOT_RATE = 20`, `LAGCOMP_MS = 200`, `MAX_PLAYERS = 20`, `MATCH_SECONDS = 900`, `DEFAULT_PORT = 7777`, plus the RPC channel ids (`CH_INPUT = 1`, `CH_SNAPSHOT = 2`, `CH_EVENT = 3`).
- `client/scenes/main.tscn` becomes `run/main_scene`. Its root script `client/client_main.gd` checks `OS.has_feature("dedicated_server") or DisplayServer.get_name() == "headless"` in `_ready()` and, when true, immediately swaps to `server/scenes/server_main.tscn` and returns — so one binary serves both roles and the dedicated-server export still boots.
- `server/server_main.gd` (`extends Node`):
  - Parse `OS.get_cmdline_user_args()` (the args after the bare `--`): `--port=`, `--registry=`, `--name=`, `--max-players=`, `--bot-target=`, `--seed=`. Fall back to env `LS_PORT`, `LS_REGISTRY`, `LS_NAME`, `LS_MAX_PLAYERS`, `LS_BOT_TARGET`, then to the `NetConstants` defaults. Unknown args: log a warning, do not abort.
  - Create the host: `var peer := ENetMultiplayerPeer.new(); peer.create_server(port, max_players)`; on error, `push_error` and `get_tree().quit(1)`. Assign `multiplayer.multiplayer_peer = peer`.
  - Connect `multiplayer.peer_connected` / `peer_disconnected` to handlers that forward to `MatchLoop`.
  - Set `Engine.max_fps = NetConstants.TICK_RATE` and drive the sim from a fixed accumulator in `_process(delta)` (accumulate `delta`, run `MatchLoop.tick()` while `acc >= TICK_DELTA`, subtract; clamp to at most 5 catch-up ticks per frame so a stall cannot spiral). Do **not** use `_physics_process` for the authoritative tick — it must stay independent of the render/physics rate.
  - Maintain `tick: int`, incremented once per sim tick, and the match seed (`--seed` or `Time.get_unix_time_from_system()` hashed) exposed as `match_seed` for every seeded RNG in the match.
  - Log one startup banner line: name, port, max players, registry URL, seed.
- `server/match_loop.gd`, `class_name MatchLoop extends Node`, a plain state machine — no networking inside it, so it is unit-testable headless:
  - `enum State { LOBBY, ORBIT, MATCH, RESULTS }`, `var state`, `var state_time: float`, `var tick: int`.
  - `tick()` advances `state_time` by `NetConstants.TICK_DELTA` and applies transitions:
    - LOBBY → ORBIT when `human_count >= 2` and a 10 s countdown elapses, or when `lobby_timeout` (120 s) expires with ≥1 human (bots fill the rest).
    - ORBIT → MATCH after 20 s.
    - MATCH → RESULTS when `MATCH_SECONDS` elapses or `alive_team_count() <= 1`.
    - RESULTS → LOBBY after 20 s, resetting `tick`, `state_time` and player cash.
  - `signal state_changed(from, to)`, `signal match_ended(winning_team, reason)` where `reason` is `"last_team"` or `"timer"`.
  - `add_player(id, is_bot)` / `remove_player(id)` keep a `players: Dictionary` of ids → `{team, alive, cash, is_bot}`. The tiebreak at the 15:00 timer is **most cash on hand** (see plan 3.1/3.2): implement `winning_team_by_cash()` summing per-team cash, and use it only for the `"timer"` reason.
  - Injectable clock: `tick()` takes no delta and uses `NetConstants.TICK_DELTA` so tests can call it N times deterministically.
- Nothing in `server/` may be preloaded from `shared/` consumers; `shared/` must not preload `server/`.

## Acceptance
- GUT file `tests/server/test_match_loop.gd` (constructs `MatchLoop` directly, no networking):
  - `test_lobby_waits_for_two_humans()` — with 1 human, 3000 ticks keep state `LOBBY` until the 120 s timeout, then it goes to `ORBIT`.
  - `test_orbit_lasts_20s()` — entering ORBIT then ticking `20 * 30` times lands in `MATCH`, one tick earlier it does not.
  - `test_match_ends_on_last_team()` — 2 teams, mark team B dead → `match_ended` emits with `winning_team == "A"` and reason `"last_team"` on the next tick.
  - `test_timer_tiebreak_is_cash()` — 2 teams alive at `900 * 30` ticks, team B holds $2400 vs team A $1600 → `match_ended` with `winning_team == "B"`, reason `"timer"`.
- `godot --headless --path . -- --port=7777 --name=Test` starts, prints the banner and stays running; `Ctrl-C` exits cleanly.
- `docker compose -f docker/docker-compose.yml up game1` shows the banner in the container logs.

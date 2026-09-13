# HIGH — Game server heartbeat to the registry

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-server-bootstrap, infra-registry-service

## Files
- `server/net/registry_heartbeat.gd` (new)
- `tests/server/test_registry_heartbeat.gd` (new)
- `server/server_main.gd` (modify)

## Issue
The registry container serves `/servers` from records that expire after 30 s, but no game server posts to it, so the in-game server browser would always be empty. Each match container must announce itself every 10 s with its name, map, mode and current player count, and must survive the registry being down or slow without stalling the 30 Hz match tick.

## Fix
- `server/net/registry_heartbeat.gd`, `class_name RegistryHeartbeat extends Node`, server-only (nothing under `client/` may reference it).
- Configuration comes from `server_main.gd`: `registry_url` (`--registry=` / `$LS_REGISTRY`), `server_name`, `port`, `mode` (`solo|duo|trio|squad`), `map_name`, `version` (`ProjectSettings.get_setting("application/config/version")`).
- If `registry_url` is empty, the node disables itself and logs one line — a LAN/dev server must run fine with no registry at all.
- Use `HTTPRequest` (never a blocking `HTTPClient` loop) as a child node so the request never blocks the tick:
  - A `Timer` with `wait_time = 10.0`, `autostart = true` fires `_send()`.
  - `_send()` skips if a request is still in flight (`http.get_http_client_status() != STATUS_DISCONNECTED`) and increments `skipped_count`.
  - POSTs `JSON.stringify(payload)` with header `Content-Type: application/json` to `registry_url + "/heartbeat"`.
  - `payload` = `{"name", "map", "mode", "players", "max_players", "port", "version"}` where `players` is **humans + bots currently in the match** (the browser shows a filled server) and `max_players` is the slot cap. Take both from `MatchLoop`.
- `request_completed` handler: on HTTP 200 reset `fail_streak = 0`; otherwise increment it and log at most one warning per 60 s (a chatty container log is worse than a missing server). Back off the timer to 30 s after 3 consecutive failures and back to 10 s on the first success.
- On `NOTIFICATION_WM_CLOSE_REQUEST` / `_exit_tree`, fire one best-effort `POST /heartbeat` with `"players": -1`? No — the registry has no delete endpoint; instead simply stop sending and let the 30 s TTL expire the entry. Document that in a comment so nobody adds a delete route later.
- Split the payload construction into a static, side-effect-free function `static build_payload(name, map, mode, players, max_players, port, version) -> Dictionary` so the test can check it without any HTTP.

## Acceptance
- GUT file `tests/server/test_registry_heartbeat.gd`:
  - `test_payload_shape()` — `build_payload("S1","town","squad",14,20,7777,"0.1.0")` has exactly the seven documented keys, `players == 14`, `port == 7777`.
  - `test_disabled_without_url()` — a `RegistryHeartbeat` with `registry_url = ""` reports `enabled == false` and creates no `Timer`.
  - `test_backoff_after_failures()` — calling the failure handler 3 times sets the timer's `wait_time` to 30.0; a success resets it to 10.0.
- Integration (manual, with the compose stack up): `docker compose up -d`, wait 15 s, then `curl -s localhost:8080/servers` lists the `game1` entry with the right name, port and a non-zero player count; stopping `game1` makes the entry disappear from `/servers` within 30 s.

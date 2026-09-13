# HIGH — Client connect, handshake and disconnect handling

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-server-bootstrap

## Files
- `client/net/client_net.gd` (new)
- `server/net/handshake.gd` (new)
- `shared/net/net_messages.gd` (new)
- `client/ui/connect_screen.tscn` (new)
- `client/ui/connect_screen.gd` (new)
- `tests/server/test_handshake.gd` (new)

## Issue
The server opens an ENet host but no client can join it, and there is no agreed handshake, so the server has no name or team preference for a peer and no way to reject a mismatched build. Disconnects (timeout, quit, kick) currently leave nothing to clean up because nothing is tracked. Max 20 slots with bots filling the rest means slot accounting has to be correct from the first join. A peer that connects while a match is running must be accepted as a spectator only; there is no mid-match spawn.

## Fix
- `shared/net/net_messages.gd`, `class_name NetMessages`, holds the message dictionaries and the protocol version as `const PROTOCOL_VERSION := 1`. Define plain helper constructors returning `Dictionary` (cheap and printable) rather than custom classes:
  - `hello(name, team_pref, protocol, build_hash) -> Dictionary`
  - `welcome(peer_id, slot, team, match_seed, state, server_tick) -> Dictionary`
  - `reject(reason: String) -> Dictionary` with reasons `"full"`, `"protocol"`, `"banned"`, `"bad_name"`.
- `client/net/client_net.gd` (autoload `ClientNet`):
  - `connect_to(host: String, port: int, player_name: String, team_pref: int)` → `ENetMultiplayerPeer.create_client`, assign to `multiplayer.multiplayer_peer`.
  - On `multiplayer.connected_to_server`, `rpc_id(1, "server_hello", NetMessages.hello(...))`.
  - `@rpc("authority", "call_remote", "reliable")` `client_welcome(msg)` stores `my_peer_id`, `my_slot`, `my_team`, `match_seed`, `server_tick` and emits `signal connected(welcome)`.
  - `@rpc("authority", "call_remote", "reliable")` `client_rejected(msg)` emits `signal rejected(reason)` and tears the peer down.
  - Handle `multiplayer.connection_failed`, `server_disconnected` → `signal disconnected(reason)`, set `multiplayer.multiplayer_peer = null`, return to the connect screen. Never leave a dead peer assigned.
  - A connect attempt that gets no `welcome` within 8 s counts as a timeout and disconnects.
- `server/net/handshake.gd`, `class_name Handshake` — pure logic, no RPC, so it is testable:
  - `validate(hello: Dictionary, current_humans: int, max_players: int, banned: Array) -> Dictionary` returning `{"ok": bool, "reason": String, "name": String, "team": int}`.
  - Rules, in order: protocol mismatch → `"protocol"`; peer id in `banned` → `"banned"`; `current_humans >= max_players` → `"full"` (bots do not occupy human slots — the server kicks a bot instead when a human arrives and `bot_target` fills the roster, so the "full" check counts **humans + humans-reserved slots**, not bots); a name that is empty, longer than 20 chars or not `[A-Za-z0-9_ -]` after trimming → sanitise to `Player<peer_id>` rather than rejecting, and only return `"bad_name"` when the field is missing entirely.
  - `team` is clamped to `1..max_teams`; `0` means "assign me one" → return the smallest team with free space for the mode's team size (1/2/3/4).
- Server side: an `@rpc("any_peer", "call_remote", "reliable")` `server_hello(msg)` on the server main node calls `Handshake.validate`, then either `MatchLoop.add_player(peer_id, false)` + `rpc_id(peer_id, "client_welcome", ...)`, or `rpc_id(peer_id, "client_rejected", ...)` followed by `multiplayer.multiplayer_peer.disconnect_peer(peer_id)` on the next frame.
- Never trust anything else from a client: no position, no cash, no weapon in the hello.
- `multiplayer.peer_disconnected` → `MatchLoop.remove_player(peer_id)`, free that player's node, and free its lag-comp history slot; if the match is in progress the player is treated as dead (their cash bag drops — implemented later in `econ-kill-drop`, leave a `# TODO(econ-kill-drop)` hook).
- `client/ui/connect_screen.tscn`: name field, IP field (default `127.0.0.1`), port spinbox (default 7777), team-size option button, Connect button, and a status label bound to `connected/rejected/disconnected`. Plain Control nodes; the styled server browser is `ui-server-browser`.

## Acceptance
- GUT file `tests/server/test_handshake.gd`:
  - `test_protocol_mismatch_rejected()` — hello with `protocol = 999` → `{ok: false, reason: "protocol"}`.
  - `test_full_server_rejected()` — `current_humans = 20`, `max_players = 20` → reason `"full"`.
  - `test_bad_name_is_sanitised_not_rejected()` — name `"  <script>  "` → `ok == true` and `name` matches `^Player\d+$` or the sanitised form, never the raw string.
  - `test_team_zero_gets_smallest_team()` — teams `{1: 4, 2: 1}` with team size 4 → assigned team `2`.
- Manual: run the headless server, launch two editor clients, both reach the welcome and appear in the server log with distinct peer ids and slots; closing one logs the disconnect and decrements the player count.

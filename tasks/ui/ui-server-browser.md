# HIGH — Server browser: registry list, filters, direct connect

**Category:** ui
**Priority:** HIGH
**Status:** TODO
**Milestone:** M9
**Depends on:** infra-registry-service, net-registry-heartbeat, net-client-connect

## Files
- `client/ui/menu/server_browser.tscn` (new)
- `client/ui/menu/server_browser.gd` (new)
- `client/net/registry_client.gd` (new)
- `tests/test_registry_client.gd` (new)

## Issue
Game servers already POST a heartbeat every 10 s to the registry service, and the registry serves `GET /servers`, but the client has no way to see that list — the only way to play is a hardcoded IP. Without a browser (list, filters, refresh, direct connect) the multiplayer loop is untestable by anyone who is not editing source.

## Fix
- `client/net/registry_client.gd`: a `Node` wrapping `HTTPRequest`. `fetch(registry_url: String)` GETs `<registry>/servers` and parses the JSON array the registry publishes: per entry `{name, map, mode, players, max_players, bots, ip, port, region, version, last_heartbeat}`. Signals `servers_received(Array)` and `fetch_failed(reason)`. 5 s timeout, one in-flight request at a time.
- Treat the response as untrusted input: validate types and clamp strings before display (a registry entry is written by whoever runs a server), drop entries whose `version` does not match the client's, and mark entries whose `last_heartbeat` is older than 30 s as stale rather than listing them as live.
- The registry URL comes from a setting (`registry_url`, default `http://localhost:8080` for dev) editable in the browser's footer, so a player can point at another registry.
- `server_browser.tscn`: a `Tree` or `ItemList` with sortable columns — Name, Map, Mode, Players (`7+13 bots / 20`), Ping, Region. Refresh button plus auto-refresh every 15 s while the screen is open. Double-click or Join connects via the existing `net-client-connect` path.
- Ping: measure it yourself — send a small ENet or UDP probe per listed server, at most 8 concurrent, and show `—` until a reply arrives. Do not trust a ping value from the registry.
- Filters: mode (solo/duo/trio/squad), region, max ping slider, "hide full", "hide empty", and a name search box. Filtering is client-side over the fetched array; no extra registry calls.
- Direct connect: an `IP:port` field with validation (IPv4 or hostname, port 1–65535) and a Connect button that bypasses the registry entirely — this must keep working when the registry is down.
- Connection states: show Connecting / Failed (with the reason from `net-client-connect`) / Version mismatch, with a Cancel that aborts cleanly and returns to the list.
- Empty and error states: "No servers found — check the registry URL, or use Direct Connect" rather than a blank list.

## Acceptance
- GUT test `tests/test_registry_client.gd`:
  - `test_parse_valid`: a fixture JSON array of 3 servers produces 3 entries with the expected fields.
  - `test_stale_filtered`: an entry with `last_heartbeat` 45 s old is excluded from the live list.
  - `test_version_mismatch_dropped`: an entry whose `version` differs from the client's is not listed.
  - `test_malformed_response`: invalid JSON and a JSON object (not array) both emit `fetch_failed` and never crash.
  - `test_direct_connect_validation`: `"256.1.1.1:7777"` and `"1.2.3.4:99999"` are rejected; `"1.2.3.4:7777"` and `"host.example:7777"` are accepted.
- Manual: `docker compose up` (registry + two game servers), open the browser — both servers appear within 15 s with live player counts, filters narrow the list, Join enters a match, and stopping the registry still allows Direct Connect.

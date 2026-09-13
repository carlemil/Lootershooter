# HIGH — Server-browser registry service (Python stdlib)

**Category:** infra
**Priority:** HIGH
**Status:** TODO
**Milestone:** M0
**Depends on:** infra-dockerfile

## Files
- `registry/registry.py` (new)
- `registry/Dockerfile` (new)
- `registry/test_registry.py` (new)
- `docker/docker-compose.yml` (modify)

## Issue
Clients need an in-game server list showing name, map, players, ping and mode, and game servers announce themselves with a heartbeat every 10 s. Nothing serves that list today. The plan fixes the implementation at roughly 60 lines of Python **stdlib only** (`http.server`) in its own container — no Flask, no FastAPI, no database.

## Fix
- `registry/registry.py`, stdlib only (`http.server`, `json`, `threading`, `time`, `os`, `argparse`). No third-party imports.
- In-memory dict `servers: dict[str, dict]` keyed by `"<host>:<port>"`, guarded by a `threading.Lock`.
- `POST /heartbeat` with a JSON body `{"name","map","mode","players","max_players","port","version"}`:
  - The advertised host is the **request's** client address (`self.client_address[0]`), never a body-supplied host, unless the env var `LS_TRUST_HOST_HEADER=1` is set (for NAT/dev).
  - Store the record with `last_seen = time.monotonic()`. Reply `200` with `{"ok": true, "ttl": 30}`.
  - Validate: `players` and `max_players` are ints in `0..64`, `port` is `1..65535`, strings are truncated to 64 chars. Reject malformed bodies with `400` and a JSON error — this is a trust boundary, do not crash the handler.
- `GET /servers` returns `{"servers": [...]}` — every record whose `last_seen` is within `TTL = 30` seconds (three missed 10 s heartbeats), each as `{"host","port","name","map","mode","players","max_players","version","age"}`. Sort by `players` descending.
- `GET /health` returns `{"ok": true, "count": n}`.
- Anything else → `404` JSON. Override `log_message` to a one-line stderr format so container logs stay readable.
- Sweep expired entries lazily inside `GET /servers` (no background thread needed).
- Serve with `ThreadingHTTPServer(("0.0.0.0", port), Handler)`; port from `--port` / `$PORT`, default `8080`.
- `registry/Dockerfile`: `FROM python:3.12-slim`, `COPY registry.py /app/`, `WORKDIR /app`, non-root user, `EXPOSE 8080`, `CMD ["python","registry.py"]`. No `pip install` line at all.
- `registry/test_registry.py`: plain `unittest` (stdlib), starts the server on port 0 in a thread and drives it with `urllib.request`. This is Python, not GUT — it runs with `python -m unittest discover registry`.
- Add/confirm the `registry` service in `docker/docker-compose.yml` (`build: ../registry`, `8080:8080`).

## Acceptance
- `python -m unittest discover -s registry -p 'test_*.py'` passes with at least these cases:
  - POST a heartbeat then GET `/servers` → 1 entry whose `host` equals the client IP and `players` matches.
  - Two heartbeats from the same host:port → still 1 entry, fields updated (no duplicates).
  - An entry whose `last_seen` is monkeypatched 31 s into the past is absent from `/servers`, and `/health` reports `count` excluding it.
  - `POST /heartbeat` with body `{"players": "many"}` → HTTP 400 and the server is still answering `/health`.
- `curl -s localhost:8080/servers` against the compose stack returns valid JSON.
- `wc -l registry/registry.py` is under 120 lines and `grep -E '^(import|from)' registry/registry.py` shows stdlib modules only.

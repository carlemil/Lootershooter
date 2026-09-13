# HIGH — Multi-stage Dockerfile and compose stack

**Category:** infra
**Priority:** HIGH
**Status:** TODO
**Milestone:** M0
**Depends on:** infra-export-presets

## Files
- `docker/Dockerfile` (new)
- `docker/docker-compose.yml` (new)
- `docker/.dockerignore` (new)
- `tools/run-local-server.ps1` (new)

## Issue
One container must equal one match instance (up to 20 slots, lobby → 15-min match → results, scaling by adding containers). Nothing builds or runs the server today. The build must not ship the Godot editor: stage 1 exports with the `server-linux` preset, stage 2 is a `debian:bookworm-slim` runtime holding only the binary and the `.pck`.

## Fix
- `docker/Dockerfile`, two stages, build context = repo root (compose sets `context: ..`, `dockerfile: docker/Dockerfile`).
- **Stage 1 `builder`**: base `barichello/godot-ci:4.7.2` (or `FROM debian:bookworm-slim` plus a downloaded `Godot_v4.7.2-stable_linux.x86_64` headless build and the matching `export_templates.tpz` unzipped to `/root/.local/share/godot/export_templates/<version>.stable/`). Pin the version in an `ARG GODOT_VERSION=4.7.2`.
  - `COPY . /src`, `WORKDIR /src`, then `RUN mkdir -p /out && godot --headless --export-release "server-linux" /out/server.x86_64`.
  - Import assets first (`godot --headless --import` or a throwaway `--quit` run) so the export does not fail on a cold `.godot/` cache.
- **Stage 2 runtime**: `FROM debian:bookworm-slim`. `RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libfontconfig1 && rm -rf /var/lib/apt/lists/*`. Create a non-root user `game` and `WORKDIR /app`. `COPY --from=builder /out/server.x86_64 /out/server.pck /app/`, `RUN chmod +x /app/server.x86_64`, `USER game`.
  - `EXPOSE 7777/udp`.
  - `ENV LS_PORT=7777 LS_REGISTRY=http://registry:8080 LS_NAME=Lootershooter LS_MAX_PLAYERS=20 LS_BOT_TARGET=20`.
  - `ENTRYPOINT ["/app/server.x86_64","--headless","--"]` and `CMD ["--port=7777","--registry=http://registry:8080"]` so the args the server parses in `net-server-bootstrap` come after the bare `--`.
- `docker/.dockerignore`: `.godot/`, `builds/`, `.git/`, `docs/`, `tasks/`, `tests/`, `addons/gut/`.
- `docker/docker-compose.yml` (compose spec, no `version:` key):
  - service `registry`: `build: ../registry`, port `8080:8080`, restart `unless-stopped`.
  - service `game1`: build from this Dockerfile, `depends_on: [registry]`, ports `7777:7777/udp`, env `LS_NAME=Lootershooter #1`, `LS_PORT=7777`, `LS_REGISTRY=http://registry:8080`.
  - service `game2`: identical but `7778:7778/udp`, `LS_PORT=7778`, `profiles: ["extra"]` so it only starts with `--profile extra`.
- `tools/run-local-server.ps1`: wraps `docker compose -f docker/docker-compose.yml up --build` with a `-Detach` switch and a `-Extra` switch that adds `--profile extra`; prints the UDP ports and the registry URL when up.

## Acceptance
- `docker build -f docker/Dockerfile -t lootershooter-server .` from the repo root succeeds and the final image is under ~150 MB (`docker images` — no editor, no templates in the runtime layer).
- `docker run --rm lootershooter-server --port=7777 --registry=http://127.0.0.1:8080` logs the server-bootstrap banner and does not exit (once `net-server-bootstrap` is done; before that, it must at least start the headless binary without a "Main scene not defined" crash loop).
- `docker compose -f docker/docker-compose.yml up -d` brings up `registry` and `game1`; `docker compose ps` shows both healthy.
- `docker run --rm --entrypoint ls lootershooter-server /app` shows exactly `server.x86_64` and `server.pck`.

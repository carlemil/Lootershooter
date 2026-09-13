# Lootershooter — project conventions

Godot 4.4+ (latest stable), GDScript only. One project, two export presets: `client-windows` and `server-linux` (Dedicated Server export mode, run with `--headless`). Plan: `README.md`. Tasks: `tasks/<cat>/<cat>-<name>.md`.

## Layout

```
shared/    runs on BOTH client and server: player controller, ballistics, inventory, zone math, data loader, net messages
server/    server only: match loop, spawner, lag-comp history, money spawner, hot zones, bots/, learning recorder, registry heartbeat
client/    client only: ui/, viewmodels, audio/, input, prediction/reconcile
world/     map scenes, kits, navmesh, loot markers
data/      weapons.json, cartridges.json, items.json, prices.json, bots.json, bots_learned.json
tests/     GUT tests
docker/    Dockerfile (multi-stage export -> debian:bookworm-slim), docker-compose.yml
registry/  server-browser registry (Python stdlib http.server) + Dockerfile
tools/     export.ps1, test.ps1, run-local-server.ps1
docs/      plan.html and design notes
```

## Rules

- Server-authoritative. The client sends only `{input_vector, look, buttons, tick}` plus explicit requests (`buy(item_id)`, `fire{tick, origin, dir}`). Every damage, cash and inventory decision is made on the server.
- Shared simulation is deterministic: fixed 30 Hz server tick, seeded RNG only (match seed), no `randf()` in `shared/`.
- Data-driven: no weapon/item stats or prices in scripts. Everything in `data/*.json`, loaded by the `Data` autoload, schema-checked by a test.
- Bots feed the same input struct as humans through the same path. No bot-only movement or damage code.
- Server tick 30 Hz, snapshots 20 Hz, lag-compensation history 200 ms.
- Money is the only loot. Store purchases go to inventory only if slot and weight allow.
- No `class_name` collisions across `shared/`, `server/`, `client/`; prefix server-only classes with `Srv`, client-only with `Cl`.

## Commands (Windows, PowerShell)

```
# unit tests (GUT)
godot --headless -s addons/gut/gut_cmdln.gd -gexit
# or
tools\test.ps1

# local server + client
tools\run-local-server.ps1        # headless server on 7777
godot --path . -- --connect=127.0.0.1:7777

# exports
tools\export.ps1 client-windows
tools\export.ps1 server-linux

# docker
docker compose -f docker/docker-compose.yml up --build
```

`godot` must be on PATH (Godot 4.4+ console binary). If not installed yet, task `infra-godot-project` documents the install.

## Task workflow

- Work tasks in the order given in `README.md` (vertical slice first). One task = one commit, message `<cat>: <short title>`.
- Each task file has `## Acceptance`. Run it. Logic tasks ship a GUT test in `tests/`; scene tasks say what to open and observe.
- When a task is done: delete its file from `tasks/`, tick it in `README.md`, commit.
- Sub-agents implement; the session reviews the diff and runs the test command itself before committing (see the `orchestrator` skill).
- Out-of-scope findings go to the `Queue / follow-ups` list in `README.md`, never into the current commit.

## Assets

Only CC0 / MIT / permissive assets. Record every pack in `docs/ASSETS.md` with source URL and licence when it is added. Kenney, Quaternius, KayKit, Poly Haven, ambientCG are CC0; Sketchfab models are per-model (check CC-BY vs CC0 and credit CC-BY in `docs/ASSETS.md`).

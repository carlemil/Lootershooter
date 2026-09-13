# HIGH — Godot project scaffold and folder layout

**Category:** infra
**Priority:** HIGH
**Status:** TODO
**Milestone:** M0
**Depends on:** none

## Files
- `project.godot` (new)
- `.gitignore` (modify — already exists)
- `.editorconfig` (new)
- `shared/.gdignore-placeholder` (new, empty marker file — delete once real scripts land)
- `CLAUDE.md` (modify — already exists; verify, do not rewrite)

## Issue
`D:/source/Lootershooter` contains only `tasks/`, `PLAN.md`, `CLAUDE.md`, `.gitignore` and `docs/`. There is no Godot project, so nothing can be opened, run or tested. Every later task (netcode, movement, ballistics) assumes a fixed folder layout where `shared/` runs on both client and server, `server/` is server-only, `client/` is client-only and all tunable numbers live in `data/*.json`. That layout has to exist and be enforced by convention before any code is written.

## Fix
- Create `project.godot` for Godot **4.4+** (`config_version=5`). Set `config/name="Lootershooter"`, `config/features=PackedStringArray("4.4", "Forward Plus")`, `run/main_scene="res://client/scenes/main.tscn"` is NOT yet valid — leave `run/main_scene` empty for now; task `net-server-bootstrap` sets it.
- In `project.godot` set:
  - `[physics] common/physics_ticks_per_second=60` (render/physics), and add a project setting `lootershooter/net/tick_rate=30` and `lootershooter/net/snapshot_rate=20` under a custom `[lootershooter]` section so both sides read the same constants.
  - `[rendering] renderer/rendering_method="forward_plus"`, `renderer/rendering_method.mobile="gl_compatibility"`.
  - `[input]` actions: `move_forward` (W), `move_back` (S), `move_left` (A), `move_right` (D), `jump` (Space), `sprint` (Shift), `crouch` (Ctrl), `prone` (Z), `lean_left` (Q), `lean_right` (E), `fire` (MB1), `aim` (MB2), `reload` (R), `interact` (F), `inventory` (Tab), `map` (M), `store` (B). Physical keycodes only, so layouts other than QWERTY still work.
- Create the directory skeleton exactly as plan section 2, each with a `.gitkeep`:
  `addons/`, `shared/`, `server/`, `client/`, `world/`, `data/`, `tests/`, `docker/`, `registry/`, `tools/`, `docs/`.
- Extend the existing `.gitignore` so it covers: `.godot/`, `.import/`, `export_presets.cfg` is **kept** (needed by CI) but `*.pck`, `*.x86_64`, `builds/`, `out/`, `*.translation`, `.DS_Store`, `learn/*.jsonl`, `data/bots_learned.json`.
- `.editorconfig`: `root = true`; for `*.gd` use `indent_style = tab`, `indent_size = 4`, `end_of_line = lf`, `insert_final_newline = true`, `charset = utf-8`; for `*.json`/`*.py`/`*.yml` use 2-space / 4-space spaces respectively.
- `CLAUDE.md` already exists and already states the points below; read it and only add what is missing:
  - Test command: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.
  - `shared/` = both sides, `server/` = server only, `client/` = client only; a script in `shared/` must never `preload` from `client/` or `server/`.
  - Server-authoritative: client sends only `{input_vector, look, buttons, tick}`; all damage and economy decisions happen on the server.
  - Shared sim is deterministic: fixed 30 Hz server tick, seeded RNG only, **no `randf()`/`randi()` in `shared/`** — use `RandomNumberGenerator` seeded from the match seed.
  - Bots feed the same input path as humans; no bot-only code paths in the sim.
  - No weapon/item numbers in scripts — everything in `data/*.json`.
  - One task = one commit.
- The git repo already exists; make no commit (the orchestrator commits).
- Do not add any addon yet; `infra-gut-tests` installs GUT.

## Acceptance
- `godot --headless --path D:/source/Lootershooter --quit` exits 0 with no script or project-settings errors.
- `ls` shows all 11 top-level directories from plan section 2 plus `project.godot`, `.gitignore`, `.editorconfig`, `CLAUDE.md`.
- `git status` shows `.godot/` as ignored.
- Opening `project.godot` in a text editor shows `lootershooter/net/tick_rate=30` and `lootershooter/net/snapshot_rate=20`.

# HIGH — GUT test harness and smoke test

**Category:** infra
**Priority:** HIGH
**Status:** TODO
**Milestone:** M0
**Depends on:** infra-godot-project

## Files
- `addons/gut/` (new, vendored addon)
- `tests/test_smoke.gd` (new)
- `tests/.gutconfig.json` (new)
- `tools/test.ps1` (new)
- `project.godot` (modify)

## Issue
Every logic task in this plan (ballistics, stamina, zone maths, economy) is specified with unit tests under `tests/`, but there is no test runner. Without GUT installed and a one-command CLI invocation, `/tdd` cannot do a red-green cycle and CI cannot verify anything. The command the whole repo standardises on is `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

## Fix
- Vendor the GUT addon (Godot 4.x branch, 9.x) into `addons/gut/`. Download from the Godot Asset Library or the GitHub release zip; copy only the `addons/gut` folder. Do not add it as a submodule.
- Enable the plugin in `project.godot` under `[editor_plugins] enabled=PackedStringArray("res://addons/gut/plugin.cfg")`.
- Create `tests/.gutconfig.json` with:
  - `"dirs": ["res://tests/"]`, `"include_subdirs": true`, `"prefix": "test_"`, `"suffix": ".gd"`,
  - `"log_level": 1`, `"should_exit": true`, `"should_exit_on_success": true`.
- Create `tests/test_smoke.gd` extending `GutTest` with:
  - `test_engine_version_is_4_4_or_newer()` — asserts `Engine.get_version_info()["major"] == 4 and Engine.get_version_info()["minor"] >= 4`.
  - `test_net_settings_present()` — asserts `ProjectSettings.get_setting("lootershooter/net/tick_rate") == 30` and `snapshot_rate == 20`.
  - `test_shared_dir_exists()` — asserts `DirAccess.dir_exists_absolute(ProjectSettings.globalize_path("res://shared"))`.
- Create `tools/test.ps1` (PowerShell, Windows 11 host):
  - Accepts optional `-Filter <substring>` mapped to GUT's `-gunit_test_name`, and optional `-Dir <res path>` mapped to `-gdir`.
  - Resolves the Godot binary from `$env:GODOT_BIN`, falling back to `godot`.
  - Runs `& $godot --headless --path $PSScriptRoot/.. -s addons/gut/gut_cmdln.gd -gconfig=res://tests/.gutconfig.json -gexit` and exits with the child process exit code so CI fails on a red test.
- Add a note in `CLAUDE.md` that new tests go in `tests/` mirroring the source folder (`tests/shared/…`, `tests/server/…`) with the `test_` prefix.
- Do not add a GitHub Actions workflow; the command above is the CI contract.

## Acceptance
- `godot --headless -s addons/gut/gut_cmdln.gd -gexit` from the project root runs and reports `3 passing` with exit code 0.
- `tools/test.ps1` run from PowerShell prints the same summary and `$LASTEXITCODE` is 0.
- Introducing a deliberately failing assert in `tests/test_smoke.gd` makes the command exit non-zero (verify, then revert).

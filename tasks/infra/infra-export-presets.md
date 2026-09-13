# HIGH — Export presets: client-windows, server-linux and server-windows

**Category:** infra
**Priority:** HIGH
**Status:** TODO
**Milestone:** M0
**Depends on:** infra-godot-project

## Files
- `export_presets.cfg` (new)
- `tools/export.ps1` (new)
- `.gitignore` (modify)

## Issue
The server ships as a Docker image built by exporting a dedicated-server binary, and the Dockerfile task hard-codes the preset name `server-linux`. Neither preset exists yet, so `godot --headless --export-release "server-linux"` fails and the container cannot be built. The client also needs a Windows preset for local playtesting, and the server must also export as a native Windows binary (`server-windows`) so a match server can run on a Windows box without Docker.

## Fix
- Create `export_presets.cfg` with exactly three presets, in this order:
  - `[preset.0]` `name="client-windows"`, `platform="Windows Desktop"`, `runnable=true`, `export_path="builds/windows/Lootershooter.exe"`, export filter `exclude_filter="server/*,tests/*,addons/gut/*,tasks/*,docs/*,registry/*,docker/*,tools/*"`, embed pck false.
  - `[preset.1]` `name="server-linux"`, `platform="Linux"`, `runnable=true`, `export_path="builds/linux/server.x86_64"`, and in its options set `binary_format/architecture="x86_64"` and **dedicated server mode**: `application/export_type` / `dedicated_server=true` (Godot 4.7 Linux preset key `binary_format/embed_pck=false`, `texture_format/*=false` for all, and the preset option `dedicated_server` set so textures/audio are stripped).
  - `server-linux` `exclude_filter="client/*,tests/*,addons/gut/*,tasks/*,docs/*,tools/*,registry/*,docker/*,world/**/*.png,world/**/*.jpg"`.
  - `[preset.2]` `name="server-windows"`, `platform="Windows Desktop"`, `runnable=true`, `export_path="builds/windows-server/server.exe"`, `binary_format/architecture="x86_64"`, `application/console_wrapper_icon`/console subsystem enabled so logs show in a terminal, dedicated-server mode and the same `exclude_filter` as `server-linux`. It must launch with `server.exe --headless -- --port=7777`.
- Keep `data/*.json` and `world/*.tscn` **included** in both presets — the server needs map collision, navmesh and item data.
- `export_presets.cfg` is committed (remove it from `.gitignore` if present); `builds/` is ignored.
- Create `tools/export.ps1`:
  - Params `-Preset <client-windows|server-linux|server-windows>` (default all three) and `-Debug` switch.
  - Resolves Godot via `$env:GODOT_BIN` else `godot`; ensures the target folder from the preset's `export_path` exists (`New-Item -ItemType Directory -Force`).
  - Runs `& $godot --headless --path <project root> --export-release "<preset>" <abs export path>` (`--export-debug` when `-Debug`).
  - Fails loudly with a clear message when export templates for that platform are missing (check the exit code and stderr for "No export template found").
- Document in `CLAUDE.md`: export templates must match the engine version; the Docker build installs them in stage 1 so the preset name must never change.

## Acceptance
- `godot --headless --path . --export-release "server-linux" builds/linux/server.x86_64` produces a binary plus `server.pck` (on a machine with Linux export templates installed).
- `tools/export.ps1 -Preset client-windows` produces `builds/windows/Lootershooter.exe`.
- `tools/export.ps1 -Preset server-windows` produces `builds/windows-server/server.exe`; running it with `--headless -- --port=7777` starts listening on UDP 7777 (verify with `Get-NetUDPEndpoint -LocalPort 7777`).
- `grep -c 'name="' export_presets.cfg` returns 3 and the names are exactly `client-windows`, `server-linux` and `server-windows`.
- `git status` shows `builds/` untracked-and-ignored, `export_presets.cfg` tracked.

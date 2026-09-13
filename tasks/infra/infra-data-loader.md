# HIGH — Data loader autoload and schema checks

**Category:** infra
**Priority:** HIGH
**Status:** TODO
**Milestone:** M0
**Depends on:** infra-gut-tests

## Files
- `shared/data/game_data.gd` (new, autoload `GameData`)
- `data/cartridges.json` (new)
- `data/weapons.json` (new)
- `data/items.json` (new)
- `data/prices.json` (new)
- `data/bots.json` (new)
- `tests/shared/test_game_data.gd` (new)
- `project.godot` (modify)

## Issue
A hard rule of this project is that no weapon, item or bot number lives in a script — ballistics, the wrist store and bot profiles all read `data/*.json`. Today there is neither data nor a loader, and nothing checks that a weapon's `cartridge` key actually names a cartridge that exists, which would fail at runtime deep inside the projectile sim. The loader must run on both client and server (it lives in `shared/`) and must fail loudly at boot, not at the first shot.

## Fix
- `shared/data/game_data.gd`, `class_name GameDataService extends Node`, registered as the autoload **`GameData`** in `project.godot` (first autoload, before any net singleton).
- `_ready()` calls `load_all()`, which reads each file with `FileAccess.get_file_as_string` + `JSON.parse_string`, stores them in typed dictionaries, then calls `validate()`.
- Public API (all read-only, return `{}` / `[]` on unknown keys after pushing an error):
  - `get_cartridge(id: String) -> Dictionary`
  - `get_weapon(id: String) -> Dictionary`
  - `get_item(id: String) -> Dictionary`
  - `get_price(id: String) -> int`
  - `get_bot_profile(id: String) -> Dictionary`
  - `all_weapons() -> PackedStringArray`, `all_items() -> PackedStringArray`
  - `load_all(dir: String = "res://data") -> Array[String]` returns the list of validation errors so tests can call it on a fixture dir without touching the autoload state.
- File shapes (top-level object keyed by id, never an array — id lookups must be O(1)):
  - `cartridges.json` per id: `{"name", "mass_g", "muzzle_velocity", "drag_k", "base_damage", "pellets"}`. Seed it with the plan's section 3.4 values: `556x45` 990, `762x39` 715, `762x51` 850, `762x54r` 830, `30carbine` 600, `45acp` 260, `9x18` 320, `762x25` 450, `12ga_buck` 400 with `"pellets": 8`, `38spl` 260.
  - `weapons.json` per id: `{"name","class","cartridge","rpm","fire_modes","mag_size","reload_s","ads_time_s","recoil":{...},"spread":{...},"ergonomics"}`. Seed with **three** weapons only (`m16a1`, `ak47`, `m1911a1`); the full list is task `gun-catalog-vietnam`.
  - `items.json` per id: `{"name","category","slot","weight","stack"}` — seed with the three weapons above plus `bandage`, `flak_vest_1`, `ammo_556x45`.
  - `prices.json`: flat `{"<item_id>": <int dollars>}` for every id in `items.json`.
  - `bots.json`: `{"profiles": {"rusher": {"weights": {...}}, ...}, "difficulties": {"easy": {"reaction_ms": 700, "aim_sigma_deg": 4.0}, ...}}`. Seed the five profiles named in plan 3.7 with placeholder weights.
- `validate()` collects errors (never `assert`s) into an `Array[String]` and, when non-empty, calls `push_error` per line and `OS.crash`-free `get_tree().quit(1)` **only when `OS.has_feature("dedicated_server")`** — the editor should show errors, the server should refuse to boot. Checks:
  1. Every `weapons[*].cartridge` exists in `cartridges`.
  2. Every weapon id exists in `items` and every item id exists in `prices`.
  3. `rpm > 0`, `mag_size > 0`, `muzzle_velocity > 0`, `mass_g > 0`, `weight >= 0`.
  4. `fire_modes` is a non-empty subset of `["semi","burst","auto","bolt","pump"]`.
  5. `items[*].slot` is one of `primary, sidearm, melee, throwable, gadget, armor, helmet, backpack, consumable, ammo, attachment`.
- No `randf()` and no game logic in this file — it is a pure loader.

## Acceptance
- GUT file `tests/shared/test_game_data.gd`:
  - `test_every_weapon_cartridge_exists()` — for each id in `all_weapons()`, `get_cartridge(get_weapon(id).cartridge)` is non-empty.
  - `test_every_item_has_a_price()` — `get_price(id) > 0` for every id in `all_items()`.
  - `test_cartridge_values()` — `get_cartridge("556x45").muzzle_velocity == 990.0` and `get_cartridge("12ga_buck").pellets == 8`.
  - `test_validate_catches_dangling_cartridge()` — writes a temp fixture dir under `user://` with a weapon referencing `"nope"`, calls `load_all(fixture)` and asserts the returned error array has exactly 1 entry mentioning `nope`.
- `godot --headless -s addons/gut/gut_cmdln.gd -gexit` is green.
- Booting the headless server with a deliberately broken `data/weapons.json` exits non-zero with the error printed (verify, then revert).

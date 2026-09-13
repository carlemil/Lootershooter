# MEDIUM — Import and organise the free asset kits

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-terrain-blockout

## Files
- `world/kits/` (new)
- `world/kits/KITS.md` (new)
- `world/kits/building_part.gd` (new)
- `tools/import_check.gd` (new)

## Issue
Every remaining world task (town, hamlets, outposts, foliage, bridge/tunnels) needs a shared library of modular pieces with consistent scale, pivots, collision and LODs. Dropping raw downloads into the project gives mismatched units, missing collision and no licence record — and the licences must be tracked, since some Sketchfab weapon models are CC-BY rather than CC0.

## Fix
- Create `world/kits/<pack>/` folders and import these specific free packs (verify the licence at download time):
  - **Kenney** (CC0): *City Kit*, *Survival Kit*, *Furniture Kit*, *Tower Defense* (sandbags), *Nature Kit*, *UI Pack*, *Game Icons*, *Input Prompts*, *Car Kit*, *Blaster Kit* (weapon placeholders).
  - **Quaternius** (CC0): *Ultimate Nature Pack*, *Ultimate Buildings*, *Ultimate Vehicles*, *Universal Animated Characters*.
  - **KayKit** (CC0): bits/dungeon/character packs for props and kitbash parts.
  - **Poly Haven** (CC0): foliage and prop models, HDRIs for `world-lighting-variants`.
  - **ambientCG** (CC0): ground, concrete, wood, corrugated-metal materials.
- Normalise on import: 1 unit = 1 metre, Y-up, pivot at the piece's floor-centre, `-Z` forward. Re-export or apply an import-scale in the `.import` settings rather than scaling nodes in scenes.
- Give every building piece a trimesh `StaticBody3D` collision (`use_collision` in the import dock, or a `-col` suffixed mesh) and layer it on the `world` physics layer. Foliage gets **no** collision except tree trunks (capsule).
- LODs: rely on Godot 4's automatic mesh LOD; for the heaviest foliage use Terrain3D's instancer with its own LOD settings. Set `visibility_range_end` on small props (crates, stalls) at 120 m.
- `world/kits/building_part.gd`: a tiny shared script for kit pieces exposing `material_type: String` (wood / bamboo / sheet_metal / brick / concrete) so `gun-penetration-ricochet` can look up penetration values from the surface it hit, and `is_climbable: bool` for vault/mantle detection.
- `world/kits/KITS.md`: a table of pack → source URL → licence → date downloaded → what it is used for. Any CC-BY asset gets an attribution line here and in the eventual credits screen; prefer a CC0 substitute where one exists.
- `tools/import_check.gd`: an editor/headless script that walks `world/kits/`, reporting any mesh with no collision, any piece whose bounding box suggests the wrong scale (a "house" under 2 m tall), and any material without a `material_type`.

## Acceptance
- `world/kits/` contains at least the Kenney City/Survival/Nature kits, Quaternius Nature + Buildings, and the ambientCG material set, each in its own folder.
- `world/kits/KITS.md` lists every imported pack with a licence and URL; no pack is present in the folder without a row.
- Running `godot --headless -s tools/import_check.gd` reports zero scale errors and zero building pieces without collision.
- Dropping any three pieces into a test scene at the same Y places them flush on the ground with no gaps at the pivot.
- Project import time from a clean `.godot/` folder stays under 5 minutes.

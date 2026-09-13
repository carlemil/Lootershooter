# MEDIUM — Biome dressing: paddies, rubber plantation, jungle

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-terrain-blockout, world-kits-import

## Files
- `world/maps/mekong/biomes/paddies.tscn` (new)
- `world/maps/mekong/biomes/plantation.tscn` (new)
- `world/maps/mekong/biomes/jungle.tscn` (new)
- `world/maps/mekong/mekong.tscn` (modify)
- `shared/world/concealment_volume.gd` (new)

## Issue
The terrain blockout has painted biomes but no vegetation, so 80% of the map is open ground with nothing to break line of sight and none of the plan's concealment rules exist — notably that crawling in paddy water hides you from bots' vision beyond 40 m. Foliage also has to be instanced rather than placed as nodes, or the 2 km map will not hold frame rate.

## Fix
- Use the **Terrain3D instancer** for all high-count foliage (grass, paddy rice, shrubs, bamboo clumps, palms) with the addon's LOD and density settings — never thousands of scene nodes. Meshes from **Quaternius *Ultimate Nature Pack***, **Kenney *Nature Kit*** and **Poly Haven** models (all CC0).
- `paddies.tscn`: a dike grid of low earth walls (0.6–1.0 m, walkable tops, `is_climbable`) dividing flooded fields; rice instanced densely inside the fields; a few water buffalo troughs and irrigation gates as props. Water depth 0.3–0.5 m so it slows movement (`move-swim`'s shallow rules) without swimming.
- `plantation.tscn`: rubber trees instanced in **regular rows** with ~5 m spacing along the east slope — the visual gimmick is that sight-lines exist down the rows and nowhere else. Tapping cups and a small processing shed for cover.
- `jungle.tscn`: dense canopy of tall trees with trunk capsule collision, bamboo clumps, undergrowth, fallen logs, and 2–3 clearings so fights are possible. Hills from the blockout stay walkable — keep slopes under the controller's limit on the main routes and use cliffs only as deliberate walls.
- `shared/world/concealment_volume.gd`: an `Area3D` (`concealment` group) with `@export var conceal_beyond_m := 40.0` and `@export var requires_prone := true`. Placed over paddy fields and dense undergrowth. `bot-perception` queries it: a player inside, prone (or crouched where `requires_prone` is false), is not detected by bots beyond `conceal_beyond_m`. Humans get the corresponding visual concealment for free from the foliage.
- Keep foliage out of a 3 m corridor either side of the road splines and out of building footprints so navmesh and driving still work; use the instancer's exclusion painting.
- Budget: set per-biome instance densities so a 1080p mid-range GPU holds ≥ 60 fps standing in the densest jungle; tune `visibility_range_end` per foliage tier (grass 60 m, shrubs 120 m, trees 400 m).

## Acceptance
- Open `mekong.tscn`: all three biome scenes load; paddies, plantation rows and jungle are visually distinct from ground level and from 300 m up.
- Rubber trees are in recognisable straight rows (stand at a row end and see ≥ 100 m down the gap).
- Foliage is instanced: `get_tree().get_node_count()` for the map stays under 5000 despite the density.
- Concealment: ≥ 6 `concealment` volumes cover the paddy fields; a prone player inside one is not detected by a bot at 60 m but is at 30 m (verify once `bot-perception` exists; until then assert the volume's `is_concealed(pos, stance, distance)` helper directly).
- No foliage instance intersects a road spline corridor or a building footprint.
- ≥ 60 fps at 1080p standing in the jungle, ≥ 90 fps in the paddies.

# HIGH — Terrain3D 2 km blockout: heightmap, biome splat, roads, water

**Category:** world
**Priority:** HIGH
**Status:** TODO
**Milestone:** M6
**Depends on:** infra-godot-project

## Files
- `world/maps/mekong/mekong.tscn` (new)
- `world/maps/mekong/terrain/` (new)
- `world/maps/mekong/roads.tscn` (new)
- `world/maps/mekong/water.tscn` (new)
- `world/world_root.gd` (new)
- `tools/bake_map.ps1` (new)

## Issue
There is no map. Everything downstream — loot markers, zone bounds (map half-extent 1000 m), hot-zone placement, the smuggler truck's road splines, bot navmesh, swimming volumes — assumes a 2 km × 2 km Terrain3D world with the plan's six biomes laid out. This task produces the blockout only: correct scale, readable terrain shapes, painted biome regions, road splines and water volumes. Buildings arrive in the later world tasks.

## Fix
- Install the **Terrain3D** GDExtension (MIT, pick the release built for Godot 4.7, from the Godot asset library / tokisan.com) into `addons/terrain3d/`; commit the addon but not its build artefacts.
- `world/maps/mekong/mekong.tscn`: root `Node3D` with `world_root.gd`, a `Terrain3D` node with region size 1024 and **4 regions covering 2048 m × 2048 m centred on the origin** (so world X/Z run −1024…+1024 and `ZoneMath.map_half_extent = 1000` leaves a 24 m shoulder). Vertical range roughly −5 m (canal beds) to 140 m (jungle hills).
- Sculpt the heightmap to the plan's layout: flat flooded rice paddies in the south-west quadrant (elevation 2–6 m, dike grid), jungle hills along the north-east (60–140 m), a rubber plantation on the gentle east slope (rows), a river running north-south with branching canals through the paddies, the town on the west bank near the bridge, hamlets scattered, three outposts on high ground. Save a reference top-down PNG at `world/maps/mekong/layout.png`.
- Paint the Terrain3D splat/control map with texture slots: 0 mud/paddy, 1 grass, 2 jungle floor, 3 dirt road, 4 sand/riverbank, 5 concrete/town. Textures from **ambientCG** and **Poly Haven** (CC0), imported at 2K with albedo/normal/roughness into `world/textures/`.
- `roads.tscn`: a `Node3D` named `Roads` in the group `roads`, containing `Path3D` splines for the main north-south highway, the bridge approach, the town grid, and two dirt tracks to the outposts. Each `Path3D` gets a `road_width_m` metadata value. These are consumed by `zone-smuggler-truck` and `world-navmesh-bake`.
- `water.tscn`: `Area3D` volumes (`water` group) for the river, each canal and the flooded paddies, each with a `water_depth_m` metadata and a flat water mesh at the volume's top. `move-swim` reads the group; paddies are shallow (0.4 m — prone hides you, no swimming), the river deep (3 m).
- `world/world_root.gd`: exposes `get_spawn_bounds()`, `get_roads()`, `get_water_volumes()` and holds the `loot_*` marker groups so the money spawner has one entry point. Nothing gameplay-specific lives in the scene itself.
- `tools/bake_map.ps1`: one command to re-import terrain data and (later) re-bake the navmesh, so this is repeatable.

## Acceptance
- Open `world/maps/mekong/mekong.tscn` in the editor and F6: terrain loads with no errors, the playable area measures 2048 m across (verify with two `Marker3D`s at ±1024 on X), and no hole in the heightmap.
- All six biomes are visually distinguishable from a top-down camera at 1500 m, matching `layout.png`.
- `Roads` contains ≥ 5 `Path3D` nodes, all in the `roads` group; walking the highway spline end to end stays on painted road texture.
- `water` group contains ≥ 6 `Area3D` volumes; a player body entering the river triggers the area, and the paddy volumes report a depth under 0.5 m.
- Frame time on a mid-range GPU at 1080p with no props ≤ 8 ms (blockout budget headroom for the kits).

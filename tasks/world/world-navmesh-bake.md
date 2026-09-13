# MEDIUM — Navmesh bake, nav links and the road graph

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-town, world-hamlets, world-outposts, world-rivers-bridge-tunnels, world-paddies-plantation-jungle

## Files
- `world/maps/mekong/navigation.tscn` (new)
- `world/nav/road_graph.gd` (new)
- `world/nav/road_graph.tres` (new)
- `tools/bake_map.ps1` (modify)
- `tests/test_road_graph.gd` (new)

## Issue
Bots cannot move: there is no baked navigation for the 2 km map, no links for the things that are not walkable surfaces (vaults, ladders, tunnel hatches), and no road graph for bot driving. Baking 4 km² as one region is also too slow to iterate on and too big for a single `NavigationRegion3D`.

## Fix
- `navigation.tscn`: split the map into a **4 × 4 grid of 512 m `NavigationRegion3D` tiles**, each baking only the geometry in its cell (source geometry mode "group explicit", group `navmesh_source`). Tiles stitch at their edges via matching cell size/height, so keep bake settings identical: agent radius 0.4 m, height 1.8 m, max slope 45°, cell size 0.25 m, cell height 0.2 m.
- Put building interiors, the bridge deck and the tunnel network in the `navmesh_source` group; exclude foliage, water volumes deeper than 1.0 m, and small props.
- Bake a **separate crouch-height region set** for the tunnels (agent height 1.3 m) as its own `NavigationRegion3D` on navigation layer 2, so surface bots do not path into a 1.4 m tunnel standing up. Bots switch layers when they use a tunnel link.
- `NavigationLink3D`s (group `nav_links`), one per traversal that the mesh cannot express: every ladder (town fire escapes, watchtowers, stilt houses), every vaultable ledge ≤ 1.5 m marked `is_climbable`, and every tunnel entrance (bidirectional, connecting layer 1 ↔ layer 2). Set a `travel_cost` higher than walking so bots prefer normal routes unless the link is a real shortcut.
- `world/nav/road_graph.gd` + baked `road_graph.tres`: build an `AStar3D` from the `roads` group's `Path3D` splines — sample each spline every 10 m into nodes, connect consecutive samples, and connect samples from different splines within 12 m of each other (junctions). Expose `nearest_node(pos)`, `path_between(a, b) -> PackedVector3Array` and `road_width_at(node)` for `bot-vehicles-teams`.
- `tools/bake_map.ps1`: add a `-Nav` switch that re-bakes all 16 tiles plus the tunnel region headlessly and re-generates `road_graph.tres`, printing per-tile bake time.

## Acceptance
- GUT test `tests/test_road_graph.gd`: `path_between` returns a connected path from the town road node to the far outpost road node with no gap between consecutive points larger than 15 m; `nearest_node` for a point 5 m off the highway returns a node within 12 m; the graph has ≥ 200 nodes and is a single connected component.
- Full bake via `tools/bake_map.ps1 -Nav` completes without errors; each tile bakes in under 60 s.
- In-editor: dropping a `NavigationAgent3D` at the town centre and targeting a hamlet 900 m away returns a path that crosses the bridge (not a straight line through the river).
- Link counts: `nav_links` group contains one link per ladder, per marked vaultable ledge and per tunnel entrance; every tunnel entrance link connects navigation layer 1 to layer 2.
- No navmesh surface exists over water deeper than 1.0 m or on slopes above 45°.

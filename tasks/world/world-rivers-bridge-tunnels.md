# MEDIUM — River, canals, bridge and the tunnel network

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-terrain-blockout, world-kits-import, world-town

## Files
- `world/kits/props/tunnel_segment.tscn` (new)
- `world/maps/mekong/bridge.tscn` (new)
- `world/maps/mekong/tunnels.tscn` (new)
- `world/maps/mekong/water.tscn` (modify)
- `world/maps/mekong/mekong.tscn` (modify)

## Issue
The river currently splits the map with no way across but swimming, which makes the east half a dead zone, and the plan's signature flank route — a Cu-Chi-style tunnel network linking the town, a hamlet and an outpost — does not exist. Tunnels are also the cheapest way to give the map vertical/hidden space without more buildings.

## Fix
- `bridge.tscn`: a single road bridge carrying the highway spline over the river — 8 m wide, 60–80 m span, concrete piers, a guard post at each end built from sandbags. Sight-lines along the deck make it the map's natural chokepoint; add two under-deck maintenance ledges reachable by ladder so it is not a pure killbox. Road spline continuity: the `Path3D` from `roads.tscn` must run unbroken across the deck for vehicles and bot driving.
- `tunnel_segment.tscn`: a 4 m modular piece (straight, 90° corner, T-junction, entrance shaft, chamber variants) with 1.4 m interior height — **crouch-only**, no sprinting, `material_type = "earth"`. Kitbash from Kenney/KayKit parts with an ambientCG dirt material. Each entrance is a concealed hatch under a hut floor, inside a bunker, or in a paddy dike.
- `tunnels.tscn`: 300–500 m of connected segments with **at least 5 entrances** linking the town, two hamlets, one outpost and one jungle clearing, plus 2–3 small chambers holding `loot_hamlet`-tier markers. Include one dead end and one loop so the network is not a single corridor.
- Tunnel lighting: near-dark, requiring the flashlight gadget or a flare; add faint entrance light shafts so the player can find their way out.
- Register every entrance with a `NavigationLink3D` pair (surface ↔ tunnel) tagged for `world-navmesh-bake` so bots can use the network; mark hatch meshes `is_climbable` for the ladder-down animation.
- Canals (`water.tscn` modify): 3–5 navigable canals 4–8 m wide, 1.5–2.5 m deep, cutting through the paddies to the river, each with its own `Area3D` water volume and `water_depth_m`; add small footbridges (1 m wide planks) at four crossings so infantry have options besides swimming.
- Audio hooks: tunnels get a reverb bus area, water volumes a splash surface tag for `audio-footsteps-surfaces-vehicles-ambience`.

## Acceptance
- Open `mekong.tscn` and cross the bridge on foot and (once vehicles exist) by road spline without falling through geometry; the highway `Path3D` is continuous across the span.
- Tunnels: ≥ 5 entrances, all enterable; walking the network end to end takes ≥ 300 m of travel; standing up inside is impossible (forced crouch) and there are ≥ 2 chambers with loot markers.
- Every tunnel entrance has a matching `NavigationLink3D` (count links == count entrances × 1) in the `nav_links` group.
- Canals: ≥ 3 water volumes deeper than 1.5 m, each triggering swimming; the four footbridges are crossable without entering the water.
- No water volume overlaps a building interior, and the river volume does not extend under the bridge deck's walkable surface.

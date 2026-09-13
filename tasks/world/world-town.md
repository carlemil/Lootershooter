# MEDIUM — Town: market, temple, colonial blocks, safes

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-kits-import, econ-money-piles, econ-safes

## Files
- `world/maps/mekong/town.tscn` (new)
- `world/maps/mekong/mekong.tscn` (modify)
- `world/kits/props/market_stall.tscn` (new)

## Issue
The town is the map's hot drop and, with the outposts, must hold roughly 40% of the world's cash value — but nothing is built. The plan calls for a market, a temple, and colonial blocks of 3–4 floors on the west bank by the bridge, with the only safes on the map (plus the outposts) and enough interior space that indoor fights and vertical play actually happen.

## Fix
- Build `town.tscn` as a `Node3D` instanced into `mekong.tscn` at the west-bank site from the blockout, roughly 400 m × 400 m.
- Content, kitbashed from **Kenney *City Kit*** (colonial blocks, walls, windows, doors), **Quaternius *Ultimate Buildings*** (shells), **KayKit** bits and **Kenney *Furniture Kit*** (interiors):
  - 8–12 colonial blocks of 3–4 floors, each with a **enterable ground floor and at least one interior stair or ladder to the roof**; balconies overlooking the main street.
  - A covered market of 20+ `market_stall.tscn` pieces in two rows, low walls and awnings for cover.
  - A temple with a raised platform and a courtyard — the visual landmark, visible from the hills.
  - A street grid connected to the `Roads` splines from the blockout, with the bridge approach on the east edge.
- Loot markers (`Marker3D`, one per plausible hiding spot — shelves, counters, back rooms, roof corners):
  - `loot_town` group: **≥ 60 markers** spread across the blocks and market, at least 4 per enterable building, never inside geometry (check with a 0.3 m sphere).
  - `loot_safe` group: **4 markers**, all in interior back rooms or the temple, at least 40 m apart so one player cannot crack two safely.
- Every building piece carries a `material_type` from `building_part.gd` (brick/concrete for colonial blocks, wood/sheet_metal for stalls) so penetration works correctly indoors.
- Mark climbable ledges (window sills, low walls ≤ 1.5 m) with `is_climbable = true` for `move-jump-vault-ladder`; add `Ladder` areas on the two fire-escape ladders.
- Keep the interiors navigable: no doorway narrower than 1.1 m, no interior step taller than 0.3 m, so the navmesh bake produces a connected indoor surface.
- Occlusion: add `OccluderInstance3D` bake for the block exteriors, and set `visibility_range_end` on interior furniture at 60 m.

## Acceptance
- Open `world/maps/mekong/town.tscn`: it loads standalone with no missing-resource errors.
- Counts: ≥ 8 multi-floor buildings, every one enterable with roof access; ≥ 20 market stalls; exactly 4 `loot_safe` markers; ≥ 60 `loot_town` markers (verify with `get_tree().get_nodes_in_group("loot_town").size()` from a test scene).
- Run `mekong.tscn` and walk the town: no marker floats in mid-air or clips inside a wall, every stair and ladder is usable, and you can get from street to roof in three of the blocks without vaulting through geometry.
- Money spawner with the town instanced reports town + outpost value at 38–45% of the world total (the check added in `econ-money-piles`).
- Client frame time in the town at 1080p ≤ 12 ms with the blockout budget.

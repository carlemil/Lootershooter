# MEDIUM — Three military outposts with high-tier cash

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-kits-import, econ-money-piles, econ-safes

## Files
- `world/kits/props/sandbag_wall.tscn` (new)
- `world/kits/props/bunker.tscn` (new)
- `world/kits/props/watchtower.tscn` (new)
- `world/maps/mekong/outposts/outpost_01.tscn` … `outpost_03.tscn` (new)
- `world/maps/mekong/mekong.tscn` (modify)

## Issue
The map has no high-risk/high-reward locations outside the town, so a squad that skips the hot drop has nowhere to spend the mid-game building a $3000 loadout. The plan specifies three outposts with sandbags, a bunker, a watchtower and the map's best cash ($200–500 piles plus safes) — these plus the town carry ~40% of the world's value.

## Fix
- Build the three reusable pieces from **Kenney *Tower Defense*** (sandbags), **Kenney *Survival Kit*** / **City Kit** (corrugated huts, crates) and **KayKit** bits, with ambientCG concrete and sandbag materials:
  - `sandbag_wall.tscn`: 4 m straight and a corner variant, 1.2 m tall (chest-high cover you can lean and vault over — `is_climbable = true`), `material_type = "sandbag"` mapping to low penetration.
  - `bunker.tscn`: half-buried concrete, one entrance, two firing slits, interior 4 × 6 m, `material_type = "concrete"` (non-penetrable per the plan's material table).
  - `watchtower.tscn`: 8–10 m wooden tower with a ladder and a railed platform — a sniper perch that is deliberately exposed.
- Three outpost scenes, 80–120 m across, each with: a perimeter of sandbag walls with two gaps, 1 bunker, 1–2 watchtowers, a supply area of crates and barrels, a radio mast, a vehicle bay connected to a road spline, and sight-lines broken by the layout so the towers are not simply dominant.
- Place them per the blockout: one on a jungle hill overlooking the paddies, one guarding the bridge, one on the plantation ridge. All on high ground, ≥ 400 m from the town.
- Loot markers: `loot_outpost` group, **≥ 10 per outpost** (≥ 30 total) in the bunker, supply crates, tower platforms and the vehicle bay; plus **1 `loot_safe` marker per outpost**, inside the bunker (so cracking one means committing to the worst room to be caught in).
- Navmesh-friendliness: bunker entrance ≥ 1.2 m wide, tower ladders registered as `Ladder` areas for the `NavigationLink3D`s in `world-navmesh-bake`, sandbag gaps wide enough for a bot to path through without a link.
- Add `OccluderInstance3D` on the bunker and huts; `visibility_range_end` 150 m on crates and barrels.

## Acceptance
- Open each outpost scene standalone: loads with no missing resources.
- Counts against the loaded `mekong.tscn`: exactly 3 outpost instances; ≥ 10 `loot_outpost` markers each (≥ 30 total); exactly 3 `loot_safe` markers from outposts (7 map-wide with the town's 4).
- Walk each outpost: every watchtower ladder is climbable to the platform, the bunker is enterable and its firing slits are shootable through but not walkable, and sandbag walls can be vaulted.
- Outpost piles roll $200–500 and outpost safes $800–1500 per `data/loot_tiers.json`.
- Town + outposts together account for 38–45% of total spawned value (the `econ-money-piles` check).

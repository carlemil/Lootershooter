# MEDIUM — Five hamlets of stilt houses with loot markers

**Category:** world
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M6
**Depends on:** world-kits-import, econ-money-piles

## Files
- `world/kits/props/stilt_house.tscn` (new)
- `world/kits/props/hut.tscn` (new)
- `world/maps/mekong/hamlets/hamlet_01.tscn` … `hamlet_05.tscn` (new)
- `world/maps/mekong/mekong.tscn` (modify)

## Issue
Between the town and the outposts the map is empty, so mid-game rotations have no cover and no small-value loot ($50–150 per hamlet pile). The plan wants five hamlets of stilt houses scattered across the paddies and riverbanks — the low-tier, low-risk loot tier that keeps a poor player moving rather than dying broke.

## Fix
- Build two reusable pieces first, kitbashed from **Kenney *Survival Kit*** and **Quaternius *Ultimate Buildings*** with **ambientCG** wood/thatch/corrugated materials:
  - `stilt_house.tscn`: raised floor 1.2–1.8 m on posts, one room, a ladder or ramp up (`Ladder` area or a `is_climbable` ramp), open under-floor space to fight in, thatch or sheet-metal roof. `material_type` = `wood` for walls, `sheet_metal` for roofs — both penetrable, which is the point of a hamlet fight.
  - `hut.tscn`: ground-level single room, doorway, no window glass.
- Five hamlet scenes, each 60–100 m across with 6–10 buildings, a dirt track connecting to the nearest road spline, a well or water trough, fences, drying racks and a few Quaternius palms/banana plants for cover. Vary the layouts — do not instance the same hamlet five times.
- Placement across the blockout: two in the rice paddies (on dikes, with the under-floor space over shallow water), one on the river bank near the canals, one at the rubber plantation edge, one on a jungle-hill shoulder. None within 250 m of the town or an outpost.
- Loot markers: `loot_hamlet` group, **≥ 6 per hamlet** (≥ 30 total), placed in house interiors, under stilt floors and beside wells — never floating, never inside a mesh. No `loot_town` or `loot_safe` markers in hamlets.
- Ensure every building is enterable and the interior is navmesh-connectable (doorway ≥ 1.1 m, ramp slope ≤ 30°), and that the under-stilt space is tall enough (≥ 1.1 m) to crouch-walk through.
- Instance all five into `mekong.tscn` under a `Hamlets` node; set `visibility_range_end` on small props at 120 m.

## Acceptance
- Open each of the five hamlet scenes standalone: loads with no missing resources.
- Counts, verified from a test scene against the loaded `mekong.tscn`: exactly 5 hamlet instances, each with ≥ 6 `Marker3D`s in the `loot_hamlet` group (≥ 30 total), and zero `loot_safe` markers among them.
- Walk each hamlet in-game: every house can be entered, every ladder/ramp climbed, and you can crouch under a stilt house without clipping.
- No hamlet is within 250 m of the town centre or any outpost (measure in the editor).
- Money piles spawned at hamlet markers all roll $50–150 (the tier from `data/loot_tiers.json`).

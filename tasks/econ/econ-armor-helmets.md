# MEDIUM — Flak vests and helmets with tiers and durability

**Category:** econ
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-store-catalog, econ-inventory, gun-hitzones-damage

## Files
- `shared/combat/armor.gd` (new)
- `data/items.json` (modify)
- `shared/player_state.gd` (modify)
- `tests/test_armor.gd` (new)

## Issue
Flak vests (I/II/III) and helmets (M1 steel, M1 with visor) are in the store at $400–1200 but have no effect: `gun-hitzones-damage` applies raw zone multipliers with no armor term. The design wants tiered percentage reduction, durability lost per hit, and a tier-II helmet that stops pistol rounds outright — which is what makes the $1200 purchase readable to the player.

## Fix
- Add armor entries to `data/items.json`: `{"kind": "armor"|"helmet", "tier": 1..3, "reduction": 0.25|0.40|0.55, "durability": 120|200|300, "weight_kg", "stops_pistol": bool}`. Helmet tier II+ sets `stops_pistol = true`. No numbers in scripts.
- `shared/combat/armor.gd`, `class_name Armor` (`RefCounted`): holds `item_id`, `tier`, `durability_left`. `absorb(damage: float, cartridge: Dictionary) -> Dictionary` returns `{final_damage, durability_lost, broke}`.
  - Rule: if `stops_pistol` and the cartridge's `class == "pistol"` and the hit zone is HEAD → `final_damage = 0`, durability loss = the full blocked damage.
  - Otherwise `absorbed = damage * reduction`, `final_damage = damage - absorbed`, `durability_lost = absorbed` (rounded up).
  - When `durability_left` hits 0 the piece breaks: it is removed from the slot, stops reducing anything, and emits `armor_broke(peer_id, slot)` for the HUD/audio. A broken vest occupies no weight.
  - Vest covers CHEST and STOMACH; helmet covers HEAD and NECK; limbs are never armored. Pick the piece by hit zone, apply at most one.
- `shared/player_state.gd`: add `armor: Armor` and `helmet: Armor`, set/cleared when the armor/helmet inventory slot changes. Replicate `tier` and a 0–1 durability fraction to the owning client (HUD) and only the tier to others (visual model swap).
- Wire `absorb` into the existing damage pipeline **after** the hit-zone multiplier and before HP subtraction, so the order is `base × energy_fraction × zone_mult → armor → HP`.
- Armor weight feeds `move-stamina`'s weight scaling; tier III is heavy enough to be a real trade-off.

## Acceptance
- GUT test `tests/test_armor.gd`:
  - Tier II vest (0.40, 200 durability) taking a 100-damage chest hit → `final_damage == 60`, `durability_left == 160`.
  - Repeated hits break the vest exactly when durability reaches 0; the next hit takes full damage and `armor_broke` fired once.
  - A .45 ACP head hit against a tier II helmet deals 0 damage and costs durability; the same hit against a tier I helmet deals reduced, non-zero damage.
  - A limb hit is unaffected by any armor.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

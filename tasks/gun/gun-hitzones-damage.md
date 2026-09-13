# HIGH — Hurtboxes, zone multipliers and armor durability

**Category:** gun
**Priority:** HIGH
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-cartridge-sim

## Files
- `shared/combat/hitzones.gd` (new)
- `shared/combat/damage.gd` (new)
- `shared/player/hitboxes.tscn` (new)
- `server/combat/damage_resolver.gd` (new)
- `tests/shared/test_damage.gd` (new)

## Issue
Projectiles fly but nothing takes damage: the player capsule has no hurtboxes and there is no damage formula. The design's formula is fixed — `damage = base × energy_fraction × zone multiplier × armor` with head 2.4, neck 1.5, chest 1.0, stomach 0.9, limbs 0.6, and armor that reduces by tier and loses durability per hit (helmets stop pistol rounds outright at tier II). All of it resolves on the server.

## Fix
- `shared/player/hitboxes.tscn`: an `Area3D` per zone under the player's `HitboxRoot`, each in group `"hitbox"` with an exported `zone: String` — `head` (sphere r 0.12 at the Head node), `neck` (small capsule), `chest`, `stomach`, `arm_l`, `arm_r`, `leg_l`, `leg_r`. Collision layer `hitbox` only; they must not collide with movement. Their local poses are driven by the stance blend so a prone player's boxes lie flat.
- `shared/combat/hitzones.gd`, `class_name HitZones`: `const MULT = {"head": 2.4, "neck": 1.5, "chest": 1.0, "stomach": 0.9, "arm_l": 0.6, "arm_r": 0.6, "leg_l": 0.6, "leg_r": 0.6}` and `static multiplier(zone: String) -> float` defaulting to 1.0 with a `push_warning` on an unknown zone.
- `shared/combat/damage.gd`, `class_name Damage`, static and pure:
  - `static compute(base_damage: float, energy_fraction: float, zone: String, armor_tier: int, helmet_tier: int, cartridge_class: String) -> Dictionary` returning `{"damage": float, "armor_damage": float, "stopped": bool}`.
  - Armor reduction by tier: `[0.0, 0.25, 0.40, 0.55]` for the vest (applies to `chest`/`stomach`), same table for the helmet (applies to `head`/`neck`).
  - **Helmet rule**: `helmet_tier >= 2` and `cartridge_class == "pistol"` → `stopped = true`, damage 0, armor durability still consumed.
  - Armor durability: `armor_damage = base_damage * energy_fraction * 0.5`; when a piece's durability hits 0 its tier drops by one (down to 0). Durability values live in `data/items.json` (`"durability": 200` style), not here.
  - Damage is applied **only** to the armor's covered zones; limbs and unarmoured zones ignore tiers entirely.
- `server/combat/damage_resolver.gd` (server only): takes `(projectile, hitbox, player)`, looks up the zone, calls `Damage.compute` with the cartridge's `base_damage` and `Ballistics.energy_fraction(projectile)`, applies it to `PlayerState.health`, decrements armor durability, and emits `signal player_damaged(victim_id, attacker_id, damage, zone, tick)` plus `signal player_killed(victim_id, attacker_id, tick)` at ≤ 0 health. Team damage is off by default (`friendly_fire = false` config on the match).
- A projectile that hits a player stops unless the round both penetrated a limb and retains > 60 % energy — keep that decision in `gun-penetration-ricochet`; here, just report the remaining energy.
- Death hands off to `econ-kill-drop` (cash bag + $300 bounty) and to `zone-teams-dbno` (knock instead of kill in team modes) via those signals — do not implement either here.

## Acceptance
- GUT file `tests/shared/test_damage.gd` (pure maths, `base_damage = 40`):
  - `test_headshot_multiplier()` — full energy, no armor, `head` → 96.0 ±0.01; `chest` → 40.0; `leg_l` → 24.0.
  - `test_energy_falloff()` — `energy_fraction = 0.5`, chest, no armor → 20.0.
  - `test_vest_tier_reduction()` — chest, `armor_tier = 2` → `40 * 0.6 = 24.0` ±0.01, and `armor_damage > 0`.
  - `test_helmet_stops_pistol_at_tier2()` — `head`, `helmet_tier = 2`, `cartridge_class = "pistol"` → `stopped == true`, damage 0.0; the same hit with `cartridge_class = "rifle"` does real damage.
  - `test_limbs_ignore_armor()` — `leg_l` with `armor_tier = 3` → 24.0 (unchanged).
  - `test_durability_drops_tier()` — consuming a tier-2 vest's durability to 0 leaves `armor_tier == 1`.
- Manual: shoot a bot in the head, chest and leg with an M16A1 and confirm the server log shows roughly 2.4× / 1× / 0.6× damage, and a tier-II helmet no-sells an M1911A1 headshot.

# LOW — Melee: knife, bayonet and butt stroke

**Category:** gun
**Priority:** LOW
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-hitzones-damage, gun-attachments

## Files
- `shared/weapons/melee.gd` (new)
- `server/combat/melee_controller.gd` (new)
- `data/items.json` (modify)
- `tests/shared/test_melee.gd` (new)

## Issue
The inventory has a dedicated melee slot and the store sells bayonets as attachments, but there is no melee attack at all — a player who runs dry in a tunnel has nothing. It is the cheapest silent kill in the game and bots need it for the same reason.

## Fix
- Data in `data/items.json` for melee items (`"slot": "melee"`): `"damage"`, `"range_m"`, `"swing_time_s"`, `"cooldown_s"`, `"backstab_mult"`, `"weight"`. Seed with `knife_kabar` (damage 55, range 1.6, swing 0.35) and `machete` (70, 1.9, 0.55).
- `shared/weapons/melee.gd`, `class_name Melee`, static:
  - `static attack(origin, dir, range_m, space_state, exclude) -> Dictionary` — a **shape-cast** (sphere radius 0.25) rather than a thin ray, so a swing at a moving target connects; returns the first hitbox hit with its zone.
  - `static damage_for(item, zone, is_backstab) -> float` — base damage × `HitZones.multiplier(zone)`, × `backstab_mult` (default 2.0) when the attacker is within 60° of the victim's back. A knife backstab to the chest should be lethal against an unarmoured player but not against a tier-3 vest.
  - Armor applies through `Damage.compute` as usual (a flak vest genuinely helps against a knife).
- Three attack sources, all routed through the same function:
  - **Melee slot** weapon (knife/machete) — full damage, fastest swing.
  - **Bayonet** attached to a rifle (`gun-attachments` sets `melee_bonus`) — a lunge with the rifle's reach plus the bonus, usable without swapping weapons.
  - **Butt stroke** — the fallback melee with any firearm and no bayonet: low damage (25), short range (1.2 m), long cooldown. Never interrupts a reload silently; it cancels the reload explicitly.
- `server/combat/melee_controller.gd` (server only): validates the cooldown, runs the swing **inside** `LagCompRegistry.with_rewind(input.tick, attacker_id, ...)` so melee is lag-compensated like bullets, applies the damage, and emits `melee_hit` / `melee_miss` events for FX and audio. Melee makes no gunshot noise but does produce a short local sound (`footsteps` tier in `audio-gunshots-propagation`).
- Melee is blocked while swimming, mantling, diving and while the wrist store is raised.

## Acceptance
- GUT file `tests/shared/test_melee.gd`:
  - `test_range()` — a target at 1.4 m is hit by the knife (range 1.6); a target at 2.0 m is not.
  - `test_backstab_multiplier()` — a knife hit from directly behind an unarmoured target deals `55 * 2.0` × the zone multiplier and kills a 100 HP player; the same hit from the front does not.
  - `test_armor_reduces_melee()` — a tier-3 vest reduces a chest knife hit by 55 % (per the `Damage` armor table).
  - `test_butt_stroke_fallback()` — with a rifle and no bayonet, the melee attack deals 25 base at 1.2 m range and respects its longer cooldown.
  - `test_cooldown()` — a second swing inside `cooldown_s` is refused and applies no damage.
- Manual: knife a bot from behind for a one-hit kill, butt-stroke one from the front and see it survive, and confirm melee connects on a strafing target at 150 ms latency (lag comp is working).

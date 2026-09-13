# MEDIUM — Launchers: M79, M72 LAW, RPG-7 with vehicle damage

**Category:** gun
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-throwables, gun-weapon-base

## Files
- `shared/weapons/launcher.gd` (new)
- `server/combat/launcher_manager.gd` (new)
- `data/weapons.json` (modify)
- `data/items.json` (modify)
- `tests/shared/test_launcher.gd` (new)

## Issue
The store's top-end sink is the launcher row at $2000–4500 (M79, single-shot M72 LAW, RPG-7), and they are the answer to vehicles and to a squad camped in a colonial block. None exist, and their projectiles behave unlike bullets: slow, arcing, with arming distance and area damage.

## Fix
- Add to `data/weapons.json` with `"class": "launcher"`: `m79` (40 mm, ~76 m/s muzzle, single shot, break-action reload ~3.5 s, arcing, ladder sight), `m72_law` (~145 m/s, one shot then the tube is discarded — the item is consumed), `rpg7` (~115 m/s boost then sustainer to ~295 m/s, reloadable, 1 rocket per tube).
- Per-launcher projectile data: `"arm_distance_m"` (M79 ≈ 14 m, RPG ≈ 5 m — under that it bounces and does not detonate), `"blast_damage"`, `"blast_radius"`, `"vehicle_damage"`, `"self_damage": true`, `"gravity_scale"`, `"drag_k"`.
- `shared/weapons/launcher.gd`, `class_name Launcher`, static: reuses `Ballistics.step` for flight but with the launcher's own `gravity_scale` and `drag_k`, plus the RPG's two-stage thrust (`boost_s` at the muzzle velocity then a one-off `sustainer_delta_v` at `t = 0.15 s`).
  - `static is_armed(travelled_m, arm_distance_m) -> bool`; an unarmed impact spawns a dud (no explosion, no damage).
  - On impact: `Throwable.explode`-style radial damage with the launcher's blast values and line-of-sight checks, plus a separate `vehicle_damage` figure applied to any `VehicleBody3D` in radius (`veh-base-vehiclebody` defines the interface — call it through a `has_method("apply_blast")` duck check so this task does not block on M7).
  - Direct hit on a player: `blast_damage * 1.5` at the impact point, which is lethal — that is the price of the shot.
- `server/combat/launcher_manager.gd`: steps live rockets, does the segment raycast (as with bullets), handles arming, detonation and the backblast. Backblast: a small damage volume 3 m behind the shooter for the LAW and RPG — firing inside a bunker hurts you.
- Aiming: launchers use a dedicated sight with a hold-over ladder; the ADS FOV and the reticle live in `data/weapons.json`. The arc preview from `gun-throwables` is **not** shown for launchers (you learn the ladder).
- Ammo: the M79 and RPG take rocket/grenade items from the inventory (weight 1.5–2.5 kg each, sold in the store); the LAW is the weapon and the ammo in one and is removed from the inventory after firing.

## Acceptance
- GUT file `tests/shared/test_launcher.gd`:
  - `test_m79_arc()` — fired at 45°, the 40 mm grenade's range is between 300 m and 420 m, and time of flight at 150 m is between 2.0 s and 3.0 s.
  - `test_arming_distance()` — an M79 round impacting at 10 m is a dud (no blast, no damage); at 20 m it detonates.
  - `test_rpg_sustainer()` — the RPG's speed at `t = 0.5 s` is higher than its muzzle speed, and it flies flatter than the M79 over 100 m.
  - `test_blast_falls_off_and_respects_cover()` — full damage at the impact point, reduced at half the radius, zero behind a wall.
  - `test_law_is_consumed()` — after firing, the LAW item is no longer in the inventory and cannot fire again.
  - `test_vehicle_damage_applied()` — a stub object with `apply_blast` receives the launcher's `vehicle_damage` when inside the radius.
- Manual: hit a moving pickup with an RPG and destroy it; fire an M79 over a hedgerow onto a bot squad; fire a LAW with your back 1 m from a wall and take backblast damage.

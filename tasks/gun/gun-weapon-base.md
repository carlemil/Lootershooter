# HIGH — Weapon base: fire modes, RPM, recoil, sway, spread, ADS

**Category:** gun
**Priority:** HIGH
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-cartridge-sim, move-stamina

## Files
- `shared/weapons/weapon.gd` (new)
- `shared/weapons/recoil.gd` (new)
- `shared/weapons/spread.gd` (new)
- `server/combat/fire_controller.gd` (new)
- `client/player/weapon_view.gd` (new)
- `tests/shared/test_weapon.gd` (new)

## Issue
Projectiles exist but nothing decides when one is fired, where it points or how the gun climbs. Every number (RPM, fire modes, recoil pattern, sway, spread, ADS time, ergonomics) is data-driven from `data/weapons.json` — no stats in scripts. Recoil's horizontal component must be seeded so the client's predicted pattern matches the server's.

## Fix
- `shared/weapons/weapon.gd`, `class_name Weapon extends RefCounted`, built from `GameData.get_weapon(id)`: `id`, `cartridge_id`, `rpm`, `fire_modes: Array`, `current_mode`, `ads_time_s`, `ads_fov`, `ergonomics`, `next_fire_tick`, `burst_left`, `shots_fired` (the recoil pattern index), `ads_amount: float` (0..1).
  - `static can_fire(w, state, tick) -> bool` — `tick >= next_fire_tick`, ammo in the chamber (`gun-reload-mags`), not holstered/swimming/mantling, and `Dive.can_aim` is irrelevant for hip fire but blocks ADS.
  - `fire_interval_ticks()` = `max(1, round(60.0 / rpm * NetConstants.TICK_RATE))`. Weapons faster than 900 RPM fire more than once per tick — support `shots_this_tick` so an M60 at 550 RPM and a hypothetical 1200 RPM SMG both work.
  - Fire modes: `semi` (one shot per `BTN_FIRE` rising edge), `burst` (3, respecting the interval), `auto` (while held), `bolt`/`pump` (adds the weapon's `cycle_s` before the next shot). Mode switching on a keybind cycles `fire_modes`.
  - ADS: `ads_amount` moves toward 1 while `BTN_AIM` is held at `1.0 / ads_time_s` per second, and back at 1.5× that. Vaulting, diving and swimming force it to 0.
- `shared/weapons/recoil.gd`, `class_name Recoil`, static and seeded:
  - `static kick(weapon_data, shot_index, rng) -> Vector2` — vertical climb from the data's `recoil.vertical` curve (an array sampled by `shot_index`, clamped to the last entry), horizontal from `rng.randf_range(-h, h)` where `h = recoil.horizontal`. The RNG is seeded with `hash(match_seed, shooter_id, fire_tick)` so client prediction and server agree shot for shot.
  - Recoil is applied to `PlayerState.look_pitch/yaw` (the server moves the aim, the client predicts the same move), then recovers toward the pre-fire aim at `recoil.recovery` deg/s after `recoil.recovery_delay_s`.
  - `shot_index` resets after `recoil.reset_s` of not firing.
- `shared/weapons/spread.gd`, `class_name Spread`: `static cone_deg(weapon_data, state, weapon) -> float` = `base_hip` or `base_ads`, times stance multipliers (prone 0.5, crouch 0.75, stand 1.0), plus `move_penalty * horizontal_speed`, plus a first-shot bonus (`first_shot_accuracy` makes the first shot after `reset_s` land at the exact crosshair when ADS). The direction offset uses the same seeded RNG, never `randf()`.
- Sway (ADS only, visual **and** aim-affecting): a low-frequency Lissajous offset scaled by `Stamina.sway_multiplier(state)` (plan: sway rises below 30 stamina), by weight, and by stance. Deterministic — driven by `tick`, not by wall time.
- `server/combat/fire_controller.gd` (server only): consumes `BTN_FIRE` from the accepted input frames, validates rate (`can_fire`, plus an independent fire-rate sanity counter for `polish-anticheat-sanity`), computes the direction from the **server's** authoritative look angles plus spread, and calls `ProjectileManager.fire(...)` inside the lag-comp rewind for `input.tick`. The client's claimed origin/direction is never used; only its tick is.
- `client/player/weapon_view.gd`: plays the muzzle flash, the viewmodel recoil animation and the predicted camera kick; it is cosmetic and must not write `PlayerState`.

## Acceptance
- GUT file `tests/shared/test_weapon.gd`:
  - `test_rpm_to_interval()` — 600 RPM → 3 ticks between shots at 30 Hz; 900 RPM → 2; 550 RPM → 3 (rounded) and `shots_this_tick` never exceeds 2.
  - `test_semi_requires_release()` — holding `BTN_FIRE` for 30 ticks on a `semi` weapon fires exactly 1 shot; releasing and re-pressing fires a 2nd.
  - `test_burst_fires_three()` — `burst` mode with the button held for 60 ticks fires exactly 3 per press.
  - `test_recoil_is_seeded()` — two `Recoil.kick` sequences of 10 shots with the same seed are identical; a different seed differs, and the vertical component is monotonically non-decreasing over the first 5 shots.
  - `test_spread_stance_and_movement()` — prone ADS cone < crouch ADS cone < standing ADS cone < standing hip cone, and moving at 5 m/s strictly widens the cone.
  - `test_low_stamina_increases_sway()` — sway magnitude at stamina 0 is 2.5× the magnitude at stamina 100.
- Manual: hold the trigger on an M16A1 and the muzzle climbs in a repeatable vertical pattern with slight horizontal wander; ADS visibly tightens the group; sprinting then immediately aiming shows the ADS-time delay.

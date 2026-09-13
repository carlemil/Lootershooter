# MEDIUM — Tracers, impact decals, muzzle flash and shell casings

**Category:** gun
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-cartridge-sim, gun-penetration-ricochet

## Files
- `client/fx/tracer.gd` (new)
- `client/fx/tracer_pool.gd` (new)
- `client/fx/impact_fx.gd` (new)
- `client/fx/muzzle_flash.tscn` (new)
- `client/fx/casing.tscn` (new)
- `tests/client/test_tracer.gd` (new)

## Issue
Projectiles live only on the server, so from a client's point of view nothing visible happens when a gun fires — no flash, no tracer, no impact. The design specifies tracers every 5th round on LMGs, per-material impacts and ejected casings; without them, firefights are unreadable and there is no feedback for leading a target at 300 m.

## Fix
- Client receives a `tracer` event from `ProjectileManager` (`origin`, `dir`, `speed`, `cartridge_id`, `is_tracer`) and an `impact` event (`position`, `normal`, `material_id`, `kind` = `hit|penetrate|ricochet|flesh`). Both are unreliable, best-effort — a lost FX event must never desync anything.
- `client/fx/tracer.gd`: a stretched quad / `MeshInstance3D` billboard that flies from `origin` along `dir` at `speed`, stepped with the **same** `Ballistics.step` maths so the visual matches where the server's round actually is. Lifetime = time to the reported impact (or 1.5 s). Fade the last 20 %.
- `client/fx/tracer_pool.gd`: a fixed pool of 128 tracer instances, reused round-robin — never `instantiate()` per shot. Same pattern for impact decals (pool of 64, oldest recycled) and casings (pool of 48).
- Tracer visibility rules: LMGs show one tracer every 5th round (the server sets `is_tracer` from the weapon's `tracer_every` field, default 0 = never for non-LMGs); other weapons show a faint, short "vapour trail" only for rounds passing within 30 m of the local camera. First-person, your own rounds always show a subtle trail so recoil is readable.
- `client/fx/impact_fx.gd`: per `material_id`, spawn a particle burst plus a decal — dirt puff, wood splinters, sparks on metal/stone (sparks also for `ricochet`), a water splash, a blood spray for `flesh` (toggleable in settings). Decals are `Decal` nodes with a 20 s fade and a global cap.
- `client/fx/muzzle_flash.tscn`: an `OmniLight3D` flash (0.05 s) plus a billboard, attached to the viewmodel's `MuzzleAnchor` for the local player and to the third-person weapon bone for others. Suppressed weapons (`muzzle_flash: false` from `gun-attachments`) get a much smaller flash and no light.
- `client/fx/casing.tscn`: a `RigidBody3D` casing ejected with a small randomised impulse (client-only visual — `randf()` is **fine** here, this is not shared sim), despawned after 4 s, with a ping sound on the first floor contact.
- Performance guard: all FX respect a `fx_quality` setting (low disables casings and decals); the pools must never allocate during a firefight.

## Acceptance
- GUT file `tests/client/test_tracer.gd` (headless, maths only):
  - `test_pool_reuse()` — firing 300 tracers creates at most 128 instances and none is `queue_free`d.
  - `test_tracer_position_matches_ballistics()` — after 10 ticks, the tracer's position is within 0.05 m of `Ballistics.step`'s result for the same cartridge.
  - `test_lmg_tracer_every_fifth()` — a 20-round M60 burst flags exactly 4 tracer rounds (shots 5, 10, 15, 20).
  - `test_fx_events_are_optional()` — dropping every second `impact` event leaves no orphaned pooled objects after 5 s.
- Manual: fire an M60 burst at night/dusk and see every 5th round trace; shoot wood, brick, metal and water and see four distinct impacts; fire a suppressed weapon and confirm the flash barely lights the wall next to you.

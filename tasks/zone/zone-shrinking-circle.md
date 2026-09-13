# HIGH — Zone closes to zero with a wandering center and a ramping outside penalty

**Category:** zone
**Priority:** HIGH
**Status:** TODO
**Milestone:** M5
**Depends on:** econ-cash-state, net-snapshot-sync

## Files
- `shared/zone/zone_math.gd` (new)
- `server/zone/zone_service.gd` (new)
- `data/zone.json` (new)
- `tests/test_zone_math.gd` (new)

## Issue
Nothing compresses the match, and nothing ends it. The design has no phases and no timer: the safe radius shrinks linearly from R0 = 1200 m to **0** across 15:00, so at 15:00 everyone is outside and the outside-damage ramp finishes the match by attrition. The center wanders along a smooth seeded-noise path at up to 1.5 m/s with the next 30 s telegraphed on the minimap. Outside costs a flat −$20/s plus health damage that ramps with **both** continuous time outside and distance past the edge, reaching 100% of max health per second at 60 s at the edge, 30 s at 200 m out, or 15 s at 600 m out. All of it must be deterministic from the match seed so replays and the client preview agree with the server.

## Fix
- `data/zone.json`: `{"r0": 1200.0, "r_end": 0.0, "duration_s": 900.0, "center_speed_max": 1.5, "preview_s": 30.0, "cash_drain_per_s": 20.0, "ramp_full_s": 60.0, "ramp_distance_scale_m": 200.0, "map_half_extent": 1000.0}`.
- `shared/zone/zone_math.gd`, `class_name ZoneMath`, **pure static functions, no nodes** — the deterministic core both sides call:
  - `radius_at(t: float) -> float` = `lerp(r0, 0.0, clamp(t / duration_s, 0.0, 1.0))`. Past 900 s it stays 0: the circle is gone and nobody is ever inside again.
  - `center_at(t: float, seed: int) -> Vector2` — sample a `FastNoiseLite` seeded with the match seed (`TYPE_PERLIN`, fixed frequency) as `(noise_2d(t * F, 0.0), noise_2d(0.0, t * F))`, scaled to a drift budget, then **clamp each step** so `|center_at(t) - center_at(t - dt)| / dt <= center_speed_max`. Integrate the path in fixed 0.5 s steps from t = 0 and cache the array so the result is identical regardless of when it is called.
  - Clamp the center so the circle stays on the 2 km map: `center.length() <= max(0.0, map_half_extent - radius_at(t))` (early on, with R > 1000 m, this pins the center at the origin — expected; it frees up as the circle shrinks).
  - `damage_per_s(t_outside: float, d_outside: float, max_health: float) -> float`: `var t_eff := t_outside * (1.0 + d_outside / ramp_distance_scale_m)` then `return max_health * min(1.0, t_eff / ramp_full_s)`. At `t_outside == 0` the damage is 0 — stepping one metre out is free for an instant, which is what makes running the edge viable.
  - `cash_drain_per_s()` is **flat $20/s** regardless of distance or time. Do not scale it; the health ramp is the whole pressure mechanism.
  - `preview_center(t, seed)` = `center_at(t + preview_s, seed)` and `preview_radius(t)` = `radius_at(t + preview_s)` for the minimap telegraph.
  - `distance_outside(pos: Vector3, t: float, seed: int) -> float` = `max(0.0, center.distance_to(Vector2(pos.x, pos.z)) - radius_at(t))`, and `is_inside(...)` = that distance being 0 — one function bots (`move_to_zone`) and the HUD both use, no bot-specific path.
- `server/zone/zone_service.gd` (server only): holds `match_seed` and `elapsed`; per alive player tracks `t_outside: float`.
  - Each tick: if `distance_outside > 0`, accumulate `t_outside += delta`, apply `CashService.drain(peer, 20.0 * delta, "outside")` and subtract `damage_per_s(t_outside, d, max_health) * delta` HP. **If the player is inside, reset `t_outside` to 0** — re-entry fully resets the ramp, no decay, no memory.
  - Zone deaths report `killer_peer == 0` so `econ-kill-drop` still spawns a bag with the bounty.
  - Emit `zone_state(center, radius, preview_center, preview_radius)` in the 20 Hz snapshot plus each player's own `t_outside` so the HUD can show an escalating warning; clients may also recompute the circle locally from the seed for a smooth draw.
  - After 900 s the service keeps running with radius 0: every survivor is outside, every ramp climbs, and the match ends through `zone-match-loop`'s last-team-alive check within roughly a minute. There is no timer-based end here.

## Acceptance
- GUT test `tests/test_zone_math.gd` (max_health = 100):
  - `radius_at(0) == 1200`, `radius_at(450) == 600`, `radius_at(900) == 0`, `radius_at(1000) == 0`.
  - `damage_per_s(0.0, 0.0, 100) == 0.0` and `damage_per_s(0.0, 500.0, 100) == 0.0` (time, not distance alone, starts the ramp).
  - `damage_per_s(60.0, 0.0, 100) == 100.0` (edge, 60 s); `damage_per_s(30.0, 200.0, 100) == 100.0` (200 m out, 30 s); `damage_per_s(15.0, 600.0, 100) == 100.0` (600 m out, 15 s); `damage_per_s(120.0, 0.0, 100) == 100.0` (clamped, never above max_health/s).
  - Re-entry resets the ramp: drive `ZoneService` with a player 100 m outside for 30 s, step them inside for one tick, then back outside — the damage on that next outside tick equals `damage_per_s(delta, 100, 100)`, not the pre-entry value.
  - Cash drain is flat: a player 10 m outside and one 600 m outside both lose exactly $20 over 1 s.
  - `center_at(t, 42)` is reproducible across calls; seed 43 differs. Sampling every 0.5 s to 900 s, no step exceeds `1.5 * 0.5` m (+1e-4), and `center_at(t).length() <= max(0.0, 1000 - radius_at(t)) + 1e-3` throughout.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

# MEDIUM — Hot zones: schedule, falloff payout, growing pot

**Category:** zone
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M5
**Depends on:** zone-shrinking-circle, econ-cash-state

## Files
- `shared/zone/hot_zone_math.gd` (new)
- `server/zone/hot_zone_service.gd` (new)
- `data/zone.json` (modify)
- `tests/test_hot_zones.gd` (new)

## Issue
There is no reason to go anywhere specific on a 2 km map. Hot zones are the pull: they spawn at 1:00, 5:00 and 9:00, live 3–4 minutes, keep 2–3 alive at a time, and pay $8/s at the center falling linearly to $0 at the edge, per person rather than per team (so a squad of 4 at the center earns $32/s). The pot per second also grows with the zone's age, rewarding whoever holds it longest.

## Fix
- Extend `data/zone.json` with `"hot": {"spawn_times_s": [60, 300, 540], "lifetime_min_s": 180, "lifetime_max_s": 240, "radius_m": 120, "pay_center_per_s": 8.0, "age_bonus_per_min": 0.25, "max_alive": 3}`.
- `shared/zone/hot_zone_math.gd` (pure static, shared so the HUD can show the live rate):
  - `payout_per_s(distance_from_center: float, radius: float, age_s: float) -> float` = `pay_center_per_s * clamp(1.0 - distance / radius, 0.0, 1.0) * (1.0 + age_bonus_per_min * age_s / 60.0)`.
  - `is_inside(pos, center, radius) -> bool` using XZ distance only (vertical position is irrelevant — a rooftop still pays).
- `server/zone/hot_zone_service.gd` (server only):
  - Seeded from the match seed: at each scheduled spawn time, pick a center with the match RNG that is **inside the current safe circle** at that moment (`ZoneMath.center_at/radius_at`) and biased toward loot-dense areas by preferring a position within 200 m of a `loot_town`/`loot_outpost` marker cluster when one qualifies; roll a lifetime in 180–240 s.
  - Enforce `max_alive = 3` (skip a spawn if three are already up) and expire zones when their lifetime elapses, emitting `hot_zone_expired(id)`.
  - Every server tick, for every alive player inside any hot zone, `CashService.drain`-style accumulate `payout_per_s(...) * delta` into a float remainder and grant whole dollars with reason `"hotzone"`. **Per person, no team division.** A player standing in two overlapping hot zones is paid by the better one only.
  - Track `hot_zone_time_s` per player for the results scoreboard.
  - Replicate `{id, center, radius, age_s}` for all live hot zones to every client (minimap circles).

## Acceptance
- GUT test `tests/test_hot_zones.gd`:
  - `payout_per_s(0, 120, 0) == 8.0`; `payout_per_s(60, 120, 0) == 4.0`; `payout_per_s(120, 120, 0) == 0.0`; `payout_per_s(0, 120, 120) == 12.0` (2 min age, +0.5).
  - Four players at the center for 1 s each receive $8, i.e. $32 total granted — nothing is divided per team.
  - Running a full 900 s simulated match with seed 7 spawns exactly 3 hot zones at t≈60/300/540, each with a lifetime in [180, 240], and never more than 3 alive.
  - Every spawned center lies inside the safe circle at its spawn time.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

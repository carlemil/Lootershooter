# HIGH — Stamina pool: drains, regen, weight and armor scaling

**Category:** move
**Priority:** HIGH
**Status:** TODO
**Milestone:** M2
**Depends on:** move-controller-base

## Files
- `shared/player/stamina.gd` (new)
- `shared/player/movement.gd` (modify)
- `tests/shared/test_stamina.gd` (new)

## Issue
`PlayerState.stamina` exists and `Movement.step` already gates sprinting on it, but nothing ever drains or regenerates it, so sprinting is free and infinite. The design fixes the whole economy of movement on these numbers: a 100 pool, sprint −10/s, dive −25, jump −8, ADS hold −2/s with sway rising below 30, and +15/s regen after 1 s without spending — with weight and armor tier scaling the drain, which is what makes a rich, heavily-kitted player pay for their loadout. These are exact numbers and they must be unit-tested.

## Fix
- `shared/player/stamina.gd`, `class_name Stamina`, static functions only. Constants, verbatim from plan section 1:
  - `MAX = 100.0`
  - `SPRINT_DRAIN = 10.0` (per second)
  - `DIVE_COST = 25.0` (one-shot)
  - `JUMP_COST = 8.0` (one-shot)
  - `ADS_DRAIN = 2.0` (per second while ADS is held)
  - `REGEN = 15.0` (per second)
  - `REGEN_DELAY = 1.0` (seconds after the last spend)
  - `LOW_THRESHOLD = 30.0` (below this, weapon sway rises)
- Scaling:
  - `static weight_mult(weight_kg: float) -> float` = `1.0 + clamp((weight_kg - BASE_WEIGHT) / 10.0, 0.0, 1.0) * 0.8` with `BASE_WEIGHT = 15.0` — a 25 kg loadout drains 1.8×, anything heavier is capped at 1.8×.
  - `static armor_mult(armor_tier: int) -> float` = `[1.0, 1.05, 1.15, 1.3][clamp(tier, 0, 3)]`.
  - Total drain multiplier = `weight_mult * armor_mult`; it applies to **continuous drains and one-shot costs alike** (a heavy player pays more per jump too).
  - Regen is scaled the other way: `regen_rate = REGEN / weight_mult` (heavier = slower recovery), armor does not affect regen.
- `static step(state: PlayerState, input: InputFrame, delta: float, is_sprinting: bool) -> void`:
  1. `spent := 0.0`.
  2. If `is_sprinting` and the player is actually moving: `spent += SPRINT_DRAIN * delta`.
  3. If `input.pressed(BTN_AIM)`: `spent += ADS_DRAIN * delta`.
  4. One-shot costs are **not** charged here — `Movement`/`Dive` call `Stamina.charge(state, JUMP_COST)` / `charge(state, DIVE_COST)` exactly once per event, keyed on the event tick so reconciliation replays cannot double-charge (`state.last_jump_charged_tick`, `state.last_dive_charged_tick`).
  5. `spent *= weight_mult(state.weight) * armor_mult(state.armor_tier)`.
  6. If `spent > 0.0`: `state.stamina = max(0.0, state.stamina - spent)`, `state.stamina_idle = 0.0`.
     Else: `state.stamina_idle += delta`; when `stamina_idle >= REGEN_DELAY`, `state.stamina = min(MAX, state.stamina + regen_rate * delta)`.
- `static can_sprint(state) -> bool` — `stamina > 0.0`; once it hits 0 the player drops to run speed and cannot sprint again until stamina exceeds `SPRINT_RECOVER = 15.0` (prevents 1-tick sprint stutter at empty).
- `static sway_multiplier(state) -> float` — `1.0` at or above `LOW_THRESHOLD`, rising linearly to `2.5` at 0 stamina. `gun-weapon-base` multiplies its sway by this; do not implement sway here.
- Boosters (coffee/stim from `econ-healing-boosters`) will modify `REGEN` — expose `state.stamina_regen_mult: float = 1.0` now and apply it in step 6 so that task is a data change, not a rewrite.
- Deterministic: no `randf()`, no wall clock; `delta` is always `NetConstants.TICK_DELTA` on the authoritative path.

## Acceptance
- GUT file `tests/shared/test_stamina.gd` (all with `weight = 15.0`, `armor_tier = 0` unless stated):
  - `test_sprint_drains_10_per_second()` — from 100, 30 ticks of sprinting leaves 90.0 ±0.01.
  - `test_regen_after_delay()` — from 50 with no spend, 30 ticks leaves 50.0 (the 1 s delay), and 60 ticks leaves 65.0 ±0.05.
  - `test_jump_and_dive_costs()` — `charge(state, JUMP_COST)` from 100 leaves 92.0; `charge(state, DIVE_COST)` leaves 67.0; charging the same tick twice leaves 67.0 still.
  - `test_ads_drain()` — 30 ticks with `BTN_AIM` held from 100 leaves 98.0 ±0.01.
  - `test_weight_and_armor_scale_drain()` — `weight = 25.0`, `armor_tier = 2`: 30 ticks of sprinting drains `10 * 1.8 * 1.15 = 20.7` ±0.05.
  - `test_sway_multiplier()` — `sway_multiplier` at stamina 30 is 1.0; at 0 it is 2.5; at 15 it is 1.75 ±0.01.
  - `test_empty_pool_blocks_sprint_until_15()` — at 0, `can_sprint` is false; after regenerating to 14.9 still false; at 15.1 true.
- Manual: the HUD stamina bar (once `ui-hud` exists) empties in 10 s of sprinting with a light loadout and in ~5.5 s with a 25 kg tier-2 kit, and refills in ~7 s.

# HIGH — Aim model, reaction delay, burst discipline, grenades

**Category:** bot
**Priority:** HIGH
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-perception, bot-utility-brain, gun-weapon-base, gun-throwables, econ-healing-boosters

## Files
- `server/bots/bot_aim.gd` (new)
- `server/bots/actions/engage.gd` (modify)
- `server/bots/actions/retreat_heal.gd` (modify)
- `tests/test_bot_aim.gd` (new)

## Issue
Bots can see and path but cannot fight. The plan's model is specific: a target point plus angular error drawn from N(0, σ) where σ shrinks with time-on-target, a reaction delay of 250–700 ms by difficulty, and velocity lead on moving targets. Without a delay and a σ, bots are either instant laser-aimers or useless, and neither is playtestable for balance. All of it must run through `BotAgent.set_look()` / `press(FIRE)` so the same recoil, spread and ballistics apply as for a human.

## Fix
- `server/bots/bot_aim.gd`: `class_name BotAim`. State per target: `time_on_target: float`, `reaction_timer: float`, `current_error: Vector2` (yaw/pitch radians), `lead_estimate: Vector3`.
- Reaction: when `BotPerception` promotes a target to `known`, roll `reaction_timer` uniformly from the difficulty's `reaction_ms` range (`data/bots.json`, always within 250–700 ms). No `look` change toward that target and no firing until it expires. A target that re-appears within 2 s of being lost gets a halved reaction.
- Aim point: chest marker by default; head only for `hard` difficulty when `time_on_target > 1.2 s` and distance < 60 m. Add velocity lead — `aim_pos = target_pos + target_velocity * flight_time`, where `flight_time = distance / cartridge_muzzle_velocity` from the loaded weapon's cartridge record, plus a gravity-drop offset using the same ballistics helper as `gun-cartridge-sim` (reuse it, do not re-derive drop).
- Error: `sigma = base_sigma_deg * profile.aim_sigma_mult * (0.35 + 0.65 * exp(-time_on_target / 0.8))`, so σ decays to ~35% of base after roughly 1.5 s on target. Resample `current_error` from `N(0, sigma)` at 6 Hz and interpolate `look` toward `aim_pos + error` at the human turn-rate clamp from `bot-input-adapter` — never snap.
- Extra σ multipliers: target moving laterally ×1.4, bot moving ×1.5, bot at < 30 stamina ×1.3, rain/dusk ×1.2, distance > 150 m ×1.3. Suppressive fire (target only heard, not seen) uses σ ×3 and fires at the last known position at most 3 rounds.
- Firing discipline: hold `FIRE` per weapon fire mode — full-auto bursts of 3–5 rounds with 0.25–0.45 s gaps beyond 40 m, longer bursts under 15 m; semi-auto taps at the weapon's RPM cap; bolt-action waits for the cycle. Never fire while `reaction_timer > 0`, while `awareness < 1.0`, or when the first raycast from muzzle to `aim_pos` hits a teammate (friendly-fire check).
- ADS: press ADS when distance > 25 m and not sprinting; accept the ADS time from the weapon data before the first shot counts.
- Reload: when magazine is below 25% and no enemy is visible for 2 s, or when empty. Grenades (`engage.gd`): throw a frag when a known enemy has been static inside a building or behind cover for > 2 s at 12–35 m, using the existing `gun-throwables` arc helper with a cook time of 1.5 s; smoke when retreating below 35% HP. Maximum one grenade per 20 s per bot.
- `retreat_heal.gd`: break line of sight using `cover_points.best_cover`, then use the fastest healing item that fits the wound (bandage < 40% missing, first-aid kit / medkit otherwise) through the normal item-use input, interrupting if an enemy closes within 20 m.
- Everything writes only through `BotAgent`; assert no direct weapon or damage calls.

## Acceptance
- GUT test `tests/test_bot_aim.gd`:
  - `test_reaction_window`: over 200 rolls on `normal`, every `reaction_timer` lands in [0.35, 0.55] s and on `easy` within [0.55, 0.70] s; no roll ever falls outside [0.25, 0.70].
  - `test_sigma_shrinks`: σ at `time_on_target = 0` is the base value; at 1.5 s it is between 30% and 45% of base; it never reaches 0.
  - `test_velocity_lead`: a target 100 m away moving 5 m/s laterally with a 715 m/s cartridge produces an aim point led by 0.65–0.75 m.
  - `test_no_friendly_fire`: with a teammate between muzzle and target, `should_fire()` is false.
  - `test_no_fire_before_reaction`: `should_fire()` is false while `reaction_timer > 0`.
- Manual: 1 human vs 3 `normal` bots in a test map — bots take a visible beat before shooting, miss more at 150 m than at 30 m, burst rather than hose, and throw a grenade at a camped position.

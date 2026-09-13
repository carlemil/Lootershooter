# HIGH — Utility scorer, actions and personality profiles

**Category:** bot
**Priority:** HIGH
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-input-adapter, bot-perception, zone-shrinking-circle, zone-hot-zones

## Files
- `server/bots/bot_brain.gd` (new)
- `server/bots/actions/action_base.gd` (new)
- `server/bots/actions/` (new — one script per action)
- `data/bots.json` (new)
- `tests/test_bot_brain.gd` (new)

## Issue
`BotAgent` can push inputs but nothing decides what to push, so bots stand still. The plan calls for a utility scorer over ten actions (`loot`, `move_to_zone`, `go_hot_zone`, `engage`, `flank`, `retreat_heal`, `buy`, `drive`, `camp`, `revive_teammate`) with five personality profiles (Rusher, Looter, Camper, Opportunist, Squad-follower) whose weights live in `data/bots.json`, plus decision noise as a difficulty knob. Without this there is no bot behaviour at all and a 20-slot match is 17 statues.

## Fix
- `server/bots/actions/action_base.gd`: `class_name BotAction`. Interface: `name: String`, `score(ctx: Dictionary) -> float` returning 0..1, `start(agent)`, `tick(agent, delta)`, `stop(agent)`, `is_done() -> bool`, and `commitment_s: float` (minimum seconds before the brain may switch away — prevents twitching).
- One script per action in `server/bots/actions/`: `loot.gd`, `move_to_zone.gd`, `go_hot_zone.gd`, `engage.gd`, `flank.gd`, `retreat_heal.gd`, `buy.gd`, `drive.gd`, `camp.gd`, `revive_teammate.gd`. In this task each `score()` is fully implemented; `tick()` may delegate to stubs that later tasks (`bot-navigation`, `bot-combat`, `bot-economy`, `bot-vehicles-teams`) fill in — define the stub function names now so those tasks have a seam.
- `server/bots/bot_brain.gd`: runs at 5 Hz per bot (staggered by `peer_id`), not every tick. Builds `ctx` once: `{hp_frac, stamina_frac, cash, ammo_frac, has_weapon, enemies (from BotPerception), nearest_enemy_dist, teammates_dbno, zone_center, zone_radius, dist_outside_zone, time_to_zone_edge, hot_zones, nearest_loot, nearest_vehicle, match_time_left, learned (from bots_learned.json)}`.
- Scoring: `final = clamp(raw_score, 0, 1) * profile_weight[action] * (1 + randfn(0, decision_noise))`, pick the argmax, honour the current action's `commitment_s` unless a hard interrupt fires (taking damage, zone damage, teammate knocked).
- Baseline `score()` shapes (tune later in `polish-playtest-balance`): `move_to_zone` = 0 inside the circle with > 60 s of slack, ramping to 1.0 when `time_to_zone_edge < 20 s` or already outside; `engage` = `visible_enemy * clamp((1 - dist/150), 0, 1) * hp_frac * has_weapon`; `retreat_heal` = `(1 - hp_frac)^2` gated on owning a healing item; `loot` = `(1 - cash/2500) * nearby_loot_density`; `buy` = `clamp(cash/1200, 0, 1) * gap_in_loadout`; `go_hot_zone` = pot size × inverse distance, damped while an enemy is visible; `camp` = high only for Camper profile, inside the zone, with a held position; `flank` = enemy known but not visible for 3–8 s; `drive` = `dist_to_target > 300 m` and a vehicle within 60 m; `revive_teammate` = 0.95 flat when a teammate is DBNO within 80 m and no enemy is within 30 m.
- `data/bots.json` schema: `{"profiles": {"rusher": {"weights": {...ten actions...}, "aim_sigma_mult": 0.9, "reaction_mult": 0.85, "aggression": 0.9}, "looter": {...}, "camper": {...}, "opportunist": {...}, "squad_follower": {...}}, "difficulty": {"easy": {"reaction_ms": [550,700], "aim_sigma_deg": 3.5, "perception_mult": 0.6, "decision_noise": 0.25}, "normal": {"reaction_ms": [350,550], "aim_sigma_deg": 2.0, "perception_mult": 1.0, "decision_noise": 0.15}, "hard": {"reaction_ms": [250,400], "aim_sigma_deg": 1.0, "perception_mult": 1.4, "decision_noise": 0.07}}}`. Reaction bounds must stay inside the plan's 250–700 ms window.
- The brain never writes to `PlayerState`; every effect goes through `BotAgent.set_move/set_look/press/tap`.
- Add a `bot_debug` server flag that logs `peer_id, chosen action, top-3 scores` once per decision for tuning.

## Acceptance
- GUT test `tests/test_bot_brain.gd`:
  - `test_zone_urgency_wins`: a bot 300 m outside the circle with full HP and no enemies chooses `move_to_zone`.
  - `test_low_hp_retreats`: `hp_frac = 0.2`, a medkit in inventory and an enemy at 120 m yields `retreat_heal` over `engage`.
  - `test_profile_weights_matter`: the identical `ctx` (enemy at 40 m, inside zone) scores `engage` highest for `rusher` and `camp` or `loot` highest for `camper`.
  - `test_commitment`: after choosing `loot` with `commitment_s = 4.0`, a 0.5 s later re-evaluation with a marginally better `buy` score keeps `loot`.
  - `test_profiles_schema`: all five profiles in `data/bots.json` define a weight for all ten action names, and every difficulty's `reaction_ms` lies within [250, 700].
- Run `godot --headless -s addons/gut/gut_cmdln.gd -gexit` — all green.

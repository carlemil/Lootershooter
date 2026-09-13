# MEDIUM — Bots sample learned priors with epsilon noise; difficulty knobs

**Category:** bot
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-learning-recorder, bot-utility-brain, bot-economy, bot-navigation, zone-drop-in

## Files
- `server/bots/learned_priors.gd` (new)
- `server/bots/bot_manager.gd` (modify)
- `server/bots/actions/loot.gd` (modify)
- `server/bots/actions/buy.gd` (modify)
- `data/bots.json` (modify)
- `tests/test_learned_priors.gd` (new)

## Issue
`data/bots_learned.json` gets produced but nothing reads it, so bots still drop, loot and buy from hardcoded heuristics and play nothing like the humans the recorder observed. The plan requires bots to sample the priors with ε-noise so they are not all identical, and the four difficulty knobs (reaction, aim σ, perception, decision noise) need one place that applies them rather than each bot task rolling its own.

## Fix
- `server/bots/learned_priors.gd`: server-only autoload. Loads `data/bots_learned.json` once at match start (hot-reload on `--reload-priors` for tuning). If the file is missing or its heat grid is uniform, every sampler falls back to its heuristic and logs "priors: cold start" once.
- `sample_drop_point(rng, epsilon) -> Vector3`: build a weighted distribution over the 64×64 `drop_picks` grid (cell 31.25 m), mix with a uniform distribution at weight `epsilon` (default 0.25), sample a cell and jitter uniformly inside it. Team leaders sample; teammates cluster within the 150 m the drop rules allow.
- `sample_loot_route(rng, from_building_id, epsilon) -> String`: softmax over `loot_routes[from]` transitions with ε uniform mixing; returns the next building id. `loot.gd` uses it to pick the next building instead of pure nearest-first once the current building is swept.
- `hot_cell_near(pos, radius, phase) -> Vector3`: samples `heat_early`/`heat_late` by match phase (< 5 min vs > 10 min) so bots drift toward where humans actually are late-match; used by `camp.gd` and by `move_to_zone.gd` to choose which side of the circle to approach from.
- `buy_bias(item_category) -> float`: normalised frequency from `buy_priority`, blended 50/50 with the profile's static `buy_priority` list so learned data nudges rather than overrides personality.
- `engage_pref_dist() -> float`: samples the `engage_hist` histogram; `bot-combat` uses it to pick a preferred hold distance (a bot that prefers 40 m pushes; one that prefers 180 m holds).
- Every sampler takes the bot's own seeded `RandomNumberGenerator` (seeded from `match_seed ^ peer_id`) so a replay of a seed reproduces bot behaviour — required by the plan's determinism rule.
- Per-bot ε comes from `data/bots.json` `difficulty.<level>.epsilon` (easy 0.4, normal 0.25, hard 0.12) — lower ε means closer to observed human behaviour.
- `bot_manager.gd`: on spawn, assign each bot `{profile, difficulty}` from a match-level mix, default `easy 25% / normal 55% / hard 20%`, overridable by `--bot-difficulty=<easy|normal|hard|mix>`. Apply the four knobs in one place: `reaction_ms` → `BotAim`, `aim_sigma_deg` → `BotAim`, `perception_mult` → `BotPerception`, `decision_noise` → `BotBrain`. No other file reads the difficulty table.

## Acceptance
- GUT test `tests/test_learned_priors.gd`:
  - `test_hot_cells_preferred`: with a fixture where one cell holds 80% of drop mass, 1000 samples at `epsilon = 0.0` land in that cell > 95% of the time; at `epsilon = 1.0` the distribution is within 10% of uniform.
  - `test_cold_start_uniform`: loading a uniform default `bots_learned.json` makes `sample_drop_point` uniform and logs the cold-start notice once.
  - `test_seeded_repeatable`: two bots with the same `peer_id` and `match_seed` produce identical drop points and route picks; different peer ids differ.
  - `test_difficulty_knobs_applied`: spawning a `hard` bot sets `BotAim.base_sigma_deg == 1.0`, `BotPerception.perception_mult == 1.4` and `BotBrain.decision_noise == 0.07` from `data/bots.json`.
- Manual: run two headless matches with the same seed and `--bot-difficulty=normal`; bot drop points and first-building picks match between runs. After feeding the aggregator a recorded human match, bots visibly favour the town on drop.

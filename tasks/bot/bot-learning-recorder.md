# MEDIUM — Telemetry JSONL recorder and aggregator to bots_learned.json

**Category:** bot
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M8
**Depends on:** bot-input-adapter, econ-money-piles, econ-store-catalog, zone-match-loop

## Files
- `server/learning/recorder.gd` (new)
- `server/learning/aggregator.gd` (new)
- `tools/aggregate_learning.ps1` (new)
- `data/bots_learned.json` (new — generated, seed a neutral default)
- `tests/test_learning_aggregator.gd` (new)

## Issue
The plan's "learning" is not ML: it is a server recorder that writes what real players actually do, plus an aggregator that turns it into priors bots sample from. Nothing records anything today, so bots have no idea where humans drop, which buildings get looted, at what ranges fights happen, or what people buy — and the same telemetry is what `polish-playtest-balance` needs for price and damage tuning. The output format is fixed by the plan: a 64×64 heat grid over the 2 km map, loot-route popularity and buy priorities in `data/bots_learned.json`.

## Fix
- `server/learning/recorder.gd`: server-only autoload, enabled by `--record` (default on for dedicated servers). Appends newline-delimited JSON to `learn/<YYYY-MM-DD>.jsonl`, one write batch every 2 s (buffer in memory, one `FileAccess` append per flush — never a write per event).
- Record types, each line `{"t": <match_time_s>, "match": <match_id>, "seed": <int>, "type": ..., ...}`:
  - `"pos"`: every 2 s, `{"players": [[peer, x, z, alive, cash, is_bot], ...]}` — humans and bots both, with `is_bot` so the aggregator can filter to human behaviour only.
  - `"loot"`: `{"peer", "kind": "pile|safe|bag", "value", "x", "z", "building_id"}`.
  - `"engage"`: on each damage event, `{"attacker", "victim", "dist", "weapon", "hit_zone", "damage"}`.
  - `"drop"`: at landing, `{"peer", "x", "z", "is_leader"}`.
  - `"buy"`: `{"peer", "item_id", "price", "cash_after", "match_time"}`.
  - `"hotzone"`: `{"zone_id", "players_inside", "pot"}` every 10 s.
  - `"end"`: `{"winner_team", "survivors", "cash_on_hand"}`.
- Rotate and cap: if the day's file exceeds 200 MB, start `learn/<date>.<n>.jsonl`. Never block the game loop — if a flush takes over 5 ms, log and drop the batch.
- `server/learning/aggregator.gd`: runnable headless (`godot --headless -s server/learning/aggregator.gd -- --in learn/ --out data/bots_learned.json`). Reads every `.jsonl` in the input directory, ignores lines it cannot parse, and writes:
  - `"heat"`: 64×64 float grid (cell = 31.25 m) of normalised human presence-time, from `"pos"` lines with `is_bot == false`; separate sub-grids `"heat_early"` (0–5 min) and `"heat_late"` (10–15 min).
  - `"drop_picks"`: 64×64 normalised counts from `"drop"` lines.
  - `"loot_routes"`: ordered building-id transition counts `{"<from>": {"<to>": n}}` per player sequence, plus per-building `"value_mean"` and `"visit_rate"`.
  - `"engage_hist"`: engagement distance histogram in 10 m buckets 0–300 m plus a tail bucket.
  - `"buy_priority"`: per item category, mean purchase time and purchase frequency, ordered.
  - `"meta"`: `{"matches": n, "generated": iso8601, "version": 1}`.
- Cold start: commit a neutral `data/bots_learned.json` with a uniform heat grid and empty routes so bots work on a fresh install; `bot-learned-sampling` must treat a uniform grid as "no information".
- `tools/aggregate_learning.ps1`: one-liner wrapper that runs the aggregator and reports the number of matches consumed. (A Python-stdlib equivalent is acceptable if the GDScript run proves awkward headless — same output schema either way.)
- Telemetry contains peer ids and no personal data; do not log names or IPs.

## Acceptance
- GUT test `tests/test_learning_aggregator.gd`:
  - `test_heat_grid_shape`: aggregating a fixture JSONL yields a `heat` array of exactly 64 rows × 64 columns, values in [0, 1], summing to ≈ 1.0.
  - `test_bot_positions_excluded`: a fixture where all bot positions sit in cell (0,0) and human positions in (32,32) yields `heat[0][0] == 0`.
  - `test_engage_histogram`: three damage events at 15 m, 95 m and 240 m land in buckets 1, 9 and 24.
  - `test_malformed_line_skipped`: a file with one truncated JSON line still aggregates the valid lines and reports the skip count.
- Run a 1-minute headless match with `--record`, confirm `learn/<today>.jsonl` exists with `pos` lines roughly every 2 s, then run `tools/aggregate_learning.ps1` and confirm `data/bots_learned.json` parses and has a non-uniform heat grid.

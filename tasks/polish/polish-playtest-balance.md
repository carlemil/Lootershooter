# MEDIUM — Balance pass: tune prices, damage and bot difficulty from telemetry

**Category:** polish
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M10
**Depends on:** bot-learning-recorder, bot-learned-sampling, polish-killcam-stats, polish-perf-pass, econ-store-catalog

## Files
- `tools/balance_report.gd` (new)
- `tools/balance_report.ps1` (new)
- `data/prices.json` (modify)
- `data/weapons.json` (modify)
- `data/bots.json` (modify)
- `docs/balance-notes.md` (new)
- `tests/test_balance_report.gd` (new)

## Issue
Every number in the game is a first guess: $800 starting cash, $8/s at hot-zone centre, $300 kill bounty, the >$3000 rich-bounty threshold, −$20/s and −2 HP/s outside the zone, the whole $200–$4500 store ladder, and the bot difficulty knobs. The recorder from `bot-learning-recorder` and the match stats from `polish-killcam-stats` now produce the data needed to check them, but nothing turns that data into a readable report or a tuning decision.

## Fix
- `tools/balance_report.gd`: runnable headless (`godot --headless -s tools/balance_report.gd -- --in learn/ --out docs/balance-notes.md`). Reads the same JSONL the aggregator reads and emits a Markdown report — this is an analysis tool, it changes no game data automatically.
- Report sections and the questions each answers:
  - **Economy curve**: median cash on hand at 2 / 5 / 10 / 15 min, and the fraction of players who ever cross $3000 (the rich-bounty threshold). If under ~15% cross it, the marker never fires and the pressure valve is dead — raise income or lower the threshold.
  - **Store usage**: purchase frequency and median purchase time per item id and category; items bought by under 2% of players are mispriced or weak, items bought by over 80% are underpriced. Flag both automatically.
  - **Weapon performance**: kills, damage per shot, accuracy and median engagement distance per weapon, normalised by how often each weapon is owned. Flag any weapon whose kills-per-owner-minute is more than 1.5× or under 0.5× the median.
  - **Time-to-kill**: TTK histogram per weapon class against each armour tier, so head 2.4× / chest 1.0× and the vest tiers can be sanity-checked against intent.
  - **Zone and hot zones**: deaths attributed to zone damage vs players, mean time spent outside, and hot-zone attendance and payout per zone — is $8/s at centre worth the risk, and does the growing pot actually pull people in?
  - **Bot difficulty**: human-vs-bot and bot-vs-bot kill ratios per difficulty, mean bot survival time, and mean engagement distance vs human engagement distance. Target: `normal` bots win roughly 35–45% of their fights against median human players.
  - **Match shape**: match duration distribution, how often the 15:00 tiebreak on cash actually decides, and placement vs cash-earned correlation.
- `tools/balance_report.ps1`: wrapper that runs the report over `learn/` and opens the output.
- `docs/balance-notes.md` is the living record: each tuning pass appends a dated section with the numbers observed, the change made to `data/prices.json` / `data/weapons.json` / `data/bots.json`, and the expectation for the next pass. Data edits stay in the JSON files — never move tuned values into scripts.
- Guardrails for any change: prices move by at most 25% per pass, damage by at most 15%, and bot `reaction_ms` must stay inside the plan's 250–700 ms window and `aim_sigma_deg` above 0.5 so `hard` bots never become pixel-perfect.
- Run the first pass on data from at least 10 matches (bot-only soak matches from `tools/perf_soak.ps1` count for weapon and TTK data, but economy and hot-zone conclusions need human matches — say so in the report header when the sample is bot-only).

## Acceptance
- GUT test `tests/test_balance_report.gd`:
  - `test_ttk_histogram`: a fixture with three kills at 0.8 s, 1.2 s and 3.5 s produces the correct per-class buckets and a median of 1.2 s.
  - `test_weapon_normalisation`: a weapon owned by 2 players with 4 kills ranks above one owned by 20 players with 10 kills on kills-per-owner-minute.
  - `test_outlier_flags`: an item bought by 95% of players is flagged underpriced; one bought by 1% is flagged unused.
  - `test_bot_only_header`: a data set with no human players emits the bot-only caveat in the report header.
- Run `tools/balance_report.ps1` over a 10-match data set and confirm `docs/balance-notes.md` is generated with every section populated and at least one concrete flagged recommendation.
- After applying one tuning pass, a re-run shows the flagged metric moving in the intended direction; record both tables in `docs/balance-notes.md`.

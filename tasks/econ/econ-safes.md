# MEDIUM — Safes: 5 s crack, loud, big payout

**Category:** econ
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-money-piles

## Files
- `shared/loot/safe.tscn` (new)
- `shared/loot/safe.gd` (new)
- `server/economy/money_spawner.gd` (modify)
- `data/loot_tiers.json` (modify)
- `tests/test_safe.gd` (new)

## Issue
Town buildings and outposts need a high-risk, high-reward cash source: a safe worth $800–1500 that takes 5 s of uninterrupted channelling to crack and makes a noise event audible far enough to draw players in. Nothing like this exists; money piles are all instant pickups, so there is no reason to contest a specific room.

## Fix
- Add a `"loot_safe": {"min": 800, "max": 1500, "weight": 0.15}` tier to `data/loot_tiers.json`. Safes spawn only from markers in the `loot_safe` group (placed by `world-town` and `world-outposts` only).
- `server/economy/money_spawner.gd`: spawn `safe.tscn` for `loot_safe` markers instead of `money_pile.tscn`, using the same seeded RNG, and cap at 8 safes per match.
- `shared/loot/safe.gd` (`StaticBody3D` + interact `Area3D`): states `LOCKED`, `CRACKING`, `OPEN`. `start_crack(peer_id)` / `cancel_crack(peer_id)` are server-validated (player within 2 m, alive, not already cracking another safe).
- Crack progress accumulates `delta` only while the player holds the interact key and stays within 2 m; any of {moved out of range, released key, died, got knocked} cancels and **resets progress to 0** (no partial credit). At `>= 5.0 s` the safe pays `CashService.grant(peer_id, amount, "safe")` once and goes `OPEN`.
- Emit a repeating noise event while cracking: `SoundEvents.emit_noise(global_position, "safe_crack", 150.0)` every 1.0 s (150 m radius — loud enough to pull a nearby squad, quieter than a gunshot). Bots subscribe to the same event bus as `bot-perception`, so no bot-specific hook.
- Replicate a `crack_progress: float` 0–1 to clients within 30 m so the HUD can draw the channel bar; on cancel replicate the reset.
- Only one player may crack a given safe at a time; a second `start_crack` is refused while `CRACKING` by another peer.

## Acceptance
- GUT test `tests/test_safe.gd`:
  - Ticking `start_crack` + 5.0 s of `_process` grants once, amount within 800–1500, state `OPEN`; a second 5 s channel grants nothing.
  - Cancelling at 4.9 s then re-cracking requires a full further 5.0 s (progress reset to 0).
  - A second peer's `start_crack` while another is cracking returns `false`.
  - Cracking emits ≥ 5 noise events over 5 s with radius 150.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

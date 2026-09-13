# HIGH — Magazines, partial mags, chamber +1 and ammo types

**Category:** gun
**Priority:** HIGH
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-weapon-base

## Files
- `shared/weapons/magazine.gd` (new)
- `shared/weapons/ammo_pool.gd` (new)
- `server/combat/reload_controller.gd` (new)
- `tests/shared/test_magazine.gd` (new)

## Issue
Weapons can fire forever because there is no ammunition. The design is PUBG-style: mags are objects, a partial mag you swap out is kept as a separate partial mag rather than merged, there is a chamber +1 round, and ammo is bought per cartridge box in the wrist store. That interacts directly with inventory weight and with the economy, so it has to be modelled properly rather than as a single ammo counter.

## Fix
- `shared/weapons/magazine.gd`, `class_name Magazine extends RefCounted`: `cartridge_id`, `capacity`, `rounds`, `is_partial()` = `rounds < capacity`. Mags are inventory items with weight (`data/items.json` gives `mag_<cartridge>` a weight per round plus a base).
- `shared/weapons/ammo_pool.gd`, `class_name AmmoPool`: per-player, holds `mags: Dictionary[cartridge_id -> Array[Magazine]]` and loose `boxes: Dictionary[cartridge_id -> int]` (bought ammo arrives as loose rounds).
  - `best_mag(cartridge_id) -> Magazine` picks the **fullest** mag (PUBG behaviour), `take_mag()` removes it, `store_mag(mag)` keeps a partial one as-is — never merge partials automatically.
  - `refill_from_boxes(cartridge_id)` is an explicit action (a "load magazines" inventory verb), moving loose rounds into partial mags oldest-first.
  - `total_rounds(cartridge_id)` for the HUD.
- Weapon state additions: `mag: Magazine` (currently inserted, may be null), `chambered: int` (0 or 1).
  - Firing consumes `chambered` first, then pulls one from `mag` into the chamber. `rounds_available() = chambered + (mag ? mag.rounds : 0)`.
- `server/combat/reload_controller.gd` (server authoritative, the client only predicts the animation):
  - `start_reload(player, weapon, tick)` — refused when already reloading, when no mag with rounds exists, or when the mag is already full and `chambered == 1`.
  - Two durations from `data/weapons.json`: `reload_s` (tactical, chamber kept → the new mag plus the chambered round, so `mag_size + 1`) and `reload_empty_s` (bolt drop, slower, `chambered` becomes 1 from the new mag). Bolt/pump weapons instead reload `rounds_per_load` at a time and can be interrupted between rounds.
  - Reload can be **cancelled** by sprinting, swapping, vaulting or firing (for shell-by-shell weapons the rounds already loaded are kept).
  - On completion: `store_mag(old_mag)` if it has rounds, `mag = take_mag()`, set `chambered` per the tactical/empty rule, emit `signal reload_finished(player_id, weapon_id, rounds)`.
- Swap speed comes from the weapon's `ergonomics` (`swap_s = base_swap / ergonomics`); swapping cancels any reload.
- The HUD ammo readout is `chambered + mag.rounds` / `total_rounds(cartridge)`.

## Acceptance
- GUT file `tests/shared/test_magazine.gd`:
  - `test_chamber_plus_one()` — a 30-round weapon reloaded tactically with a full mag and a chambered round reports `rounds_available() == 31`.
  - `test_partial_mags_kept_separate()` — swap out a mag with 12 rounds, then a second with 7: the pool holds two partial mags of 12 and 7, not one of 19.
  - `test_best_mag_is_fullest()` — with mags of 7, 30 and 12 rounds, `best_mag` returns the 30.
  - `test_empty_reload_is_slower_and_chambers()` — reloading from a truly empty weapon takes `reload_empty_s` ticks and ends with `chambered == 1` and `mag.rounds == mag_size - 1`.
  - `test_reload_cancel_keeps_state()` — cancelling a mag-fed reload halfway leaves the original mag inserted with its original count.
  - `test_refill_from_boxes()` — 40 loose 5.56 rounds into two partial mags (12 and 7 of 30) fills them to 30 and 29 and leaves 0 loose.
- Manual: fire an M16A1 dry, reload (slower, bolt drop), fire 5, tactical-reload (faster, ammo count shows 31), and confirm the dropped partial mag reappears in the inventory as its own stack.

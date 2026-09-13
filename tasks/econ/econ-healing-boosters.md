# MEDIUM — Healing items and boosters

**Category:** econ
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M4
**Depends on:** econ-store-catalog, econ-inventory, move-stamina

## Files
- `shared/consumables/consumable_use.gd` (new)
- `server/economy/consumable_service.gd` (new)
- `data/items.json` (modify)
- `tests/test_consumables.gd` (new)

## Issue
Healing ($50–600: bandage, first-aid kit, morphine, medkit) and boosters ($100–300: coffee, stim, painkiller) are priced in the catalog but do nothing when bought, so the only use for cash is guns and there is no way to recover from a fight without dying. Use times, heal amounts and booster effects must be data, not code.

## Fix
- Extend each consumable entry in `data/items.json` with `{"use_time_s", "heal": int, "heal_over_time": {"hp_per_s", "duration_s"}, "effects": {...}, "cancel_on_damage": bool}`. Suggested values to fill in: bandage 4 s / +15 HP (cap 75), first-aid kit 6 s / heal to 75, morphine 5 s / +30 over 8 s and ignores the limp, medkit 10 s / full 100. Coffee: stamina regen ×1.5 for 90 s. Stim: +12% move speed and stamina regen ×1.5 for 45 s, plus aim jitter +20%. Painkiller: −30% incoming-damage flinch and +10 HP over 20 s.
- `shared/consumables/consumable_use.gd`: pure channel logic (start, accumulate, cancel) usable by the client for the progress bar and by bots; injected time so it is headless-testable.
- `server/economy/consumable_service.gd` (server only) is authoritative: `use(item_id)` RPC → validate the item is in the inventory, the player is alive/not knocked, not sprinting, not swimming, and not already channelling. Channel for `use_time_s`; **cancel on taking damage** when `cancel_on_damage` (bandage/first-aid/medkit yes, morphine/painkiller no) or on sprint/swim/vehicle entry. Only on completion: remove one from the inventory, apply the heal/effect.
- Health cap rule: instant-heal items cap at their listed ceiling (bandage cannot take you past 75); medkit alone reaches 100.
- Effects are tracked in a per-player `active_effects` dictionary with expiry timestamps; `move-stamina` reads a `stamina_regen_mult`, the movement controller reads `move_speed_mult`, and the weapon sway reads `aim_jitter_mult`. Stacking the same booster refreshes the duration rather than adding a second instance.
- Replicate active-effect ids + remaining time to the owning client for the HUD icons.

## Acceptance
- GUT test `tests/test_consumables.gd`:
  - At 40 HP, a completed bandage gives 55 HP; a second bandage gives 70; a third gives 75 (cap), not 85.
  - Taking damage at 3.0 s of a 4 s bandage cancels it: no heal, item **not** consumed.
  - Morphine is not cancelled by damage and applies 30 HP over 8 s (assert HP at t=4 s is +15).
  - Drinking coffee twice does not stack the multiplier (still 1.5) but resets the remaining duration to 90 s.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

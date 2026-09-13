# MEDIUM — Attachments: scopes, suppressor, bipod, drum, foregrip, bayonet

**Category:** gun
**Priority:** MEDIUM
**Status:** TODO
**Milestone:** M3
**Depends on:** gun-weapon-base, gun-reload-mags

## Files
- `shared/weapons/attachments.gd` (new)
- `data/items.json` (modify)
- `data/weapons.json` (modify)
- `client/player/scope_view.gd` (new)
- `tests/shared/test_attachments.gd` (new)

## Issue
The store sells scopes (M84, ART, PSO-1), a rare suppressor, bipods, drum mags, foregrips and bayonets at $150–1200, but weapons have no attachment slots so none of it can do anything. Attachments are the main money sink between rifles and the reason to keep earning after a first purchase.

## Fix
- Extend `data/weapons.json` per weapon with `"attach_slots": ["optic", "muzzle", "underbarrel", "magazine", "bayonet"]` — only the slots that weapon actually accepts (a Mosin takes `optic` and `bayonet`, an M60 takes `underbarrel` only, etc.).
- Extend `data/items.json` for each attachment with `"category": "attachment"`, `"slot": "attachment"`, `"attach_slot": "<optic|muzzle|underbarrel|magazine|bayonet>"`, `"fits": ["m16a1", "xm177", ...]` (explicit whitelist — era correctness matters, a PSO-1 does not go on an M16), plus a `"mods"` dictionary of multiplicative/additive modifiers.
- `shared/weapons/attachments.gd`, `class_name Attachments`, static and pure:
  - `static can_attach(weapon_id, item_id) -> bool` — the weapon exposes the slot **and** the item's `fits` list contains the weapon id.
  - `static apply(weapon_data: Dictionary, attached: Dictionary) -> Dictionary` returns an **effective** weapon-stat dictionary. Never mutate the loaded data. Modifier keys and their maths:
    - `ads_time_mult`, `spread_mult`, `recoil_vertical_mult`, `recoil_horizontal_mult`, `sway_mult`, `ergonomics_mult`, `reload_mult` — multiply.
    - `zoom` (optic only) — replaces the ADS FOV: M84 ≈ 2.5×, ART ≈ 3×, PSO-1 ≈ 4×.
    - `mag_size_add` (drum mag) — adds to `mag_size`, with `reload_mult` and a weight penalty.
    - `loudness_mult` (suppressor, 0.35) and `muzzle_flash: false` — feeds `audio-gunshots-propagation`'s distance tiers and `bot-perception`'s hearing radius, which is the suppressor's real value.
    - `melee_bonus` (bayonet) — read by `gun-melee`.
  - Apply order is fixed: multiply all multipliers together in the slot order `optic, muzzle, underbarrel, magazine, bayonet`, so the result is order-independent and testable.
- Attachment weight adds to `PlayerState.weight`, which feeds `Stamina.weight_mult` — a scoped, bipodded rifle genuinely costs sprint time.
- Bipod: only active while prone (or crouched against a ledge); when active, multiply recoil by its `deployed_recoil_mult` and sway by `deployed_sway_mult`. Deploying takes 0.5 s and is cancelled by any stance change.
- `client/player/scope_view.gd`: renders a scope reticle overlay (magnified `SubViewport` for `zoom >= 3`, a simple FOV change plus reticle texture below that) and applies `ads_sensitivity_mult / zoom` to the mouse sensitivity while aiming.
- Purchasing and slot-fitting go through `econ-store-catalog`/`econ-inventory`; here just expose `can_attach` for them to call.

## Acceptance
- GUT file `tests/shared/test_attachments.gd`:
  - `test_fit_whitelist()` — `can_attach("m16a1", "scope_pso1")` is false; `can_attach("svd", "scope_pso1")` is true.
  - `test_apply_is_order_independent()` — applying `{optic: x, muzzle: y}` and `{muzzle: y, optic: x}` yields identical effective stats.
  - `test_suppressor_reduces_loudness()` — the effective `loudness_mult` is 0.35 ±0.001 and `muzzle_flash == false`.
  - `test_drum_mag_size_and_reload()` — an AK drum raises `mag_size` from 30 to 75 and multiplies `reload_s` by its `reload_mult` (> 1.0).
  - `test_bipod_only_prone()` — the effective recoil with a bipod equipped but standing equals the un-bipodded recoil; prone and deployed, it is strictly lower.
  - `test_does_not_mutate_data()` — after `apply`, `GameData.get_weapon("m16a1").ads_time_s` is unchanged.
- Manual: buy a PSO-1 for an SVD, attach it, and confirm the scope view magnifies, the sensitivity scales down, and the extra weight shortens the sprint before stamina empties.

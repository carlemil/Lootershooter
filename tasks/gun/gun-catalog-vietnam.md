# HIGH — Full Vietnam-era weapon catalog in data/weapons.json

**Category:** gun
**Priority:** HIGH
**Status:** TODO
**Milestone:** M3
**Depends on:** infra-data-loader, gun-weapon-base, gun-reload-mags

## Files
- `data/weapons.json` (modify)
- `data/cartridges.json` (modify)
- `data/items.json` (modify)
- `data/prices.json` (modify)
- `tests/shared/test_weapon_catalog.gd` (new)

## Issue
`data/weapons.json` holds three placeholder weapons, but the store catalog in the design lists the full era-correct arsenal across nine classes at fixed price bands. Until they all exist with real stats, the economy has nothing to sell and the ballistics code is exercised by one rifle.

## Fix
- Add every weapon from plan section 3.3, each with the full stat block already consumed by `gun-weapon-base`/`gun-reload-mags`/`gun-attachments` (`name, class, cartridge, rpm, fire_modes, mag_size, reload_s, reload_empty_s, ads_time_s, ads_fov, cycle_s, ergonomics, recoil{vertical[], horizontal, recovery, recovery_delay_s, reset_s}, spread{base_hip, base_ads, move_penalty, first_shot_accuracy}, attach_slots, weight`):
  - Pistol: `m1911a1` (.45 ACP, 7), `tt33` (7.62×25, 8), `makarov_pm` (9×18, 8), `sw_model10` (.38 Spl, 6 revolver — no mag, `reload_s` per full cylinder).
  - SMG: `m3a1_grease` (.45, 30, ~450 RPM), `pps43` (7.62×25, 35, ~650), `k50m` (7.62×25, 35, ~700).
  - Shotgun: `ithaca37` (12 ga, 5, pump), `winchester1897` (12 ga, 5, pump).
  - Carbine: `m1_carbine` (.30 Carbine, 15, semi), `m2_carbine` (.30 Carbine, 30, semi+auto ~750), `sks` (7.62×39, 10, semi).
  - Rifle: `m14` (7.62×51, 20, semi+auto), `m1_garand` (.30-06 → add cartridge `3006` at 850 m/s, 8, semi, en-bloc clip), `mosin_m44` (7.62×54R, 5, bolt).
  - Assault: `m16a1` (5.56, 30, semi+auto ~750), `xm177` (5.56, 30, ~800), `ak47` (7.62×39, 30, ~600), `akm` (7.62×39, 30, ~600), `type56` (7.62×39, 30, ~600).
  - LMG: `m60` (7.62×51, 100 belt, ~550), `rpd` (7.62×39, 100 drum, ~650).
  - Sniper: `m40` (7.62×51, 5, bolt), `m21` (7.62×51, 20, semi), `mosin_pu` (7.62×54R, 5, bolt), `svd` (7.62×54R, 10, semi).
  - Launchers are `gun-launchers`; list only their ids here so prices exist.
- Era check: every weapon must plausibly exist by 1975 — no Picatinny rails, no red dots, no polymer. Put the in-service year in a `"year"` field and let the test enforce `year <= 1975`.
- Add the missing cartridge `3006` to `data/cartridges.json` and make sure `12ga_buck` keeps `pellets: 8`.
- Add a matching entry to `data/items.json` (slot `primary` or `sidearm`, real `weight` in kg — an M60 is ~10.5 kg, an M1911 ~1.1 kg) and a price in `data/prices.json` inside the plan's bands: pistol 200–300, SMG 600–800, shotgun 700–900, carbine 700–1100, rifle 1000–1400, assault 1800–2500, LMG 3200–3800, sniper 2600–4000.
- Balance rule of thumb to apply while tuning: `base_damage` on the cartridge, not the weapon; the weapon differentiates through RPM, recoil, ergonomics and mag size. Keep 7.62×39 and 5.56 within one chest shot of each other so no rifle is strictly dominant.
- Recoil `vertical` arrays: 8–12 entries, rising then flattening; heavier cartridges start higher; LMGs have high early climb but a long flat tail.

## Acceptance
- GUT file `tests/shared/test_weapon_catalog.gd`:
  - `test_all_classes_present()` — at least one weapon exists for each of `pistol, smg, shotgun, carbine, rifle, assault, lmg, sniper`, and the total weapon count is ≥ 25.
  - `test_prices_in_band()` — every weapon's price falls inside its class band from plan 3.3 (parametrised over the band table).
  - `test_era_check()` — every weapon has `year <= 1975` and `year >= 1891` (Mosin).
  - `test_stats_sane()` — for every weapon: `rpm` in 30..1200, `mag_size` in 1..250, `ads_time_s` in 0.15..0.9, `weight` in 0.6..12.0, `recoil.vertical` non-empty and non-decreasing over its first 3 entries.
  - `test_cartridges_resolve()` — every `cartridge` id exists (re-run of the `infra-data-loader` check over the now-full catalog).
- Manual: open the wrist store and confirm every category tab has stock at the intended prices; fire one weapon from each class and confirm none crashes on a missing key.

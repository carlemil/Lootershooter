# Lootershooter — Plan

Vietnam-era first-person battle royale with a Counter-Strike money economy. Godot 4.4+ / GDScript client and headless dedicated server (Docker), 2–20 players in teams of 1–4, 15-minute matches, player-like bots.

This file is the source of truth for project state. Tasks live in `tasks/<cat>/<cat>-<name>.md` (see §5); work them with the orchestrator flow described in `CLAUDE.md`. The presentation version of this plan is `docs/plan.html`.

## Status

| Milestone | Scope | Status |
|---|---|---|
| M0 | Scaffold: project, GUT, export presets, Docker, registry, data loader | TODO |
| M1 | Netcode core: ENet, spawn, input stream, snapshots, prediction, lag-comp | TODO |
| M2 | Movement and stamina | TODO |
| M3 | Weapons and ballistics | TODO |
| M4 | Economy, loot, wrist store, inventory | TODO |
| M5 | Zone, hot zones, match flow, drop-in, teams | TODO |
| M6 | World: terrain, town, hamlets, outposts, rivers, tunnels, navmesh | TODO |
| M7 | Vehicles | TODO |
| M8 | Bots and learning | TODO |
| M9 | UI and audio | TODO |
| M10 | Polish and hardening | TODO |

**Vertical slice order (first playable loop):** M0 → M1 → 15,16,20,22 → 23,24,26,27,29 → 35,36,39,40,41 → 45,47,48 → 51 (blockout) → 64–68 → 73,74,76.

**Next task:** `tasks/infra/infra-godot-project.md`

## Queue / follow-ups

- (empty)

---

## 1. Locked design decisions

| Area | Decision |
|---|---|
| Engine | Godot 4.4+ (latest stable at scaffold time), GDScript, one project, two export presets: `client-windows`, `server-linux` (Dedicated Server export mode + `--headless`) |
| Netcode | ENet via `MultiplayerAPI`. Server-authoritative. Server tick 30 Hz, client 60+ Hz. Client-side prediction + reconciliation for own movement; interpolation for others; lag-compensated (rewound) hit registration on server |
| Server hosting | One container = one match instance (up to 20 slots, loops lobby → 15-min match → results). Scale = more containers. `docker compose` for local dev |
| Server browser | Tiny registry service (Python stdlib `http.server`, ~60 lines, own container). Game servers POST heartbeat every 10 s; clients GET `/servers`. In-game list with name, map, players, ping, mode |
| Perspective | First-person only. Arms + weapon viewmodel for self, full-body third-person model for others |
| Players | 2–20 humans, bots fill to a configurable target (default 20). Teams: solo / duo / trio / squad (1–4) |
| Match | No hard cap. At 15:00 the circle has closed completely (radius 0 m). The match then runs on for the seconds it takes the second-to-last team to bleed out from the outside-zone damage ramp. Win = last team alive. Cash on hand is a scoreboard stat, never a tiebreak |
| Zone | No phases. Safe circle radius shrinks continuously from R0 to 0 over 15 min. Center **wanders** along a smooth noise path, telegraphed on the minimap 30 s ahead. Outside: cash drains −$20/s, and health damage ramps with *both* continuous time outside and distance from the edge: effective time = t_outside × (1 + d_outside / 200 m), damage per second = max_health × min(1, effective / 60). So 100%/s after 60 s at the edge, after 30 s at 200 m out, after 15 s at 600 m out. Stepping back in resets the ramp. You really want to be inside |
| Hot zones | 2–3 at a time, spawn/expire over the match. Pay cash per second to everyone inside, scaled by proximity to the zone center (linear falloff). Visible on minimap. Each pays more the longer it's been alive (pot grows) |
| Economy | Everyone starts with $800. Income: money piles (buildings), safes, kill drops (victim's unspent cash + $300 bounty), hot-zone ticks. Money is the **only** loot. Per match; nothing persists |
| Store | Wrist "pipboy" store, open anywhere. Raising it takes 1.5 s, lowers weapon, still can move/walk. Buy → item goes to inventory only if slot/weight fits, else refused. Fixed catalog and prices |
| Inventory | Slots (primary ×2, sidearm, melee, throwables ×4, gadget ×2, armor, helmet, backpack) + backpack-tier capacity for consumables/ammo, with weight affecting stamina |
| Movement | stand, crouch-walk, prone/crawl, walk, run, sprint, jump, vault/mantle (≤1.5 m), ladder climb, lean L/R, dive (sprint → prone) |
| Stamina | 100 pool. Sprint −10/s, dive −25, jump −8, ADS hold −2/s (sway rises when < 30). Regen +15/s after 1 s. Weight and armor tier scale drain |
| Weapons | Vietnam-era only (list §3). Realistic ballistics: projectile sim with gravity + drag, per-cartridge muzzle velocity, penetration with energy loss, ricochet at shallow angles, hit-zone multipliers, armor with durability |
| Vehicles | Civilian ground only: sedan, pickup, motorbike/scooter, motorcycle + sidecar, three-wheeler cargo (Lambro), tractor. Suggested add: sampan/longtail boat for canals (still civilian, no air). Fuel, shootable tires, exposed occupants |
| Drop-in | Match starts on an orbital reentry screen: pick a spot on the map, reentry capsule → freefall with steering → parachute (auto at 300 m, manual any time above). Purely a state machine; no orbital physics |
| Bots | Server-only. Utility AI + personality profiles. "Learning" = server records real-player heatmaps (drop spots, loot routes, engagement ranges, hot-zone timing) into a JSON that bots sample from. Difficulty knobs: reaction time, angular aim error, perception, decision noise |
| Map | 2 km × 2 km. Terrain3D. Biomes: rice paddies (flooded, slow, hides prone), jungle hills, rubber plantation, riverine + canals, small town (market, temple, colonial blocks 3–4 floors), 5 hamlets (stilt houses), 3 military outposts (sandbags, bunker, watchtower, more cash), bridge, tunnel network (Cu-Chi-style flank routes) |
| Testing | GUT (Godot Unit Test) addon; CLI run `godot --headless -s addons/gut/gut_cmdln.gd -gexit`. Task files follow the `tasks/<cat>/<cat>-<name>.md` format your `/tdd` skill parses |

---

## 2. Architecture

```
Lootershooter/
  project.godot
  addons/                gut/, terrain3d/
  shared/                runs on BOTH sides: player controller, ballistics, inventory,
                         zone math, items catalog loader, net messages
  server/                match loop, spawner, lag-comp history, loot/money spawner,
                         hot zones, bots/, learning recorder, registry heartbeat
  client/                UI (HUD, wrist store, minimap, server browser), viewmodels,
                         audio, input, prediction/reconcile
  world/                 map scenes, kits, navmesh bake, loot spawn markers
  data/                  weapons.json, cartridges.json, items.json, prices.json, bots.json
  tests/                 GUT tests (unit tests target shared/ + server/ logic)
  docker/                Dockerfile (multi-stage: export → slim runtime), docker-compose.yml
  registry/              server browser registry (python stdlib), Dockerfile
  tools/                 export.ps1, run-local-server.ps1, bake scripts
  docs/                  plan.html (the webpage), design notes
  PLAN.md                the plan document (orchestrator source of truth)
  CLAUDE.md              conventions, test command, run commands
  tasks/<cat>/*.md       small tasks
```

Key rules baked into `CLAUDE.md`:
- Server never trusts client input beyond `{input_vector, look, buttons, tick}`; every economy/damage decision is server-side.
- Shared code is deterministic-ish (fixed tick, no `randf()` without seeded RNG) so prediction and server agree.
- Data-driven: no weapon stats in scripts; everything in `data/*.json` with a loader + schema check test.
- Bots use the *same* `PlayerState` and input path as humans (they feed inputs), so no bot-only cheats and netcode stays single-path.
- One task = one commit (orchestrator contract).

Networking detail:
- Movement: client sends input each tick, predicts locally, server simulates authoritatively, sends state snapshots (20 Hz, delta-compressed) and the last processed input tick; client rewinds/replays.
- Shooting: client sends `fire {tick, origin, dir}`; server rewinds hitboxes to that tick (200 ms history ring), runs the projectile sim from that state.
- Projectiles live server-side only; clients get a `tracer` event (origin, dir, velocity) and simulate visuals locally.
- Interest management: simple, all 20 players replicated (20 × 20 Hz is fine); loot/money piles via `MultiplayerSpawner` with visibility by distance.

Docker:
- Stage 1: official Godot headless + Linux export templates, `godot --headless --export-release "server-linux" /out/server.x86_64`.
- Stage 2: `debian:bookworm-slim`, copy binary + pck, `ENTRYPOINT ["./server.x86_64","--headless","--","--port=7777","--registry=http://registry:8080"]`.
- `docker-compose.yml`: `registry` + `game1` (+ optional `game2`) on host network or mapped UDP ports.

---

## 3. Design spec (what goes on the webpage and in PLAN.md)

### 3.1 Match flow
1. Lobby (server browser → join → team select, ready) → countdown when ≥2 players or on host timer; bots fill remaining slots.
2. Orbit screen: map overview, choose drop point (team leader chooses, teammates cluster within 150 m). 20 s timer.
3. Drop: reentry (5 s, no control) → freefall (steer, up to 60 m/s, tilt for lateral 15 m/s) → chute (auto 300 m, manual earlier for glide) → land.
4. Match. Zone radius shrinks linearly R0 = 1200 m → 0 m at 15:00. Center wanders (Perlin path, max 1.5 m/s). Hot zones spawn at 1:00, 5:00, 9:00 (each lives 3–4 min).
5. End: last team alive. After 15:00 the circle is gone and the outside-damage ramp (100%/s after 60 s) ends the match within about a minute. Scoreboard: kills, cash earned, cash spent, distance, hot-zone time.
6. Return to lobby, same server, next match.

### 3.2 Economy
- Start $800. Cash is a number on the player; only loot is cash.
- Money piles: hamlet house $50–150, town building $100–300, outpost $200–500, safe $800–1500 (5 s to crack, loud, only in town/outposts). ~300 piles across map, ~40% of world value in the town + outposts.
- Kill: victim drops a cash bag containing all their unspent money + $300 bounty; bag lasts 90 s. Knocked (in teams) drops nothing until finished.
- Hot zone tick: $8/s at center → $0 at edge, shared per person (not per team). A team of 4 at center earns $32/s.
- Outside zone: −$20/s cash drain, plus health damage that ramps with continuous time outside AND distance from the edge: `t_eff = t_outside * (1 + d_outside / 200)`, `dmg_per_s = max_health * min(1, t_eff / 60)`. Caps at 100% of max health per second: 60 s at the edge, 30 s at 200 m out, 15 s at 600 m out. Re-entering resets `t_outside`. A rich player outside still bleeds cash first.
- "Rich bounty": anyone carrying > $3000 gets a pulsing marker on all minimaps every 20 s. Creates pressure to spend; keeps the store loop alive.
- No timer tiebreak: the fully closed circle ends the match by attrition. Cash on hand is a scoreboard stat only.

### 3.3 Store catalog (wrist pipboy) — initial prices
| Category | Item | $ |
|---|---|---|
| Pistol | M1911A1 / TT-33 / Makarov PM / S&W Model 10 | 200–300 |
| SMG | M3A1 Grease Gun / PPS-43 / K-50M | 600–800 |
| Shotgun | Ithaca 37 / Winchester 1897 trench | 700–900 |
| Carbine | M1 Carbine / M2 Carbine / SKS | 700–1100 |
| Rifle | M14 / M1 Garand / Mosin M44 | 1000–1400 |
| Assault rifle | M16A1 / XM177 / AK-47 / AKM / Type 56 | 1800–2500 |
| LMG | M60 / RPD | 3200–3800 |
| Sniper | M40 / M21 / Mosin PU / SVD | 2600–4000 |
| Launcher | M79 / M72 LAW (1 shot) / RPG-7 | 2000–4500 |
| Throwable | M67 frag / F1 / M18 smoke / Mk3A2 concussion / Molotov | 150–400 |
| Placeable | M18A1 Claymore / tripwire grenade trap / toe-popper mine | 400–700 |
| Armor | Flak vest (I / II / III), Helmet (M1 steel, w/ visor) | 400–1200 |
| Backpack | Satchel / Rucksack / ALICE pack (cap tiers) | 200–600 |
| Healing | Bandage / First-aid kit / Morphine / Medkit | 50–600 |
| Booster | Coffee (stamina regen) / Stim (speed + regen, jitter) / Painkiller | 100–300 |
| Gadget | Binoculars / Flare gun (illuminates + marks) / Flashlight / Radio (reveals next zone move 60 s ahead) / Ghillie wrap | 150–800 |
| Attachments | Scopes (M84, ART, PSO-1), suppressor (rare, pricey), bipod, drum mag, bayonet, foregrip | 150–1200 |
| Ammo | Per cartridge boxes | 20–80 |
| Vehicle | Fuel can, tire repair | 50–100 |

### 3.4 Ballistics model (server-side, shared code)
- Per cartridge: mass (g), muzzle velocity (m/s), drag coefficient (simple G1 scalar), base damage curve vs energy.
  - 5.56×45 (990 m/s), 7.62×39 (715), 7.62×51 (850), 7.62×54R (830), .30 Carbine (600), .45 ACP (260), 9×18 (320), 7.62×25 (450), 12 ga buck (400, 8 pellets), .38 Spl (260).
- Projectile stepped every server tick (33 ms) as raycast segments; gravity 9.81; velocity decay `v -= k*v²*dt`.
- Damage = base × energy fraction × zone multiplier (head 2.4, neck 1.5, chest 1.0, stomach 0.9, limbs 0.6) × armor (vest/helmet reduce by tier %, lose durability per hit; helmets stop pistol rounds fully at tier II).
- Penetration: material table (wood 0.6, bamboo 0.7, sheet metal 0.4, brick 0.1, concrete 0) × remaining energy; max one wall.
- Ricochet: on hard surfaces when incidence angle < 15°, 30% chance, 40% energy kept.
- Weapon: RPM, fire modes, recoil pattern (vertical climb + horizontal random seeded), sway (stance/stamina/weight), spread (ADS/hip/moving), reload (mag swap; partial mags kept as separate mags PUBG-style), chamber +1, first-shot accuracy, aim-down-sight time, ergonomics affecting swap speed.
- Tracers every 5th round on LMGs; audio: supersonic crack + delayed report by distance.

### 3.5 Movement & stamina — see §1. Extra: leaning blocks sprint; crawling in paddy water hides you from bots' vision at > 40 m; vaulting cancels ADS; dive gives 0.3 s of no-aim.

### 3.6 Vehicles
Sedan (4 seats, 90 km/h), pickup (2 + 3 bed, exposed), scooter (1 + pillion, 55 km/h, quiet), motorcycle + sidecar (3, gunner can shoot), Lambro three-wheeler (1 + 4 in cargo, slow, tanky), tractor (very slow, high HP, offroad). Suggested sampan (4, canals/river). Simple arcade `VehicleBody3D` tuning; fuel 0–100; tires shootable; engine noise audible 250 m; horns.

### 3.7 Bots
- Utility scorer over actions: `loot`, `move_to_zone`, `go_hot_zone`, `engage`, `flank`, `retreat_heal`, `buy`, `drive`, `camp`, `revive_teammate`.
- Profiles (weights): Rusher, Looter, Camper, Opportunist, Squad-follower.
- Perception: view cone 110°, distance-based detection with occlusion raycasts, hearing (gunshots 600 m, vehicles 250 m, footsteps 20 m).
- Aim: target point + angular error N(0, σ) where σ shrinks with time-on-target; reaction delay 250–700 ms by difficulty; leads moving targets by measured velocity.
- Navigation: NavigationServer3D on baked navmesh; navigation links for vault/ladder/tunnel entrances; vehicle paths on road spline graph.
- "Learning" recorder (server): every 2 s writes player positions, per-building loot events, engagement distance histogram, drop picks, purchases to `learn/<date>.jsonl`; a nightly (or per-match) aggregator produces `data/bots_learned.json` (heat grid 64×64, loot-route popularity, buy priorities). Bots sample from it with ε-noise so they're not identical.
- Must also do the human stuff: buy from the wrist store, drive, throw grenades, revive, spectate-worthy behaviour.

### 3.8 World
- Terrain3D heightmap 2048 m, hand-painted biomes + splat maps; foliage via Terrain3D instancer.
- Modular kits: stilt house, hut, market stall, temple, colonial block, bunker, sandbag, watchtower, bridge, tunnel segments, fences, paddies dikes.
- Loot markers as `Marker3D` groups per building tier; money spawner picks from markers with tier weights.
- Roads spline → vehicle nav + bot driving; canals with `Area3D` water volumes (swim slow, no sprint, weapons holstered; drop heavy backpack to swim faster).
- Day + dusk variants first; monsoon rain later (masks audio, lowers bot perception).

### 3.9 UI
- HUD: health, stamina, cash, compass strip, ammo, zone timer, kill feed, team panel, DBNO indicators.
- Minimap (top-right, rotates), full map (M) with zone, wander preview, hot zones, pings, bounty markers.
- Wrist store: 3D wrist device with a `SubViewport` UI; category tabs, item cards, "fits in inventory" check, purchase confirmation.
- Inventory (Tab): slots, weight bar, drag/drop, attachments.
- Server browser: list, filters (mode, region/ping), refresh, direct connect by IP.
- Spectate after death (teammates), end scoreboard.

### 3.10 What you missed (recommended additions, all included in tasks marked *stretch* where big)
1. **Sound propagation** — the single biggest thing for a FPS: distance-based gunshot falloff, supersonic crack, footsteps by surface, vehicle noise, rain masking. Included in core tasks.
2. **Knock-down / revive (DBNO)** in team modes, plus spectate.
3. **Ping system** (Apex style) — needed for teams without voice.
4. **Tunnels & booby traps** — Vietnam flavour, flank routes, cheap area-denial.
5. **Smuggler truck event** — replaces the airdrop: a civilian truck spawns on a road, drives a route, carries $2500; hijack it or blow it.
6. **Rich bounty marker** (>$3000) — economy pressure valve.
7. **Radio gadget** reveals the zone's next wander direction — information as an item.
8. **Weather/time variants** — dusk + rain change bot perception and sound.
9. **Swimming rules** for the canals (drop pack, holster).
10. **Anti-cheat basics**: server authority, input rate limits, speed/teleport sanity, fire-rate checks, per-match seed.
11. **Match stats & kill cam** (replay last 5 s from server history).
12. **Accessibility/settings**: rebindable keys, FOV, sensitivity, colourblind minimap, subtitles for callouts.
13. **Match seed + deterministic loot layout** so replays/debugging work.
14. **Telemetry** for tuning prices and bot difficulty (same recorder as the bots).

---

## 4. Free assets (all CC0 unless noted — verify licence at download time)

| Need | Source |
|---|---|
| Terrain | [Terrain3D](https://tokisan.com/terrain3d/) (MIT, Godot 4.4+, GDExtension, foliage instancer with LODs) |
| Ground/wall textures | [ambientCG](https://ambientcg.com) (CC0), [Poly Haven](https://polyhaven.com) textures + HDRIs (CC0) |
| Foliage (bamboo, palms, grass, jungle) | Poly Haven models (CC0), Quaternius *Ultimate Nature Pack* (CC0), Kenney *Nature Kit* (CC0) |
| Buildings/props | Kenney *City Kit*, *Furniture Kit*, *Survival Kit*, *Tower Defense* sandbags (CC0); KayKit bits packs (CC0); Quaternius *Ultimate Buildings* (CC0). Stilt houses/temples: OpenGameArt CC0 search, otherwise kitbash from Kenney pieces |
| Vehicles | Kenney *Car Kit* (sedan, pickup, tractor, CC0); Quaternius *Ultimate Vehicles* (scooter/motorbike, CC0) |
| Weapons | Sketchfab free (check CC-BY vs CC0 per model): [Low-Poly Weapon Asset Pack](https://sketchfab.com/3d-models/low-poly-weapon-asset-pack-762c43cc1532421eb0452b64e2bdd483) (M60, M16), [M60 Vietnam](https://sketchfab.com/3d-models/m60-machine-gun-vietnam-war-2f21855be3f545749239efaa5f1c8ff1), [Low Poly AK-47](https://sketchfab.com/3d-models/low-poly-ak-47-9ee0f5c01dfe4f09a61d60b450ec5117); OpenGameArt [CC0 3D Weapons](https://opengameart.org/content/cc0-3d-weapons) and [AK-47 low poly pack](https://opengameart.org/content/ak-47-low-poly-weapon-pack-wip). Gaps (M14, SKS, M79, PPS-43) → placeholder from Kenney *Blaster Kit* shapes until modelled |
| Characters / arms | Quaternius *Universal Animated Characters* (CC0, rigged), KayKit character packs (CC0); FPS arms: Quaternius rig cropped. Animations: Mixamo (free to use in games, not redistributable as-is) or Quaternius packs |
| UI, icons, fonts | Kenney *UI Pack*, *Game Icons*, *Input Prompts* (CC0); Google Fonts |
| Audio | Kenney *Audio* packs (CC0), freesound.org (filter CC0), Sonniss GDC bundles (royalty-free) for gunshots/jungle ambience |
| Skins | Recolour texture atlases of the character pack (cheap, CC0 stays CC0) |

Sources found in search: [Godot dedicated server docs](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_dedicated_servers.html), [briancain/GodotServer-Docker](https://github.com/briancain/GodotServer-Docker), [rivet-dev/godot-docker](https://github.com/rivet-dev/godot-docker), [Terrain3D asset](https://godotengine.org/asset-library/asset/3892), [itch.io CC0 3D](https://itch.io/game-assets/assets-cc0/tag-3d), [Kenney on Godot forum](https://forum.godotengine.org/t/kenneys-assets-free-and-creative-commons-cc0/36658).

---

## 5. Milestones and tasks (what goes into `tasks/`)

Task categories (directories): `infra`, `net`, `move`, `gun`, `econ`, `zone`, `world`, `veh`, `bot`, `ui`, `audio`, `polish`. Priority HIGH = on the critical path to a playable loop.
Each task below becomes `tasks/<cat>/<cat>-<name>.md` with Files / Issue / Fix / acceptance test.

**M0 — Scaffold (infra)**
1. `infra-godot-project` — project.godot, folder layout, `.gitignore`, `.editorconfig`, git init.
2. `infra-gut-tests` — add GUT, `tests/test_smoke.gd`, `tools/test.ps1`, CI-able command.
3. `infra-export-presets` — client-windows + server-linux presets, `tools/export.ps1`.
4. `infra-dockerfile` — multi-stage export → slim runtime; `docker compose up` runs a server.
5. `infra-registry-service` — python stdlib registry with heartbeat + list, its Dockerfile, compose entry, 1 test.
6. `infra-data-loader` — `data/*.json` schema + loader autoload + test that every weapon references a known cartridge.

**M1 — Netcode core (net)**
7. `net-server-bootstrap` — headless detection, ENet host, port/args parsing, match loop skeleton (lobby/match/results states).
8. `net-client-connect` — connect by IP, handshake (name, team pref), disconnect handling.
9. `net-player-spawn` — `MultiplayerSpawner` for players, server-owned `PlayerState`.
10. `net-input-stream` — client → server input packets with tick numbers; rate limit.
11. `net-snapshot-sync` — 20 Hz snapshots, delta-compressed, last-acked tick.
12. `net-prediction-reconcile` — local prediction + rewind/replay; test with simulated 150 ms latency.
13. `net-lagcomp-history` — 200 ms hitbox ring buffer + rewind API on server.
14. `net-registry-heartbeat` — server posts heartbeat; test.

**M2 — Movement & stamina (move)**
15. `move-controller-base` — `CharacterBody3D` shared controller: walk/run/sprint, gravity, slopes, step-up.
16. `move-stances` — crouch/prone with collider changes and camera height blending.
17. `move-lean` — Q/E lean with wall check.
18. `move-jump-vault-ladder` — jump, mantle detection (≤1.5 m), ladders.
19. `move-dive` — sprint → dive → prone, no-aim window.
20. `move-stamina` — pool, drains, regen, weight/armor scaling; unit tests for the maths.
21. `move-swim` — water volumes, holster, slow, drop-pack option.
22. `move-fp-camera-arms` — first-person camera, arms viewmodel, head bob, FOV settings.

**M3 — Weapons & ballistics (gun)**
23. `gun-cartridge-sim` — projectile stepper (gravity, drag, per-tick raycast); tests for drop at 100/300 m.
24. `gun-hitzones-damage` — hurtboxes, zone multipliers, armor durability; tests.
25. `gun-penetration-ricochet` — material table, energy loss, ricochet rule; tests.
26. `gun-weapon-base` — fire modes, RPM, recoil pattern, sway, spread, ADS; data-driven.
27. `gun-reload-mags` — mag objects, partial mags, chamber +1, ammo types.
28. `gun-attachments` — scopes/suppressor/bipod/drum/foregrip/bayonet effects.
29. `gun-catalog-vietnam` — all weapons in `data/weapons.json` with era-checked stats.
30. `gun-throwables` — frag/F1/smoke/concussion/molotov with cook + arc preview.
31. `gun-placeables` — claymore, tripwire trap, toe-popper.
32. `gun-launchers` — M79, M72 LAW, RPG-7 with vehicle damage.
33. `gun-tracers-fx` — tracers, impact decals, muzzle flash, shell casings.
34. `gun-melee` — knife/bayonet/butt stroke.

**M4 — Economy, loot, store (econ)**
35. `econ-cash-state` — cash on PlayerState, server-only mutation API, events; tests.
36. `econ-money-piles` — marker-based spawner with building tiers, pickup interaction.
37. `econ-safes` — 5 s crack, noise event, big payout.
38. `econ-kill-drop` — cash bag with bounty, 90 s decay.
39. `econ-inventory` — slots, weight, backpack tiers, fits-check; tests.
40. `econ-store-catalog` — `data/items.json` + `prices.json`; server-side purchase validation.
41. `econ-wrist-store-ui` — 3D wrist device + SubViewport UI, raise animation, buy flow.
42. `econ-rich-bounty` — >$3000 marker pulse.
43. `econ-healing-boosters` — bandage/kit/morphine/medkit, coffee/stim/painkiller effects.
44. `econ-armor-helmets` — vest/helmet tiers, durability, visuals.

**M5 — Zone, hot zones, match flow (zone)**
45. `zone-shrinking-circle` — continuous radius to 0 at 15:00, wandering center (seeded noise), cash drain + damage ramp from time outside × distance factor (caps at 100%/s, 60 s at the edge, resets on re-entry); tests.
46. `zone-hot-zones` — spawn schedule, payout falloff, growing pot; tests.
47. `zone-match-loop` — lobby → orbit → drop → match → results → lobby; match clock; win = last team alive, no timer cap or tiebreak.
48. `zone-drop-in` — orbit map pick, reentry → freefall → chute state machine with steering.
49. `zone-teams-dbno` — team assignment, knock-down, revive, spectate teammates.
50. `zone-smuggler-truck` — road event with $2500, hijack/destroy.

**M6 — World (world)**
51. `world-terrain-blockout` — Terrain3D 2 km heightmap, biome splat, roads spline, water volumes.
52. `world-kits-import` — import + organise Kenney/Quaternius/Poly Haven kits, LOD, collision.
53. `world-town` — market, temple, colonial blocks, safes.
54. `world-hamlets` — 5 hamlets with stilt houses, loot markers.
55. `world-outposts` — 3 outposts, bunkers, watchtowers, high-tier cash.
56. `world-paddies-plantation-jungle` — biome dressing, foliage instancing, prone-hide volumes.
57. `world-rivers-bridge-tunnels` — canals, bridge, tunnel network with nav links.
58. `world-navmesh-bake` — navmesh + nav links (vault/ladder/tunnel), road graph for vehicles.
59. `world-lighting-variants` — day, dusk; rain (stretch).

**M7 — Vehicles (veh)**
60. `veh-base-vehiclebody` — enter/exit, seats, fuel, damage, tires, engine audio hooks.
61. `veh-catalog` — sedan, pickup, scooter, sidecar bike (gunner), Lambro, tractor.
62. `veh-net-sync` — server-owned vehicle physics, occupant sync.
63. `veh-sampan` — canal boat (stretch).

**M8 — Bots (bot)**
64. `bot-input-adapter` — bot feeds the same input path as a client.
65. `bot-perception` — vision cone + occlusion + hearing events.
66. `bot-utility-brain` — scorer + actions; profiles in `data/bots.json`.
67. `bot-navigation` — navmesh moves, nav links, cover points.
68. `bot-combat` — aim model with error/reaction, burst discipline, grenades, retreat/heal.
69. `bot-economy` — loot routes, wrist-store purchases by profile.
70. `bot-vehicles-teams` — driving, squad follow, revive.
71. `bot-learning-recorder` — telemetry JSONL + aggregator → `data/bots_learned.json`.
72. `bot-learned-sampling` — bots sample drop/loot/route/buy priors; difficulty knobs.

**M9 — UI & audio (ui, audio)**
73. `ui-hud` — health/stamina/cash/ammo/compass/killfeed/team panel.
74. `ui-minimap-fullmap` — minimap, full map, zone + wander preview, hot zones, pings, bounty.
75. `ui-inventory` — slots, weight, drag/drop, attachments.
76. `ui-server-browser` — list from registry, filters, direct connect.
77. `ui-lobby-orbit-scoreboard` — lobby, team select, orbit pick, results.
78. `ui-settings-keybinds` — rebinds, FOV, sens, audio, accessibility.
79. `audio-gunshots-propagation` — distance tiers, supersonic crack, delayed report.
80. `audio-footsteps-surfaces-vehicles-ambience` — surface footsteps, vehicles, jungle/rain ambience.

**M10 — Polish & hardening (polish)**
81. `polish-anticheat-sanity` — speed/teleport/fire-rate/input-rate checks.
82. `polish-killcam-stats` — 5 s server-history kill cam, match stats.
83. `polish-skins-recolours` — atlas recolours, selection in lobby.
84. `polish-perf-pass` — 20 players + bots on server at 30 Hz within budget; client 60 fps target.
85. `polish-playtest-balance` — price/damage tuning from telemetry.

Suggested order for a first *playable loop* (vertical slice): M0 → M1 → 15,16,20,22 → 23,24,26,27,29 → 35,36,39,40,41 → 45,47,48 → 51 (blockout only) → 64–68 → 73,74,76. Everything else layers on.

---


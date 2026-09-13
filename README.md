# Lootershooter

Vietnam-era first-person battle royale with a Counter-Strike money economy. Godot 4.4+ / GDScript client and headless dedicated server (Docker), 2–20 players in teams of 1–4, a circle that closes to nothing at 15:00, player-like bots.

**The plan:** https://carlemil.github.io/Lootershooter/ (source: `docs/plan.html`). Design decisions, architecture, spec, free assets and the task board live there and only there. Section numbers referenced in task files (§1–§5) point to that page.

Tasks live in `tasks/<cat>/<cat>-<name>.md`; work them with the flow in `CLAUDE.md`. This file tracks project state only.

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

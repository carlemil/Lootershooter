# HIGH — Player spawning and server-owned PlayerState

**Category:** net
**Priority:** HIGH
**Status:** TODO
**Milestone:** M1
**Depends on:** net-client-connect

## Files
- `shared/player/player_state.gd` (new)
- `shared/player/player.tscn` (new)
- `shared/player/player.gd` (new)
- `server/net/player_spawner.gd` (new)
- `tests/shared/test_player_state.gd` (new)

## Issue
Handshake finishes and the server knows a peer exists, but no body is created for it, so there is nothing to move, hit or replicate. Everything downstream (movement, stamina, ballistics, cash, bots) reads and writes one struct, `PlayerState`, and it must be authoritative on the server only. Bots need the exact same node and state as humans so the sim has a single code path.

## Fix
- `shared/player/player_state.gd`, `class_name PlayerState extends RefCounted` — pure data plus trivial accessors, **no** node references, so it can be unit-tested and copied into the lag-comp history ring:
  - Identity: `peer_id: int` (0 for bots), `bot_id: int` (0 for humans), `slot: int`, `team: int`, `display_name: String`, `is_bot: bool`.
  - Transform: `position: Vector3`, `velocity: Vector3`, `look_yaw: float`, `look_pitch: float`.
  - Condition: `health: float = 100.0`, `stamina: float = 100.0`, `stance: int` (enum `STAND, CROUCH, PRONE`), `lean: float` (−1..1), `alive: bool`, `dbno: bool`.
  - Economy/loadout: `cash: int = 800`, `weight: float`, `armor_tier: int`, `helmet_tier: int`, `held_slot: int`.
  - Bookkeeping: `last_input_tick: int`, `spawn_tick: int`.
  - `duplicate_state() -> PlayerState` — a deep-enough copy for the history ring.
  - `to_snapshot() -> Dictionary` / `static from_snapshot(d) -> PlayerState` with **short keys** (`p`, `v`, `y`, `pt`, `h`, `st`, `sn`, `ln`, `c`) to keep snapshot bytes down; only fields other players need go into the public snapshot — `cash` and `stamina` are sent to the owner and teammates only (flag `to_snapshot(full: bool)`).
  - `reset_for_match(spawn_pos: Vector3)` restores health 100, stamina 100, cash 800 (plan: everyone starts with $800, per match only).
- `shared/player/player.tscn`: `CharacterBody3D` root named `Player` with a capsule `CollisionShape3D` (height 1.8, radius 0.35), a `Node3D` `Head` at y = 1.65, a `Node3D` `HitboxRoot` (populated by `gun-hitzones-damage`), and a `MultiplayerSynchronizer` configured later by `net-snapshot-sync`. No camera in the shared scene — the client attaches it in `move-fp-camera-arms` for the local player only.
- `shared/player/player.gd`, `class_name Player extends CharacterBody3D`:
  - `var state: PlayerState`, `var is_server: bool`, `var is_local: bool`.
  - `apply_input(input: Dictionary, delta: float)` — the single entry point for movement, called identically by the server (from received packets and from bot brains) and by the client (prediction). Movement maths itself lands in `move-controller-base`; here it is a stub that stores the input and emits `signal input_applied(tick)`.
  - Sets `set_multiplayer_authority(1)` — the **server** is always the authority; clients never own their body.
- `server/net/player_spawner.gd`: a `MultiplayerSpawner` wrapper on the server:
  - `spawn_player(peer_id: int, team: int, is_bot: bool) -> Player` instantiates `player.tscn`, builds the `PlayerState`, sets `spawn_tick`, adds it under `/root/Server/Players` with the node name `"P%d" % unique_id` (peer id for humans, `1000 + bot_id` for bots so ids never collide) and registers it in a `players: Dictionary[int, Player]`.
  - `despawn_player(unique_id)` frees the node and removes it from the dict and from the lag-comp registry.
  - `spawn_bots_to_target(target: int)` fills the roster with bot players **through the same `spawn_player` call** — bots differ only by `is_bot` and by who feeds their input.
  - The spawner's `spawn_function` sends only `{unique_id, team, display_name, is_bot}` so a client can build a visual body; all other state arrives via snapshots.
- Spawn positions in M1 are a simple ring of `max_players` points at radius 20 m around the origin (`Vector3(cos(a) * 20, 1, sin(a) * 20)`), seeded from the match seed. The real drop-in is `zone-drop-in`.

## Acceptance
- GUT file `tests/shared/test_player_state.gd`:
  - `test_defaults()` — a fresh `PlayerState` has `health == 100.0`, `stamina == 100.0`, `cash == 800`, `alive == true`.
  - `test_snapshot_roundtrip()` — set position `(1.5, 2.0, -3.25)`, yaw 1.2, health 73.5; `from_snapshot(to_snapshot(true))` reproduces all of them exactly (floats compared with `assert_almost_eq`, tolerance 0.001).
  - `test_public_snapshot_hides_cash()` — `to_snapshot(false)` has no `c` key; `to_snapshot(true)` does.
  - `test_duplicate_is_independent()` — mutating the copy's position leaves the original unchanged.
- Manual: with 2 clients connected, the server log shows 2 `Player` nodes plus 18 bot players after `spawn_bots_to_target(20)`, and each client sees 20 bodies in the scene tree.

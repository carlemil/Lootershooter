# HIGH — Server-authoritative cash on PlayerState

**Category:** econ
**Priority:** HIGH
**Status:** TODO
**Milestone:** M4
**Depends on:** net-player-spawn, infra-data-loader

## Files
- `shared/player_state.gd` (modify)
- `server/economy/cash_service.gd` (new)
- `tests/test_cash_service.gd` (new)

## Issue
`PlayerState` has no money. Everything in M4/M5 (money piles, safes, kill bags with the $300 bounty, wrist-store purchases, hot-zone $8/s ticks, the −$20/s outside-zone drain, the >$3000 rich bounty and the end-of-match scoreboard) needs one authoritative place where cash changes and one event stream everything else can listen to. Without it, each feature will mutate an int from a different script and the client will be able to lie about its balance.

## Fix
- Add `@export var cash: int = 0` to `shared/player_state.gd` plus `const STARTING_CASH := 800`. The client may read it but never write it; mark the property with a comment "server-authoritative, mutate via CashService only".
- Create `server/economy/cash_service.gd` as a `Node` autoloaded **server-side only** (guard with `if not multiplayer.is_server(): return`), class_name `CashService`.
- API: `grant(peer_id: int, amount: int, reason: String) -> int` and `charge(peer_id: int, amount: int, reason: String) -> bool`. `grant` returns the new balance; `charge` returns `false` and mutates nothing when `amount > cash` (never allow a negative balance). Both reject `amount <= 0` and return unchanged/false.
- `drain(peer_id: int, amount_float: float, reason: String)` for per-second penalties: accumulate a `float` remainder per player so a −$20/s drain applied at 30 Hz loses no money to int truncation; flush whole dollars into `charge`. Clamp at 0 (a broke player outside the zone just stops paying, HP still ticks).
- Signal `cash_changed(peer_id: int, new_balance: int, delta: int, reason: String)` emitted on every successful mutation. Reasons used by later tasks: `"start"`, `"pile"`, `"safe"`, `"bag"`, `"bounty"`, `"hotzone"`, `"outside"`, `"purchase"`, `"death"`.
- `reset_match()` sets everyone to `STARTING_CASH` with reason `"start"` and clears drain remainders; the match loop calls it.
- Track `earned` and `spent` running totals per peer for the results scoreboard; expose `get_stats(peer_id) -> Dictionary` returning `{cash, earned, spent}`.
- Replicate `cash` to the owning client only (send via an RPC on `cash_changed` to that peer, plus the full value in the snapshot); other players' cash is never sent except through the rich-bounty marker.
- Any RPC entry point that changes cash must be `@rpc("any_peer", "call_remote", "reliable")` and use `multiplayer.get_remote_sender_id()` — never a peer id from the payload.

## Acceptance
- GUT test `tests/test_cash_service.gd`:
  - `reset_match()` then `get_stats(1).cash == 800`.
  - `charge(1, 2500, "purchase")` returns `false` and balance stays 800 (insufficient funds).
  - `charge(1, 300, "purchase")` returns `true`, balance 500, `spent == 300`; `grant(1, 300, "bounty")` → balance 800, `earned == 1100` (start excluded or included consistently — assert the value the implementation documents).
  - `drain(1, 20.0/30.0, "outside")` called 30 times reduces the balance by exactly 20.
- `cash_changed` fires once per successful mutation and not at all for a rejected `charge`.
- Run: `godot --headless -s addons/gut/gut_cmdln.gd -gexit`.

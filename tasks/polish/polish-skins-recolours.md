# LOW — Character skins as atlas recolours, selectable in the lobby

**Category:** polish
**Priority:** LOW
**Status:** TODO
**Milestone:** M10
**Depends on:** ui-lobby-orbit-scoreboard, world-kits-import

## Files
- `client/skins/skin_manager.gd` (new)
- `data/skins.json` (new)
- `client/ui/menu/skin_picker.gd` (new)
- `shared/player/player_state.gd` (modify)
- `tests/test_skins.gd` (new)

## Issue
Every player uses the same character model, so telling teammates apart at distance relies on nameplates alone and there is no visual variety across a 20-player match. This is cosmetic polish with no gameplay weight, which is why it is last: money is per-match only and nothing persists, so skins are a free pick in the lobby, not an unlock or a purchase.

## Fix
- Skins are recolours of the existing CC0 character atlas (Quaternius *Universal Animated Characters* / KayKit), not new meshes — the asset stays CC0 and the draw call count does not change.
- `data/skins.json`: `{"skins": [{"id": "vc_black", "name": "Black Pyjamas", "atlas": "res://client/skins/atlas_vc_black.png", "team_tintable": true}, ...]}`. Ship 6–8: black pyjamas, khaki, olive drab, tiger stripe, ARVN tan, farmer, ghillie-wrapped, mud-caked. Produce each atlas by recolouring the base texture offline and committing the PNG; do not recolour at runtime with shaders per player.
- `client/skins/skin_manager.gd`: caches `StandardMaterial3D` instances per skin id (one material shared by every player wearing it, so 20 players cost at most 8 materials). `apply(character_node, skin_id, team_color)` swaps the albedo texture and, when `team_tintable`, tints a small team-colour band via a second material slot on the armband mesh.
- `player_state.gd` gains `skin_id: String`, replicated with the rest of the player state. The server validates the id against `data/skins.json` on join and falls back to the default — a client must not be able to send an arbitrary path (it would be a texture-load vector).
- `skin_picker.gd`: a lobby panel with a rotating preview of the local character and a grid of skins. Selection sends `rpc_id(1, "set_skin", skin_id)`; changes are accepted only in the lobby state, never mid-match.
- Ghillie interaction: the ghillie-wrap *gadget* from the store overrides the visual skin while equipped and is not a cosmetic choice — keep that override in the item code and have `skin_manager` simply honour an `override_skin` field so the two systems do not fight.
- Teams keep their colour independent of skin: nameplate, minimap dot and armband band are always the team colour, so a skin can never make a teammate look like an enemy.
- No skin may change the silhouette, size or hitbox — assert the mesh and collider are untouched.

## Acceptance
- GUT test `tests/test_skins.gd`:
  - `test_invalid_skin_rejected`: `set_skin("res://../../etc/passwd")` and `set_skin("nope")` both leave `skin_id` at the default.
  - `test_material_reuse`: applying the same skin to 5 characters creates exactly 1 material instance.
  - `test_mid_match_rejected`: a `set_skin` during the match state is ignored; the same call in lobby is accepted.
  - `test_team_color_preserved`: applying any skin leaves the armband material's team tint unchanged.
- Manual: pick each skin in the lobby, confirm it appears on your character for other clients in the next match, that teammates remain identifiable by armband and nameplate colour at 100 m, and that the ghillie gadget overrides the skin while equipped.

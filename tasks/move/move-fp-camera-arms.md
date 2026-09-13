# HIGH — First-person camera, arms viewmodel, head bob and FOV

**Category:** move
**Priority:** HIGH
**Status:** TODO
**Milestone:** M2
**Depends on:** move-stances, move-lean

## Files
- `client/player/fp_camera.gd` (new)
- `client/player/fp_rig.tscn` (new)
- `client/player/viewmodel.gd` (new)
- `client/settings/view_settings.gd` (new)
- `tests/client/test_fp_camera.gd` (new)

## Issue
The game is first-person only: you see arms and a weapon viewmodel, everyone else sees a full third-person body. There is no camera at all right now, so the client is unplayable even though the server simulates correctly. The camera also has to consume the *predicted* state (eye height from the stance blend, roll from lean) rather than computing its own, or the view will disagree with the hitboxes the server rewinds. Viewmodel rendering must not clip through walls, which needs a separate near-plane camera, not a hack.

## Fix
- `client/player/fp_rig.tscn`, attached by the client to the **local** player only (never to remote bodies or bots):
  - `Camera3D` `MainCamera` (`current = true`, `near = 0.05`, `far = 2000`, `fov` from settings, default 90).
  - A `SubViewport`-free approach for the viewmodel: a second `Camera3D` `ViewmodelCamera` on render layer 2 with `near = 0.01`, `far = 5`, `fov = 65`, and the arms/weapon meshes set to layer 2 only, with `MainCamera` culling layer 2. This is the standard no-clip viewmodel setup — no extra viewport cost.
  - `Node3D` `ViewmodelRoot` parented to the camera, holding the arms and the weapon attach point `Node3D` `MuzzleAnchor` (the ballistics origin comes from the **server**, not from here — the anchor is visual only).
- `client/player/fp_camera.gd`:
  - Mouse look: accumulate `InputEventMouseMotion` into `yaw`/`pitch` scaled by sensitivity, clamp pitch to ±89°, and feed them into the outgoing `InputFrame` — the camera is an *input source*, the authoritative angles come back in the snapshot. Apply the local angles immediately (that is prediction), and on reconciliation snap only if the server's angle differs by more than 2°.
  - Position: follow the player's `Head` node exactly (eye height from `stance_blend`, lateral offset and roll from `state.lean`). Never add a second lean or a second crouch offset here.
  - `Input.mouse_mode = MOUSE_MODE_CAPTURED` while playing; release on Esc / focus loss / when the full map or store UI is open.
- Head bob and sway, purely cosmetic and **client-only** (they must never touch `state`, or prediction diverges):
  - Bob amplitude scaled by horizontal speed: 0 at rest, 0.03 m at run, 0.05 m at sprint, at 2 × step frequency; disabled while prone, on a ladder, while ADS and while mantling.
  - Landing punch: a short downward camera offset proportional to impact `velocity.y`, decaying over 0.25 s.
  - Camera-lag sway: the viewmodel lerps toward the camera rotation with a 0.08 s time constant so fast turns swing the weapon.
- `client/settings/view_settings.gd`: an autoload persisting to `user://settings.cfg` with `fov` (70–110, default 90), `mouse_sensitivity`, `ads_sensitivity_mult` (default 0.75), `invert_y`, `bob_enabled`, `viewmodel_fov`. `ui-settings-keybinds` later builds the UI over this; the resource and the defaults live here.
- FOV behaviour: sprinting adds `+6` FOV over 0.15 s, ADS drops to the weapon's ADS FOV (from `data/weapons.json` via `gun-weapon-base`) over the weapon's ADS time — both purely visual lerps on top of the setting.
- Remote players: the client shows the third-person body from `net-player-spawn`; make sure the local player's own body mesh is set to render layer 3 and excluded from `MainCamera` so you never see your own torso from inside.

## Acceptance
- GUT file `tests/client/test_fp_camera.gd` (headless, no rendering — test the maths, not the pixels):
  - `test_pitch_clamped()` — feeding 10 rad of upward mouse delta leaves pitch at `deg_to_rad(89)` ±0.001.
  - `test_eye_height_follows_stance_blend()` — with `stance_blend` 0.0/0.5/1.0 for STAND→CROUCH, the camera local y is 1.65 / 1.35 / 1.05 ±0.01.
  - `test_bob_does_not_touch_state()` — after 60 ticks of bob updates, `PlayerState.position` and `look_yaw` are byte-identical to a run with `bob_enabled = false`.
  - `test_fov_setting_clamped()` — setting `fov = 200` stores 110; `fov = 10` stores 70.
- Manual: run the client against the headless server — mouse look is smooth and captured, crouching lowers the view smoothly, leaning rolls the camera, the weapon never clips into a wall when you walk up to one, and sprinting widens the FOV slightly.

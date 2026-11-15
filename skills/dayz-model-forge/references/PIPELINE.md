# Pipeline

Script paths below are relative to the tool folder, `tools/model-forge/` at the plugin root.

`forge/build_vest.py` only chains the steps; every script also runs on its own
(`blender -b [X.blend] --python <s>.py -- args`). Usage lines are in each script's docstring.

## Vest (`--kind vest`, default)

| # | script | what it does |
|---|---|---|
| 1 | `s02_fit.py` | imports the meshes of the glb/zip (joins the chosen ones), loads the vanilla MLOD body and finds the **uniform scale + height + depth** at which the item's cavity hugs the torso (raycast from the item's axis vs the outer radius of the torso without arms/head; smallest scale with <=10% of the samples penetrating). Test vest: male 0.895, female 0.78 |
| 2 | `s03_skin.py` | **loose parts over the arm** (shoulder pads) are detected automatically (connected component whose points mostly have the arm as nearest skin): rotated about the arm axis to the side (+ `KV_PAD_BACK_DEG`) and tilted (`KV_PAD_TILT_DEG`, pivot at the shell centre); weights = the vanilla skin under them blended 75% with `LeftArm` (`PAD_ARM_BLEND`), fading out along the collar strap; they leave the arm by a small translation + a capped push. Everything else: **gaussian push** against the whole body (sigma 3 cm, 4 mm clearance, "inside" confirmed by ray parity) and **height-band weights** (`weights_bands.py`) |
| 2b | `s09_pad_idle_angle.py` | only with shoulder pads: poses the rig in `idle_game` (arm down, `ArmExtra` lagging half) and measures how much the shell sticks out in front of and behind the **visible** arm (BALANCE). The build re-runs `s03` by secant until +-3 mm. The tilt is fixed (`PAD_TILT_FIXED`, 16 deg), not calibrated |
| 3 | `s05b_source_tex.py` / `s05_texture.py` | the model's own textures (normal map repaired: invalid texels or noise without local coherence -> flat) or generated textures (camo + AO + fabric normal baked on the UVs) |
| 4 | `s07_export.py` | LOD 1/2/3 (100/45/18%, welds vertices before decimating); weights read from the vertex groups and carried to the LODs by nearest vertex |
| 5 | `mlod_write.py` | `_m/_f/_g` MLOD. Ground: laid face up and turned 180 deg vertically (upright icon) |
| 6 | `ImageToPAA` + rvmat | `_co` DXT1, `_nohq` DXT5; rvmat following the vanilla `ballisticvest.rvmat` (+ `_damage/_destruct` with the vanilla MC maps) |
| 7 | `binarize` (cwd `P:\`) | a CHECK only, in the work dir: fails on `Material not loaded`, on a missing `_nohq` in the ODOL or a missing skeleton in `_m/_f` |
| 8 | `s08_verify_p3d.py` | PROOF: rebuilds the scene from the written p3d (normals from the file, backface culling), poses it on the rig |

Helpers: `s01_inspect.py` (look at a model before building: meshes, open boundaries, single surface),
`s04_posetest.py` (poses `rest/idle/idle_game/bend/twist/aim...` from the .blend), `s_render.py`,
`s_debug_armparts.py` (paints the arm parts), `winding_check.py`, `ref_weights.py` (weights by height of a reference
p3d; needs numpy), `mlod_dump.py` (dump any MLOD), `sheet.py` (render contact sheet).

## MLOD conventions (measured on the vanilla body and on working community vest MLODs)

- p3d `(x, y-up, z)` = Blender `(x, z, y)`; the character's front = `-z` in the p3d = `-Y` in Blender. The engine
  mirrors the MLOD Z (memory points, icon).
- The y<->z swap is a reflection: Blender's vertex order already is the MLOD order; stored normal =
  `-(nx, nz, ny)` (pointing inward in p3d space, like BI's body).
- Per-vertex weight: `0` outside, `1` = 1.0, otherwise `round(255 - 254*w)`; face byte = 1 when all its points are in
  the selection. Weights normalized, at most 4 bones per vertex.
- Worn `_m/_f`: LOD 1, 2, 3, 1100 (copy of 1) + empty Geometry 1e13 with `autocenter=0`; bone selections in
  lowercase + `camo`; `lodnoshadow=1`; `model.cfg` with `skeletonName = "DayzTemporarySkeleton"`.
- Ground `_g`: visuals + Geometry (`component01` box with `#Mass#`) + Memory (`boundingbox_min/max`, `invview`,
  `ce_center`, `ce_radius`) + View 6e15 + Fire 7e15 (penetration rvmat).

## Full garment (`--kind top`)

| # | script | what changes |
|---|---|---|
| 1 | `s02_fit.py` | same, with an automatic pre-scale for a model in another unit |
| 1b | `s02b_repose.py` | centre line of each sleeve -> poses the rig's arm/forearm along it -> copies the skin of the posed body -> inverse skinning back to the A-pose; stretches the sleeve to the wrist (`KV_SLEEVE_END`); **fits the sleeve on the arm tube** from where the arm leaves the trunk (centres each slice, opens radially to the skin + `KV_TUBE_GAP` 12 mm) |
| 2 | `s03_skin.py` (`KV_MODE=top`) | push against the **visible skin** (a face hidden inside another shell is left out), 8 mm clearance + L^2/8R per vertex, "inside" = inside any body shell; the push spreads **along the surface** (edge paths) and is smoothed; weights copied from the visible skin |
| 2b | `s02c_transfer.py` | **female**: not fitted from the source model; carried over from the finished `_m`, from the male to the female body keeping the same distance from the skin (ray from the male visible skin -> female skin), smoothed; then `s03` with the female body |
| 3 | `s05b_source_tex.py` | textures extracted from the .glb by material role, PBR factors applied, occlusion baked into the colour, max 2048 |
| 4 | `s07_export.py` (`KV_INNER_SHELL=1`) | inverted inner shell 1.5 mm (single-surface garment) |

Steps 1, 1b and 2 run on the male only.

Config: slot `Body`, vanilla `BomberJacket_ColorBase` as the model, `requiredAddons` + `DZ_Characters_Tops`.

## Backpack (`--kind backpack`, ~90%: see LESSONS)

| # | script | what it does |
|---|---|---|
| 1 | `s02d_place_backpack.py` | imports and joins; several materials -> UVs in atlas cells (`glb_info.py`); real size kept (0.3-0.9 m); harness side to the body (rays: from the strap side they pass between the straps and stop only on the back panel); vertex group `kv_rigid` (1 = bag behind the panel, 0 = harness); hangs it: slides in from behind until the bag touches the back, at the height (up to +8 cm above the shoulder line) and loop opening **in depth only** where the harness enters the body the least |
| 2 | `s03_skin.py` (`KV_MODE=backpack`) | the same garment push (visible skin, along the surface) on the harness only; the bag does not move; weights: bag = `Spine3`, harness = trunk/clavicle skin (arm -> that side's `Shoulder`, pelvis -> `Spine1`, neck -> `Spine3`) |
| 2b | `s02c_transfer.py` | female: the bag moves as ONE BLOCK (mean of the vertices touching the back, then backs off until it clears her back); the harness follows the skin |
| 3 | `s05b_source_tex.py` | atlas: one square cell per material, side by side; accepts specular-glossiness (`KHR_materials_pbrSpecularGlossiness`) |
| 4 | `mlod_write.py` (`KV_GROUND_BACK_UP=1`) | on the ground pockets up (the icon shows the outer face) |

Config: vanilla `CoyoteBag_ColorBase` as the model (slot `Back`, `rotationFlags = 16`), `requiredAddons` +
`DZ_Characters_Backpacks`. No attachment proxies yet (a chemlight/radio attaches but does not show).

## Environment overrides

The scripts read a few `KV_*` environment variables (the `KV_` prefix is historical). `build_vest.py` sets
`KV_MODE`, `KV_PAD_BACK_DEG`, `KV_PAD_TILT_DEG`, `KV_INNER_SHELL` and `KV_GROUND_BACK_UP` itself. Tuning knobs you can
set before a build: `KV_GAP`, `KV_TUBE_GAP`, `KV_SLEEVE_END`, `KV_PAD_ARM_BLEND`, `KV_TEX_MAX`, `KV_BP_TOP`, `KV_BP_FLIP`
(see each script for the default and the measured reason). Change one at a time: see `INGAME-TEST.md`.

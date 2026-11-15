---
name: dayz-model-forge
description: >-
  Model Forge pipeline: external 3D model (.glb / Sketchfab zip) -> WEARABLE DayZ item (MLOD _m/_f/_g p3d +
  paa + rvmat + model.cfg) without Object Builder: fit to the vanilla bodies, bone weights, LODs, binarize
  check and render proof, shoulder-pad calibration. Validated in-game for vests and tops (jackets); backpacks
  at ~90%. Load it for ANY request like "put this model/vest/jacket/backpack in DayZ", "import from
  Sketchfab", "fix the rig/weights/size of the clothing", "the shoulder pad/sleeve looks wrong in game", or
  when changing the pipeline. Triggers: Sketchfab, glb, gltf, clothing, vest, plate carrier, jacket, shirt,
  backpack, shoulder pad, rig, skinning, bone weights, _m.p3d, _f.p3d, _g.p3d, invview, clothing model.cfg,
  forge.json, build_vest.
---

# DayZ Model Forge

## Where things are

The tool's full source (Python scripts, `config/forge.example.json`, `templates/`, and the `README.md` with
requirements and setup) is in **`tools/model-forge/`** at the root of the plugin repository. In Claude Code that
is `${CLAUDE_PLUGIN_ROOT}/tools/model-forge`; from this skill folder it is `../../tools/model-forge`. Below,
`$FORGE` means that folder. This is the only place its location is written.

What you need to read is inside this skill, in `references/`:

- [references/LESSONS.md](references/LESSONS.md): what failed and why (each item cost a round). Read first.
- [references/INGAME-TEST.md](references/INGAME-TEST.md): in-game checklist and symptom -> parameter.
- [references/PIPELINE.md](references/PIPELINE.md): steps, scripts, MLOD conventions, `KV_*` overrides.
- [references/CONFIG.md](references/CONFIG.md): the `config.cpp` class and the vanilla class per kind.

Windows only: Blender 4.4, Python 3 + Pillow, DayZ Tools, the P: drive mounted with the mod on it. The vanilla
bodies (BI DayZ-Misc, ADPL-SA) and a character rig `.blend` are NOT shipped: the user provides them
(`$FORGE/README.md`, "What you must provide", has the rig contract and a check). If they are missing, say so
and stop; do not work around them.

## Flow for a new item

1. **License first.** `https://api.sketchfab.com/v3/models/<uid>` -> `isDownloadable`, `license`. Only CC0 /
   CC-BY downloadable, or bought with a license that covers a mod. View-only or no license = private test at
   most, never a release. Tags of a commercial game usually mean an extracted asset: refuse it.
2. **Open the zip and report what came:** `info.json` (`textures_skipped`), how many meshes, whether there are
   `_CO/_NOHQ/_SMDI` or PBR maps (`$FORGE/forge/s01_inspect.py` also finds open boundaries and single surfaces).
   No textures = `--texture bake`, and TELL the user before spending a round (do not promise a texture that did
   not come).
3. **The mod's forge.json** (copy `$FORGE/config/forge.example.json`): `data_dir` inside the PBO folder (the PBO
   path comes from `$PBOPREFIX$`), `rig_blend`, the two bodies. Then
   `python $FORGE/forge/build_vest.py --config <mod>/3d/forge.json --check-config`.
4. Build, in the background (~2 min per item, more with shoulder pads):
   `python $FORGE/forge/build_vest.py --config <forge.json> --src <zip|glb> --name <prefix>_<name>
   [--kind vest|top|backpack] [--meshes ALL|names] [--texture source|bake]`.
5. **Read the check lines** (`FIT`, `pads ...: balance` with |balance| <= 3 mm, `binarizes OK`) and **look at
   `preview_<name>.png`** (rendered from the written p3d): front, **BACK and side**. If something is wrong,
   diagnose with a measurement (`s09_pad_idle_angle.py`, `s04_posetest.py`, `s_debug_armparts.py`,
   `winding_check.py`, `mlod_dump.py`), not with a guess.
6. Write the class in `config.cpp` (template in [references/CONFIG.md](references/CONFIG.md)), validate with `CfgConvert -bin`.
7. **Do not pack** unless the user asks. Remind them: binarize with cwd `P:\`, otherwise the ODOL comes out
   without `_nohq/_smdi` and the item looks flat.
8. The in-game test is the user's. Translate their screenshot with [references/INGAME-TEST.md](references/INGAME-TEST.md), change ONE parameter,
   rebuild, and show the before/after render in the same framing as their screenshot.

## Vest: `--kind vest` (validated in-game)

- Rigid garment = weights by **height band** (`weights_bands.py`), never "nearest body vertex".
- Push against the **whole body**; "inside" confirmed by **ray parity** (the face sign fails in folds).
- Shoulder pads detected automatically; 75% `LeftArm` + 25% skin; twist about the arm **calibrated** by the
  front/back measure against the arm MESH in `idle_game`; tilt **fixed** (`PAD_TILT_FIXED`). What the emulation
  does not reproduce is not a calibration target. The loop keeps the best run.

## Full garment: `--kind top` (validated in-game, male and female)

- The `Body` slot REPLACES the bare torso (`torso3_m`, y 0.858-1.543): the garment must cover it; the legs
  part goes up to 1.143.
- Sleeves: `s02b_repose` (centre line -> pose the rig -> skin of the posed body -> inverse skinning) + stretched
  to the wrist, then **fitted on the arm tube** (each slice centred, opened to the skin + 12 mm). Single surface ->
  inner shell (`KV_INNER_SHELL`). Weights = skin. Clearance 8 mm.
- "Inside the body" by body SHELL (torso/arms/legs overlap; parity on the whole body lies).
- Garment push along the **visible skin** and **along the surface** (edge paths), never a gaussian through space:
  that tore the sleeve and hem into teeth in the first test.
- Textures from the .glb by material, with the PBR factors (`metallicFactor` 0!). Max 2048.
- **The female garment comes from the finished `_m`** (`s02c_transfer.py`: same distance from the skin, male
  body to female body), never fitted on its own: a uniform scale gave a man's jacket on a woman.
- Do NOT retry: push driven by the body vertices, subdividing near the skin.

## Backpack: `--kind backpack` (~90% in game, male)

- `s02d_place_backpack`: harness toward the body (rays), RIGID bag (`kv_rigid`) against the back, height (up to
  +8 cm above the shoulder line) and loop opening IN DEPTH ONLY, by the sum of the harness depth inside the body.
  Opening around the top of the bag stretched the straps down (they hung 12 cm below the bag).
- `s03` backpack mode: garment push on the harness only; bag = `Spine3`; harness = trunk/clavicle skin.
- Female: `s02c` moves the bag as a block (not checked in game yet). Ground: pockets up (`KV_GROUND_BACK_UP`).
- Several materials -> atlas (`glb_info.py`, `s05b`); specular-glossiness supported.
- Config: copy the vanilla `CoyoteBag_ColorBase` (slot `Back`, `rotationFlags = 16`). No attachment proxies yet.

## A new item kind (trousers, helmet, mask...)

Each new kind is its own `--kind`, without changing what is already validated. Before coding, check in the
vanilla data (`P:\scripts`, `P:\DZ\characters\...`, the config.cpp of the base classes) the slot, the base
class, the LODs/proxies and the selections. A starting plan, not a measured fact:

- **Trousers** (slot `Legs`, replaces the bare legs): same line as the top: legs in the rig pose, skin weights,
  surface push, `_f` from `_m`; must meet the hem of the top.
- **Helmet / mask** (slots `Headgear` / `Mask`): rigid on the head bone, fitted to the vanilla head; check how
  vanilla hides hair / head parts.
- Always: front, BACK and side renders before delivering; `_f` from `_m` when the item follows the body; model
  license before the build.

## MLOD facts (measured)

p3d `(x, y, z)` = Blender `(x, z, y)`; Blender vertex order = MLOD order; stored normal = `-(nx, nz, ny)`; weight
byte `round(255 - 254w)` (0 = outside, 1 = 1.0); ground model with the collar at **-Z** (otherwise the icon is
upside down). The mod keeps **MLOD**: the build only CHECKS the binarize.

## Rules

- Never commit third-party assets into the tool or the plugin: models, textures, `.p3d`, `.paa`, `.blend`, the rig,
  the DayZ-Misc bodies.
- Changed the pipeline? Rebuild an item already validated and compare the `.p3d` md5: an unintended difference is
  a regression.
- "Builds and binarizes" is not "works". Without the user's in-game test, say "not proven in game yet".
- A new lesson that was measured goes into [references/LESSONS.md](references/LESSONS.md).

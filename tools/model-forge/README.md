# Model Forge: 3D model -> wearable DayZ item, without Object Builder

Takes an external 3D model (`.glb`, or the `.zip` you download from Sketchfab) and turns it into a **wearable DayZ
item** with no GUI step: it fits the item to the vanilla male and female bodies, weights it to the character
bones, builds the LODs, writes the `.p3d` files as MLOD, converts the textures to `.paa`, writes the `.rvmat` and
`model.cfg`, checks that `binarize` accepts the result, and renders proof images **from the written files**.

Everything runs headless: Blender in background mode (`blender -b`) plus the DayZ Tools command-line programs.

## Status (honest)

| `--kind` | what | status |
|---|---|---|
| `vest` | rigid vest / plate carrier, shoulder pads detected and calibrated | **validated in-game** (two test models): worn, animates, original texture, pads follow the arm, icon and ground item |
| `top` | jacket / shirt with sleeves (slot `Body`) | **validated in-game**, male and female (the female garment is carried over from the finished male one) |
| `backpack` | rigid bag + harness over the shoulders (slot `Back`) | **~90%** in the 2nd in-game test: worn, straps on the shoulders; fine tuning pending, female not checked in game |
| trousers, helmet, mask, anything else | | **not supported yet** |

"Validated in-game" means tested on internal test mods, on the vanilla characters. Your model is a new case:
a clean build and a good render are **not** proof that it works in the game. Test it (see
[INGAME-TEST.md](../../skills/dayz-model-forge/references/INGAME-TEST.md)).

## Requirements (Windows only)

| what | why |
|---|---|
| **Blender 4.4** (the tested version; installer or portable zip from blender.org) | fit, weights, LODs, renders, all with `-b` (no GUI) |
| **Python 3** + **Pillow** (`python -m pip install Pillow`) | runs `build_vest.py`, the MLOD writer and the preview sheet |
| **DayZ Tools** (Steam, free) | `ImageToPAA` (textures), `binarize` (the check), `CfgConvert` (your config) |
| the **P: work drive** mounted, with your mod on it | `binarize` only loads materials with cwd `P:\`; your PBO folder must sit at `P:\<its $PBOPREFIX$>`, as usual for DayZ mods |
| the **vanilla bodies** and a **character rig** `.blend` | not shipped here (licenses): see next section |

## What you must provide (not shipped, and why)

### 1. Vanilla bodies (Bohemia Interactive, DayZ-Misc)

Download `Body parts/character_male.p3d` and `Body parts/character_female.p3d` from BI's public repository
**[BohemiaInteractive/DayZ-Misc](https://github.com/BohemiaInteractive/DayZ-Misc)**. They are licensed under the
**ADPL-SA** (Arma and DayZ Public License Share-Alike), so this tool does not redistribute them. Point
`body_male` / `body_female` in your `forge.json` to them. They are the size and skin reference for every fit.

### 2. A DayZ character rig as `.blend` (`rig_blend`)

The pipeline poses the item on the character skeleton (sleeve repose, shoulder-pad calibration, proof renders).
It was developed with a community DayZ character rig that cannot be redistributed. Your `.blend` must follow
this contract (the scripts look objects up by name):

- an object named **`Armature`**: the DayZ character skeleton (114 bones), bone names in CamelCase that match the
  vanilla body selections case-insensitively (`Pelvis`, `Spine`...`Spine3`, `Neck`, `LeftShoulder`, `LeftArm`,
  `LeftArmRoll`, `LeftArmExtra`, `LeftForeArm`, ..., `LeftHand`, and the `Right*` mirror);
- two meshes named **`male player`** and **`female player`**: the vanilla bodies, weighted to that armature with an
  Armature modifier;
- lined up with the bodies as this tool loads them from the MLOD (p3d `(x, y, z)` -> Blender `(x, z, y)`, metres,
  character facing `-Y`). Quick check in Blender's Python console:

  ```python
  import bpy; a = bpy.data.objects["Armature"]
  print(len(a.data.bones), a.matrix_world @ a.data.bones["LeftArm"].head_local)
  # expected: 114 and about (0.16, 0.01, 1.44)
  ```

If you do not have one: DayZ-Misc also ships `Rig and Animations/animation_rig_character.fbx` (the character
armature). Importing it into Blender, loading the two body `.p3d` files with their weight selections (the
function `load_p3d_mesh` in `forge/bl_common.py` turns them into vertex groups), naming the objects as above and
adding the Armature modifier should give a valid rig. **This route has not been tested by us**: run the check
above before your first build.

### 3. The model, with a license that allows it

Only use a model you are allowed to use: **CC0 / CC-BY and downloadable**, or bought with a license that covers
a game mod. For Sketchfab, check before downloading:

```
https://api.sketchfab.com/v3/models/<uid>        ->  "isDownloadable": true  and  "license"
```

A view-only model or one without a license is a private test at most, never a release. Tags of a commercial
game usually mean an extracted asset: skip it. CC-BY requires credit to the author in your mod description.

## Setup

1. Put the bodies and the rig somewhere stable, e.g. `%USERPROFILE%\dayz-forge\` (`RIG.blend`,
   `DayZ-Misc\Body parts\character_male.p3d`, `...\character_female.p3d`).
2. Copy [config/forge.example.json](config/forge.example.json) next to your mod, e.g. `<mod>\3d\forge.json`, and
   edit it:

   | key | meaning |
   |---|---|
   | `blender` | path to `blender.exe`; empty = detected (`blender` on PATH, then `Program Files\Blender Foundation`) |
   | `dayz_tools_bin` | `...\DayZ Tools\Bin`; empty = detected in your Steam libraries |
   | `p_drive` | the work drive, `P:\` by default |
   | `p_drive_real` | the folder behind `P:` when it is a `subst`; empty = read from `subst`; only needed when your mod path is given through that folder instead of `P:\` |
   | `rig_blend`, `body_male`, `body_female` | the files from the previous section |
   | `mod_root` | the mod folder (relative to the json) |
   | `data_dir` | inside the PBO folder: where the `.p3d/.paa/.rvmat/model.cfg` go (relative to `mod_root`) |
   | `source_dir` | where the textures (PNG) and `preview_<name>.png` go (relative to `mod_root`), outside the PBO |
   | `pbo_path` | empty = derived from the `$PBOPREFIX$` above `data_dir` |

   Relative paths are relative to the json file; `%VARS%` are expanded.
3. Check the configuration without building:

   ```
   python <forge>\forge\build_vest.py --config <mod>\3d\forge.json --check-config
   ```

   `<forge>` is this folder. It prints every resolved path and stops at the first one that is missing.

Typical mod layout:

```
P:\MyTag\MyMod\
  3d\forge.json                 copied from config\forge.example.json
  3d\source\                    PNG textures + preview_<name>.png
  MyMod_Client\$PBOPREFIX$      contains MyTag\MyMod\MyMod_Client
  MyMod_Client\data\vests\      data_dir: <name>_m/_f/_g.p3d, .paa, .rvmat, model.cfg
```

## Usage

```
python <forge>\forge\build_vest.py --config <mod>\3d\forge.json --src <model.zip|.glb> --name <prefix>_<name>
       [--kind vest|top|backpack] [--texture source|bake] [--meshes ALL|name1,name2] [--work DIR]
```

- Before the build, look inside the zip: `info.json` (`textures_skipped: true` means **no textures came**), how
  many meshes, whether there are `_co/_nohq/_smdi` or glTF PBR maps. `forge/s01_inspect.py` renders the model and
  reports open boundaries and single surfaces.
- `--texture source` uses the model's own maps (DayZ `_co/_nohq/_smdi` or glTF PBR, also specular-glossiness).
  `--texture bake` generates a procedural camo for a model that came without textures.
- `--meshes` picks the meshes to keep (default: all of them, joined).
- `--name`: lowercase, no spaces; it prefixes every output file and the `model.cfg` classes.
- A build takes about 2 minutes per item (more for a vest with shoulder pads: the calibration loop re-runs
  steps). Read the check lines it prints: `FIT`, `pads ...: balance` (|balance| <= 3 mm), `binarizes OK`.

Outputs:

- in `data_dir`: `<name>_m.p3d`, `<name>_f.p3d`, `<name>_g.p3d` (MLOD: the PBO tool binarizes them),
  `<name>_co/_nohq/_smdi.paa`, `<name>.rvmat` (+ `_damage`, `_destruct`), and `model.cfg` (created from
  [templates/model_skeleton.cfg](templates/model_skeleton.cfg) if missing; the item's classes are appended);
- in `source_dir`: `textures\<name>_*.png` and **`preview_<name>.png`**: front, back, side, posed, female, LOD3 and
  ground, rendered from the written `.p3d`. **Look at the back and side views**, not only the front.

Then:

1. Write the item class in your `config.cpp` (template and per-kind notes in [CONFIG.md](../../skills/dayz-model-forge/references/CONFIG.md)) and
   validate it with `CfgConvert.exe -bin -dst x.bin config.cpp`.
2. Pack the mod with your usual PBO tool, **with binarize running with cwd `P:\`** (otherwise the ODOL loses the
   `_nohq/_smdi` material and the item looks flat in game).
3. Test in game with [INGAME-TEST.md](../../skills/dayz-model-forge/references/INGAME-TEST.md): it maps each symptom to the parameter to change.
   Change one parameter per round.

## Not included in this tool (and why)

| left out | why |
|---|---|
| `character_male.p3d`, `character_female.p3d` | Bohemia Interactive, ADPL-SA: download them from DayZ-Misc |
| `RIG.blend` | community rig, not ours to redistribute: build or bring your own (contract above) |
| the test models (vests, jacket, backpack), their textures and renders | third-party Sketchfab models (CC-BY): not ours to redistribute; renders of them are derivatives |
| generated `.p3d`, `.paa`, `.rvmat`, PBOs | build outputs of third-party models |
| `.bisign`, `.bikey`, `.biprivatekey` | signing keys and signatures are personal: never shared |
| internal planning notes | not useful outside the original project |

## Files

- `forge/build_vest.py`: the one command (chains the steps below; every step also runs on its own).
- `forge/s0*.py`, `forge/s_*.py`: the Blender steps and debug renders; `forge/mlod_write.py` / `mlod_dump.py`:
  MLOD writer and reader (plain Python); `forge/weights_bands.py`, `skin_bvh.py`, `glb_info.py`, `bl_common.py`:
  shared helpers. Usage lines are in each script's docstring. Source comments are in English.
- [PIPELINE.md](../../skills/dayz-model-forge/references/PIPELINE.md): the steps, the scripts and the measured MLOD conventions.
- [LESSONS.md](../../skills/dayz-model-forge/references/LESSONS.md): what failed and why. Read it before changing the pipeline.
- [INGAME-TEST.md](../../skills/dayz-model-forge/references/INGAME-TEST.md): in-game checklist and symptom -> parameter.
- [CONFIG.md](../../skills/dayz-model-forge/references/CONFIG.md): the `config.cpp` class.

## Changing the pipeline

Each new item type should be its own `--kind`, without changing what already works. After any change, rebuild
an item you already validated and compare the `.p3d` files (md5): a difference you did not intend is a
regression.

## Using it from Claude Code or Codex

This folder is part of a plugin: the `dayz-model-forge` skill and agent drive it (license check, build, reading
the checks, in-game feedback loop).

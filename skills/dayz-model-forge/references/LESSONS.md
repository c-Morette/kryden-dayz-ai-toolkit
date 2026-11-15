# Measured lessons

Every item below cost one build-and-test round. Format: what was tried -> what happened -> what stayed.
The in-game tests were run on internal test mods (male and female characters).

# Vest (03/10/2026, a plate-carrier vest, 5 in-game tests)

## Weights
- **Weight of the nearest body vertex** -> the arm leaked into 29% of the vest; it tore when the arm moved.
  Stayed: **height bands** copied from 3 working community vests (pelvis at the bottom, spine1/2 on the belly,
  spine3 on the chest, shoulder <=0.3 at the top, arm <=0.07, neck only at the collar).
- **Shoulder pad with a fixed 0.7 `LeftArm`** -> sat 18 deg behind an arm raised 60 deg. **0.9-1.0 `LeftArm`**
  -> took the whole arm twist in idle and moved to the front (1st test). **Skin only** (~0.44 Arm + 0.42
  ArmExtra) -> flared like a wing with the arm down (`ArmExtra` only follows half). Stayed: **75% Arm + 25% skin**.
- Recomputing band weights in `s07` erased the shoulder-pad weights -> the LODs read the vest's vertex groups.

## Push (interpenetration)
- **Torso without arms** as the reference -> a mesh with a hole at the shoulder, wrong sign from the nearest
  face -> the shoulder pad bulged 15 cm. Stayed: the **whole body** (closed), pushing only where the nearest skin
  is torso.
- **Sign from the nearest face normal** fails in folds (female armpit: points 7 cm OUTSIDE came out "inside" ->
  a fin). Stayed: confirm with **ray parity in 3 directions**.
- A rigid part pushed vertex by vertex with no cap -> a fin; **scaling the part** about the arm axis -> inflated
  1.6x. Stayed: a small translation (<=3 cm) + a capped push (2 cm), limited to the part itself.

## Shoulder pad position
- Measuring against the **bone** -> wrong: the rig's arm bone does not run through the middle of the arm mesh.
  Measuring the **centroid** of all the parts -> wrong: the back straps pull the mean. Stayed: how much the
  **main shell sticks out in front of and behind the arm mesh** in an emulated game pose; it matched the tests
  (+76 mm "in front", +42 "almost", +15/+18 "still in front").
- Calibrating **tilt + front/back together** (pivot at the shoulder) diverged and saved the worst result. Stayed:
  the tilt is a **fixed value** taken from the in-game test (16 deg, pivot at the shell centre), only front/back is
  calibrated, and the loop keeps the **best** run, never the last one. Rule: what the emulation does not
  reproduce does not become an automatic calibration target.

## Files and tools
- `binarize` with cwd != `P:\` -> `Material not loaded` and an ODOL **without** `_nohq/_smdi` (exit code 0).
  Always cwd `P:\`.
- A ready ODOL in the mod's source gets in the way of the PBO tool and cannot be edited -> the mod keeps **MLOD**.
- Ground model with the collar at +Z of the p3d -> **upside-down inventory icon** (the engine mirrors Z); on the
  ground it looked right. Stayed: collar at -Z (turn 180 deg vertically after laying it down).
- glTF splits vertices at UV seams -> weld before decimating (LOD3 from 12.8k to 3k points).
- A Sketchfab download may come **without textures** (`textures_skipped: true` in `info.json`) or with a normal
  map full of random noise blocks (they pass the vector-length test) -> detect by **local coherence**.
- The rig body's vertex groups include selections that are not bones (`l_arm_injury`, `personality`) with
  weight 1 -> filter by the armature's bones when picking the "dominant bone".
- Pillow is not in Blender's Python and numpy is not in the system Python (by default) -> image steps run inside
  Blender.

# Full garment (03/10/2026, a CC-BY jacket from Sketchfab)

- **Scale:** a model in another unit (~3 units tall) hit the search limit (0.5). Stayed: estimate the scale from
  the body's chest radius / the model's cavity radius and **pre-scale** only what is outside the range (vests
  stay byte-identical).
- **Sleeves out of the rig pose** (~11-18 deg more open): a PCA of "everything beyond the armpit" caught the
  vertical side of the trunk and RAISED the sleeves. Stayed: **sleeve centre line** by slices, pose the rig's arm
  + forearm along it, copy the skin of the **posed** body and do **inverse skinning** (the shoulder blends through
  the weights). Short sleeves are stretched smoothly to the wrist (male x1.05, female x1.27).
- In DayZ, clothing in the `Body` slot **replaces** the bare torso (`MaleTorso_Base` -> `torso3_m.p3d`,
  y 0.858-1.543); the legs part goes up to 1.143 and the hands part brings the arms. The garment must cover the
  bare torso.
- **Single surface** (71 open boundaries): DayZ renders one side only -> **inner shell** inverted 1.5 mm.
- **Textures inside the .glb**: extract by role in the material; the material's `metallicFactor = 0` zeroes the B
  channel of the ORM (without it the `_smdi` came out orange/metallic). Occlusion (R of the ORM) baked into the
  colour. 4k -> 2048.
- **Garment weights = skin** (nearest face, barycentric, smoothed over 2 cm), forearm/elbow/wrist/hand included.
  Clearance 8 mm (4 mm let the skin show in poses).
- **"Inside the body" test with the vanilla body:** the body is **several overlapping shells** (torso, arms,
  legs...). Parity on the whole body says "outside" where two shells overlap (shoulder): 168 jacket vertices were
  inside and the test said 1. Stayed (garments only): **inside any shell = inside**.
- **Hole at the armpit** (arm showing between the sleeve and the side of the trunk, only with the arm in A-pose):
  the jacket's armhole sits 2-3 cm further out than the vanilla arm-trunk junction. The right diagnosis = **a
  camera ray through the hole's pixel** listing what is in front. Attempts that FAILED: a push driven by the body
  vertices (does not converge, pushes the wrong tube), subdividing near the skin (LOD1 -> 102k tris and the
  armpit got crushed), clearance by triangle size (the triangles there were only 2 cm). Solved on 04/10/2026 by the
  sleeve tube fit + the surface push (next item).
- The faceting in posed renders of a low-poly mesh comes from Blender (deformed custom normals), not from the
  file: it looks the same with and without the inner shell.
- **1st in-game test (04/10/2026): hem and right sleeve torn into teeth.** The defect was already in the BACK
  render of the build itself and slipped through because only the front one was checked. The rule now: look at
  the back and side renders before delivering. Causes measured step by step (the fit and the repose came out
  smooth, `s03` tore it):
  1. After the repose the sleeve sat **2.5-4 cm above** the vanilla arm and **as thin as it**: the sleeve line does
     not pass through the shoulder joint the rig rotates about, and the model was made for a thinner arm. The
     push had to move the wall 4-5 cm, and the gaussian **through space** (7.5 cm radius) reached the opposite wall
     of the tube. Stayed: **sleeve tube fit** (`s02b`). From where the arm leaves the trunk, each slice is centred
     on the arm (centre of the slice's box, not the mean of the vertices) and each vertex moves radially out to
     the skin + 12 mm, with the push spread over the welded mesh.
  2. Hem: the nearest vertex was the **bottom of the torso hidden inside the underwear** (legs shell), normal
     pointing down. The hem dropped 3-5 cm, every other vertex. Stayed: distance, direction and weights from the
     **visible skin** (a shell face inside another shell leaves the BVH), direction = from the nearest skin point to
     the vertex (the face normal jumps from facet to facet on the low-poly hip) and a push **along the surface**
     (edge paths, not a radius in space), with the displacement smoothed 3x over the mesh.
  The armpit window in A-pose went away with it. **2nd in-game test (male): "100%".**
- **Female fitted on its own (uniform scale, like the vest) = a man's jacket on a woman** (in-game test
  04/10/2026): square shoulders, armhole 4 cm high inside the female shoulder (armpit cloth 6-8 cm inside the
  body -> a flap behind the armpit) and the hem 8 cm higher than on the male -> **a gap above the trousers**.
  Stayed: the female garment **comes from the finished male one** (`s02c_transfer.py`). Each vertex keeps its
  distance from the skin: nearest point of the male visible skin -> its ray to the vertex -> where that line meets
  the female skin -> same distance from there; displacement smoothed over the mesh; then push + female skin
  weights. It follows the bust and the narrow shoulder and keeps the hem at the male height. Validated in-game
  ("100%"). `_m` and `_g` do not change.

# Backpack (04/10/2026, a CC-BY low-poly tactical backpack from Sketchfab)

- **Two materials with their own textures** (bag + harness) and the p3d has ONE texture set (`camo`) -> atlas: one
  cell per material, UVs remapped in `s02d` and images assembled in `s05b` by the same rule (`glb_info.py`).
  Material in **specular-glossiness**: the map was constant (spec 0, gloss 0.12/0.24) = matte fabric, that is right.
- The source harness wrapped a smaller torso than the vanilla one: **no rigid position** kept the straps outside
  the body. The "nothing inside" search hung the backpack BEHIND the body, away from the back. Stayed: the bag
  touches the back and the harness is opened and pushed.
- Shoulder line measured without excluding the head -> it caught the ear (1.76 m). Stayed: filter out the head/neck
  vertices.
- Harness push 6 cm deep inside the shoulder -> crushed straps. Opening the loop reduces what the push has to move.
- **Opening the loop by scaling about the top of the bag (x1.21) stretched the straps downward**: the webbing
  that returns to the base hung 12 cm below the backpack, hooked at the hip (1st in-game test). Stayed: open
  **in depth only** (y from the panel), chosen together with the height by the sum of the depth inside the body.
- A height criterion by the COUNT of vertices inside picked the top 16 cm above the shoulder (count dominated by
  the bottom ends). Stayed: sum of the depths, height capped at +8 cm.
- **2nd in-game test (04/10/2026, male): "90%"**: worn, straps on the shoulders, nothing hanging; fine tuning
  pending.
- Female: the bag moves as a block; her hips touch the base and the bag backs off ~4 cm (~2 cm further from the
  back than on the male). Open question whether it shows in game.

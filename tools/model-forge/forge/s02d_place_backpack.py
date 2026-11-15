"""Place a BACKPACK on the vanilla male body (backpacks only; the female is carried over from it by s02c).

blender -b --python s02d_place_backpack.py -- <out.blend> <model.glb|.zip> [<mesh names, comma> | ALL]

A backpack does not wrap the torso like a vest: it hangs from the shoulders by the harness and rests on the back.
  1. import + join; several materials -> UVs laid out in atlas cells (glb_info; s05b builds the same atlas)
  2. real size kept when plausible (0.3-0.9 m tall), else scaled to 0.55 m
  3. harness toward the body (-Y): rays from each side - from the harness side they slip between the straps and
     reach the back panel deep inside, from the outer side they stop on the pockets
  4. vertex group 'kv_rigid': 1 for the bag (behind its back panel, moves as one block), 0 for the harness
  5. hang it: bag top at the shoulder line (KV_BP_TOP), slid forward until the bag touches the back; the harness
     left inside the body is opened over the skin by s03
Writes <out.blend> with 'vest' (the backpack) and 'body' (vanilla male LOD 0 with weights), as s03 expects.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import mathutils
import numpy as np
import glb_info
from bl_common import BODY_M, load_p3d_mesh
from skin_bvh import inside, visible_skin

args = sys.argv[sys.argv.index("--") + 1:]
OUTBLEND, SRC = args[0], args[1]
MESHES = (args[2] if len(args) > 2 else "ALL").split(",")
GAP = 0.006           # backpack -> skin at rest
if not BODY_M:
    raise SystemExit("FORGE_BODY_MALE not set (build_vest.py sets it from forge.json)")

GLB = SRC
if SRC.lower().endswith(".zip"):
    import zipfile
    with zipfile.ZipFile(SRC) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".glb")][0]
        GLB = os.path.join(os.path.dirname(os.path.abspath(OUTBLEND)), "src_" + os.path.basename(name))
        if not os.path.exists(GLB):
            open(GLB, "wb").write(z.read(name))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == "MESH" and (MESHES == ["ALL"] or o.name in MESHES)]
assert meshes, "no mesh matched %s" % MESHES
for o in list(bpy.data.objects):
    if o.type == "MESH" and o not in meshes:
        bpy.data.objects.remove(o, do_unlink=True)
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type == "EMPTY":
        bpy.data.objects.remove(o, do_unlink=True)
bag = meshes[0]
if len(meshes) > 1:
    with bpy.context.temp_override(active_object=bag, selected_editable_objects=meshes, selected_objects=meshes):
        bpy.ops.object.join()
bag.name = bag.data.name = "vest"
bag.data.transform(bag.matrix_world)
bag.matrix_world = mathutils.Matrix()

# ---- 1. atlas UVs --------------------------------------------------------------------------------------------
j = glb_info.read_json(GLB)
mats = glb_info.atlas_materials(j)
if len(mats) > 1:
    ncell = glb_info.atlas_cells(len(mats))
    cell_of = {j["materials"][mi].get("name"): k for k, mi in enumerate(mats)}
    uvl = bag.data.uv_layers["UVMap"]
    outside = 0
    for p in bag.data.polygons:
        mname = bag.data.materials[p.material_index].name if bag.data.materials else None
        k = cell_of.get(mname, cell_of.get((mname or "").rsplit(".", 1)[0], 0))
        for li in p.loop_indices:
            u, v = uvl.data[li].uv
            outside += not (-0.001 <= u <= 1.001)
            uvl.data[li].uv = ((k + min(max(u, 0.0), 1.0)) / ncell, v)
    print("atlas: %d materials -> %d cells across%s" % (len(mats), ncell,
          "" if not outside else " - WARNING %d UVs outside 0..1 were clamped (tiling textures)" % outside))

# ---- 2. size ---------------------------------------------------------------------------------------------------
V = np.array([v.co[:] for v in bag.data.vertices])
h = V[:, 2].max() - V[:, 2].min()
if not 0.3 <= h <= 0.9:
    k = 0.55 / h
    bag.data.transform(mathutils.Matrix.Scale(k, 4)); V *= k
    print("size: %.2f m tall is not a backpack size -> scaled x%.3f to 0.55 m" % (h, k))
else:
    print("size: %.2f m tall, kept" % h)

# ---- 3. harness toward the body -------------------------------------------------------------------------------
bvh_bag = mathutils.bvhtree.BVHTree.FromObject(bag, bpy.context.evaluated_depsgraph_get())
mn, mx = V.min(0), V.max(0)
depth = {}
for side, sgn in (("-Y", 1.0), ("+Y", -1.0)):
    y0 = mn[1] - 0.01 if sgn > 0 else mx[1] + 0.01
    hits = []
    for x in np.linspace(mn[0], mx[0], 24)[2:-2]:
        for z in np.linspace(mn[2], mx[2], 24)[2:-2]:
            hh = bvh_bag.ray_cast(mathutils.Vector((x, y0, z)), mathutils.Vector((0, sgn, 0)), 2.0)
            if hh[0] is not None:
                hits.append(hh[3])
    depth[side] = float(np.median(hits)) if hits else 0.0
harness = max(depth, key=depth.get)
print("harness side: %s (median first hit %.0f mm from -Y, %.0f mm from +Y)" % (
    harness, depth["-Y"] * 1000, depth["+Y"] * 1000))
if harness == "+Y" or os.environ.get("KV_BP_FLIP") == "1":
    bag.data.transform(mathutils.Matrix.Rotation(math.pi, 4, "Z"))
    V = np.array([v.co[:] for v in bag.data.vertices])
bag.data.update()

# ---- 4. rigid bag vs harness, in the bag's own frame: from the harness side the rays reach the back panel at
# the median depth measured above; what is in front of that plane is harness (straps, belts), the rest is bag.
V = np.array([v.co[:] for v in bag.data.vertices])
mn = V.min(0)
y_panel = mn[1] + depth[harness] - 0.01
rigid = np.clip((V[:, 1] - (y_panel - 0.03)) / 0.03, 0, 1)
rigid = rigid * rigid * (3 - 2 * rigid)

# ---- 5. hang it: slid forward from behind until the bag touches the back, at the height where the straps cross
# the body the least. What is left inside is opened over the skin (6 here, then s03). A rigid search for "nothing
# inside at all" hung the bag behind the body instead: no rigid position cleared the straps (04/10/2026).
body = load_p3d_mesh(BODY_M, 0, "body")
vis, shells = visible_skin(body)
B = np.array([v.co[:] for v in body.data.vertices])
gn = {g.index: g.name.lower() for g in body.vertex_groups}
headw = np.array([sum(g.weight for g in v.groups if gn[g.group] in ('head', 'neck', 'neck1') or gn[g.group].startswith('face'))
                  for v in body.data.vertices])
trap = B[(np.abs(B[:, 0]) > 0.08) & (np.abs(B[:, 0]) < 0.18) & (np.abs(B[:, 1]) < 0.12) & (headw < 0.5)]   # not the head
shoulder_top = float(trap[:, 2].max())
R = np.where(rigid > 0.99)[0]
soft = 1 - rigid
cx = (V[:, 0].min() + V[:, 0].max()) / 2
Vsrc = V - np.array([cx, 0.0, 0.0])


def closest(Vt):
    """smallest signed distance of the rigid bag to the visible skin (negative = inside)"""
    best = 9.0
    for i in R:
        q = mathutils.Vector(Vt[i])
        loc, n, fi, d = vis.find_nearest(q)
        best = min(best, -d if (q - loc).dot(n) < 0 else d)
    return best


def hang(top):
    """bag top at z=top, slid forward from far behind until the bag touches the back"""
    Vt = Vsrc + np.array([0.0, 0.6 - Vsrc[:, 1].min(), top - Vsrc[R, 2].max()])
    lo, hi = 0.0, 0.9                                # forward shift: lo = clear, hi = inside
    for _ in range(20):
        mid = (lo + hi) / 2
        if closest(Vt - np.array([0, mid, 0])) > GAP:
            lo = mid
        else:
            hi = mid
    return Vt - np.array([0, lo, 0])


def harness_inside(Vt):
    """how deep the harness is inside the body: sum of the depths (m) of the harness vertices that are inside"""
    tot = 0.0
    for i in np.where(soft > 0.01)[0]:
        q = mathutils.Vector(Vt[i])
        if any(inside(q, b) for b, _ in shells):
            tot += vis.find_nearest(q)[3]
    return round(tot, 2)


# ---- 6. open the harness loop: the source straps wrap a smaller torso. Open it in DEPTH only (scale y away from
# the back panel), never in height: scaling about the top of the bag (1st try, x1.21) stretched the straps
# downward and their lower webbing hung 12 cm below the bag, curled at the hip (in-game test 04/10/2026).
# Pushing them out vertex by vertex instead crumpled them (up to 6 cm deep).
def opened(Vt, k):
    Vo = Vt.copy()
    y0 = Vt[R, 1].min()                              # the back panel plane, where the straps leave the bag
    Vo[:, 1] += soft * (k - 1) * (Vt[:, 1] - y0)
    return Vo


def best_open(Vt):
    trials = [(k, harness_inside(opened(Vt, k))) for k in np.arange(1.0, 1.41, 0.04)]
    return min(trials, key=lambda t: (t[1], t[0])), trials


# height + depth opening together: where the straps go through the body the least (the arc of the 1st backpack's
# straps sits lower than the vanilla trapezius: with the bag's top on the shoulder line they crossed it 4-6 cm deep)
offs = [float(os.environ["KV_BP_TOP"])] if os.environ.get("KV_BP_TOP") else list(np.arange(-0.04, 0.081, 0.02))
rows = []
for off in offs:
    (k, dep), _ = best_open(hang(shoulder_top + off))
    rows.append((off, k, dep))
off, kbest, dep = min(rows, key=lambda r: (r[2], r[0]))
Z_TOP = shoulder_top + off
print("bag top vs shoulder line / depth opening -> harness depth inside the body (sum, m): %s -> %+.2f m, x%.2f" % (
    " ".join("%+.2f/x%.2f:%.2f" % r for r in rows), off, kbest))
V = opened(hang(Z_TOP), kbest)
for i, v in enumerate(bag.data.vertices):
    v.co = V[i]
bag.data.update()
ins = 0
for i in np.where(rigid < 0.99)[0]:
    q = mathutils.Vector(V[i]); loc, n, fi, d = vis.find_nearest(q)
    ins += (q - loc).dot(n) < 0
print("hung: bag top z=%.3f (shoulder line %.3f), bottom z=%.3f, back panel touching at %.0f mm | harness: %d of "
      "%d vertices inside the body (s03 opens them)" % (V[R, 2].max(), shoulder_top, V[:, 2].min(), closest(V) * 1000,
                                                           ins, int((rigid < 0.99).sum())))
vg = bag.vertex_groups.new(name="kv_rigid")
for i, r in enumerate(rigid):
    if r > 0:
        vg.add([i], float(r), "REPLACE")
print("rigid bag: %d of %d vertices behind the back panel plane, %d harness" % (
    int((rigid > 0.99).sum()), len(V), int((rigid < 0.01).sum())))
bpy.ops.wm.save_as_mainfile(filepath=OUTBLEND)
json.dump({"top_vs_shoulder": float(Z_TOP - shoulder_top), "loop_open": float(kbest), "top": float(V[R, 2].max()), "shoulder_top": shoulder_top, "harness": harness},
          open(os.path.splitext(OUTBLEND)[0] + "_fit.json", "w"), indent=1)
print("SAVED", OUTBLEND)

"""Fit the vest to a vanilla body (male or female): similarity transform (uniform scale + vertical + depth
offset) chosen so the vest cavity encloses the torso as tightly as possible without penetration.

blender -b --python s02_fit.py -- <male|female> <out.blend> <model.glb|.zip> [<mesh names, comma> | ALL]
With ALL (default) every mesh of the file is joined. Bodies come from FORGE_BODY_MALE/FEMALE (build_vest).
Writes <out.blend> with objects: vest (fitted, transforms applied), body (vanilla LOD 0 with weights).
Also prints/writes fit.json next to the blend.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree
from bl_common import *

args = sys.argv[sys.argv.index("--") + 1:]
SEX, OUTBLEND = args[0], args[1]
SCRD = os.path.dirname(os.path.abspath(__file__))
SRC = args[2]
MESHES = (args[3] if len(args) > 3 else "ALL").split(",")
if not (BODY_M and BODY_F):
    raise SystemExit("FORGE_BODY_MALE / FORGE_BODY_FEMALE not set (build_vest.py sets them from forge.json)")

GLB = SRC
if SRC.lower().endswith(".zip"):  # pull the .glb out of the Sketchfab zip
    import zipfile
    with zipfile.ZipFile(SRC) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".glb")][0]
        GLB = os.path.join(os.path.dirname(os.path.abspath(OUTBLEND)), "src_" + os.path.basename(name))
        if not os.path.exists(GLB):
            open(GLB, "wb").write(z.read(name))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == "MESH" and (MESHES == ["ALL"] or o.name in MESHES)]
assert meshes, "no mesh matched %s; have %s" % (MESHES, [o.name for o in bpy.data.objects if o.type == "MESH"])
for o in list(bpy.data.objects):
    if o.type == "MESH" and o not in meshes:
        bpy.data.objects.remove(o, do_unlink=True)
for o in meshes:
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type == "EMPTY":
        bpy.data.objects.remove(o, do_unlink=True)
vest = meshes[0]
if len(meshes) > 1:
    with bpy.context.temp_override(active_object=vest, selected_editable_objects=meshes, selected_objects=meshes):
        bpy.ops.object.join()
print("vest source:", GLB, "meshes:", [m for m in MESHES], "verts", len(vest.data.vertices), "faces", len(vest.data.polygons))
vest.name = "vest"
vest.data.name = "vest"
vest.data.transform(vest.matrix_world)
vest.matrix_world = mathutils.Matrix()

body = load_p3d_mesh(BODY_M if SEX == "male" else BODY_F, 0, "body")

# ---- body torso BVH (no arms, no head) ---------------------------------------------
ARM = ("arm", "hand", "elbow", "wrist")
def is_excluded(vg_name):
    n = vg_name.lower()
    return any(k in n for k in ARM) or n == "head" or n.startswith("face")
excl_w = np.zeros(len(body.data.vertices))
idx_excl = [vg.index for vg in body.vertex_groups if is_excluded(vg.name)]
for v in body.data.vertices:
    for g in v.groups:
        if g.group in idx_excl:
            excl_w[v.index] += g.weight
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
kill = [f for f in bm.faces if np.mean([excl_w[v.index] for v in f.verts]) > 0.5]
bmesh.ops.delete(bm, geom=kill, context="FACES")
torso_bvh = BVHTree.FromBMesh(bm)
bm.free()
vest_bvh = BVHTree.FromObject(vest, bpy.context.evaluated_depsgraph_get())

# ---- pre-scale models made in other units: the search below covers scales 0.5..1.0. Estimate the scale as
# body chest radius / model cavity radius at mid height; only out-of-range models are touched (a vest made
# near 1 m - like the two approved ones - is left exactly as before). Jacket of 03/10/2026: ~3 units tall.
vco0 = np.array([v.co[:] for v in vest.data.vertices])
c0 = (vco0.min(0) + vco0.max(0)) / 2
span = float((vco0.max(0) - vco0.min(0)).max())
r_model = []
for th in np.linspace(0, 2 * math.pi, 16, endpoint=False):
    d = mathutils.Vector((math.cos(th), math.sin(th), 0.0))
    hit = vest_bvh.ray_cast(mathutils.Vector((c0[0], c0[1], c0[2])), d, span)
    if hit[0] is not None:
        r_model.append(hit[3])
r_body = []
for th in np.linspace(0, 2 * math.pi, 16, endpoint=False):
    d = mathutils.Vector((math.cos(th), math.sin(th), 0.0))
    hit = torso_bvh.ray_cast(mathutils.Vector((0.0, 0.0, 1.25)) + d * 0.6, -d, 0.6)
    if hit[0] is not None:
        r_body.append(0.6 - hit[3])
s_est = float(np.median(r_body) / np.median(r_model)) if r_model and r_body else 1.0
PRESCALE = 1.0
if s_est < 0.55 or s_est > 1.05:
    PRESCALE = s_est / 0.8
    vest.data.transform(mathutils.Matrix.Scale(PRESCALE, 4))
    vest.data.update()
    vest_bvh = BVHTree.FromObject(vest, bpy.context.evaluated_depsgraph_get())
print("scale estimate %.3f -> prescale %.4f" % (s_est, PRESCALE))

vco = np.array([v.co[:] for v in vest.data.vertices])
vmin, vmax = vco.min(0), vco.max(0)
print("vest bbox", vmin.round(3), vmax.round(3))
NT = 32
thetas = np.linspace(0, 2 * math.pi, NT, endpoint=False)
dirs = np.stack([np.cos(thetas), np.sin(thetas), np.zeros(NT)], 1)

# ---- vest cavity axis (x center, y center from front/back inner walls) ---------------
xc = float((vmin[0] + vmax[0]) / 2)
ycs = []
for h in np.linspace(vmin[2] + 0.35 * (vmax[2] - vmin[2]), vmin[2] + 0.75 * (vmax[2] - vmin[2]), 9):
    y0 = float((vmin[1] + vmax[1]) / 2)
    o = mathutils.Vector((xc, y0, h))
    a = vest_bvh.ray_cast(o, mathutils.Vector((0, -1, 0)))
    b = vest_bvh.ray_cast(o, mathutils.Vector((0, 1, 0)))
    if a[0] and b[0]:
        ycs.append((a[0].y + b[0].y) / 2)
yc = float(np.median(ycs))
print("vest axis x=%.4f y=%.4f (from %d slices)" % (xc, yc, len(ycs)))

# ---- vest inner radius r_v(h, theta) ---------------------------------------------------
HS = np.arange(vmin[2] + 0.005, vmax[2] - 0.005, 0.004)
rv = np.full((len(HS), NT), np.nan)
for i, h in enumerate(HS):
    o = mathutils.Vector((xc, yc, h))
    for j in range(NT):
        hit = vest_bvh.ray_cast(o, mathutils.Vector(dirs[j]), 1.0)
        if hit[0] is not None:
            rv[i, j] = hit[3]
ring = np.isfinite(rv).mean(1)
print("vest ring coverage per height (min/mean)", ring.min().round(2), ring.mean().round(2))

# ---- body outer radius r_b(Z, theta) for several axis depths ---------------------------
ZS = np.arange(0.70, 1.75, 0.004)
DYS = np.arange(-0.04, 0.0401, 0.005)
R = 0.6
rb = np.full((len(DYS), len(ZS), NT), np.nan)
for k, dy in enumerate(DYS):
    for i, z in enumerate(ZS):
        for j in range(NT):
            d = mathutils.Vector(dirs[j])
            o = mathutils.Vector((0.0, dy, z)) + d * R
            hit = torso_bvh.ray_cast(o, -d, R)
            if hit[0] is not None:
                rb[k, i, j] = R - hit[3]
            else:
                rb[k, i, j] = 0.0  # nothing of the torso on this ray (above the shoulders)

# ---- search: for each (z0, dy) the smallest scale with <= ALLOW penetrating samples ----
GAP_MIN = 0.0    # local penetrations are fixed later by the anti-clip push (s03)
ALLOW = 0.10
best = None
valid = np.isfinite(rv)
hv = HS - vmin[2]
results = []
for k, dy in enumerate(DYS):
    for z0 in np.arange(0.70, 1.20, 0.005):
        for s in np.arange(0.50, 1.00, 0.005):
            Z = z0 + s * hv
            inside = (Z >= ZS[0]) & (Z <= ZS[-1])
            zi = np.clip(np.round((Z - ZS[0]) / 0.004).astype(int), 0, len(ZS) - 1)
            b = rb[k][zi]                      # (H, NT)
            m = valid & inside[:, None] & (b > 0)
            if m.sum() < 0.3 * valid.sum():
                continue
            gap = s * rv - b
            g = gap[m]
            pen = (g < GAP_MIN).mean()
            if pen <= ALLOW:
                results.append((s, z0, dy, pen, float(np.median(g)), int(m.sum())))
                break
if not results:
    k = len(DYS) // 2
    for z0 in np.arange(0.70, 1.20, 0.05):
        row = []
        for s in np.arange(0.50, 1.20, 0.05):
            Z = z0 + s * hv
            inside = (Z >= ZS[0]) & (Z <= ZS[-1])
            zi = np.clip(np.round((Z - ZS[0]) / 0.004).astype(int), 0, len(ZS) - 1)
            b = rb[k][zi]
            m = valid & inside[:, None] & (b > 0)
            g = (s * rv - b)[m]
            row.append("%.2f" % ((g < GAP_MIN).mean() if len(g) else -1))
        print("DIAG z0=%.2f pen by s(0.5..1.15):" % z0, " ".join(row))
    # where do penetrations come from at a plausible fit
    s, z0 = 0.75, 0.95
    Z = z0 + s * hv
    zi = np.clip(np.round((Z - ZS[0]) / 0.004).astype(int), 0, len(ZS) - 1)
    b = rb[k][zi]
    gap = s * rv - b
    for i in range(0, len(HS), 10):
        print("DIAG h=%.3f Z=%.3f gaps:" % (hv[i], Z[i]), " ".join("%5.2f" % x if np.isfinite(x) else "  -  " for x in gap[i]))
    raise SystemExit("no fit")
results.sort(key=lambda r: (r[0], r[4]))
for r in results[:8]:
    print("cand s=%.3f z0=%.3f dy=%.3f pen=%.3f median_gap=%.4f n=%d" % r)
s, z0, dy, pen, mg, n = results[0]

# ---- apply ------------------------------------------------------------------------------
T = (mathutils.Matrix.Translation((0.0, dy, z0)) @ mathutils.Matrix.Scale(s, 4)
     @ mathutils.Matrix.Translation((-xc, -yc, -vmin[2])))
vest.data.transform(T)
vest.data.update()
fit = {"sex": SEX, "prescale": PRESCALE, "scale": s, "z0": z0, "dy": dy, "pen": pen, "median_gap": mg,
       "axis_vest": [xc, yc, float(vmin[2])], "matrix": [list(r) for r in T]}
vco = np.array([v.co[:] for v in vest.data.vertices])
fit["bbox_min"] = vco.min(0).round(4).tolist()
fit["bbox_max"] = vco.max(0).round(4).tolist()
print("FIT", json.dumps(fit))
json.dump(fit, open(os.path.splitext(OUTBLEND)[0] + "_fit.json", "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=OUTBLEND)

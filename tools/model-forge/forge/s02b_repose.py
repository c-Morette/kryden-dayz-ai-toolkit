"""Repose the SLEEVES of a fitted top into the rig's A-pose (tops only; vests have no sleeves).

blender -b fit_<sex>.blend --python s02b_repose.py -- <RIG.blend> <out.blend> <male|female>

The source model's sleeves rarely match the DayZ rest pose (jacket of 03/10/2026: sleeves ~25 deg flatter than
the rig's arms, the arms came out under them). Steps:
  1. measure each sleeve's axis: upper half and lower half (PCA of the garment beyond the shoulder)
  2. pose the vanilla rig's LeftArm/LeftForeArm (and right) along those axes
  3. copy the skin weights of the POSED vanilla body to the garment (nearest face, barycentric, smoothed)
  4. inverse skinning v_rest = (sum w_b M_b)^-1 v_posed  -> the sleeves come down to the rig pose and the
     shoulder blends through the weights instead of a hard cut
  5. sleeves stretched to the wrist, then fitted on the arm tube (centred per slice, opened radially to clear
     the skin) from where the arm leaves the trunk
Writes out.blend = the fit blend with 'vest' reposed (objects 'vest' and 'body' as s03 expects).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh
import bpy
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

RIG, OUTB, SEX = sys.argv[sys.argv.index("--") + 1:][:3]
vest = bpy.data.objects["vest"]
keep_body = "male player" if SEX == "male" else "female player"
with bpy.data.libraries.load(RIG, link=False) as (src, dst):
    dst.objects = ["Armature", keep_body]
arm, rbody = dst.objects
for o in (arm, rbody):
    bpy.context.scene.collection.objects.link(o)
if not any(m.type == "ARMATURE" for m in rbody.modifiers):
    mm = rbody.modifiers.new("arm", "ARMATURE"); mm.object = arm
for m in rbody.modifiers:
    if m.type == "ARMATURE":
        m.object = arm
bpy.context.view_layer.update()      # appended objects keep an identity matrix_world until the scene updates
A = arm.matrix_world.copy()
pbs = arm.pose.bones


def head_w(name):
    return np.array((A @ pbs[name].bone.head_local)[:])


def rot_world(bone, R3):
    """apply a WORLD-space rotation (3x3, rest frame) to a pose bone about its head"""
    pb = pbs[bone]
    Mw = (A @ pb.bone.matrix_local).to_3x3().normalized()
    Rl = Mw.inverted() @ mathutils.Matrix(R3) @ Mw
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Rl.to_quaternion() @ pb.rotation_quaternion


def line_dir(C, toward):
    """least-squares direction of a polyline of centre points"""
    c = C - C.mean(0)
    d = np.linalg.svd(c, full_matrices=False)[2][0]
    return d if np.dot(d, toward) > 0 else -d


def sleeve_centreline(V, J, d, sgn):
    """centres of slices perpendicular to d (from the shoulder J) using only garment points well outside the
    torso. A plain PCA of 'everything beyond the armpit' also took the vertical side panel of the jacket and
    gave an almost vertical axis - the repose then RAISED the sleeves (1st try, 03/10/2026)."""
    sel = V[sgn * V[:, 0] > abs(J[0]) + 0.10]
    t = (sel - J) @ d
    L = np.percentile(t, 98)
    pts, ts = [], []
    for tt in np.linspace(0.12 * L, 0.96 * L, 16):
        s = sel[np.abs(t - tt) < 0.015]
        if len(s) >= 6:
            pts.append(s.mean(0)); ts.append(tt)
    return np.array(pts), np.array(ts), L


V = np.array([v.co[:] for v in vest.data.vertices])
report = {}
for side, sgn in (("Left", 1.0), ("Right", -1.0)):
    J = head_w(side + "Arm"); E = head_w(side + "ForeArm"); H = head_w(side + "Hand")
    up_a = (E - J) / np.linalg.norm(E - J); lo_a = (H - E) / np.linalg.norm(H - E)
    arm_len = np.linalg.norm(H - J)
    C, ts, L = sleeve_centreline(V, J, (H - J) / np.linalg.norm(H - J), sgn)
    split = 0.5 * L
    up_s = line_dir(np.vstack([J, C[ts < split]]), up_a)      # the sleeve hangs from the shoulder joint
    lo_s = line_dir(C[ts >= split], lo_a)
    R1 = np.array(mathutils.Vector(up_a).rotation_difference(mathutils.Vector(up_s)).to_matrix())
    rot_world(side + "Arm", R1)
    # forearm: rotation in the REST frame so that R1 @ R2 @ lo_a = lo_s
    tgt = R1.T @ lo_s
    R2 = np.array(mathutils.Vector(lo_a).rotation_difference(mathutils.Vector(tgt)).to_matrix())
    rot_world(side + "ForeArm", R2)
    ang1 = math.degrees(math.acos(np.clip(np.dot(up_a, up_s), -1, 1)))
    ang2 = math.degrees(math.acos(np.clip(np.dot(R1 @ lo_a, lo_s), -1, 1)))
    report[side] = (ang1, ang2, L, arm_len)
    print("sleeve %s: upper arm off by %.1f deg, forearm %.1f deg | sleeve length %.3f m vs arm %.3f m" % (
        side, ang1, ang2, L, arm_len))
bpy.context.view_layer.update()

# ---- skin weights of the posed body -> garment ------------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()
ev = rbody.evaluated_get(dg)
BP = np.array([(rbody.matrix_world @ v.co)[:] for v in ev.data.vertices])
bones = {b.name for b in arm.data.bones}
gi = {vg.index: vg.name for vg in rbody.vertex_groups}
names = sorted(bones)
col = {n: i for i, n in enumerate(names)}
BW = np.zeros((len(BP), len(names)))
for v in rbody.data.vertices:
    for g in v.groups:
        n = gi[g.group]
        if n in col:
            BW[v.index, col[n]] += g.weight
BW /= np.maximum(BW.sum(1, keepdims=True), 1e-9)
tris = [list(p.vertices) for p in ev.data.polygons]
bvh = BVHTree.FromPolygons([tuple(p) for p in BP], tris)


def bary_weights(p):
    loc, n, fi, d = bvh.find_nearest(mathutils.Vector(p))
    a, b, c = (mathutils.Vector(BP[i]) for i in tris[fi][:3])
    w = mathutils.geometry.barycentric_transform(loc, a, b, c, mathutils.Vector((1, 0, 0)), mathutils.Vector((0, 1, 0)), mathutils.Vector((0, 0, 1)))
    w = np.clip(np.array(w[:]), 0, None)
    w /= max(w.sum(), 1e-9)
    return (BW[tris[fi][:3]] * w[:, None]).sum(0)


W = np.array([bary_weights(p) for p in V])
kd = KDTree(len(V))
for i, p in enumerate(V):
    kd.insert(p, i)
kd.balance()
nb = [[j for (_, j, _) in kd.find_range(p, 0.02)] for p in V]
for _ in range(2):
    W = np.array([W[n].mean(0) for n in nb])
W /= np.maximum(W.sum(1, keepdims=True), 1e-9)

# ---- inverse skinning back to the rest pose ----------------------------------------------------
Mb = np.zeros((len(names), 4, 4))
for n, i in col.items():
    pb = pbs[n]
    Mb[i] = np.array((A @ pb.matrix) @ (A @ pb.bone.matrix_local).inverted())
Vh = np.hstack([V, np.ones((len(V), 1))])
Vr = np.zeros_like(V)
for k in range(len(V)):
    M = np.tensordot(W[k], Mb, axes=1)
    Vr[k] = (np.linalg.inv(M) @ Vh[k])[:3]
moved = np.linalg.norm(Vr - V, axis=1)
print("reposed: max move %.1f mm, mean %.1f mm" % (moved.max() * 1000, moved.mean() * 1000))

# ---- sleeves down to the wrist: stretch along the (rest) arm axis, smoothly from the upper arm on ----------
SLEEVE_END = float(os.environ.get("KV_SLEEVE_END", 0.97))     # cuff at this fraction of shoulder->wrist
for side, sgn in (("Left", 1.0), ("Right", -1.0)):
    J = head_w(side + "Arm"); H = head_w(side + "Hand")
    d = (H - J) / np.linalg.norm(H - J)
    m = sgn * Vr[:, 0] > abs(J[0]) + 0.02
    t = (Vr[m] - J) @ d
    L = np.percentile(t, 99)
    k = SLEEVE_END * np.linalg.norm(H - J) / L
    if k <= 1.0:
        print("sleeve %s: length %.3f m already reaches %.0f%% of the arm, not stretched" % (side, L, 100 * SLEEVE_END))
        continue
    ramp = np.clip((t - 0.15 * L) / (0.25 * L), 0, 1)
    ramp = ramp * ramp * (3 - 2 * ramp)
    shift = (np.maximum(t - 0.15 * L, 0) * (k - 1)) * ramp     # extra length grows along the sleeve
    Vr[m] += shift[:, None] * d
    print("sleeve %s: stretched %.3f -> %.3f m (x%.2f) to reach the wrist" % (side, L, L * k, k))

# ---- sleeves ON the arm: centre every slice on the vanilla arm and widen it to clear the skin ----------------
# After the repose the jacket's sleeves sat 2.5-4 cm ABOVE the vanilla arm (the sleeve line does not pass through
# the shoulder joint the rig rotates about) and were as thin as the arm (model made for a slimmer arm). The s03
# push then had to move the sleeve wall 4-5 cm and tore the sleeve (1st in-game test of the jacket, 04/10/2026).
# Only beyond the point where the arm leaves the trunk (there the sleeve is a closed tube); ramps in over RAMP.
TUBE_GAP = float(os.environ.get("KV_TUBE_GAP", 0.012))
TUBE_RAMP = 0.08
body = bpy.data.objects["body"]
gn = {vg.index: vg.name.lower() for vg in body.vertex_groups}
BC = np.array([v.co[:] for v in body.data.vertices])
armw = np.zeros(len(BC))
for v in body.data.vertices:
    for g in v.groups:
        n = gn[g.group]
        if any(k in n for k in ("arm", "hand", "elbow", "wrist")) and "shoulder" not in n:
            armw[v.index] += g.weight
bfaces = [list(p.vertices) for p in body.data.polygons]
bvh_arm = BVHTree.FromPolygons([tuple(p) for p in BC], [f for f in bfaces if all(armw[i] > 0.5 for i in f)])
bvh_trunk = BVHTree.FromPolygons([tuple(p) for p in BC], [f for f in bfaces if all(armw[i] < 0.5 for i in f)])
bmw = bmesh.new(); bmw.from_mesh(vest.data)          # glTF splits vertices at UV seams: walk the welded mesh
for v, p in zip(bmw.verts, Vr):
    v.co = p
bmesh.ops.remove_doubles(bmw, verts=bmw.verts, dist=1e-5)
bmw.verts.ensure_lookup_table()
kdv = KDTree(len(bmw.verts))
for v in bmw.verts:
    kdv.insert(v.co, v.index)
kdv.balance()
widx = np.array([kdv.find(p)[1] for p in Vr])
wadj = [[e.other_vert(v).index for e in v.link_edges] for v in bmw.verts]
bmw.free()


def chain_coords(P, J, E, H):
    """arc length t along shoulder->elbow->wrist, the axis point and the axis direction of each point"""
    t = np.zeros(len(P)); a = np.zeros_like(P); u = np.zeros_like(P); best = np.full(len(P), np.inf)
    t0 = 0.0
    for A0, A1 in ((J, E), (E, H)):
        L = np.linalg.norm(A1 - A0); d = (A1 - A0) / L
        s = np.clip((P - A0) @ d, 0, L)
        ap = A0 + s[:, None] * d
        dist = np.linalg.norm(P - ap, axis=1)
        m = dist < best
        best[m] = dist[m]; t[m] = t0 + s[m]; a[m] = ap[m]; u[m] = d
        t0 += L
    return t, a, u


def fill(T, X):
    """interpolate the NaN rows of a per-slice table, then a 5-slice moving average"""
    X = X.copy()
    for c in range(X.shape[1]):
        ok = ~np.isnan(X[:, c])
        X[:, c] = np.interp(T, T[ok], X[ok, c])
    K = np.ones(5) / 5
    return np.stack([np.convolve(np.pad(X[:, c], 2, mode="edge"), K, "valid") for c in range(X.shape[1])], 1)


def slice_centre(R, u):
    """centre of the bounding box of a slice's radial offsets, in the plane perpendicular to u (the vertex mean
    is pulled toward the side of the sleeve with more vertices - folds)"""
    e1 = np.cross(u, (0.0, 0.0, 1.0)); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    p, q_ = R @ e1, R @ e2
    return e1 * (p.min() + p.max()) / 2 + e2 * (q_.min() + q_.max()) / 2


TUBE_SMOOTH = 10
for side, sgn in (("Left", 1.0), ("Right", -1.0)):
    J = head_w(side + "Arm"); E = head_w(side + "ForeArm"); H = head_w(side + "Hand")
    L1 = np.linalg.norm(E - J); Ltot = L1 + np.linalg.norm(H - E)
    T = np.arange(0.0, Ltot - 0.015, 0.01)
    uT = np.array([(E - J) / L1 if tc <= L1 else (H - E) / np.linalg.norm(H - E) for tc in T])
    aT = np.array([J + uT[k] * tc if tc <= L1 else E + uT[k] * (tc - L1) for k, tc in enumerate(T)])
    bi = np.where((sgn * BC[:, 0] > 0) & (armw > 0.5))[0]
    tb, ab, _ = chain_coords(BC[bi], J, E, H)
    keep = (tb > 0.005) & (tb < Ltot - 0.01)          # points clipped to the joint or past the wrist (hand)
    tb, rb = tb[keep], (BC[bi] - ab)[keep]
    cb = np.full((len(T), 3), np.nan); rarm = np.full((len(T), 1), np.nan)
    for k, tc in enumerate(T):
        mb = np.abs(tb - tc) < 0.015
        if mb.sum() >= 6:
            cb[k] = slice_centre(rb[mb], uT[k]); rarm[k] = np.linalg.norm(rb[mb] - cb[k], axis=1).max()
    cb = fill(T, cb); rarm = fill(T, rarm)[:, 0]
    tfree = None
    for k, tc in enumerate(T):
        loc, n, fi, dd = bvh_trunk.find_nearest(mathutils.Vector(aT[k] + cb[k]))
        if loc is not None and dd > rarm[k] + 0.04:
            tfree = tc; break
    if tfree is None:
        print("sleeve %s: the arm never leaves the trunk, tube fit skipped" % side); continue
    # the sleeve = welded vertices reachable from the cuff without crossing back to t < tfree
    gi_all = np.where(sgn * Vr[:, 0] > 0)[0]
    tg_all, _, _ = chain_coords(Vr[gi_all], J, E, H)
    tw = np.full(len(wadj), -1.0)
    tw[widx[gi_all]] = tg_all
    seed = widx[gi_all[np.argmax(tg_all)]]
    insl = np.zeros(len(wadj), bool); insl[seed] = True; st = [seed]
    while st:
        x = st.pop()
        for y in wadj[x]:
            if not insl[y] and tw[y] > tfree:
                insl[y] = True; st.append(y)
    sel = np.where(insl[widx])[0]
    tg, ag, ug = chain_coords(Vr[sel], J, E, H)
    rg = Vr[sel] - ag
    cg = np.full((len(T), 3), np.nan)
    for k, tc in enumerate(T):
        mg = np.abs(tg - tc) < 0.015
        if mg.sum() >= 6:
            cg[k] = slice_centre(rg[mg], uT[k])
    cg = fill(T, cg)
    ramp = np.clip((tg - tfree) / TUBE_RAMP, 0, 1); ramp = ramp * ramp * (3 - 2 * ramp)
    off = np.stack([np.interp(tg, T, cb[:, c] - cg[:, c]) for c in range(3)], 1)
    cbv = np.stack([np.interp(tg, T, cb[:, c]) for c in range(3)], 1)
    P1 = Vr[sel] + ramp[:, None] * off
    q = P1 - ag - cbv
    q -= ug * (q * ug).sum(1, keepdims=True)
    rv = np.linalg.norm(q, axis=1)
    need = np.zeros(len(sel)); dirs = np.zeros_like(q)
    for k in range(len(sel)):
        if rv[k] < 1e-4:
            continue
        dirs[k] = q[k] / rv[k]
        o = mathutils.Vector(ag[k] + cbv[k]); dirv = mathutils.Vector(dirs[k]); far = 0.0
        cur = o
        for _ in range(8):                           # outermost arm skin (the arm shells overlap at the elbow)
            h = bvh_arm.ray_cast(cur, dirv, 0.15)
            if h[0] is None or (h[0] - o).length > 0.15:
                break
            far = (h[0] - o).length; cur = h[0] + dirv * 1e-5
        need[k] = max(0.0, far + TUBE_GAP - rv[k])
    # radial push per vertex, spread over the welded sleeve so a fold does not become a spike
    wreq = np.zeros(len(wadj)); np.maximum.at(wreq, widx[sel], need)
    wn = wreq.copy()
    for _ in range(TUBE_SMOOTH):
        avg = np.array([wn[a_].mean() if a_ else 0.0 for a_ in wadj])
        wn = np.where(insl, np.maximum(wreq, avg), 0.0)
    push = ramp * wn[widx[sel]]
    Vr[sel] = P1 + push[:, None] * dirs
    print("sleeve %s: tube fit from t=%.2f m (arm leaves the trunk) on %d verts: re-centred by up to %.0f mm, "
          "widened by up to %.0f mm (mean %.0f mm)" % (side, tfree, len(sel),
          np.linalg.norm(ramp[:, None] * off, axis=1).max() * 1000, push.max() * 1000, push.mean() * 1000))
for i, v in enumerate(vest.data.vertices):
    v.co = Vr[i]
vest.data.update()
for o in (rbody, arm):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=OUTB)
print("SAVED", OUTB)

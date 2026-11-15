"""Anti-clip push against the vanilla torso + bone weights by height bands.

blender -b fit_<sex>.blend --python s03_skin.py -- <out.blend>
Input objects: vest (fitted by s02), body (vanilla LOD 0 with its bone selections).
Output: same objects; vest gets vertex groups named like the RIG.blend armature bones (CamelCase).

Why bands and not "nearest body vertex": the nearest transfer spread arm weights over 29% of the vest and
the vest tore when the arms moved. The bands reproduce the pattern of 3 working mod vests (JPC/IOTV/6B23).
"""
import heapq
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from weights_bands import ALLOWED, ARM_FADE_T, PAD_ARM_BLEND, arm_axis, band_weights, skin_bone

OUTBLEND = sys.argv[sys.argv.index("--") + 1:][0]
vest = bpy.data.objects["vest"]
body = bpy.data.objects["body"]
GAP = 0.004          # minimum distance vest -> skin after the push (m)
# vest (default): rigid garment, height-band weights, shoulder pads. top: cloth that copies the skin (jacket,
# shirt): pushed off the WHOLE body arms included, weights copied from the skin, no pad detection.
MODE = os.environ.get("KV_MODE", "vest")
# backpack: the cloth machinery of 'top' for the harness; the bag (vertex group kv_rigid from s02d) stays put
CLOTH = MODE in ("top", "backpack")
if CLOTH:
    # cloth: 4 mm left skin showing through in poses (smoothed garment weights vs raw skin weights, and the
    # in-game arm LODs differ from LOD 0) - jacket of 03/10/2026
    GAP = float(os.environ.get("KV_GAP", 0.008))
SIGMA = 0.03         # push falloff radius (m)

# ---- body: arm-chain weight per vertex/face. The push and the "inside" test use the FULL (closed) body:
# a torso-only surface has a hole at the shoulder and its nearest-face sign is garbage there (it inflated
# the shoulder pads of the 2nd test vest by 15 cm). Only points whose nearest skin is torso get pushed.
gname = {vg.index: vg.name.lower() for vg in body.vertex_groups}
armchain = np.zeros(len(body.data.vertices))
for v in body.data.vertices:
    for g in v.groups:
        n = gname[g.group]
        if any(k in n for k in ("arm", "hand", "elbow", "wrist")) and "shoulder" not in n:
            armchain[v.index] += g.weight
face_arm = np.array([np.mean([armchain[i] for i in p.vertices]) for p in body.data.polygons])
full_bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())

if MODE == "top":
    # low-poly cloth: where it touches the body its triangles are bigger than the gap, and the arm crossed the
    # middle of an armpit triangle with all 3 corners outside (jacket of 03/10/2026). Subdivide only the faces
    # within SUBDIV_DIST of the skin (2 rounds), so the vertex push below can resolve them.
    SUBDIV_DIST = float(os.environ.get("KV_SUBDIV_DIST", 0.02))
    for rnd in range(int(os.environ.get("KV_SUBDIV_ROUNDS", 0))):   # OFF: LOD1 went to 102k tris and the
                                                                 # armpit crumpled (jacket 03/10/2026)
        bm_s = bmesh.new(); bm_s.from_mesh(vest.data)
        bm_s.verts.ensure_lookup_table()
        near = set()
        for v in bm_s.verts:
            loc, n, idx, d = full_bvh.find_nearest(v.co)
            if loc is not None and (d < SUBDIV_DIST or (v.co - loc).dot(n) < 0):
                near.add(v.index)
        faces = [f for f in bm_s.faces if any(v.index in near for v in f.verts)]
        edges = list({e for f in faces for e in f.edges})
        if not edges:
            bm_s.free(); break
        bmesh.ops.subdivide_edges(bm_s, edges=edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm_s, faces=[f for f in bm_s.faces if len(f.verts) > 3])
        nf0 = len(vest.data.polygons)
        bm_s.to_mesh(vest.data); bm_s.free()
        vest.data.update()
        print("subdivided near the skin (round %d): %d faces close -> mesh %d -> %d faces" % (
            rnd, len(faces), nf0, len(vest.data.polygons)))

vco = np.array([v.co[:] for v in vest.data.vertices])
NV = len(vco)
GAPV = np.full(NV, GAP)
RIGID = np.zeros(NV)
if "kv_rigid" in vest.vertex_groups:
    _gi = vest.vertex_groups["kv_rigid"].index
    for v in vest.data.vertices:
        for g in v.groups:
            if g.group == _gi:
                RIGID[v.index] = g.weight
if CLOTH:
    # a garment triangle of side L laid over a convex body part of radius R lets the body bulge L^2/(8R) between
    # its corners. The jacket's armpit triangles (~8 cm) let the pectoral/deltoid stand 1.5-2 cm in front of the
    # cloth with every corner pushed clear (ray-cast diagnosis, 03/10/2026). So each vertex keeps GAP + L^2/8R.
    BULGE_R = float(os.environ.get("KV_BULGE_R", 0.05))
    elen = np.zeros(NV); ecnt = np.zeros(NV)
    for e in vest.data.edges:
        a_, b_ = e.vertices
        L = float(np.linalg.norm(vco[a_] - vco[b_]))
        elen[a_] += L; elen[b_] += L; ecnt[a_] += 1; ecnt[b_] += 1
    Lm = elen / np.maximum(ecnt, 1)
    GAPV = GAP + np.minimum(Lm ** 2 / (8 * BULGE_R), 0.02)
    print("clearance per vertex: %.1f..%.1f mm (mean edge %.1f mm)" % (GAPV.min() * 1000, GAPV.max() * 1000, Lm.mean() * 1000))


PARITY_DIRS = [mathutils.Vector(d).normalized() for d in ((1, 0.013, 0.007), (0.011, -1, 0.017), (0.009, 0.015, 1))]


def inside_by_parity(p):
    """majority of 3 rays: odd number of crossings = inside. The nearest-face sign alone is wrong on folds
    (female armpit: points 7 cm OUTSIDE came out as inside and the push grew a fin on the shoulder pad)."""
    votes = 0
    for d in PARITY_DIRS:
        hits, cur = 0, mathutils.Vector(p)
        for _ in range(64):
            h = full_bvh.ray_cast(cur, d, 5.0)
            if h[0] is None:
                break
            hits += 1
            cur = h[0] + d * 1e-5
        votes += hits % 2
    return votes >= 2


# The vanilla body is several OVERLAPPING shells (torso, arms, legs, head...). Counting crossings on the whole
# body says "outside" where two shells overlap (shoulder: torso + arm) - the jacket stayed 1.5 cm inside the
# deltoid with every vertex "outside" (ray-cast diagnosis 03/10/2026). Tops: inside = inside ANY shell.
SHELLS = []
SHELL_FACES = []
if CLOTH:
    bm_c = bmesh.new(); bm_c.from_mesh(body.data); bm_c.verts.ensure_lookup_table(); bm_c.faces.ensure_lookup_table()
    fcomp = np.full(len(bm_c.faces), -1); ncomp = 0
    for f0 in bm_c.faces:
        if fcomp[f0.index] >= 0:
            continue
        st = [f0]; fcomp[f0.index] = ncomp
        while st:
            f = st.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if fcomp[g.index] < 0:
                        fcomp[g.index] = ncomp; st.append(g)
        ncomp += 1
    bco = [v.co.copy() for v in bm_c.verts]
    for c in range(ncomp):
        fs = [[v.index for v in bm_c.faces[i].verts] for i in np.where(fcomp == c)[0]]
        if len(fs) >= 50:
            SHELLS.append(BVHTree.FromPolygons(bco, fs))
            SHELL_FACES.append(np.where(fcomp == c)[0])
    bm_c.free()
    print("body shells for the inside test: %d" % len(SHELLS))


def inside_shell(p, bvh_s):
    loc, n, idx, d = bvh_s.find_nearest(mathutils.Vector(p))
    if loc is None or d > 0.06 or (mathutils.Vector(p) - loc).dot(n) >= 0:
        return False
    votes = 0
    for dd in PARITY_DIRS:
        hits, cur = 0, mathutils.Vector(p)
        for _ in range(32):
            h = bvh_s.ray_cast(cur, dd, 5.0)
            if h[0] is None:
                break
            hits += 1
            cur = h[0] + dd * 1e-5
        votes += hits % 2
    return votes >= 2


# Tops: distance, push direction and skin weights come from the VISIBLE skin only. A face of one shell that lies
# inside another (torso bottom tucked into the legs part, top of the upper arm inside the torso) has a normal that
# points anywhere: the jacket hem was pushed DOWN along the tucked torso, 3-5 cm, in teeth (1st in-game test of the
# jacket, 04/10/2026).
VIS_BVH, VIS_FACE = None, None
if CLOTH:
    bpolys = [list(p.vertices) for p in body.data.polygons]
    bco_v = [v.co.copy() for v in body.data.vertices]
    in_shell = np.zeros(len(bpolys), bool); hidden = np.zeros(len(bpolys), bool)
    for ci, fis in enumerate(SHELL_FACES):
        in_shell[fis] = True
        for fi in fis:
            cen = sum((bco_v[k] for k in bpolys[fi]), mathutils.Vector()) / len(bpolys[fi])
            hidden[fi] = any(inside_shell(cen, SHELLS[cj]) for cj in range(len(SHELLS)) if cj != ci)
    VIS_FACE = np.where(~hidden)[0]
    VIS_BVH = BVHTree.FromPolygons(bco_v, [bpolys[fi] for fi in VIS_FACE])
    print("visible skin: %d of %d body faces (%d hidden inside another shell)" % (len(VIS_FACE), len(bpolys), hidden.sum()))


def signed_dist(pts):
    """signed distance to the full body, its normal, and whether the nearest skin is the arm chain"""
    out = np.zeros(len(pts)); nrm = np.zeros((len(pts), 3)); onarm = np.zeros(len(pts), bool)
    for i, p in enumerate(pts):
        if VIS_BVH is not None:
            loc, n, idx, d = VIS_BVH.find_nearest(mathutils.Vector(p))
            idx = VIS_FACE[idx]
        else:
            loc, n, idx, d = full_bvh.find_nearest(mathutils.Vector(p))
        if SHELLS:
            out[i] = -d if any(inside_shell(p, s) for s in SHELLS) else d
        else:
            out[i] = d if (mathutils.Vector(p) - loc).dot(n) >= 0 or not inside_by_parity(p) else -d
        nrm[i] = n[:]
        if VIS_BVH is not None and d > 1e-4:
            # cloth: away from the nearest skin POINT. The face normal jumps from facet to facet of the low-poly
            # hips and neighbouring hem vertices went different ways (teeth)
            nrm[i] = np.sign(out[i] if out[i] != 0 else 1.0) * (np.array(p) - np.array(loc[:])) / d
        onarm[i] = face_arm[idx] > 0.5
    return out, nrm, onarm


# ---- loose parts that sit on the upper arm (shoulder pads): rigid, follow the arm, never pushed ------
bmv = bmesh.new(); bmv.from_mesh(vest.data)
bmesh.ops.remove_doubles(bmv, verts=bmv.verts, dist=1e-5)      # glTF splits vertices at UV seams
bmv.verts.ensure_lookup_table()
comp = np.full(len(bmv.verts), -1)
nc = 0
for v0 in bmv.verts:
    if comp[v0.index] >= 0:
        continue
    stack = [v0]; comp[v0.index] = nc
    while stack:
        v = stack.pop()
        for e in v.link_edges:
            o = e.other_vert(v)
            if comp[o.index] < 0:
                comp[o.index] = nc; stack.append(o)
    nc += 1
wco = np.array([v.co[:] for v in bmv.verts])
bmv.free()
kdw = KDTree(len(wco))
for i, p in enumerate(wco):
    kdw.insert(p, i)
kdw.balance()
vcomp = np.array([comp[kdw.find(p)[1]] for p in vco])          # original vertex -> welded component
if CLOTH:
    widx = np.array([kdw.find(p)[1] for p in vco])                # original vertex -> welded vertex
    wadj = [set() for _ in range(len(wco))]
    for e in vest.data.edges:
        a_, b_ = widx[e.vertices[0]], widx[e.vertices[1]]
        if a_ != b_:
            wadj[a_].add(b_); wadj[b_].add(a_)
    wadj = [list(x) for x in wadj]
    wrep = np.zeros(len(wco), int); wrep[widx] = np.arange(NV)


def surface_range(w0, radius, wp):
    """welded vertices within an edge-path distance of welded vertex w0: {vertex: distance}"""
    dist = {w0: 0.0}; h = [(0.0, w0)]
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]:
            continue
        for w in wadj[u]:
            nd = d + math.dist(wp[u], wp[w])
            if nd <= radius and nd < dist.get(w, 1e9):
                dist[w] = nd; heapq.heappush(h, (nd, w))
    return dist
sd0, _, onarm0 = signed_dist(vco)
ARM_PART = np.zeros(NV, bool)
arm_comps = []
for c in range(nc):
    m = vcomp == c
    # a part is "on the arm" when most of its points have the arm as nearest skin
    if MODE == "vest" and m.sum() >= 50 and onarm0[m].mean() > 0.5:
        ARM_PART |= m
        arm_comps.append(c)
        cen = vco[m].mean(0)
        print("arm part: component %d, %d verts, centroid %s, inside arm %d" % (c, m.sum(), cen.round(3), (sd0[m] < 0).sum()))
print("components %d, arm-part verts %d" % (nc, ARM_PART.sum()))


def clip_stats(tag, pts):
    sd, _, onarm = signed_dist(pts)
    t = ~ARM_PART & ~onarm
    print("%s: inside torso=%d (<%.0fmm: %d) | inside arms (not pushed)=%d | arm parts inside=%d" % (
        tag, (sd[t] < 0).sum(), GAP * 1000, (sd[t] < GAP).sum(), (sd[~ARM_PART & onarm] < 0).sum(),
        (sd[ARM_PART] < 0).sum()))


def kdtree(pts):
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    return kd


SIGMA_ARM = 0.015   # arm parts: tighter falloff, and only inside the same loose part

# ---- shoulder pads on the SIDE of the arm: in game (03/10/2026) they sat in front of it. The source model
# has them ~25 deg forward of lateral around the arm axis; rotate every arm part of a side about the arm
# axis (one angle per side, from its biggest part, so the pieces stay together) until that part's centre
# has no forward component. PAD_EXTRA_BACK_DEG pushes further back if a test still shows them forward.
PAD_EXTRA_BACK_DEG = float(os.environ.get("KV_PAD_BACK_DEG", 15.0))   # 2nd in-game test: still a bit forward; more LeftArm weight = more twist
PAD_TILT_DEG = float(os.environ.get("KV_PAD_TILT_DEG", 0.0))   # bottom of the pad back, about its centre (build_vest passes PAD_TILT_FIXED)
for side_sign in (1.0, -1.0):
    comps = [c for c in arm_comps if np.sign(vco[vcomp == c, 0].mean()) == side_sign]
    if not comps:
        continue
    main = max(comps, key=lambda c: int((vcomp == c).sum()))
    J, d = arm_axis(side_sign)
    cen = vco[vcomp == main].mean(0)
    a = J + d * np.dot(cen - J, d)
    perp = (cen - a) - d * np.dot(cen - a, d)
    fwd = np.array([0.0, -1.0, 0.0]) - d * (-d[1])                 # character front, perpendicular to the arm
    fwd /= np.linalg.norm(fwd)
    ang = math.atan2(np.dot(perp, fwd), np.linalg.norm(perp - fwd * np.dot(perp, fwd)))   # > 0 = forward
    want = -np.linalg.norm(perp) * math.sin(math.radians(PAD_EXTRA_BACK_DEG))           # forward component wanted
    cands = [np.array(mathutils.Matrix.Rotation(s * (ang + math.radians(PAD_EXTRA_BACK_DEG)), 3, mathutils.Vector(d)))
             for s in (1.0, -1.0)]                                  # the rotation sense depends on the side
    R = min(cands, key=lambda R: abs(np.dot(R @ perp, fwd) - want))
    m = np.isin(vcomp, comps)
    vco[m] = a + (vco[m] - a) @ R.T
    print("pads %s: centre was %.0f deg forward of the side of the arm -> rotated back, now %.1f mm forward" % (
        "left" if side_sign > 0 else "right", math.degrees(ang), np.dot(R @ perp, fwd) * 1000))
    # TILT: 3rd in-game test - the shell leaned with its bottom forward (~12 deg) while the arm hangs slightly
    # back. Rotate about the axis perpendicular to the arm and to the front (with the arm down: the lateral
    # axis), pivoting on the shell's own centre - pivoting on the shoulder joint also slid the whole pad
    # back and fought the front/back balance (the joint calibration diverged).
    if abs(PAD_TILT_DEG) > 1e-3:
        k = np.cross(d, fwd); k /= np.linalg.norm(k)
        probe = np.array(mathutils.Matrix.Rotation(math.radians(1.0), 3, mathutils.Vector(k)))
        sgn = -1.0 if np.dot(probe @ d - d, fwd) > 0 else 1.0     # positive PAD_TILT_DEG = far end moves BACK
        Rt = np.array(mathutils.Matrix.Rotation(sgn * math.radians(PAD_TILT_DEG), 3, mathutils.Vector(k)))
        piv = vco[vcomp == main].mean(0)
        vco[m] = piv + (vco[m] - piv) @ Rt.T
        print("pads %s: tilted %.1f deg (+ = bottom back)" % ("left" if side_sign > 0 else "right", PAD_TILT_DEG))

clip_stats("before", vco)
# arm parts are rigid shells. An uncapped per-vertex push moved only the inner face of the female pad by
# 8 cm and grew a fin; scaling the part about the arm axis inflated the pads x1.6 (both rejected, renders
# 03/10/2026). What works: a small rigid translation of the part (median need, <= 3 cm), then the
# per-vertex push below, capped at ARM_PUSH_MAX; whatever is deeper stays and is reported.
ARM_SHIFT_MAX = 0.03
ARM_PUSH_MAX = 0.02
for c in arm_comps:
    m = np.where(vcomp == c)[0]
    sd, nrm, onarm = signed_dist(vco[m])
    v = (sd < GAP) & onarm
    if not v.any():
        continue
    need = (GAP - sd[v])[:, None] * nrm[v]
    T = np.median(need, 0)
    if np.linalg.norm(T) > ARM_SHIFT_MAX:
        T *= ARM_SHIFT_MAX / np.linalg.norm(T)
    vco[m] += T
    print("arm part %d: %d verts inside the arm (deepest %.1f mm) -> shifted %.1f mm" % (
        c, v.sum(), -sd[v].min() * 1000, np.linalg.norm(T) * 1000))
kd = kdtree(vco)
for it in range(6 if not CLOTH else 15):   # top: the smoothed push converges slower
    sd, nrm, onarm = signed_dist(vco)
    # vest body vs torso skin; arm parts (pad, biceps band) vs arm skin - the vanilla arm is thicker than
    # the arm the model was made for, so its band sat inside the biceps
    if CLOTH:
        bad = np.where((sd < GAPV) & (RIGID < 0.99))[0]   # sleeves must clear the arms too; never the rigid bag
    else:
        bad = np.where((sd < GAP) & ((~onarm & ~ARM_PART) | (onarm & ARM_PART)))[0]
    if len(bad) == 0:
        break
    depth = GAPV[bad] - sd[bad]
    depth = np.where(ARM_PART[bad], np.minimum(depth, ARM_PUSH_MAX / 6), depth)   # 6 iterations -> cap
    need = depth[:, None] * nrm[bad]
    best = np.zeros((NV, 3)); bestmag = np.zeros(NV)
    if CLOTH:
        # cloth: each violator pushes its neighbourhood ALONG THE SURFACE (edge paths). Through space the gaussian
        # reached the opposite wall of a thin sleeve and tore it (1st in-game test of the jacket, 04/10/2026).
        wp = [tuple(p) for p in vco[wrep]]
        first = {}
        for k, i in enumerate(bad):
            if widx[i] not in first or depth[k] > depth[first[widx[i]]]:
                first[widx[i]] = k
        wbest = np.zeros((len(wco), 3)); wmag = np.zeros(len(wco))
        for w0, k in first.items():
            mag0 = np.linalg.norm(need[k])
            for j, dist in surface_range(w0, 2.5 * SIGMA, wp).items():
                m = mag0 * math.exp(-(dist / SIGMA) ** 2)
                if m > wmag[j]:
                    wmag[j] = m; wbest[j] = need[k] * (m / mag0)
        for _ in range(3):                    # the max of many gaussians is ragged where two violators meet
            wbest = 0.5 * wbest + 0.5 * np.array([wbest[a_].mean(0) if a_ else wbest[j] for j, a_ in enumerate(wadj)])
        wmag = np.linalg.norm(wbest, axis=1)
        best, bestmag = wbest[widx], wmag[widx]
        best = best * (1 - RIGID)[:, None]; bestmag = bestmag * (1 - RIGID)   # backpack: the bag does not bend
    for k, i in enumerate(bad if not CLOTH else []):   # each violator pushes its neighbourhood with a gaussian falloff
        mag0 = np.linalg.norm(need[k])
        sig = SIGMA_ARM if ARM_PART[i] else SIGMA
        for (co, j, dist) in kd.find_range(vco[i], 2.5 * sig):
            if ARM_PART[j] != ARM_PART[i] or (ARM_PART[i] and vcomp[j] != vcomp[i]):
                continue
            m = mag0 * math.exp(-(dist / sig) ** 2)
            if m > bestmag[j]:
                bestmag[j] = m
                best[j] = need[k] * (m / mag0)
    vco = vco + best * 1.05
    print("push it %d: violators=%d max push=%.1fmm" % (it, len(bad), bestmag.max() * 1000))
    kd = kdtree(vco)
clip_stats("after", vco)

if MODE == "top" and os.environ.get("KV_BODY_PUSH", "0") == "1":   # OFF: did not converge (2nd try too)
    # 1st version (no rules) raised the inside count 1 -> 43: at the armpit fold an ARM vertex found a face of
    # the TORSO tube as nearest and pushed it into the arm. Rule now: an arm vertex never pushes a torso face;
    # push capped per iteration. Ray-cast diagnosis that motivated it: the pectoral/deltoid stood 1.5-2 cm in
    # FRONT of the jacket at the armpit, between the corners of one big triangle.
    # ---- 2nd push, driven by the BODY's vertices: a low-poly garment has big triangles at the armpit and the
    # arm passed through the middle of one with all 3 corners outside (jacket of 03/10/2026: skin showing at
    # the armpit). Every body vertex that is outside (or closer than GAP to) a garment face pushes that face
    # out. Rim faces (cuffs, collar, hem) are skipped: the hand/neck legitimately go through those openings.
    polys = [list(p.vertices) for p in vest.data.polygons]
    bm_r = bmesh.new(); bm_r.from_mesh(vest.data)
    bmesh.ops.remove_doubles(bm_r, verts=bm_r.verts, dist=1e-5)
    rim_pos = np.array([v.co[:] for e in bm_r.edges if e.is_boundary for v in e.verts]) if any(
        e.is_boundary for e in bm_r.edges) else np.zeros((0, 3))
    bm_r.free()
    kd_rim = KDTree(max(len(rim_pos), 1))
    for i, p in enumerate(rim_pos):
        kd_rim.insert(p, i)
    kd_rim.balance()
    body_pts = np.array([v.co[:] for v in body.data.vertices])
    SIGMA_T = 0.015
    PUSH_CAP = 0.010
    # arm-chain class of every body vertex (dominant weight) and of every garment vertex (its nearest skin)
    body_arm = armchain > 0.5
    g_arm = np.zeros(NV, bool)
    for i, p in enumerate(vco):
        loc, n, fi, d = full_bvh.find_nearest(mathutils.Vector(p))
        g_arm[i] = face_arm[fi] > 0.5
    for it in range(5):
        gb = BVHTree.FromPolygons([tuple(p) for p in vco], [tuple(p) for p in polys])
        # orientation of the garment winding: + if its face normals point away from the body
        votes = 0
        for p in vco[::max(1, NV // 400)]:
            loc, n, fi, d = gb.find_nearest(mathutils.Vector(p))
            bl, bn, bfi, bd = full_bvh.find_nearest(mathutils.Vector(p))
            votes += 1 if n.dot(mathutils.Vector(p) - bl) > 0 else -1
        s_out = 1.0 if votes >= 0 else -1.0
        need_at, need_vec = [], []
        for bi, b in enumerate(body_pts):
            loc, n, fi, d = gb.find_nearest(mathutils.Vector(b), 0.03)
            if loc is None:
                continue
            if body_arm[bi] and not any(g_arm[k] for k in polys[fi]):
                continue                                # arm vs torso tube: the arm is meant to be outside it
            if len(rim_pos) and kd_rim.find(loc)[2] < 0.02:
                continue                                # near an opening: hand / neck / waist go through
            sd = (mathutils.Vector(b) - loc).dot(n) * s_out      # > 0: the body is OUTSIDE the garment
            if sd > -GAP:
                need_at.append(np.array(loc[:])); need_vec.append(np.array(n[:]) * s_out * min(sd + GAP, PUSH_CAP))
        if not need_at:
            break
        best = np.zeros((NV, 3)); bestmag = np.zeros(NV)
        kdg = kdtree(vco)
        for at, vec in zip(need_at, need_vec):
            mag0 = np.linalg.norm(vec)
            for (co, j, dist) in kdg.find_range(at, 2.5 * SIGMA_T):
                mm = mag0 * math.exp(-(dist / SIGMA_T) ** 2)
                if mm > bestmag[j]:
                    bestmag[j] = mm; best[j] = vec * (mm / mag0)
        vco = vco + best * 1.05
        print("body-driven push it %d: %d body points outside/too close, max push %.1f mm" % (it, len(need_at), bestmag.max() * 1000))
    clip_stats("after body-driven push", vco)

for i, v in enumerate(vest.data.vertices):
    v.co = vco[i]
vest.data.update()

W = band_weights(vco) if MODE == "vest" else None

# ---- shoulder pads: copy the weights of the vanilla arm skin under them, so they twist with the arm exactly
# like the deltoid/biceps do (LeftArm + LeftArmRoll/Extra + clavicle). Smoothed over the side's parts so
# the assembly moves as one; the strap that climbs to the collar fades to the clavicle.
def pad_bone(n):
    l = n.lower()
    for side in ("left", "right"):
        S = side.capitalize()
        if l.startswith(side):
            r = l[len(side):]
            if r.startswith("shoulder"):
                return S + "Shoulder"
            if r.startswith("armroll") or r.startswith(("forearm", "elbow", "wrist", "hand")):
                return S + "ArmRoll"
            if r.startswith("armextra"):
                return S + "ArmExtra"
            if r.startswith("arm"):
                return S + "Arm"
    if l in ("spine3", "spine2", "neck"):
        return "Spine3"
    return None


if CLOTH:
    # copy the vanilla skin: nearest body face, barycentric blend of its vertices' weights, light smoothing
    gname_c = {vg.index: vg.name for vg in body.vertex_groups}
    BWs = np.zeros((len(body.data.vertices), len(ALLOWED)))
    for v in body.data.vertices:
        for g in v.groups:
            b = skin_bone(gname_c[g.group])
            if b:
                BWs[v.index, ALLOWED.index(b)] += g.weight
    BWs /= np.maximum(BWs.sum(1, keepdims=True), 1e-9)
    body_co = np.array([v.co[:] for v in body.data.vertices])
    tris_b = [list(p.vertices) for p in body.data.polygons]
    W = np.zeros((NV, len(ALLOWED)))
    for i, p in enumerate(vco):
        loc, n, fi, d = VIS_BVH.find_nearest(mathutils.Vector(p))     # visible skin (see VIS_BVH)
        fi = VIS_FACE[fi]
        a, b, c = (mathutils.Vector(body_co[k]) for k in tris_b[fi][:3])
        w = mathutils.geometry.barycentric_transform(loc, a, b, c, mathutils.Vector((1, 0, 0)),
                                                     mathutils.Vector((0, 1, 0)), mathutils.Vector((0, 0, 1)))
        w = np.clip(np.array(w[:]), 0, None); w /= max(w.sum(), 1e-9)
        W[i] = (BWs[tris_b[fi][:3]] * w[:, None]).sum(0)
    kdw2 = kdtree(vco)
    nbw = [[j for (_, j, _) in kdw2.find_range(p, 0.02)] for p in vco]
    for _ in range(2):
        W = np.array([W[nn].mean(0) for nn in nbw])
    W[W < 0.02] = 0
    order = np.argsort(-W, 1)
    W[np.arange(NV)[:, None], order[:, 4:]] = 0
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)

if MODE == "backpack":
    # harness: the skin under it, but only trunk + clavicle (arm -> that side's Shoulder, pelvis -> Spine1, neck ->
    # Spine3): a strap that followed the arm or the head would stretch. The bag: Spine3, one rigid block
    # (a working community MLOD backpack weights spine3 + spine1 + the shoulders).
    remap = {}
    for k, b in enumerate(ALLOWED):
        if any(t in b for t in ("Arm", "Hand", "Elbow", "Wrist")):
            remap[k] = ALLOWED.index(("Left" if b.startswith("Left") else "Right") + "Shoulder")
        elif b == "Pelvis":
            remap[k] = ALLOWED.index("Spine1")
        elif b == "Neck":
            remap[k] = ALLOWED.index("Spine3")
    for k, t in remap.items():
        W[:, t] += W[:, k]; W[:, k] = 0
    Wbag = np.zeros(len(ALLOWED)); Wbag[ALLOWED.index("Spine3")] = 1.0
    W = RIGID[:, None] * Wbag + (1 - RIGID)[:, None] * W
    W[W < 0.02] = 0
    order = np.argsort(-W, 1)
    W[np.arange(NV)[:, None], order[:, 4:]] = 0
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)

BWa = np.zeros((len(body.data.vertices), len(ALLOWED)))
for v in body.data.vertices:
    for g in v.groups:
        b = pad_bone(gname[g.group])
        if b:
            BWa[v.index, ALLOWED.index(b)] += g.weight
region = np.where(BWa.sum(1) > 0.5)[0]
BWa[region] /= BWa[region].sum(1, keepdims=True)
kdb = KDTree(len(region))
for k, i in enumerate(region):
    kdb.insert(body.data.vertices[i].co, k)
kdb.balance()
for side_sign in (1.0, -1.0):
    m = np.where(ARM_PART & (np.sign(vco[:, 0]) == side_sign))[0]
    if len(m) == 0:
        continue
    Wp = np.zeros((len(m), len(ALLOWED)))
    for k, i in enumerate(m):
        near = kdb.find_n(vco[i], 4)
        w = np.array([1.0 / max(dd, 1e-4) for (_, _, dd) in near])
        Wp[k] = (BWa[region[[j for (_, j, _) in near]]] * w[:, None]).sum(0) / w.sum()
    kdp = kdtree(vco[m])
    nb = [[j for (_, j, _) in kdp.find_range(vco[i], 0.04)] for i in m]
    for _ in range(3):
        Wp = np.array([Wp[n].mean(0) for n in nb])
    S = "Left" if side_sign > 0 else "Right"
    arm1 = np.zeros(len(ALLOWED)); arm1[ALLOWED.index(S + "Arm")] = 1.0
    g = float(os.environ.get("KV_PAD_ARM_BLEND", PAD_ARM_BLEND))
    Wp = (1 - g) * Wp + g * arm1
    J, d = arm_axis(side_sign)
    t = (vco[m] - J) @ d
    f = np.interp(t, ARM_FADE_T, [0.0, 1.0])[:, None]
    clav = np.zeros(len(ALLOWED)); clav[ALLOWED.index(S + "Shoulder")] = 1.0
    Wp = f * Wp + (1 - f) * clav
    Wp[Wp < 0.02] = 0
    order = np.argsort(-Wp, 1)
    Wp[np.arange(len(Wp))[:, None], order[:, 4:]] = 0
    W[m] = Wp / Wp.sum(1, keepdims=True)
    print("pads %s: mean weights %s" % ("left" if side_sign > 0 else "right",
          {ALLOWED[k]: round(float(W[m, k].mean()), 2) for k in range(len(ALLOWED)) if W[m, k].mean() > 0.01}))
cnt = (W > 0).sum(1)
print("influences/vertex", {int(k): int((cnt == k).sum()) for k in range(1, 5)})
for vg in list(vest.vertex_groups):
    if vg.name != "kv_rigid":                     # backpack: s02c (female) needs it; s07 reads only bone groups
        vest.vertex_groups.remove(vg)
for k, b in enumerate(ALLOWED):
    vg = vest.vertex_groups.new(name=b)
    for i in np.where(W[:, k] > 0)[0]:
        vg.add([int(i)], float(W[i, k]), "REPLACE")
    print("  %-14s verts=%5d max=%.2f" % (b, (W[:, k] > 0).sum(), W[:, k].max()))
bpy.ops.wm.save_as_mainfile(filepath=OUTBLEND)
print("SAVED", OUTBLEND)

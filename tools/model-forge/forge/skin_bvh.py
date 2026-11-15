"""The vanilla body as BVHs: per-shell (torso, arms, legs, head are separate overlapping parts) and the VISIBLE
skin (faces not inside another shell). Same rules as s03 top; used by s02c (female transfer) and s02d (backpack).
"""
import bmesh
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree

PARITY_DIRS = [mathutils.Vector(d).normalized() for d in ((1, 0.013, 0.007), (0.011, -1, 0.017), (0.009, 0.015, 1))]


def shells(obj):
    """the vanilla body is several overlapping closed-ish shells (torso, arms, legs, head): one BVH per part"""
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.faces.ensure_lookup_table()
    comp = np.full(len(bm.faces), -1); nc = 0
    for f0 in bm.faces:
        if comp[f0.index] >= 0:
            continue
        st = [f0]; comp[f0.index] = nc
        while st:
            f = st.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if comp[g.index] < 0:
                        comp[g.index] = nc; st.append(g)
        nc += 1
    bm.free()
    co = [v.co.copy() for v in obj.data.vertices]
    polys = [list(p.vertices) for p in obj.data.polygons]
    out = []
    for c in range(nc):
        fis = np.where(comp == c)[0]
        if len(fis) >= 50:
            out.append((BVHTree.FromPolygons(co, [polys[i] for i in fis]), fis))
    return out, co, polys


def inside(p, bvh):
    loc, n, idx, d = bvh.find_nearest(p)
    if loc is None or d > 0.06 or (p - loc).dot(n) >= 0:
        return False
    votes = 0
    for dd in PARITY_DIRS:
        hits, cur = 0, p
        for _ in range(32):
            h = bvh.ray_cast(cur, dd, 5.0)
            if h[0] is None:
                break
            hits += 1
            cur = h[0] + dd * 1e-5
        votes += hits % 2
    return votes >= 2


def visible_skin(obj):
    """BVH of the faces that are not inside another shell (same rule as s03 top)"""
    sh, co, polys = shells(obj)
    hidden = np.zeros(len(polys), bool)
    for ci, (_, fis) in enumerate(sh):
        for fi in fis:
            cen = sum((co[k] for k in polys[fi]), mathutils.Vector()) / len(polys[fi])
            hidden[fi] = any(inside(cen, sh[cj][0]) for cj in range(len(sh)) if cj != ci)
    vis = np.where(~hidden)[0]
    return BVHTree.FromPolygons(co, [polys[i] for i in vis]), sh

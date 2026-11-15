"""Female top FROM the male one (tops only): carry the fitted, pushed male garment over to the female body.

blender -b skin_male.blend --python s02c_transfer.py -- <out fit_female.blend>

Fitting the source model to the female body on its own (uniform scale, like the vests) gave a man's jacket on a
woman: square shoulders, the armhole 4 cm high inside the shoulder (a flap behind the armpit) and the hem 8 cm
higher than on the male, a see-through gap above the trousers (in-game test of 04/10/2026).
Each garment vertex keeps its distance from the skin: nearest point of the male VISIBLE skin, the ray from there
through the vertex, the point where that ray line meets the female skin, the same offset from it. The
displacement is smoothed over the welded garment; s03 then pushes and weights it against the female body.
Writes out.blend with 'vest' (carried over) and 'body' (the female MLOD), as s03 expects.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh
import bpy
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from bl_common import BODY_F, load_p3d_mesh
from skin_bvh import inside, visible_skin

OUTB = sys.argv[sys.argv.index("--") + 1:][0]
if not BODY_F:
    raise SystemExit("FORGE_BODY_FEMALE not set (build_vest.py sets it from forge.json)")
REACH = 0.12          # farthest the female skin may be from the male skin along the ray (m)
SMOOTH = 6

vest = bpy.data.objects["vest"]
male = bpy.data.objects["body"]
male.name = "body_male"
female = load_p3d_mesh(BODY_F, 0, "body")


mvis, _ = visible_skin(male)
fvis, fsh = visible_skin(female)
V = np.array([v.co[:] for v in vest.data.vertices])
D = np.zeros_like(V)
miss = 0
for i, p in enumerate(V):
    pv = mathutils.Vector(p)
    loc, n, fi, d = mvis.find_nearest(pv)
    u = (pv - loc) / d if d > 1e-5 else n
    # male skin point inside the female body -> her skin is further out along u, else further in
    ray = u if any(inside(loc, b) for b, _ in fsh) else -u
    h = fvis.ray_cast(loc, ray, REACH)
    if h[0] is None:
        miss += 1
        continue
    D[i] = np.array((h[0] + u * d)[:]) - p

# smooth the displacement over the welded garment (glTF splits vertices at UV seams; facets of the low-poly
# bodies make neighbouring rays land on different faces)
bm = bmesh.new(); bm.from_mesh(vest.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.verts.ensure_lookup_table()
kd = KDTree(len(bm.verts))
for v in bm.verts:
    kd.insert(v.co, v.index)
kd.balance()
widx = np.array([kd.find(p)[1] for p in V])
adj = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
bm.free()
WD = np.zeros((len(adj), 3)); cnt = np.zeros(len(adj))
np.add.at(WD, widx, D); np.add.at(cnt, widx, 1)
WD /= np.maximum(cnt, 1)[:, None]
for _ in range(SMOOTH):
    WD = 0.5 * WD + 0.5 * np.array([WD[a].mean(0) if a else WD[k] for k, a in enumerate(adj)])
D = WD[widx]

# backpack: the bag (vertex group kv_rigid from s02d) moves as ONE block - the mean move of its vertices that touch
# the back - and is then slid back until it clears her back; only the harness follows her skin vertex by vertex
RIG = np.zeros(len(V))
if "kv_rigid" in vest.vertex_groups:
    gi = vest.vertex_groups["kv_rigid"].index
    for v in vest.data.vertices:
        for g in v.groups:
            if g.group == gi:
                RIG[v.index] = g.weight
    near = [i for i in np.where(RIG > 0.99)[0] if mvis.find_nearest(mathutils.Vector(V[i]))[3] < 0.05]
    Drig = D[near].mean(0) if near else np.zeros(3)
    D = RIG[:, None] * Drig + (1 - RIG)[:, None] * D
    rid = np.where(RIG > 0.99)[0]

    def clearance(dy):
        best = 9.0
        for i in rid:
            q = mathutils.Vector(V[i] + D[i] + (0, dy, 0))
            loc, n, fi, d = fvis.find_nearest(q)
            best = min(best, -d if (q - loc).dot(n) < 0 else d)
        return best
    lo, hi = 0.0, 0.0
    if clearance(0.0) < 0.006:
        hi = 0.15
        for _ in range(16):
            mid = (lo + hi) / 2
            if clearance(mid) < 0.006:
                lo = mid
            else:
                hi = mid
    D += RIG[:, None] * np.array([0.0, hi, 0.0])
    print("bag moved as a block by %s mm (+%.0f mm back to clear her back)" % ((Drig * 1000).round(0), hi * 1000))
mag = np.linalg.norm(D, axis=1)
print("transfer male -> female: moved %.0f mm max, %.0f mm mean; %d vertices without female skin in reach" % (
    mag.max() * 1000, mag.mean() * 1000, miss))
for i, v in enumerate(vest.data.vertices):
    v.co = V[i] + D[i]
vest.data.update()
for vg in list(vest.vertex_groups):        # s03 copies the female skin weights
    if vg.name != "kv_rigid":
        vest.vertex_groups.remove(vg)
bpy.data.objects.remove(male, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=OUTB)
print("SAVED", OUTB)

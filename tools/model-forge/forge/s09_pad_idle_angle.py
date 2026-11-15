"""Measure where the shoulder pads end up around the arm in the emulated in-game idle pose.

blender -b RIG.blend --python s09_pad_idle_angle.py -- <skin_<sex>.blend> <male|female>
Prints  PAD_IDLE_FWD_DEG left=<a> right=<b> mean=<m>   (> 0 = pad centre in FRONT of the arm, < 0 = behind)

The pad is every vertex whose biggest weight is LeftArm/RightArm (the biceps band included, since it is
part of the same assembly). Angle measured around the posed upper-arm bone, in the plane perpendicular to
it, from the outward (lateral) direction towards the character front (-Y).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import mathutils
import numpy as np

SKIN, SEX = sys.argv[sys.argv.index("--") + 1:][:2]
with bpy.data.libraries.load(SKIN, link=False) as (src, dst):
    dst.objects = ["vest"]
vest = dst.objects[0]
bpy.context.scene.collection.objects.link(vest)
arm = bpy.data.objects["Armature"]
mod = vest.modifiers.new("arm", "ARMATURE")
mod.object = arm

# same pose as s04 "idle_game" (arm down, deltoid helper lagging half)
POSE = [("LeftArm", "Y", 42), ("RightArm", "Y", -42), ("LeftArmExtra", "Y", -17), ("RightArmExtra", "Y", 17)]
pbs = arm.pose.bones
for b, ax, deg in POSE:
    pb = pbs[b]
    Mw = (arm.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
    Rl = Mw.inverted() @ mathutils.Matrix.Rotation(math.radians(deg), 3, ax) @ Mw
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Rl.to_quaternion() @ pb.rotation_quaternion
bpy.context.view_layer.update()

dg = bpy.context.evaluated_depsgraph_get()
ev = vest.evaluated_get(dg)
P = np.array([(vest.matrix_world @ v.co)[:] for v in ev.data.vertices])
body = bpy.data.objects["male player" if SEX == "male" else "female player"]
evb = body.evaluated_get(dg)
BP = np.array([(body.matrix_world @ v.co)[:] for v in evb.data.vertices])
gb = {vg.index: vg.name for vg in body.vertex_groups}
bones = {b.name for b in arm.data.bones}          # the body also has non-bone groups (l_arm_injury...) at 1.0
BEST_BODY = []
for v in body.data.vertices:
    gs = sorted(((g.weight, gb[g.group]) for g in v.groups if gb[g.group] in bones), reverse=True)
    BEST_BODY.append(gs[0][1] if gs else "")
BEST_BODY = np.array(BEST_BODY)
gi = {vg.index: vg.name for vg in vest.vertex_groups}
best = []
for v in vest.data.vertices:
    gs = sorted(((g.weight, gi[g.group]) for g in v.groups), reverse=True)
    best.append(gs[0][1] if gs else "")
import bmesh
from mathutils.kdtree import KDTree
# connected parts (welded: glTF splits vertices at UV seams) - measure the BIGGEST arm part only: the back
# straps of the assembly pull a plain centroid backwards (first version of this script said -17 deg while
# the render clearly showed the shell in front of the arm)
bm = bmesh.new(); bm.from_mesh(vest.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.verts.ensure_lookup_table()
comp = np.full(len(bm.verts), -1); nc = 0
for v0 in bm.verts:
    if comp[v0.index] >= 0:
        continue
    st = [v0]; comp[v0.index] = nc
    while st:
        v = st.pop()
        for e in v.link_edges:
            o = e.other_vert(v)
            if comp[o.index] < 0:
                comp[o.index] = nc; st.append(o)
    nc += 1
kd = KDTree(len(bm.verts))
for v in bm.verts:
    kd.insert(v.co, v.index)
kd.balance()
vcomp = np.array([comp[kd.find(v.co)[1]] for v in vest.data.vertices])
res = {}
for side in ("Left", "Right"):
    isarm = np.array([b == side + "Arm" for b in best])
    if not isarm.any():
        continue
    cs, cnt = np.unique(vcomp[isarm], return_counts=True)
    m = vcomp == cs[np.argmax(cnt)]
    # reference = the VISIBLE arm, not the bone: the rig's upper-arm bone does not run through the middle of
    # the arm mesh, so "lateral to the bone" still looked forward in the render. Compare, at the same
    # heights, the shell centre with the centre of the posed arm skin (what a side view shows).
    c = P[m].mean(0)
    zlo, zhi = np.percentile(P[m, 2], [10, 90])
    sel = (BEST_BODY == side + "Arm") & (BP[:, 2] > zlo) & (BP[:, 2] < zhi)
    if sel.sum() < 10:
        sel = (BEST_BODY == side + "Arm")
    ac = BP[sel].mean(0)
    # what a side view shows: how far the shell sticks out in front of the arm vs behind it (front = -Y)
    front = (BP[sel, 1].min() - P[m, 1].min()) * 1000.0
    back = (P[m, 1].max() - BP[sel, 1].max()) * 1000.0
    # TILT in the side view (y-z plane): long axis of the shell (top slice -> bottom slice) vs the arm
    # (arm skin slices at the same heights). 3rd in-game test (03/10/2026): the shell leaned with its bottom
    # forward while the arm hangs slightly back - the user wants it parallel to the arm.
    # SILHOUETTE in the side view (what the user outlined): in horizontal slices, the front (min y) and back
    # (max y) edges of the shell and of the upper arm; fit a line to each edge, average front+back slope.
    # The top of the shell curves over the shoulder, so only its lower 75% is used.
    z = P[m, 2]
    z0, z1 = np.percentile(z, 3), np.percentile(z, 75)
    armv = np.isin(BEST_BODY, [side + "Arm", side + "ArmExtra", side + "ArmRoll", side + "Shoulder"])

    def edge_slope(pts, lo, hi):
        zs, f, b = [], [], []
        for zz in np.linspace(lo, hi, 9):
            s = pts[np.abs(pts[:, 2] - zz) < 0.008]
            if len(s) >= 3:
                zs.append(zz); f.append(s[:, 1].min()); b.append(s[:, 1].max())
        if len(zs) < 4:
            return float("nan")
        kf = np.polyfit(zs, f, 1)[0]; kb = np.polyfit(zs, b, 1)[0]
        return math.degrees(math.atan(-(kf + kb) / 2))                           # + = bottom further back

    pad_ang = edge_slope(P[m], z0, z1)
    arm_ang = edge_slope(BP[armv & (np.abs(BP[:, 0]) > 0.12)], z0, z1)
    tilt = arm_ang - pad_ang                                                     # + = shell bottom ahead of the arm line
    res[side] = ((c[1] - ac[1]) * 1000.0, front, back, tilt)
for side, (cm, fr, bk, tl) in res.items():
    print("PAD_IDLE %s %s: centre %+.1f mm (+ = behind the arm) | sticks out in front %.1f mm, behind %.1f mm | "
          "BALANCE %+.1f mm (+ = more in front) | TILT %+.1f deg (+ = bottom leaning forward vs the arm)" % (
              SEX, side, cm, fr, bk, fr - bk, tl))
# machine-readable for build_vest's calibration loop. Matches the in-game look (03/10/2026): +76 mm =
# "in front" (test 1), +42 mm = "almost, a bit forward" (test 2), +15/+18 mm still forward in the render.
print("BALANCE_MM=%s" % (("%.2f" % float(np.mean([r[1] - r[2] for r in res.values()]))) if res else "nan"))
print("TILT_DEG=%s" % (("%.2f" % float(np.mean([r[3] for r in res.values()]))) if res else "nan"))

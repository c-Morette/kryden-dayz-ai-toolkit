"""Proof from the WRITTEN p3d: rebuild the scene from <name>_<sex>.p3d (LOD index arg), bind its bone
selections to the RIG armature, render with backface culling + texture, rest and posed.
blender -b RIG_copy.blend --python s08_verify_p3d.py -- <p3d> <lod_index> <co.png> <outdir> <prefix> <male|female|ground>"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import mathutils
import numpy as np
from mathutils.bvhtree import BVHTree
from bl_common import *

args = sys.argv[sys.argv.index("--") + 1:]
P3D, LODI, CO, OUT, PREFIX, SEX = args[0], int(args[1]), args[2], args[3], args[4], args[5]
# optional zoom: ortho scale and look-at point (x z) for close-ups
OS = float(args[6]) if len(args) > 6 else 1.05
TGT = (float(args[7]), 0, float(args[8])) if len(args) > 8 else (0, 0, 1.2)
os.makedirs(OUT, exist_ok=True)
arm = bpy.data.objects["Armature"]
bone_names = {b.name.lower(): b.name for b in arm.data.bones}
vest = load_p3d_mesh(P3D, LODI, "vest", use_normals=True)
for vg in vest.vertex_groups:                       # p3d lowercase -> rig bone names
    if vg.name.lower() in bone_names:
        vg.name = bone_names[vg.name.lower()]
me = vest.data
# winding sanity: face normal vs ray parity (closed parts) on a sample
bvh = BVHTree.FromObject(vest, bpy.context.evaluated_depsgraph_get())
rng = np.random.default_rng(1)
idx = rng.choice(len(me.polygons), size=min(3000, len(me.polygons)), replace=False)
out_ok = in_bad = open_ = 0
for i in idx:
    p = me.polygons[int(i)]
    o = p.center + p.normal * 1e-4
    hits = 0
    cur = o
    for _ in range(64):
        h = bvh.ray_cast(cur, p.normal, 5.0)
        if h[0] is None:
            break
        hits += 1
        cur = h[0] + p.normal * 1e-4
    if hits == 0:
        open_ += 1
    elif hits % 2 == 0:
        out_ok += 1
    else:
        in_bad += 1
print("PARITY sample=%d escape(no hit)=%d even(outward)=%d odd(inward)=%d" % (len(idx), open_, out_ok, in_bad))

m = bpy.data.materials.new("tex"); m.use_nodes = True
tex = m.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(CO)
m.node_tree.links.new(tex.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
me.materials.append(m)

keep = {"male": "male player", "female": "female player"}.get(SEX)
for o in bpy.data.objects:
    if o.type in ("MESH", "EMPTY") and o is not vest and (keep is None or o.name != keep):
        o.hide_render = True
if keep:
    body = bpy.data.objects[keep]; body.hide_render = False
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False
    body.data.materials.clear(); body.data.materials.append(flat_material("skin", (0.80, 0.62, 0.50, 1)))
    mod = vest.modifiers.new("arm", "ARMATURE"); mod.object = arm
setup_render((900, 1100))
sc = bpy.context.scene
sc.display.shading.color_type = "TEXTURE"
sc.display.shading.show_backface_culling = True
if keep:
    render_views(OUT, PREFIX + "_rest", TGT, 4.0, [("front", 0, 0), ("back", 180, 0), ("q34", 35, 15)], ortho_scale=OS)
    pbs = arm.pose.bones
    def rot_world(bone, axis, deg):
        pb = pbs[bone]
        Mw = (arm.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
        Rl = Mw.inverted() @ mathutils.Matrix.Rotation(math.radians(deg), 3, axis) @ Mw
        pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = Rl.to_quaternion() @ pb.rotation_quaternion
    for b, ax, d in [("Spine1", "X", 10), ("Spine2", "X", 10), ("Spine3", "X", 8), ("Spine2", "Z", 10),
                     ("LeftArm", "X", 60), ("RightArm", "X", 60), ("Neck", "Z", 25)]:
        rot_world(b, ax, d)
    bpy.context.view_layer.update()
    render_views(OUT, PREFIX + "_posed", TGT, 4.0, [("q34", 35, 15), ("side", 90, 0), ("front", 0, 10)], ortho_scale=OS)
else:
    render_views(OUT, PREFIX, (0, 0, 0.2), 3.0, [("top", 0, 89), ("q34", 35, 35), ("front", 0, 5)], ortho_scale=1.0)
print("DONE")

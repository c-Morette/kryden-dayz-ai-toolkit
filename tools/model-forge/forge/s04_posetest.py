"""Pose test on the vanilla rig: blender -b RIG.blend --python s04_posetest.py -- <skin.blend> <outdir> <prefix> <male|female> [textured]
Appends 'vest' from skin.blend, binds it to 'Armature' (vertex groups = bone names) and renders poses."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import mathutils
from bl_common import *

args = sys.argv[sys.argv.index("--") + 1:]
SKIN, OUT, PREFIX, SEX = args[0], args[1], args[2], args[3]
TEX = len(args) > 4 and args[4] == "textured"
os.makedirs(OUT, exist_ok=True)
with bpy.data.libraries.load(SKIN, link=False) as (src, dst):
    dst.objects = ["vest"]
vest = dst.objects[0]
bpy.context.scene.collection.objects.link(vest)
arm = bpy.data.objects["Armature"]
mod = vest.modifiers.new("arm", "ARMATURE")
mod.object = arm
mod.use_vertex_groups = True
keep_body = "male player" if SEX == "male" else "female player"
for o in bpy.data.objects:
    if o.type == "MESH" and o not in (vest, bpy.data.objects[keep_body]):
        o.hide_render = True
    if o.type == "EMPTY":
        o.hide_render = True
body = bpy.data.objects[keep_body]
body.hide_render = False
body.hide_viewport = False
for c in body.users_collection:
    c.hide_render = False
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = False
body.name = "body_rig"
setup_render((900, 1100))
body.data.materials.clear(); body.data.materials.append(flat_material("skin", (0.80, 0.62, 0.50, 1)))
if not TEX:
    vest.data.materials.clear(); vest.data.materials.append(flat_material("vestmat", (0.32, 0.36, 0.26, 1)))
bpy.context.scene.display.shading.color_type = "TEXTURE" if TEX else "MATERIAL"

pbs = arm.pose.bones


def rot_world(bone, axis, deg):
    pb = pbs[bone]
    Mw = (arm.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
    Rw = mathutils.Matrix.Rotation(math.radians(deg), 3, axis)
    Rl = Mw.inverted() @ Rw @ Mw
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = Rl.to_quaternion() @ pb.rotation_quaternion


def reset():
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)


POSES = {
    "rest": [],
    # arms hanging at the sides, like the in-game idle (the A-pose arm is ~40 deg out)
    "idle": [("LeftArm", "Y", 42), ("RightArm", "Y", -42)],
    # emulation of the in-game idle: the deltoid helper (ArmExtra) lags ~half of the arm drop
    # (calibrated on the in-game back view of 03/10/2026, where the pads flared ~12 deg)
    "idle_game": [("LeftArm", "Y", 42), ("RightArm", "Y", -42), ("LeftArmExtra", "Y", -17), ("RightArmExtra", "Y", 17)],
    # forward bend: +X rotation in Blender world tips the top towards -Y (front)
    "bend": [("Spine1", "X", 12), ("Spine2", "X", 12), ("Spine3", "X", 12), ("Neck", "X", 10)],
    "lean_back": [("Spine1", "X", -10), ("Spine2", "X", -10), ("Spine3", "X", -8)],
    "twist": [("Spine1", "Z", 12), ("Spine2", "Z", 12), ("Spine3", "Z", 12)],
    "side": [("Spine1", "Y", 10), ("Spine2", "Y", 10), ("Spine3", "Y", 8)],
    # arms down along the body (like in game idle) and arms up/forward (aiming)
    "arms_horizontal": [("LeftArm", "Y", -40), ("RightArm", "Y", 40)],
    "aim": [("LeftArm", "X", 70), ("RightArm", "X", 70), ("LeftArm", "Y", -25), ("RightArm", "Y", 25)],
    "arms_down": [("LeftArm", "Y", 60), ("RightArm", "Y", -60), ("LeftShoulder", "Y", 15), ("RightShoulder", "Y", -15)],
}
sel = args[5].split(",") if len(args) > 5 else list(POSES)
for name in sel:
    reset()
    for b, ax, d in POSES[name]:
        rot_world(b, ax, d)
    bpy.context.view_layer.update()
    views = [("front", 0, 5), ("side", 90, 5), ("q34", 35, 15)]
    if name in ("rest", "aim", "idle", "idle_game"):
        views.append(("back", 180, 5))
    render_views(OUT, "%s_%s" % (PREFIX, name), (0, 0, 1.2), 4.0, views, ortho_scale=1.05)
print("DONE")

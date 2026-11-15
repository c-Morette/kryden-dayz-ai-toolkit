"""Debug: paint the vest faces whose vertices are rigid arm parts (LeftArm/RightArm >= 0.69) in red, the rest grey.
blender -b skin_<sex>.blend --python s_debug_armparts.py -- <outdir> <prefix>"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from bl_common import *

OUT, PREFIX = sys.argv[sys.argv.index("--") + 1:][:2]
vest = bpy.data.objects["vest"]
me = vest.data
gi = {vg.name: vg.index for vg in vest.vertex_groups}
arm_ids = {gi.get("LeftArm"), gi.get("RightArm")}
isarm = [any(g.group in arm_ids and g.weight >= 0.69 for g in v.groups) for v in me.vertices]
me.materials.clear()
me.materials.append(flat_material("rest", (0.45, 0.45, 0.42, 1)))
me.materials.append(flat_material("armpart", (0.85, 0.12, 0.10, 1)))
for p in me.polygons:
    p.material_index = 1 if all(isarm[i] for i in p.vertices) else 0
bpy.data.objects["body"].hide_render = False
setup_render((900, 1100))
bpy.context.scene.display.shading.color_type = "MATERIAL"
bpy.data.objects["body"].data.materials.clear()
bpy.data.objects["body"].data.materials.append(flat_material("skin", (0.80, 0.62, 0.50, 1)))
render_views(OUT, PREFIX, (0, 0, 1.3), 4.0, [("front", 0, 0), ("back", 180, 0), ("side", 90, 0), ("q34b", 145, 20)], ortho_scale=0.8)

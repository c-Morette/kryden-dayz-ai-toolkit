"""Render a fit/pose blend: blender -b X.blend --python s_render.py -- <outdir> <prefix> [ortho_scale] [zc]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from bl_common import *

args = sys.argv[sys.argv.index("--") + 1:]
OUT, PREFIX = args[0], args[1]
OS = float(args[2]) if len(args) > 2 else 1.1
ZC = float(args[3]) if len(args) > 3 else 1.2
os.makedirs(OUT, exist_ok=True)
setup_render((900, 1100))
sc = bpy.context.scene
use_tex = any(o.name.startswith("vest") and o.type == "MESH" and o.data.materials and o.data.materials[0]
              and o.data.materials[0].use_nodes and any(n.type == "TEX_IMAGE" for n in o.data.materials[0].node_tree.nodes)
              for o in bpy.data.objects)
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    if o.name.startswith("body"):
        o.data.materials.clear()
        o.data.materials.append(flat_material("skin", (0.80, 0.62, 0.50, 1)))
    elif o.name.startswith("vest") and not use_tex:
        o.data.materials.clear()
        o.data.materials.append(flat_material("vestmat", (0.32, 0.36, 0.26, 1)))
sc.display.shading.color_type = "TEXTURE" if use_tex else "MATERIAL"
render_views(OUT, PREFIX, (0, 0, ZC), 4.0,
             [("front", 0, 0), ("side", 90, 0), ("back", 180, 0), ("q34", 35, 15), ("top", 0, 89)], ortho_scale=OS)

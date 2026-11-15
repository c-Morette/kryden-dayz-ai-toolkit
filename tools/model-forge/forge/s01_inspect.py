"""Look at a source model before building: bbox, mesh list, open boundaries (holes you can see into), whether
it is a single surface (needs an inner shell in DayZ: single-sided rendering), and front/side/top renders.

blender -b --python s01_inspect.py -- <model.glb|.zip> <outdir>"""
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
import mathutils
import numpy as np
from bl_common import render_views, setup_render

SRC, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(OUT, exist_ok=True)
GLB = SRC
if SRC.lower().endswith(".zip"):
    with zipfile.ZipFile(SRC) as z:
        n = [x for x in z.namelist() if x.lower().endswith(".glb")][0]
        GLB = os.path.join(OUT, os.path.basename(n))
        open(GLB, "wb").write(z.read(n))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
allv = []
for o in meshes:
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    co = np.array([(o.matrix_world @ v.co)[:] for v in me.vertices])
    allv.append(co)
    print("MESH %-40s verts=%6d tris~%6d boundary_edges=%5d nonmanifold=%5d bbox %s %s" % (
        o.name, len(me.vertices), sum(len(p.vertices) - 2 for p in me.polygons), boundary, nonman,
        co.min(0).round(3), co.max(0).round(3)))
A = np.vstack(allv)
mn, mx = A.min(0), A.max(0)
print("ALL bbox", mn.round(3), mx.round(3), "size", (mx - mn).round(3), "width/height %.2f" % ((mx[0] - mn[0]) / (mx[2] - mn[2])))
setup_render((1000, 800))
bpy.context.scene.display.shading.color_type = "TEXTURE"
c = (mn + mx) / 2
d = float(np.linalg.norm(mx - mn)) * 1.6
render_views(OUT, "src", tuple(c), d, [("front", 0, 0), ("side", 90, 0), ("back", 180, 0), ("top", 0, 89), ("q34", 35, 20)],
             ortho_scale=float(max(mx - mn)) * 1.15)
print("DONE")

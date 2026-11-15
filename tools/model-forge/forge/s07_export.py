"""Export the fitted vest LODs to JSON for the MLOD writer.
blender -b skin_<sex>.blend --python s07_export.py -- <out.json> [ratios=1,0.45,0.18]
JSON: {"bones": [...], "lods": [{"ratio", "verts": [[x,y,z] Blender], "weights": [[w per bone]],
        "faces": [[[vi, nx, ny, nz, u, v] x3]]}]}  (u, v already in p3d convention: v_p3d = 1 - v_blender)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
import numpy as np
from mathutils.kdtree import KDTree
from weights_bands import ALLOWED

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
RATIOS = [float(x) for x in (args[1] if len(args) > 1 else "1,0.45,0.18").split(",")]
INNER_SHELL = os.environ.get("KV_INNER_SHELL", "0") == "1"
INNER_OFFSET = 0.0015
src = bpy.data.objects["vest"]
# the skinned vest (s03) is the source of truth for the weights; decimated LODs take the nearest vertex
gi = {vg.index: vg.name for vg in src.vertex_groups}
SW = np.zeros((len(src.data.vertices), len(ALLOWED)))
for v in src.data.vertices:
    for g in v.groups:
        if gi[g.group] in ALLOWED:
            SW[v.index, ALLOWED.index(gi[g.group])] = g.weight
kd = KDTree(len(src.data.vertices))
for v in src.data.vertices:
    kd.insert(v.co, v.index)
kd.balance()
lods = []
for r in RATIOS:
    ob = src.copy()
    ob.data = src.data.copy()
    bpy.context.scene.collection.objects.link(ob)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    if r < 0.999:
        # the glTF import splits vertices at every UV seam; weld them so the collapse can cross seams
        bmw = bmesh.new(); bmw.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bmw, verts=bmw.verts, dist=1e-5)
        bmw.to_mesh(ob.data); bmw.free()
        d = ob.modifiers.new("dec", "DECIMATE")
        d.decimate_type = "COLLAPSE"
        d.ratio = r
        d.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(me); bm.free()
    uvl = me.uv_layers["UVMap"]
    cn = me.corner_normals
    verts = [list(v.co) for v in me.vertices]
    faces = []
    for p in me.polygons:
        f = []
        for li in p.loop_indices:
            lp = me.loops[li]
            n = cn[li].vector
            u, v = uvl.data[li].uv
            f.append([lp.vertex_index, n.x, n.y, n.z, u, 1.0 - v])
        faces.append(f)
    W = SW[[kd.find(v)[1] for v in verts]]
    if INNER_SHELL:
        # single-surface cloth (jacket of 03/10/2026: 71 open edges): DayZ draws one side only, so through the
        # collar/hem/cuffs you would see the void. Add the reverse side: same faces flipped, 1.5 mm inside,
        # same UVs and weights.
        nv = len(verts)
        vn = [list(v.normal) for v in me.vertices]
        verts = verts + [[c - INNER_OFFSET * n for c, n in zip(verts[i], vn[i])] for i in range(nv)]
        faces = faces + [[[vi + nv, -nx, -ny, -nz, u, v] for (vi, nx, ny, nz, u, v) in reversed(f)] for f in faces]
        W = np.vstack([W, W])
    lods.append({"ratio": r, "verts": verts, "faces": faces, "weights": W.round(4).tolist()})
    print("LOD ratio %.2f: verts=%d tris=%d" % (r, len(verts), len(faces)))
json.dump({"bones": ALLOWED, "lods": lods}, open(OUT, "w"))
print("WROTE", OUT)

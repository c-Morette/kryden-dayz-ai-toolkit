"""Blender helpers shared by the vest pipeline scripts (run inside Blender's python)."""
import math
import os
import sys

import bpy
import mathutils

SCR = os.path.dirname(os.path.abspath(__file__))
if SCR not in sys.path:
    sys.path.insert(0, SCR)
from mlod_dump import read, decode  # noqa: E402

# vanilla bodies (MLOD from BI's DayZ-Misc repo, "Body parts/"); build_vest.py passes them from forge.json
BODY_M = os.environ.get("FORGE_BODY_MALE", "")
BODY_F = os.environ.get("FORGE_BODY_FEMALE", "")


def p3d_to_bl(p):
    return (p[0], p[2], p[1])


def load_p3d_mesh(path, lod=0, name="body", bones=None, use_normals=False):
    """Create a mesh object from an MLOD LOD (p3d -> Blender axes). Selections with per-vertex data become
    vertex groups (weights decoded). Returns the object."""
    L = read(path)[lod]
    verts = [p3d_to_bl(p) for p in L["pts"]]
    faces = []
    uvs = []
    for vs, fl, tex, mat in L["faces"]:
        # MLOD winding gives an INWARD normal in p3d space; p3d -> Blender (y<->z) is a reflection,
        # so the same order is OUTWARD in Blender. Keep the order.
        idx = [v[0] for v in vs]
        faces.append(idx)
        uvs.append([(v[2], 1.0 - v[3]) for v in vs])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    k = 0
    for poly in me.polygons:
        for j, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uvs[poly.index][j]
    if use_normals and L["nrm"]:
        # stored MLOD normals point inward in p3d space -> Blender outward = -(nx, nz, ny)
        cn = []
        for vs, fl, tex, mat in L["faces"]:
            for v in vs:
                n = L["nrm"][v[1]]
                cn.append((-n[0], -n[2], -n[1]))
        me.normals_split_custom_set(cn)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    npts = len(L["pts"])
    nf = len(L["faces"])
    for a, sname, data in L["taggs"]:
        if sname.startswith("#") or len(data) != npts + nf:
            continue
        if bones is not None and sname.lower() not in bones:
            continue
        vg = ob.vertex_groups.new(name=sname)
        groups = {}
        for i in range(npts):
            b = data[i]
            if b:
                groups.setdefault(round(decode(b), 4), []).append(i)
        for w, ids in groups.items():
            vg.add(ids, w, "REPLACE")
    return ob


def look_at(cam, target):
    d = mathutils.Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_render(res=(900, 1200), engine="BLENDER_WORKBENCH"):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    if engine == "BLENDER_WORKBENCH":
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "TEXTURE"
        sh.show_cavity = True
        sh.cavity_type = "BOTH"
    sc.world = sc.world or bpy.data.worlds.new("w")
    sc.world.color = (0.18, 0.18, 0.2)


def render_views(outdir, prefix, target, dist, views, ortho_scale=None):
    """views: list of (name, azimuth_deg, elevation_deg). Front of the character is -Y."""
    sc = bpy.context.scene
    cam = bpy.data.objects.get("_cam")
    if cam is None:
        cd = bpy.data.cameras.new("_cam")
        cam = bpy.data.objects.new("_cam", cd)
        sc.collection.objects.link(cam)
    sc.camera = cam
    if ortho_scale:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho_scale
    else:
        cam.data.type = "PERSP"
        cam.data.lens = 50
    out = []
    for vname, az, el in views:
        a = math.radians(az)
        e = math.radians(el)
        # azimuth 0 = looking at the front (camera on -Y)
        cam.location = (target[0] + dist * math.sin(a) * math.cos(e),
                        target[1] - dist * math.cos(a) * math.cos(e),
                        target[2] + dist * math.sin(e))
        look_at(cam, target)
        fp = os.path.join(outdir, "%s_%s.png" % (prefix, vname))
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        out.append(fp)
    return out


def flat_material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m

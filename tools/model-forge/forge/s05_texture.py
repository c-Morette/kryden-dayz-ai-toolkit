"""Bake the vest textures on the original UVs (the download has no image textures).
blender -b skin_male.blend --python s05_texture.py -- <outdir> [res]
Outputs (PNG): camo.png (emission bake of an object-space woodland pattern), ao.png, normal.png (fabric bump),
and composed: bake_co.png, bake_nohq.png, bake_smdi.png (build_vest renames them to <name>_*).
Object space = the fitted male vest, so the pattern scale is in real metres."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
RES = int(args[1]) if len(args) > 1 else 2048
os.makedirs(OUT, exist_ok=True)
vest = bpy.data.objects["vest"]
for o in bpy.data.objects:
    if o is not vest:
        o.hide_render = True
me = vest.data
uv = me.uv_layers["UVMap"]
me.uv_layers.active = uv
uv.active_render = True

# ---- UV sanity: bounds + overlap estimate --------------------------------------------------
loops_uv = np.zeros(len(me.loops) * 2)
uv.data.foreach_get("uv", loops_uv)
loops_uv = loops_uv.reshape(-1, 2)
print("UV bounds", loops_uv.min(0).round(3), loops_uv.max(0).round(3))
N = 512
cov = np.zeros((N, N), np.int32)
for poly in me.polygons:
    pts = loops_uv[list(poly.loop_indices)] * N
    mn = np.floor(pts.min(0)).astype(int); mx = np.ceil(pts.max(0)).astype(int)
    a, b, c = pts[0], pts[1], pts[2]
    xs = np.arange(max(mn[0], 0), min(mx[0], N)); ys = np.arange(max(mn[1], 0), min(mx[1], N))
    if len(xs) == 0 or len(ys) == 0:
        continue
    X, Y = np.meshgrid(xs + 0.5, ys + 0.5)
    def edge(p, q):
        return (q[0] - p[0]) * (Y - p[1]) - (q[1] - p[1]) * (X - p[0])
    e0, e1, e2 = edge(a, b), edge(b, c), edge(c, a)
    inside = ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
    cov[Y[inside].astype(int), X[inside].astype(int)] += 1
used = (cov > 0).sum(); over = (cov > 1).sum()
print("UV coverage %.1f%%, overlapping texels %.1f%% of used" % (100 * used / N / N, 100 * over / max(used, 1)))

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.render.bake.margin = 12
sc.render.bake.margin_type = "EXTEND"


def new_img(name, colorspace):
    im = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    im.colorspace_settings.name = colorspace
    return im


def lin(srgb):
    return tuple(((c / 255.0) ** 2.2) for c in srgb) + (1.0,)


mat = bpy.data.materials.new("bake")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new("ShaderNodeOutputMaterial")
tc = nt.nodes.new("ShaderNodeTexCoord")


def noise(scale, w, detail=3.0, rough=0.55, dist=0.5):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "4D"
    n.inputs["Scale"].default_value = scale
    n.inputs["W"].default_value = w
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    return n


def mask(src, thr):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.interpolation = "CONSTANT"
    r.color_ramp.elements[0].position = 0.0
    r.color_ramp.elements[0].color = (0, 0, 0, 1)
    r.color_ramp.elements[1].position = thr
    r.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(src.outputs["Fac"], r.inputs["Fac"])
    return r


def mix(a, b_col, m):
    x = nt.nodes.new("ShaderNodeMix")
    x.data_type = "RGBA"
    if isinstance(a, tuple):
        x.inputs[6].default_value = a
    else:
        nt.links.new(a, x.inputs[6])
    x.inputs[7].default_value = b_col
    nt.links.new(m.outputs["Color"], x.inputs["Factor"])
    return x.outputs[2]


# woodland-style 4 colour camo, blob size ~10-15 cm (object space is metres)
GREEN, KHAKI, BROWN, BLACK = lin((82, 88, 58)), lin((140, 126, 92)), lin((96, 72, 50)), lin((36, 36, 30))
c = mix(GREEN, BROWN, mask(noise(5.5, 0.0), 0.55))
c = mix(c, KHAKI, mask(noise(6.5, 3.7), 0.60))
c = mix(c, BLACK, mask(noise(8.0, 7.1, dist=0.8), 0.64))
# fine fabric mottling
grain = noise(220.0, 1.3, detail=2.0)
gm = nt.nodes.new("ShaderNodeMix"); gm.data_type = "RGBA"; gm.blend_type = "MULTIPLY"
gm.inputs["Factor"].default_value = 0.10
nt.links.new(c, gm.inputs[6]); nt.links.new(grain.outputs["Color"], gm.inputs[7])
emis = nt.nodes.new("ShaderNodeEmission")
nt.links.new(gm.outputs[2], emis.inputs["Color"])
# fabric bump for the normal bake
wave = nt.nodes.new("ShaderNodeTexWave"); wave.inputs["Scale"].default_value = 260.0
wave.wave_type = "BANDS"; wave.bands_direction = "DIAGONAL"
nt.links.new(tc.outputs["UV"], wave.inputs["Vector"])
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.0005
nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
img_node = nt.nodes.new("ShaderNodeTexImage")
nt.nodes.active = img_node
me.materials.clear()
me.materials.append(mat)
vest.select_set(True)
bpy.context.view_layer.objects.active = vest


def bake(kind, img, samples):
    img_node.image = img
    nt.nodes.active = img_node
    sc.cycles.samples = samples
    if kind == "EMIT":
        nt.links.new(emis.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    if kind == "NORMAL":
        sc.render.bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type=kind)
    img.filepath_raw = os.path.join(OUT, img.name + ".png")
    img.file_format = "PNG"
    img.save()
    print("baked", kind, img.filepath_raw)


camo = new_img("camo", "sRGB"); bake("EMIT", camo, 4)
ao = new_img("ao", "Non-Color"); bake("AO", ao, 64)
nrm = new_img("normal", "Non-Color"); bake("NORMAL", nrm, 4)


def px(img):
    a = np.zeros(RES * RES * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(RES, RES, 4)


def save(name, arr, colorspace):
    im = bpy.data.images.new(name, RES, RES, alpha=True, float_buffer=False)
    im.colorspace_settings.name = colorspace
    im.pixels.foreach_set(np.clip(arr, 0, 1).astype(np.float32).ravel())
    im.filepath_raw = os.path.join(OUT, name + ".png")
    im.file_format = "PNG"
    im.save()
    print("wrote", im.filepath_raw)


C = px(camo); A = px(ao); Nm = px(nrm)
a = A[..., :1] ** 0.8
co = C.copy()
co[..., :3] = C[..., :3] * (0.42 + 0.58 * a)       # pixels() of an sRGB byte image are linear here
co[..., 3] = 1
save("bake_co", co, "sRGB")
nohq = Nm.copy()
nohq[..., 1] = 1.0 - nohq[..., 1]                   # OpenGL (Blender) -> DirectX green
nohq[..., 3] = 1
save("bake_nohq", nohq, "Non-Color")
smdi = np.ones_like(C)
smdi[..., 1] = 0.10 + 0.12 * a[..., 0]              # specular
smdi[..., 2] = 0.22                                 # glossiness
save("bake_smdi", smdi, "Non-Color")
print("DONE")

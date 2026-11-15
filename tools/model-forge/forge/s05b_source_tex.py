"""Use the model's OWN textures instead of the procedural bake (s05).

blender -b --python s05b_source_tex.py -- <zip or folder with the textures> <outdir> <name>
Writes <name>_co.png, <name>_nohq.png, <name>_smdi.png (power of two) ready for ImageToPAA.

Accepts DayZ/Arma maps (*_co, *_nohq, *_smdi, used as they are) or glTF PBR maps as a fallback
(baseColor/albedo, normal = OpenGL -> green flipped to DirectX, metallicRoughness/ORM -> smdi).
The normal map is repaired: texels whose vector length is far from 1 (e.g. grey noise left by a broken
download) become flat (128,128,255). Runs in Blender only for numpy + image IO (no Pillow needed).
"""
import os
import re
import sys
import tempfile
import zipfile

import bpy
import numpy as np

SRC, OUT, NAME = sys.argv[sys.argv.index("--") + 1:][:3]
SRC0 = SRC
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUT, exist_ok=True)
IMG = r"\.(png|jpe?g|tga|tif)$"

TEX_MAX = int(os.environ.get("KV_TEX_MAX", 2048))   # vanilla clothing uses 2048; a 4k source is reduced


def glb_textures(data, outdir):
    """images embedded in a .glb, named by the role the material gives them (basecolor/normal/
    metallicroughness) so the patterns below pick them. Sketchfab's official glb carries them inside."""
    import json, struct
    L = struct.unpack_from("<I", data, 12)[0]
    j = json.loads(data[20:20 + L])
    off = 20 + L
    bin_len = struct.unpack_from("<I", data, off)[0]
    binc = data[off + 8: off + 8 + bin_len]
    role = {}
    for m in j.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        for key, r in (("baseColorTexture", "basecolor"), ("metallicRoughnessTexture", "metallicroughness")):
            if key in pbr:
                role.setdefault(j["textures"][pbr[key]["index"]]["source"], r)
        if "normalTexture" in m:
            role.setdefault(j["textures"][m["normalTexture"]["index"]]["source"], "normal")
        if "occlusionTexture" in m:
            role.setdefault(j["textures"][m["occlusionTexture"]["index"]]["source"], "occlusion")
    pbr0 = (j.get("materials") or [{}])[0].get("pbrMetallicRoughness", {})
    json.dump({"metallicFactor": pbr0.get("metallicFactor", 1.0), "roughnessFactor": pbr0.get("roughnessFactor", 1.0)},
              open(os.path.join(outdir, "glb_factors.json"), "w"))
    for i, im in enumerate(j.get("images", [])):
        if "bufferView" not in im:
            continue
        bv = j["bufferViews"][im["bufferView"]]
        raw = binc[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        ext = ".jpg" if "jpeg" in im.get("mimeType", "") else ".png"
        open(os.path.join(outdir, "glb_%d_%s%s" % (i, role.get(i, "image"), ext)), "wb").write(raw)


tmp = None
if SRC.lower().endswith(".zip"):
    tmp = tempfile.mkdtemp(prefix="kvtex_")
    with zipfile.ZipFile(SRC) as z:
        for n in z.namelist():
            if re.search(IMG, n, re.I):
                p = os.path.join(tmp, os.path.basename(n))
                open(p, "wb").write(z.read(n))
        if not any(re.search(IMG, n, re.I) for n in z.namelist()):
            glbs = [n for n in z.namelist() if n.lower().endswith(".glb")]
            if glbs:
                glb_textures(z.read(glbs[0]), tmp)
    SRC = tmp
elif SRC.lower().endswith(".glb"):
    tmp = tempfile.mkdtemp(prefix="kvtex_")
    glb_textures(open(SRC, "rb").read(), tmp)
    SRC = tmp
files = {n: os.path.join(SRC, n) for n in os.listdir(SRC) if re.search(IMG, n, re.I)}
print("found:", sorted(files))


def pick(*patterns):
    for p in patterns:
        for n in sorted(files):
            if re.search(p, n, re.I):
                return n
    return None


def load(name):
    """raw (non colour managed) float RGBA, rows bottom-up as Blender stores them; resized to power of 2"""
    im = bpy.data.images.load(files[name])
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    tw = min(TEX_MAX, 1 << int(round(np.log2(w)))); th = min(TEX_MAX, 1 << int(round(np.log2(h))))
    if (tw, th) != (w, h):
        im.scale(tw, th)
    a = np.empty(tw * th * 4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(th, tw, 4)


def save(arr, fname):
    h, w = arr.shape[:2]
    im = bpy.data.images.new(fname, w, h, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.join(OUT, fname)
    im.file_format = "PNG"
    im.save()


def repair_normal(n, dz_normal):
    if not dz_normal:
        n[..., 1] = 1.0 - n[..., 1]          # glTF/OpenGL -> DirectX green
    v = n * 2 - 1
    ln = np.linalg.norm(v, axis=-1)
    bad = (ln < 0.6) | (ln > 1.4) | (v[..., 2] < -0.05)
    print("normal map: %.2f%% texels invalid length -> flat" % (100 * bad.mean()))
    # random-noise blocks (broken bake/download) have unit-ish length but no spatial coherence:
    # mean dot product with the right/lower neighbour over a 9x9 window drops far below 1
    u = v / np.maximum(ln, 1e-6)[..., None]
    coh = np.ones(ln.shape, np.float32)
    coh[:, :-1] = np.minimum(coh[:, :-1], (u[:, :-1] * u[:, 1:]).sum(-1))
    coh[:-1, :] = np.minimum(coh[:-1, :], (u[:-1, :] * u[1:, :]).sum(-1))
    k = 9
    ii = np.pad(coh, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    pad = np.pad(ii, ((k // 2, k // 2), (k // 2, k // 2)), mode="edge")
    box = (pad[k:, k:] - pad[:-k, k:] - pad[k:, :-k] + pad[:-k, :-k])[:coh.shape[0], :coh.shape[1]] / (k * k)
    noise = box < 0.5
    print("normal map: %.2f%% texels are incoherent noise -> flat" % (100 * noise.mean()))
    bad |= noise
    n[bad] = (0.5, 0.5, 1.0)
    return n


def load_cell(fname, c):
    """raw float RGBA of one image scaled to c x c (rows bottom-up, as Blender stores them)"""
    im = bpy.data.images.load(os.path.join(SRC, fname))
    im.colorspace_settings.name = "Non-Color"
    if tuple(im.size) != (c, c):
        im.scale(c, c)
    a = np.empty(c * c * 4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(c, c, 4)


def glb_atlas(j, mats):
    """several materials -> ONE texture set: a square cell per material, side by side (glb_info rule; s02d lays the
    UVs out the same way). Handles metallic-roughness and specular-glossiness (KHR_materials_pbrSpecularGlossiness,
    backpack of 04/10/2026) materials."""
    ncell = glb_info.atlas_cells(len(mats))
    c = 1 << int(np.log2(TEX_MAX // ncell))
    co = np.ones((c, c * ncell, 4), np.float32)
    no = np.zeros((c, c * ncell, 3), np.float32); no[...] = (0.5, 0.5, 1.0)
    sm = np.zeros((c, c * ncell, 3), np.float32); sm[...] = (1.0, 0.16, 0.24)

    def img(texinfo):
        if not texinfo:
            return None
        src = j["textures"][texinfo["index"]]["source"]
        hit = [n for n in files if n.startswith("glb_%d_" % src)]
        return hit[0] if hit else None

    for k, mi in enumerate(mats):
        m = j["materials"][mi]
        sg = m.get("extensions", {}).get("KHR_materials_pbrSpecularGlossiness")
        pbr = m.get("pbrMetallicRoughness", {})
        cols = slice(k * c, (k + 1) * c)
        f_col = np.array((sg.get("diffuseFactor") if sg else pbr.get("baseColorFactor")) or [1, 1, 1, 1], np.float32)
        n_col = img(sg.get("diffuseTexture") if sg else pbr.get("baseColorTexture"))
        cell = load_cell(n_col, c) if n_col else np.ones((c, c, 4), np.float32)
        cell[..., :3] *= f_col[:3]
        n_ao = img(m.get("occlusionTexture"))
        if n_ao:
            cell[..., :3] *= 0.55 + 0.45 * load_cell(n_ao, c)[..., 0:1]     # no AO slot in the rvmat
        co[:, cols] = cell
        n_n = img(m.get("normalTexture"))
        if n_n:
            no[:, cols] = repair_normal(load_cell(n_n, c)[..., :3].copy(), False)
        if sg:
            n_s = img(sg.get("specularGlossinessTexture"))
            t = load_cell(n_s, c) if n_s else np.ones((c, c, 4), np.float32)
            spec = (t[..., :3] * np.array(sg.get("specularFactor", [1, 1, 1]), np.float32)).mean(-1)
            gloss = t[..., 3] * sg.get("glossinessFactor", 1.0)
            sm[:, cols, 1] = np.clip(0.08 + 0.6 * spec, 0, 1)      # same floor as the metal-rough path
            sm[:, cols, 2] = np.clip(gloss, 0, 1)
        else:
            n_s = img(pbr.get("metallicRoughnessTexture"))
            t = load_cell(n_s, c) if n_s else np.ones((c, c, 4), np.float32)
            rough = np.clip(t[..., 1] * pbr.get("roughnessFactor", 1.0), 0, 1)
            metal = t[..., 2] * pbr.get("metallicFactor", 1.0)
            sm[:, cols, 1] = 0.08 + 0.5 * metal + 0.25 * (1 - rough)
            sm[:, cols, 2] = 1 - rough
        print("atlas cell %d <- material %d %r (%s): colour %s normal %s" % (
            k, mi, m.get("name"), "spec-gloss" if sg else "metal-rough", n_col, n_n))
    save(co, NAME + "_co.png"); save(no, NAME + "_nohq.png"); save(sm, NAME + "_smdi.png")
    print("wrote", [NAME + x for x in ("_co.png", "_nohq.png", "_smdi.png")], "atlas %d x %d (%d cells of %d)" % (
        c * ncell, c, ncell, c))


if SRC0.lower().endswith(".glb"):
    import glb_info
    _j = glb_info.read_json(SRC0)
    _mats = glb_info.atlas_materials(_j)
    if len(_mats) > 1:
        glb_atlas(_j, _mats)
        sys.exit(0)

n_co = pick(r"_co\.", r"basecolor", r"albedo", r"diffuse")
n_no = pick(r"_nohq\.", r"normal")
n_sm = pick(r"_smdi\.", r"metallicroughness", r"_orm\.", r"roughness")
dz_normal = bool(n_no and re.search(r"_nohq\.", n_no, re.I))
print("co=%s normal=%s smdi/pbr=%s (DayZ normal: %s)" % (n_co, n_no, n_sm, dz_normal))
if n_co is None:
    raise SystemExit("no colour map found")

co = load(n_co)
n_orm = pick(r"metallicroughness", r"_orm\.", r"occlusion")
if n_orm and not re.search(r"_co\.", n_co, re.I):
    orm = load(n_orm)
    if orm.shape[:2] == co.shape[:2]:
        ao = orm[..., 0:1]                       # glTF ORM: R = occlusion (1 when the map has none)
        co[..., :3] *= 0.55 + 0.45 * ao          # DayZ has no AO slot in this rvmat: bake it into the colour
        print("ambient occlusion from %s baked into the colour" % n_orm)
if co[..., 3].min() < 0.98:
    print("WARNING: colour map has real alpha (min %.2f) - alpha dropped, check the result" % co[..., 3].min())
save(co, NAME + "_co.png")

if n_no:
    n = repair_normal(load(n_no)[..., :3].copy(), dz_normal)
    save(n, NAME + "_nohq.png")
else:
    save(np.broadcast_to(np.array([0.5, 0.5, 1.0], np.float32), co.shape[:2] + (3,)).copy(), NAME + "_nohq.png")

if n_sm and re.search(r"_smdi\.", n_sm, re.I):
    s = load(n_sm)[..., :3].copy()
    s[..., 0] = 1.0                          # red is unused in SMDI; vanilla keeps it white
    save(s, NAME + "_smdi.png")
elif n_sm:                                   # glTF metallicRoughness: G = roughness, B = metallic
    m = load(n_sm)
    rough, metal = m[..., 1], m[..., 2]
    fac = os.path.join(SRC, "glb_factors.json")
    if os.path.exists(fac):                      # glTF multiplies the maps by the material factors
        import json
        f = json.load(open(fac))                 # jacket of 03/10/2026: metallicFactor 0 with a white B channel
        metal = metal * f.get("metallicFactor", 1.0)
        rough = np.clip(rough * f.get("roughnessFactor", 1.0), 0, 1)
        print("pbr factors", f)
    s = np.zeros(m.shape[:2] + (3,), np.float32)
    s[..., 0] = 1.0
    s[..., 1] = 0.08 + 0.5 * metal + 0.25 * (1 - rough)
    s[..., 2] = 1 - rough
    save(s, NAME + "_smdi.png")
else:
    save(np.broadcast_to(np.array([1.0, 0.16, 0.24], np.float32), co.shape[:2] + (3,)).copy(), NAME + "_smdi.png")
print("wrote", [NAME + x for x in ("_co.png", "_nohq.png", "_smdi.png")], "size", co.shape[1], co.shape[0])

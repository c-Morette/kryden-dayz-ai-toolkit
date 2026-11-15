"""Write the vest MLODs (worn _m/_f and ground _g) from the s07 JSON.

python mlod_write.py <lods_male.json> <lods_female.json> <outdir> <tex_prefix> [name=my_vest]
  tex_prefix = PBO path of the data folder, e.g. MyTag\\MyMod\\MyMod_Client\\data\\vests (build_vest derives
               it from the $PBOPREFIX$ of the PBO that contains the data folder)

Conventions (measured on the vanilla character_male.p3d MLOD and on working community vest MLODs):
- p3d (x, y up, z) = Blender (x, z, y)  -> a reflection, so the Blender face order gives the MLOD order directly
  (cross(p1-p0, p2-p0) and the stored normals point INWARD in p3d space, like BI's own body).
- stored normal = -(nx, nz, ny) of the Blender outward normal.
- weight byte: 0 = not in selection, 1 = 1.0, else round(255 - 254 w); face byte 1 when all its points are selected.
- worn LODs: 1, 2, 3, 1100 (copy of 1) + empty Geometry 1e13 with autocenter=0 (the layout of working JPC/IOTV vest MLODs);
  bone selections lowercase + 'camo'; lodnoshadow=1.
- ground: visual LODs laid on the back (front up), Geometry/View/Fire boxes 'component01', Memory points
  boundingbox_min/max, invview, ce_center, ce_radius (JPC_g layout).
"""
import json
import math
import os
import struct
import sys

LJ_M, LJ_F, OUTDIR, TEXP = sys.argv[1:5]
NAME = sys.argv[5] if len(sys.argv) > 5 else "my_vest"
TEX = TEXP + "\\" + NAME + "_co.paa"
MAT = TEXP + "\\" + NAME + ".rvmat"
FIRE_MAT = r"dz\data\data\penetration\armor_5mm_plate.rvmat"


def enc(w):
    if w < 0.002:
        return 0
    if w >= 0.998:
        return 1
    return max(2, min(254, int(round(255 - 254 * w))))


def to_p3d(v):
    return (v[0], v[2], v[1])


class Lod:
    def __init__(self, res):
        self.res = res
        self.pts = []        # p3d coords
        self.nrm = []        # p3d (inward) normals
        self.faces = []      # [(pi, ni, u, v) x n], tex, mat
        self.sel = {}        # name -> (vertex bytes bytearray, None) -> faces computed at write
        self.props = []      # (name, value)
        self.mass = None     # list of floats per point

    def add_selection_weights(self, name, weights):
        b = bytearray(len(self.pts))
        for i, w in enumerate(weights):
            b[i] = enc(w)
        if any(b):
            self.sel[name] = b

    def add_selection_all(self, name, idx=None):
        b = bytearray(len(self.pts))
        for i in (range(len(self.pts)) if idx is None else idx):
            b[i] = 1
        self.sel[name] = b

    def bytes(self):
        out = bytearray(b"P3DM")
        out += struct.pack("<6I", 28, 256, len(self.pts), len(self.nrm), len(self.faces), 0)
        for p in self.pts:
            out += struct.pack("<3fI", p[0], p[1], p[2], 0)
        for n in self.nrm:
            out += struct.pack("<3f", *n)
        for verts, tex, mat in self.faces:
            out += struct.pack("<I", len(verts))
            for k in range(4):
                if k < len(verts):
                    out += struct.pack("<IIff", *verts[k])
                else:
                    out += struct.pack("<IIff", 0, 0, 0.0, 0.0)
            out += struct.pack("<I", 0)
            out += tex.encode("ascii") + b"\0" + mat.encode("ascii") + b"\0"
        out += b"TAGG"

        def tag(name, data):
            return b"\x01" + name.encode("ascii") + b"\0" + struct.pack("<I", len(data)) + bytes(data)

        for name, vb in self.sel.items():
            fb = bytearray(len(self.faces))
            for fi, (verts, _, _) in enumerate(self.faces):
                if all(vb[v[0]] for v in verts):
                    fb[fi] = 1
            out += tag(name, vb + fb)
        for k, v in self.props:
            out += tag("#Property#", k.encode().ljust(64, b"\0") + v.encode().ljust(64, b"\0"))
        if self.mass is not None:
            out += tag("#Mass#", struct.pack("<%df" % len(self.mass), *self.mass))
        uv = bytearray(struct.pack("<I", 0))
        for verts, _, _ in self.faces:
            for v in verts:
                uv += struct.pack("<ff", v[2], v[3])
        out += tag("#UVSet#", uv)
        out += tag("#EndOfFile#", b"")
        out += struct.pack("<f", self.res)
        return bytes(out)


def mlod(lods):
    out = bytearray(b"MLOD") + struct.pack("<II", 257, len(lods))
    for L in lods:
        out += L.bytes()
    return bytes(out)


def visual_lod(res, data, bones, xform=None, skinned=True):
    """data = one LOD of the JSON (Blender space). xform: optional (R 3x3, t) applied in Blender space."""
    L = Lod(res)
    def X(v):
        if xform is None:
            return v
        R, t = xform
        return [sum(R[r][c] * v[c] for c in range(3)) + t[r] for r in range(3)]
    def Xn(n):
        if xform is None:
            return n
        R, _ = xform
        return [sum(R[r][c] * n[c] for c in range(3)) for r in range(3)]
    L.pts = [to_p3d(X(v)) for v in data["verts"]]
    nidx = {}
    for f in data["faces"]:
        verts = []
        for (vi, nx, ny, nz, u, v) in f:
            n = Xn([nx, ny, nz])
            key = (round(-n[0], 4), round(-n[2], 4), round(-n[1], 4))
            ni = nidx.get(key)
            if ni is None:
                ni = nidx[key] = len(L.nrm)
                L.nrm.append(key)
            verts.append((vi, ni, u, v))
        L.faces.append((verts, TEX, MAT))
    if skinned:
        W = data["weights"]
        for k, b in enumerate(bones):
            L.add_selection_weights(b.lower(), [w[k] for w in W])
    L.add_selection_all("camo")
    return L


def box_faces(L, corners_bl, tex="", mat=""):
    """corners in Blender space (8, index = x + 2y + 4z bits); appends 6 quads with the MLOD winding."""
    base = len(L.pts)
    L.pts += [to_p3d(c) for c in corners_bl]
    quads = [(0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6), (0, 1, 3, 2), (4, 6, 7, 5)]
    cen = [sum(c[k] for c in corners_bl) / 8 for k in range(3)]
    for q in quads:
        P = [corners_bl[i] for i in q]
        a = [P[1][k] - P[0][k] for k in range(3)]; b = [P[2][k] - P[0][k] for k in range(3)]
        n = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
        fc = [sum(p[k] for p in P) / 4 for k in range(3)]
        if sum(n[k] * (fc[k] - cen[k]) for k in range(3)) < 0:     # want Blender-outward (CCW) order
            q = q[::-1]
            n = [-x for x in n]
        ln = math.sqrt(sum(x * x for x in n))
        ni = len(L.nrm)
        L.nrm.append((-n[0] / ln, -n[2] / ln, -n[1] / ln))
        L.faces.append(([(base + i, ni, 0.0, 0.0) for i in q], tex, mat))


def corners(mn, mx):
    return [[(mn, mx)[i & 1][0], (mn, mx)[(i >> 1) & 1][1], (mn, mx)[(i >> 2) & 1][2]] for i in range(8)]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    jm, jf = json.load(open(LJ_M)), json.load(open(LJ_F))
    for sex, J in (("m", jm), ("f", jf)):
        bones = J["bones"]
        lods = []
        for res, d in zip((1.0, 2.0, 3.0), J["lods"]):
            L = visual_lod(res, d, bones)
            L.props = [("lodnoshadow", "1")] + ([("autocenter", "0")] if res == 1.0 else [])
            lods.append(L)
        fp = visual_lod(1100.0, J["lods"][0], bones)
        fp.props = [("lodnoshadow", "1")]
        lods.append(fp)
        geo = Lod(1e13)
        geo.props = [("autocenter", "0")]
        geo.mass = []
        lods.append(geo)
        path = os.path.join(OUTDIR, "%s_%s.p3d" % (NAME, sex))
        open(path, "wb").write(mlod(lods))
        print("wrote", path, ["%g:%dpts/%dfaces" % (L.res, len(L.pts), len(L.faces)) for L in lods])

    # ---- ground model: male LODs on its back, front up ---------------------------------------
    c, s = 0.0, -1.0                               # rotation -90 deg about Blender X: front (-Y) -> up (+Z)
    Rx = [[1, 0, 0], [0, c, -s], [0, s, c]]
    # then 180 deg about the vertical: with only Rx the collar pointed to p3d +Z, which the engine flips (MLOD z
    # is mirrored in game) - the inventory icon (invview, camera above) showed the vest upside down
    # (in-game, 03/10/2026). Lying flat on the ground is unchanged.
    Rz = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
    R = [[sum(Rz[i][k] * Rx[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    if os.environ.get("KV_GROUND_BACK_UP") == "1":
        # backpack: the face to show is the OUTER one (behind the wearer, +Y): turn it to the front first, so it
        # lies on its harness with the pockets up and the icon shows the pockets (top still to p3d -Z)
        R = [[R[i][0] * -1, R[i][1] * -1, R[i][2]] for i in range(3)]
    V0 = [[sum(R[r][k] * v[k] for k in range(3)) for r in range(3)] for v in jm["lods"][0]["verts"]]
    mn = [min(v[k] for v in V0) for k in range(3)]; mx = [max(v[k] for v in V0) for k in range(3)]
    t = [-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]]
    lods = []
    for res, d in zip((1.0, 2.0, 3.0), jm["lods"]):
        L = visual_lod(res, d, None, xform=(R, t), skinned=False)
        L.props = [("lodnoshadow", "1")] + ([("autocenter", "0")] if res == 1.0 else [])
        lods.append(L)
    bmn = [mn[k] + t[k] for k in range(3)]; bmx = [mx[k] + t[k] for k in range(3)]
    print("ground bbox (Blender space)", [round(x, 3) for x in bmn], [round(x, 3) for x in bmx])
    # boxes slightly inside the visual (vanilla and working community MLODs do the same); thin slab = the vest lying flat
    gmn = [bmn[0] * 0.9, bmn[1] * 0.9, 0.0]; gmx = [bmx[0] * 0.9, bmx[1] * 0.9, bmx[2] * 0.8]
    geo = Lod(1e13); box_faces(geo, corners(gmn, gmx)); geo.add_selection_all("component01")
    geo.props = [("autocenter", "0")]; geo.mass = [0.5] * 8
    view = Lod(6e15); box_faces(view, corners(gmn, gmx)); view.add_selection_all("component01")
    fire = Lod(7e15); box_faces(fire, corners(gmn, gmx), "", FIRE_MAT); fire.add_selection_all("component01")
    fire.props = [("lodnoshadow", "1")]
    mem = Lod(1e15)
    cen = [(bmn[k] + bmx[k]) / 2 for k in range(3)]
    pts = {
        "boundingbox_min": bmn,
        "boundingbox_max": bmx,
        "invview": [cen[0], cen[1], bmx[2] + 1.2],      # camera above the item (JPC_g: 1.35 above ground)
        "ce_center": [cen[0], cen[1], 0.05],
        "ce_radius": [bmx[0], bmx[1], 0.15],
    }
    for name, p in pts.items():
        mem.add_selection_all  # noqa
        i = len(mem.pts)
        mem.pts.append(to_p3d(p))
        mem.sel[name] = None
        mem.sel[name] = (i,)
    # materialise memory selections as byte arrays
    for name, idx in list(mem.sel.items()):
        b = bytearray(len(mem.pts)); b[idx[0]] = 1; mem.sel[name] = b
    lods += [geo, mem, view, fire]
    path = os.path.join(OUTDIR, "%s_g.p3d" % NAME)
    open(path, "wb").write(mlod(lods))
    print("wrote", path, ["%g:%dpts/%dfaces" % (L.res, len(L.pts), len(L.faces)) for L in lods])


if __name__ == "__main__":
    main()

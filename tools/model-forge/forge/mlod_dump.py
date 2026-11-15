"""Detailed MLOD dump: per LOD resolution, counts, flags, every TAGG (name, size, kind), properties, mass,
selection vertex counts and weight stats, point bbox, face texture usage, face flags histogram.
Usage: python mlod_dump.py file.p3d [--points LODIDX]"""
import struct, sys, collections

def decode(b):
    if b in (0, 1):
        return float(b)
    return (255 - b) / 254.0

def read(path):
    buf = open(path, "rb").read()
    assert buf[:4] == b"MLOD"
    ver, nlods = struct.unpack_from("<II", buf, 4)
    off = 12
    lods = []
    for _ in range(nlods):
        assert buf[off:off+4] == b"P3DM"
        major, minor, npts, nnorm, nfaces, flags = struct.unpack_from("<6I", buf, off+4)
        off += 28
        pts = [struct.unpack_from("<3fI", buf, off+i*16) for i in range(npts)]
        off += npts*16
        nrm = [struct.unpack_from("<3f", buf, off+i*12) for i in range(nnorm)]
        off += nnorm*12
        faces = []
        for _f in range(nfaces):
            (nv,) = struct.unpack_from("<I", buf, off)
            vs = [struct.unpack_from("<IIff", buf, off+4+k*16) for k in range(4)][:nv]
            (fflags,) = struct.unpack_from("<I", buf, off+68)
            off += 72
            e = buf.index(b"\0", off); tex = buf[off:e].decode("ascii", "replace"); off = e+1
            e = buf.index(b"\0", off); mat = buf[off:e].decode("ascii", "replace"); off = e+1
            faces.append((vs, fflags, tex, mat))
        assert buf[off:off+4] == b"TAGG", buf[off:off+4]
        off += 4
        taggs = []
        while True:
            active = buf[off]; off += 1
            e = buf.index(b"\0", off); name = buf[off:e].decode("ascii", "replace"); off = e+1
            (size,) = struct.unpack_from("<I", buf, off); off += 4
            data = buf[off:off+size]; off += size
            taggs.append((active, name, data))
            if name == "#EndOfFile#":
                break
        (res,) = struct.unpack_from("<f", buf, off); off += 4
        lods.append(dict(res=res, flags=flags, pts=pts, nrm=nrm, faces=faces, taggs=taggs, major=major, minor=minor))
    return lods

def main():
    path = sys.argv[1]
    lods = read(path)
    for li, L in enumerate(lods):
        pts = L["pts"]; npts = len(pts); nf = len(L["faces"])
        print("=" * 70)
        print("LOD %d res=%g pts=%d normals=%d faces=%d lodflags=%d" % (li, L["res"], npts, len(L["nrm"]), nf, L["flags"]))
        if pts:
            mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
            print("  bbox min", [round(x, 4) for x in mn], "max", [round(x, 4) for x in mx])
            pf = collections.Counter(p[3] for p in pts)
            print("  point flags", dict(pf.most_common(5)))
        ff = collections.Counter(f[1] for f in L["faces"])
        print("  face flags", dict(ff.most_common(5)))
        tx = collections.Counter((f[2], f[3]) for f in L["faces"])
        for (t, m), n in tx.most_common(8):
            print("   tex %6d  %r  %r" % (n, t, m))
        nv = collections.Counter(len(f[0]) for f in L["faces"])
        print("  verts/face", dict(nv))
        for active, name, data in L["taggs"]:
            if name == "#Property#":
                k = data[:64].split(b"\0")[0].decode(); v = data[64:128].split(b"\0")[0].decode()
                print("  PROPERTY %s = %s" % (k, v))
            elif name == "#Mass#":
                ms = struct.unpack_from("<%df" % (len(data)//4), data)
                print("  MASS total=%g n=%d" % (sum(ms), len(ms)))
            elif name.startswith("#"):
                print("  TAG %s size=%d" % (name, len(data)))
            elif len(data) == npts + nf:
                vb = data[:npts]; fb = data[npts:]
                sel = [i for i in range(npts) if vb[i]]
                ws = [decode(vb[i]) for i in sel]
                full = sum(1 for i in sel if vb[i] == 1)
                extra = ""
                if len(sel) <= 4 and sel:
                    extra = " pts=" + str([tuple(round(c, 4) for c in pts[i][:3]) for i in sel])
                print("  SEL %-40s verts=%5d full=%5d wmin=%.3f wmax=%.3f faces=%5d%s" % (
                    name, len(sel), full, min(ws) if ws else 0, max(ws) if ws else 0, sum(1 for b in fb if b), extra))
            else:
                print("  TAG? %s size=%d" % (name, len(data)))

if __name__ == "__main__":
    main()

"""Compare face winding / normal conventions of LOD 0 between MLODs.
(a) cross(p1-p0,p2-p0) agrees with the stored normals   (b) cross points away from the vertical axis (area weighted)"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mlod_dump import read

for path in sys.argv[1:]:
    L = read(path)[0]
    P = L["pts"]; N = L["nrm"]
    xs = [p[0] for p in P]; zs = [p[2] for p in P]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    agree = tot = 0; out_a = all_a = 0.0
    for vs, fl, t, m in L["faces"]:
        p = [P[v[0]] for v in vs[:3]]
        a = [p[1][k] - p[0][k] for k in range(3)]; b = [p[2][k] - p[0][k] for k in range(3)]
        n = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        area = math.sqrt(sum(x*x for x in n)) / 2
        sn = [sum(N[v[1]][k] for v in vs) for k in range(3)]
        tot += 1
        agree += sum(n[k]*sn[k] for k in range(3)) > 0
        c = [sum(q[k] for q in p) / 3 for k in range(3)]
        r = [c[0] - cx, 0, c[2] - cz]
        all_a += area
        if sum(n[k]*r[k] for k in range(3)) > 0:
            out_a += area
    print("%-60s cross~stored %.3f | cross outward (area) %.3f" % (path.split("\\")[-1].split("/")[-1], agree / tot, out_a / all_a))

"""Where does each bone weigh in the reference vests? Per bone: verts, height (p3d y) percentiles, |x| range, mean w,
and a height-band table (share of weight per bone per 5 cm band)."""
import os, sys, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mlod_dump import read, decode

cfg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "model_skeleton.cfg")).read()
bones = set(b.lower() for b in re.findall(r'"([A-Za-z0-9_]+)"\s*,\s*"', cfg))
for path in sys.argv[1:]:
    L = read(path)[0]
    P = np.array([p[:3] for p in L["pts"]]); n = len(P); nf = len(L["faces"])
    W = {}
    for a, name, data in L["taggs"]:
        if name.lower() in bones and len(data) == n + nf:
            W[name.lower()] = np.array([decode(b) for b in data[:n]])
    print("==", path.split("\\")[-1], "bones:", sorted(W))
    for b, w in sorted(W.items()):
        m = w > 0
        y = P[m, 1]
        print("  %-14s n=%5d y[p5,p50,p95]=%s |x|max=%.2f wmean=%.2f" % (b, m.sum(), np.percentile(y, [5, 50, 95]).round(2), np.abs(P[m, 0]).max(), w[m].mean()))
    y0, y1 = P[:, 1].min(), P[:, 1].max()
    names = sorted(W)
    print("  band   " + " ".join("%6s" % b[:6] for b in names))
    for lo in np.arange(np.floor(y0 * 20) / 20, y1, 0.05):
        m = (P[:, 1] >= lo) & (P[:, 1] < lo + 0.05)
        if m.sum() == 0:
            continue
        tot = sum(W[b][m].sum() for b in names)
        print("  %.2f   " % lo + " ".join("%6.2f" % (W[b][m].sum() / tot) for b in names))

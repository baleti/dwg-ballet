"""bit-exact parity of dwgscene_fast.clip_polyline vs clip.py (random convex polygons, polylines with axis-aligned/degenerate/touching segments)"""
import sys, os, random, struct, math
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."); sys.path.insert(0, ROOT)
os.environ["DWG_NO_FAST"] = "1"
from dwgballet import clip
import dwgscene_fast as R
rnd = random.Random(11); bad = 0; n = 0
def bits(L): return [[struct.pack("<d", v) for v in p] for p in L]
for _ in range(20000):
    k = rnd.choice([3, 4, 4, 4, 5, 8]); c = (rnd.uniform(-50, 50), rnd.uniform(-50, 50)); r = rnd.uniform(1, 60); rot = rnd.uniform(0, 6.28)
    if rnd.random() < 0.5: poly = clip.ccw([(c[0] - r, c[1] - r), (c[0] + r, c[1] - r), (c[0] + r, c[1] + r), (c[0] - r, c[1] + r)])
    else: poly = clip.ccw([(c[0] + r * math.cos(rot + 6.2831853 * i / k), c[1] + r * math.sin(rot + 6.2831853 * i / k)) for i in range(k)])
    pts = []; x, y = rnd.uniform(-80, 80), rnd.uniform(-80, 80)
    for _ in range(rnd.randint(2, 12)):
        pts += [x, y]; m = rnd.random()
        if m < 0.25: x += rnd.choice([-10, 10, 0]); 
        elif m < 0.4: y += rnd.choice([-10, 10, 0])
        else: x += rnd.uniform(-40, 40); y += rnd.uniform(-40, 40)
        if rnd.random() < 0.1: pts += [x, y]
    pts += [x, y]
    a = clip.clip_polyline(poly, pts); b = R.clip_polyline(poly, pts); n += 1
    if bits(a) != bits(b): bad += 1
print("clip_polyline parity:", n, "cases,", bad, "differences")
sys.exit(1 if bad else 0)

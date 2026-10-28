"""parity of dwgscene_fast.sane vs flat._sane_py on random rows (finite, huge, nan, inf, ints, hatch loops, text/point rows)"""
import sys, os, random, math
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."); sys.path.insert(0, ROOT)
os.environ["DWG_NO_FAST"] = "1"
from dwgballet import flat
import dwgscene_fast as R
rnd = random.Random(5); bad = 0
def v():
    r = rnd.random()
    if r < 0.01: return float("nan")
    if r < 0.02: return rnd.choice([float("inf"), -float("inf")])
    if r < 0.04: return rnd.choice([1e12, -1e12, 9.99e11, 5e11, 7e11])
    if r < 0.06: return rnd.randint(-5, 5)
    return rnd.uniform(-1e4, 1e4)
for _ in range(30000):
    rows = []
    for _ in range(rnd.randint(0, 5)):
        k = rnd.choice("lhtpxl")
        if k == "l": rows.append(("l", "L", 7, 0, 0, [v() for _ in range(rnd.randint(0, 20))], 1, 1.0, 0))
        elif k == "h": rows.append(("h", "L", 7, [[v() for _ in range(rnd.randint(0, 8))] for _ in range(rnd.randint(0, 3))], {}, 1, 1))
        elif k in "tp": rows.append((k, "L", 7, v(), v(), 1, 1, "x"))
        else: rows.append(("x", 1))
    if flat._sane(rows) != R.sane(rows): bad += 1
print("sane parity: 30000 cases,", bad, "differences"); sys.exit(1 if bad else 0)

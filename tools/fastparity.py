"""Scene-level parity of the native fast path: for each DWG given, build every layout twice in fresh processes (DWG_NO_FAST=1 vs default) and compare
the scene JSON (build_s ignored). Exit 1 on any difference. Usage: python tools/fastparity.py FILE.dwg [...]   (drawings are never copied or uploaded)"""
import sys, os, subprocess, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD = r'''
import sys, json, hashlib
sys.path.insert(0, sys.argv[1])
from dwgballet import build
d = build.Doc(sys.argv[2]); m = d.meta(); h = hashlib.md5(); t = __import__("time").time()
for l in m["layouts"]:
    for tw in ((True, False) if not l["ps"] else (True,)):
        r = d.layout(l["i"], tw); r.pop("build_s", None); h.update(json.dumps(r, sort_keys=True, default=repr).encode())
print(h.hexdigest(), round(__import__("time").time() - t, 2))
'''


def run(f, fast):
    env = dict(os.environ)
    if fast: env.pop('DWG_NO_FAST', None)
    else: env['DWG_NO_FAST'] = '1'
    out = subprocess.run([sys.executable, '-c', CHILD, HERE, f], env=env, capture_output=True, text=True, timeout=1800)
    if out.returncode: raise RuntimeError(out.stderr[-400:])
    h, s = out.stdout.split()
    return h, float(s)


bad = 0
for f in sys.argv[1:]:
    (a, ta), (b, tb) = run(f, False), run(f, True)
    ok = a == b; bad += not ok
    print(os.path.basename(f), 'python %.2f s native %.2f s (%.2fx)' % (ta, tb, ta / max(tb, 1e-9)), 'IDENTICAL' if ok else 'DIFF', flush=True)
sys.exit(1 if bad else 0)

"""Recent files list, ~/.cache/dwg-ballet/recent.json (newest first, at most 20)."""
import json, os
from . import plat

FILE = os.environ.get('DWG_BALLET_RECENT') or os.path.join(plat.dirs.cache_dir('dwg-ballet'), 'recent.json')
MAX = 20


def _read():
    try:
        v = json.load(open(FILE))
        return [x for x in v if isinstance(x, str)]
    except Exception:
        return []


def add(path):
    try:
        lst = [path] + [x for x in _read() if x != path]
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        tmp = FILE + '.tmp'
        json.dump(lst[:MAX], open(tmp, 'w')); plat.fsio.replace_retry(tmp, FILE)
    except OSError:
        pass


def listing():
    out = []
    for p in _read():
        try: st = os.stat(p); out.append({'path': p, 'name': os.path.basename(p), 'dir': os.path.dirname(p), 'size': st.st_size, 'exists': True})
        except OSError: out.append({'path': p, 'name': os.path.basename(p), 'dir': os.path.dirname(p), 'exists': False})
    return out

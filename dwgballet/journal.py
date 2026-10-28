"""Edit journal: every state-changing command line is appended (one JSON line, flushed) to ~/.cache/dwg-ballet/journal/<sha1 of the file path>.jsonl so a crash or a
closed window loses nothing; RECOVER replays it. The journal is cleared after a successful SAVEAS / SAVE!."""
import hashlib, json, os, time
from . import plat

DIR = os.environ.get('DWG_BALLET_JOURNAL') or os.path.join(plat.dirs.cache_dir('dwg-ballet'), 'journal')


def _file(path): return os.path.join(DIR, hashlib.sha1(os.path.realpath(path).encode()).hexdigest() + '.jsonl')


def append(path, cmd):
    os.makedirs(DIR, exist_ok=True)
    with open(_file(path), 'a', encoding='utf-8') as f:
        f.write(json.dumps({'t': int(time.time()), 'cmd': cmd}) + '\n'); f.flush(); os.fsync(f.fileno())


def read(path):
    try: lines = open(_file(path), encoding='utf-8').read().splitlines()
    except OSError: return []
    out = []
    for ln in lines:
        try: out.append(json.loads(ln)['cmd'])
        except (ValueError, KeyError): pass          # a torn last line after a crash is ignored
    return out


def pop(path):
    """drop the last journal line (UNDO)"""
    p = _file(path)
    try: lines = open(p, encoding='utf-8').read().splitlines()
    except OSError: return
    if lines: open(p, 'w', encoding='utf-8').write('\n'.join(lines[:-1]) + ('\n' if len(lines) > 1 else ''))


def clear(path):
    try: os.remove(_file(path))
    except OSError: pass

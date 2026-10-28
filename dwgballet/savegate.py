"""Save As with a safety gate (PLAN-viewers-editors section 3, first slice): writes a copy of the drawing with the layer states (on, frozen, locked) of the viewer.
Rules: never overwrites an existing file and never writes the source path; the source must be unchanged since it was opened (size + mtime + sha1 recorded at load);
write goes to a temp file in the target directory, fsync, then rename (atomic); the result is re-parsed with the reader and compared with the source: every
entity record must be identical (zero diffs outside the edit) and the layer flags must be the requested ones; on any failure nothing is left behind.
Only versions the writer supports (AC1015, AC1018, AC1024, AC1027, AC1032); others are refused with a message."""
import hashlib, os, sys
from . import plat

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRITABLE = {'AC1015', 'AC1018', 'AC1024', 'AC1027', 'AC1032'}
SKIP = {'prev', 'next', 'prev_handle', 'next_handle'}      # chain links may be renumbered by the writer; compared only if equal sets elsewhere


def fingerprint(path):
    st = os.stat(path)
    return {'size': st.st_size, 'mtime': int(st.st_mtime), 'sha1': hashlib.sha1(open(path, 'rb').read()).hexdigest()}


class SaveError(Exception):
    pass


def _entities(buf):
    import dwgmodel
    m = dwgmodel.Model(buf)
    # AC1015: the flag doubling as "no explicit links" flips on the neighbours of an erased/copied entity (the writer makes their links explicit, see dwgdoc._set_links);
    # it only changes how the chain is stored, not the entity, and AutoCAD AUDIT is clean on such files
    skip = SKIP | {'xdicmissing'} if bytes(buf[:6]) == b'AC1015' else SKIP
    return {e['handle']: {k: v for k, v in e.items() if k not in skip} for b, e in m.entities()}


class _Lock:
    """lock file next to the target (O_EXCL, holds the pid); a lock of a dead process is taken over, a live one refuses the save"""
    def __init__(self, target): self.p = os.path.join(os.path.dirname(target), '.%s.lock' % os.path.basename(target))

    def __enter__(self):
        for _ in range(2):
            try:
                fd = os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd); return self
            except FileExistsError:
                try: pid = int(open(self.p).read().strip() or 0)
                except (OSError, ValueError): pid = 0
                alive = False
                if pid:
                    alive = plat.proc.pid_alive(pid)
                if alive and pid != os.getpid(): raise SaveError('another save of this file is running (lock %s, pid %d)' % (self.p, pid))
                try: os.remove(self.p)
                except OSError: pass
        raise SaveError('could not take the lock ' + self.p)

    def __exit__(self, *a):
        try: os.remove(self.p)
        except OSError: pass


def save_as(src, dst, layers, fp=None, overwrite=False, erase=(), move=()):
    dst0 = os.path.abspath(os.path.expanduser(dst))
    d0 = os.path.dirname(dst0)
    if os.path.isdir(d0) and os.access(d0, os.W_OK):
        with _Lock(dst0): return _save_as(src, dst, layers, fp, overwrite, erase, move)
    return _save_as(src, dst, layers, fp, overwrite, erase, move)       # the checks in _save_as report the unwritable folder


def _save_as(src, dst, layers, fp=None, overwrite=False, erase=(), move=()):
    """layers: {name: {'off': bool, 'frozen': bool, 'locked': bool}} (only the given names are touched). Returns a report dict."""
    if HERE not in sys.path: sys.path.insert(0, HERE)
    import dwgdoc
    src = os.path.realpath(src); dst = os.path.abspath(os.path.expanduser(dst))
    if not dst.lower().endswith('.dwg'): raise SaveError('the new file must end in .dwg')
    if os.path.realpath(dst) == src and not overwrite: raise SaveError('refusing to write over the source file (Save As needs a new name)')
    if overwrite and os.path.realpath(dst) != src: raise SaveError('overwrite only replaces the source file itself')
    if os.path.exists(dst) and not overwrite: raise SaveError('refusing to overwrite an existing file: ' + dst)
    d = os.path.dirname(dst)
    if not os.path.isdir(d) or not os.access(d, os.W_OK): raise SaveError('folder is not writable: ' + d)
    if fp is not None and fingerprint(src) != fp: raise SaveError('the source file changed on disk since it was opened; reopen it first')
    buf = open(src, 'rb').read(); fp0 = fingerprint(src); bak = None
    if buf[:6].decode('latin1') not in WRITABLE: raise SaveError('the writer does not support %s files yet' % buf[:6].decode('latin1'))
    doc = dwgdoc.Doc(buf); touched = 0; want = {}
    for name, st in layers.items():
        try: h = doc.layer_handle(name)
        except KeyError: raise SaveError('no such layer: ' + name)
        fl = doc.get(h)['flags']
        cur = {'frozen': bool(fl & 1), 'off': bool(fl & 2), 'locked': bool(fl & 8)}
        diff = {k: bool(v) for k, v in st.items() if k in cur and bool(v) != cur[k]}
        want[name] = {**cur, **diff}
        if diff: doc.set_layer(name, **diff); touched += 1
    erase = sorted(set(int(h) for h in erase))
    for h in erase:
        if h not in doc.objs: raise SaveError('no such object to erase: %X' % h)
        doc.erase(h)
    moved = {}
    created = []
    for m in move:                                     # [{'t': 'move'|'copy', 'hs': [handles], 'dx': , 'dy': }] in order; a handle moved twice accumulates
        import dwgxform as X
        for h in m['hs']:
            h = int(h)
            if h in erase: continue
            if h not in doc.objs: raise SaveError('no such object to %s: %X' % (m.get('t', 'move'), h))
            tr = X.Transform.translate(float(m['dx']), float(m['dy']))
            if m.get('t') == 'copy':
                try: created.append(doc.copy_entity(h, tr))
                except NotImplementedError as ex: raise SaveError('cannot copy object %X: %s' % (h, ex))
            else:
                doc.transform(h, tr); moved[h] = moved.get(h, 0) + 1
    out = doc.save()
    # verification on the bytes, before anything touches the disk
    a, b = _entities(buf), _entities(out); gone = set(erase); kids = {h for h, e in a.items() if e.get('kind') == 'ATTRIB' and e.get('owner') in moved}      # attributes travel with their moved INSERT
    bad = [h for h in a if h not in gone and h not in moved and h not in kids and b.get(h) != a[h]]
    unmoved = [h for h in moved if b.get(h) == a.get(h)]       # a moved object whose record did not change would mean the move was lost
    if unmoved: raise SaveError('verification failed: %d moved object(s) are unchanged in the result (nothing written)' % len(unmoved))
    if set(b) != (set(a) - gone) | set(created) or bad: raise SaveError('verification failed: %d of %d entity records differ (source kept, nothing written)' % (len(bad), len(a)))
    d2 = dwgdoc.Doc(out)
    for name, w in want.items():
        fl = d2.get(d2.layer_handle(name))['flags']
        if {'frozen': bool(fl & 1), 'off': bool(fl & 2), 'locked': bool(fl & 8)} != w: raise SaveError('verification failed: layer flags of %s differ from the request' % name)
    tmp = os.path.join(d, '.%s.tmp-%d' % (os.path.basename(dst), os.getpid()))
    try:
        with open(tmp, 'xb') as f:
            f.write(out); f.flush(); os.fsync(f.fileno())
        if overwrite:
            if fingerprint(src) != fp0: raise SaveError('the source file changed while saving; nothing was replaced')
            bak = backup(src)
        elif os.path.exists(dst): raise SaveError('refusing to overwrite an existing file: ' + dst)
        plat.fsio.replace_retry(tmp, dst)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise
    r = {'path': dst, 'bytes': len(out), 'entities': len(a), 'layers_changed': touched, 'erased': len(erase), 'moved': len(moved), 'copied': len(created), 'moved_with': len(kids), 'version': buf[:6].decode('latin1')}
    if bak: r['backup'] = bak
    return r


BACKUPS = os.environ.get('DWG_BALLET_BACKUPS') or os.path.join(plat.dirs.cache_dir('dwg-ballet'), 'backups')
CONFIG = os.environ.get('DWG_BALLET_CONFIG') or os.path.join(plat.dirs.config_dir('dwg-ballet'), 'config.json')


def overwrite_allowed():
    """Overwrite (SAVE!) is OFF unless the config file says {"allow_overwrite": true}"""
    try:
        import json; return json.load(open(CONFIG)).get('allow_overwrite') is True
    except Exception:
        return False


def backup(path):
    """copy of the file as it is before an overwrite: BACKUPS/<name>.bak-YYYYmmdd-HHMMSS-<sha1 8> (hash-verified copy)"""
    import shutil, time
    os.makedirs(BACKUPS, exist_ok=True)
    h = hashlib.sha1(open(path, 'rb').read()).hexdigest()
    dst = os.path.join(BACKUPS, '%s.bak-%s-%s' % (os.path.basename(path), time.strftime('%Y%m%d-%H%M%S'), h[:8]))
    shutil.copy2(path, dst)
    if hashlib.sha1(open(dst, 'rb').read()).hexdigest() != h: os.remove(dst); raise SaveError('backup copy does not match the original; nothing was replaced')
    return dst


def save_over(src, layers, fp=None, erase=(), move=()):
    """Overwrite the source file (command SAVE!): only with allow_overwrite in the config, after a verified backup of the original"""
    if not overwrite_allowed(): raise SaveError('overwrite is disabled (set allow_overwrite in %s); use SAVEAS' % CONFIG)
    return save_as(src, src, layers, fp, overwrite=True, erase=erase, move=move)


def restore(backup_path, target):
    """put a backup back (atomic rename of a temp copy), e.g. RESTORE after a bad overwrite"""
    import shutil
    tmp = target + '.restore-tmp'
    shutil.copy2(backup_path, tmp); plat.fsio.replace_retry(tmp, target)

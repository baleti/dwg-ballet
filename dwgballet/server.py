"""aiohttp server: /api/meta, /api/layout/<i>, static web/."""
import struct, os, json, asyncio
from aiohttp import web
from . import build, cache, files, recent, aliases, savegate, journal
from . import ole as OLE

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(HERE, 'web')


def make_app(path=None, start_layout=None, prefetch=True):
    app = web.Application()
    state = {'doc': None, 'err': None, 'meta': None, 'path': path}

    def parse():
        """build the Doc (slow); writes meta + all layouts to the disk cache in the background"""
        p = state['path']
        d = build.Doc(p)
        if state['path'] == p: state['doc'] = d
        return d

    async def load(app):
        loop = asyncio.get_running_loop()
        path = state['path']
        if not path: return
        recent.add(path)
        try: state['fp'] = savegate.fingerprint(path)       # concurrent-modification guard for Save As
        except OSError: state['fp'] = None
        m = cache.read_meta(path)
        if m:
            state['meta'] = m
            loop.run_in_executor(None, lambda: _safe(parse))        # the Doc is still needed for the entity inspector
            return
        try:
            d = await loop.run_in_executor(None, parse)
            if state['path'] != path: return
            state['meta'] = d.meta()
            cache.write_meta(path, state['meta'])
            if prefetch: loop.run_in_executor(None, lambda: _safe(lambda: prefetch_all(d, path)))
        except Exception as ex:
            import traceback; traceback.print_exc()
            names = {'AC1012': 'R13', 'AC1014': 'R14', 'AC1009': 'R12'}
            v = str(ex).strip("'\" ")
            import re as _re
            state['err'] = ('This drawing is %s (%s), a file version the parser cannot read yet.' % (names.get(v, v), v)) if isinstance(ex, NotImplementedError) and _re.fullmatch(r'AC10\d\d', v) else ('This file is not a readable DWG (%s).' % (str(ex) or type(ex).__name__)) if isinstance(ex, NotImplementedError) else ('This drawing could not be read: the file looks damaged, truncated or uses data this parser does not decode (%s).' % (str(ex)[:120] or type(ex).__name__)) if isinstance(ex, (struct.error, ValueError, IndexError, EOFError, KeyError, OverflowError, MemoryError)) else '%s: %s' % (type(ex).__name__, ex)

    def _safe(fn):
        try: return fn()
        except Exception:
            import traceback; traceback.print_exc()

    import threading
    locks = {}

    def klock(path, i, tw):
        return locks.setdefault((path, i, bool(tw)), threading.Lock())    # one build per layout at a time: a request waits for the prefetch of the same layout

    def prefetch_all(d, path):
        """default layout first (in this process), the others in forked workers that write the cache themselves (POSIX); serial elsewhere"""
        m = state['meta']
        order = [m['default']] + [l['i'] for l in m['layouts'] if l['i'] != m['default']]
        jobs = [(i, tw) for i in order for tw in ((True, False) if (not m['layouts'][i]['ps'] and d.twist_matters(i)) else (True,))]
        todo = [j for j in jobs if not os.path.exists(cache.layout_path(path, *j))]
        first = [j for j in todo if j[0] == m['default']]; rest = [j for j in todo if j[0] != m['default']]
        for j in first:
            with klock(path, *j):
                if not os.path.exists(cache.layout_path(path, *j)): cache.write_layout(path, j[0], j[1], d.layout(*j))
        if hasattr(os, 'fork') and len(rest) > 1 and not os.environ.get('DWG_NO_FORK') and not os.environ.get('DWG_FORCE_SPAWN'):
            nw = max(1, min(len(rest), (os.cpu_count() or 2) - 1, 3)); running = {}
            for j in rest:
                while len(running) >= nw:
                    pid, _ = os.wait(); running.pop(pid, None)
                pid = os.fork()
                if pid == 0:
                    code = 0
                    try: cache.write_layout(path, j[0], j[1], d.layout(*j))
                    except BaseException: code = 1
                    os._exit(code)
                running[pid] = j
            while running:
                pid, _ = os.wait(); running.pop(pid, None)
        elif len(rest) > 1 and not os.environ.get("DWG_NO_FORK"):
            from . import spawnpool
            spawnpool.build_layouts(path, rest, max(1, min(len(rest), (os.cpu_count() or 2) - 1, 3)))
        else:
            for j in rest: cache.write_layout(path, j[0], j[1], d.layout(*j))
        cache.prune()
    app.on_startup.append(lambda a: asyncio.ensure_future(load(a)))

    async def meta(req):
        if not state['path']: return web.json_response({'nodoc': True})
        if state['err']: return web.json_response({'error': state['err']})
        if not state['meta']: return web.json_response({'loading': True})
        m = dict(state['meta']); m['start'] = start_layout if start_layout is not None else m['default']
        return web.json_response(m)

    async def layout(req):
        if not state['meta']: return web.json_response({'loading': True}, status=503)
        path = state['path']
        i = int(req.match_info['i'])
        if i < 0 or i >= len(state['meta'].get('layouts', [0])): return web.json_response({'error': 'no such layout'}, status=404)
        loop = asyncio.get_running_loop()
        tw = req.query.get('twist', '1') != '0'
        tm_ = getattr(state['doc'], 'twist_matters', None)
        if not tw and tm_ is not None and not tm_(i): tw = True      # no view twist: same scene
        body = cache.read_layout(path, i, tw)
        if body is not None:
            return web.Response(body=body, content_type='application/json', headers={'Content-Encoding': 'gzip'})
        d = state['doc']
        if d is None: d = await loop.run_in_executor(None, parse)
        def build_one():
            with klock(path, i, tw):
                if not os.path.exists(cache.layout_path(path, i, tw)):
                    r_ = d.layout(i, tw); _safe(lambda: cache.write_layout(path, i, tw, r_)); return r_
            return None
        r = await loop.run_in_executor(None, build_one)
        body = cache.read_layout(path, i, tw)
        if r is None and body is None: r = await loop.run_in_executor(None, d.layout, i, tw)
        if body is not None:
            return web.Response(body=body, content_type='application/json', headers={'Content-Encoding': 'gzip'})
        resp = web.json_response(r); resp.enable_compression(); return resp

    async def olepic(req):
        d = state['doc']; h = int(req.match_info['h'])
        o = d.m.objs.get(h) if d else None
        png = OLE.image_png(o) if o is not None and o.type == 74 else None
        if not png: return web.Response(status=404)
        return web.Response(body=png, content_type='image/png', headers={'Cache-Control': 'max-age=3600'})

    async def entity(req):
        d = state['doc']; h = int(req.match_info['h'])
        if not d: return web.json_response({'kind': 'loading'})
        for es in d.sc.by_block.values():
            for e in es:
                if e['handle'] == h:
                    keep = {k: v for k, v in e.items() if k not in ('eed', 'paths', 'pts', 'verts', 'knots', 'ctrl', 'pattern_lines', 'gradient')}
                    return web.json_response({'kind': e['kind'], 'summary': ', '.join('%s=%s' % (k, (round(v, 3) if isinstance(v, float) else v)) for k, v in keep.items() if k in ('block_ref', 'text', 'height', 'text_height', 'radius', 'pattern_name', 'lweight', 'ltscale', 'rot')), 'props': keep}, dumps=lambda o: json.dumps(o, default=str))
        return web.json_response({})

    async def ctbapi(req):
        from . import ctb
        n = req.query.get('name', '')
        p = ctb.find(n)
        if not p: return web.json_response({'name': n, 'found': False})
        t = ctb.table(p)
        return web.json_response({'name': os.path.basename(p), 'found': True, 'aci': {k: [v['rgb'], v['lw'], v['screen']] for k, v in t['aci'].items()}})

    async def ctbupload(req):
        """a plot style table (.ctb) picked in the browser: parsed from the request body, nothing is stored"""
        from . import ctb
        raw = await req.read()
        try:
            t = ctb.table_bytes(raw)
        except Exception as ex:
            return web.json_response({'found': False, 'error': str(ex)[:120]})
        return web.json_response({'found': True, 'aci': {k: [v['rgb'], v['lw'], v['screen']] for k, v in t['aci'].items()}})

    async def ctblist(req):
        from . import ctb
        out = []
        for d in ctb.SEARCH:
            if d and os.path.isdir(d): out += sorted(f for f in os.listdir(d) if f.lower().endswith('.ctb'))
        return web.json_response(sorted(set(out)))

    async def index(req):
        return web.FileResponse(os.path.join(WEB, 'index.html' if state['path'] else 'start.html'))

    async def start(req):
        return web.FileResponse(os.path.join(WEB, 'start.html'))

    async def browse(req):
        return web.json_response(files.browse(req.query.get('path', '')))

    async def recent_list(req):
        return web.json_response(recent.listing())

    async def open_doc(req):
        try: body = await req.json()
        except Exception: return web.json_response({'error': 'bad request'}, status=400)
        p, err = files.check(str(body.get('path', '')).strip())
        if err: return web.json_response({'error': err}, status=400)
        state.update(doc=None, err=None, meta=None, path=p, fp=None)
        await load(app)
        return web.json_response({'ok': True, 'path': p})
    app.router.add_get('/', index)
    app.router.add_get('/start', start)
    async def saveas(req):
        """Save As with the safety gate (dwgballet/savegate.py): new file only, verified, atomic"""
        if not state['path']: return web.json_response({'error': 'no drawing is open'}, status=400)
        try: body = await req.json()
        except Exception: return web.json_response({'error': 'bad request'}, status=400)
        dst = str(body.get('path', '')).strip()
        if not dst: return web.json_response({'error': 'no target path'}, status=400)
        if not os.path.isabs(os.path.expanduser(dst)): dst = os.path.join(os.path.dirname(state['path']), dst)     # a bare name goes next to the source
        if not files.allowed(os.path.dirname(os.path.abspath(os.path.expanduser(dst)))): return web.json_response({'error': 'outside $HOME and the mounted directories'}, status=400)
        layers = {n: s for n, s in (body.get('layers') or {}).items() if isinstance(s, dict)}
        loop = asyncio.get_running_loop()
        try: r = await loop.run_in_executor(None, lambda: savegate.save_as(state['path'], dst, layers, state.get('fp'), erase=body.get('erase') or [], move=body.get('move') or []))
        except savegate.SaveError as ex: return web.json_response({'error': str(ex)}, status=409)
        except Exception as ex: return web.json_response({'error': 'save failed (%s: %s); nothing was written' % (type(ex).__name__, str(ex)[:120])}, status=500)
        recent.add(r['path']); journal.clear(state['path'])
        return web.json_response(r)
    app.router.add_post('/api/saveas', saveas)

    async def save_over(req):
        """SAVE!: overwrite the open file; off unless allow_overwrite is set in the config; verified backup of the original first"""
        if not state['path']: return web.json_response({'error': 'no drawing is open'}, status=400)
        try: body = await req.json()
        except Exception: return web.json_response({'error': 'bad request'}, status=400)
        layers = {n: s for n, s in (body.get('layers') or {}).items() if isinstance(s, dict)}
        loop = asyncio.get_running_loop()
        try: r = await loop.run_in_executor(None, lambda: savegate.save_over(state['path'], layers, state.get('fp'), erase=body.get('erase') or [], move=body.get('move') or []))
        except savegate.SaveError as ex: return web.json_response({'error': str(ex)}, status=409)
        except Exception as ex: return web.json_response({'error': 'save failed (%s: %s); the original is untouched' % (type(ex).__name__, str(ex)[:120])}, status=500)
        state['fp'] = savegate.fingerprint(state['path']); journal.clear(state['path'])
        return web.json_response(r)
    app.router.add_post('/api/save', save_over)

    async def jr(req):
        """GET: the journal of the open file; POST {cmd}: append; POST {undo:true}: drop the last line; POST {clear:true}"""
        if not state['path']: return web.json_response({'error': 'no drawing is open'}, status=400)
        if req.method == 'GET': return web.json_response(journal.read(state['path']))
        body = await req.json()
        if body.get('clear'): journal.clear(state['path'])
        elif body.get('undo'): journal.pop(state['path'])
        elif isinstance(body.get('cmd'), str): journal.append(state['path'], body['cmd'][:500])
        return web.json_response({'ok': True})
    app.router.add_get('/api/journal', jr); app.router.add_post('/api/journal', jr)

    async def alias_list(req):
        return web.json_response(aliases.load())
    app.router.add_get('/api/aliases', alias_list)
    app.router.add_get('/api/browse', browse)
    app.router.add_get('/api/recent', recent_list)
    app.router.add_post('/api/open', open_doc)
    app.router.add_get('/api/meta', meta)
    app.router.add_get('/api/layout/{i}', layout)
    app.router.add_get('/api/ctb', ctbapi)
    app.router.add_get('/api/ctblist', ctblist)
    app.router.add_post('/api/ctbupload', ctbupload)
    app.router.add_get('/api/entity/{h}', entity)
    app.router.add_get('/api/ole/{h}', olepic)
    app.router.add_static('/', WEB)
    return app

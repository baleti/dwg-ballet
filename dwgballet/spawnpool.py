"""Layout workers for platforms without os.fork (Windows, macOS spawn): each worker re-opens the drawing and writes the layout cache file itself."""
import multiprocessing as mp
from . import build, cache


def _work(path, jobs):
    d = build.Doc(path); d.meta()
    for i, tw in jobs:
        try: cache.write_layout(path, i, tw, d.layout(i, tw))
        except Exception: pass


def build_layouts(path, jobs, nw):
    """jobs: [(layout index, twist)]; nw workers, jobs dealt round-robin; returns when all workers are done"""
    nw = max(1, min(nw, len(jobs)))
    ctx = mp.get_context("spawn")
    ps = [ctx.Process(target=_work, args=(path, jobs[k::nw])) for k in range(nw)]
    for p in ps: p.start()
    for p in ps: p.join()

#!/usr/bin/env python3
"""vcompare.py FILE.dwg LAYOUT_INDEX [--oracle DIR] [--out DIR] : render our layout (headless chromium, clean mode) and the AutoCAD oracle plot
(fixed.pdf), crop both to their ink bbox, report ink precision/recall after 2px dilation, write side-by-side + diff PNG. Local use only."""
import sys, os, re, subprocess, json, socket, argparse
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORA = os.path.expanduser('~/dwg-research/oracle-out')


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def ink_bbox(im, thr=235):
    """bounding box of the ink, ignoring specks (cells of w/150 px holding fewer than ~4 ink pixels at 1800 px width): a stray point far from the drawing frames differently in the plot and in ours"""
    a = np.asarray(im.convert('RGB')).min(axis=2) < thr
    e_ = max(2, a.shape[1] // 400); a = a.copy(); a[:e_] = False; a[-e_:] = False; a[:, :e_] = False; a[:, -e_:] = False     # the rasterised page edge line is not content
    if not a.any(): return None
    H, W = a.shape; c = max(4, W // 150); need = max(3, int(12 * (W / 1800.0) ** 2))
    g = a[:H // c * c, :W // c * c].reshape(H // c, c, W // c, c).sum(axis=(1, 3))
    ys, xs = np.where(g >= need)
    if len(xs) == 0: ys, xs = np.where(g > 0)
    if len(xs) == 0: return None
    x0, y0, x1, y1 = int(xs.min() * c), int(ys.min() * c), int(min(xs.max() * c + c, W)), int(min(ys.max() * c + c, H))
    py, px = np.where(a[y0:y1, x0:x1])     # exact ink box inside the speck-free cell range (cell rounding would shift the framing by up to a cell)
    x0, y0, x1, y1 = x0 + int(px.min()), y0 + int(py.min()), x0 + int(px.max()) + 1, y0 + int(py.max()) + 1
    box0 = (x0, y0, x1, y1)
    # a hairline frame running along the sheet edge (the plot's page border) is not content: drop long thin edge lines, then reframe
    for _ in range(3):
        sub = a[y0:y1, x0:x1]
        if sub.size == 0: break
        h_, w_ = sub.shape; moved = False; bw = max(3, int(0.02 * max(h_, w_)))
        rows, cols = sub.sum(axis=1), sub.sum(axis=0)
        if rows[:3].max() > 0.6 * w_ and rows[3:3 + bw].sum() < 0.15 * w_ * bw: y0 += 3 + bw; moved = True
        elif rows[-3:].max() > 0.6 * w_ and rows[-3 - bw:-3].sum() < 0.15 * w_ * bw: y1 -= 3 + bw; moved = True
        if cols[:3].max() > 0.6 * h_ and cols[3:3 + bw].sum() < 0.15 * h_ * bw: x0 += 3 + bw; moved = True
        elif cols[-3:].max() > 0.6 * h_ and cols[-3 - bw:-3].sum() < 0.15 * h_ * bw: x1 -= 3 + bw; moved = True
        if not moved: break
        sy, sx = np.where(a[y0:y1, x0:x1])
        if len(sx) == 0: break
        x0, y0, x1, y1 = x0 + int(sx.min()), y0 + int(sy.min()), x0 + int(sx.max()) + 1, y0 + int(sy.max()) + 1
    py, px = np.where(a[y0:y1, x0:x1])
    if len(px) == 0:     # nothing but the edge frame was left (AC1015_f9fc505c6f L1): keep the box with the frame
        x0, y0, x1, y1 = box0; py, px = np.where(a[y0:y1, x0:x1])
    q = float(os.environ.get('VC_TRIM', '0'))     # percent of ink pixels trimmed per side: faint stray items framing one side only
    lo, hi = np.percentile(px, [q, 100 - q]), np.percentile(py, [q, 100 - q])
    return x0 + int(lo[0]), y0 + int(hi[0]), x0 + int(lo[1]) + 1, y0 + int(hi[1]) + 1


def run(path, li, oracle_name=None, out='/tmp', width=int(os.environ.get('VC_W', 3200)), height=int(os.environ.get('VC_H', 2260)), port=None, kind='fixed'):
    stem = os.path.splitext(os.path.basename(path))[0]
    odir = os.path.join(ORA, stem)
    dump = json.load(open(os.path.join(odir, 'dump.json')))
    lname = None
    import asyncio
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cdp import Session
    png = os.path.join(out, '%s_L%d_ours.png' % (stem, li))
    info = {}
    async def shoot():
        async with Session(path, width, height) as s:
            await s.open('clean=1&' + ('fit=full' if os.environ.get('VC_FIT', 'full') == 'full' else 'fit=bounds') + '' + ('' if os.environ.get('VC_NOPLOT') else '&plot=1') + ('&noclip=1' if kind == 'fixed' and not os.environ.get('VC_CLIP') else '') + ('&lwu=1' if li == 0 else '') + ('&twist=0' if os.environ.get('VC_NOTWIST') else '') + ('&vpborder=1' if os.environ.get('VC_VPB') else '') + ('&vpborder=0' if os.environ.get('VC_NOVPB') else '') + ('&hairA=' + os.environ['VC_HAIRA'] if os.environ.get('VC_HAIRA') else ''), layout=li)     # the AutoCAD plot of Model follows the saved view twist (AC1027_86d1204efc, AC1027_6c8a408cf4: 1.0 / .997 with twist, rotated without)
            for _ in range(2000):     # wait until the layout is loaded and the first full render finished
                if await s.js("document.body.classList.contains('clean') && typeof STAT!=='undefined' && !raf && typeof lay!=='undefined' && lay!==null && document.getElementById('msg').style.display==='none'"): break
                await asyncio.sleep(0.3)
            await asyncio.sleep(1.0)
            info['name'] = await s.js("meta.layouts[%d].name" % li)
            if os.environ.get('VC_LWK', '1') != '0':
                try:    # the fixed plot shrinks the sheet to A3 but keeps physical lineweights: scale ours to the same relative thickness
                    import fitz
                    pdf = os.path.join(odir, 'plots', '%s.%s.pdf' % (info['name'].replace(' ', '_'), kind))
                    pg = fitz.open(pdf)[0]
                    xs = [v for d in pg.get_drawings() for v in (d['rect'].x0, d['rect'].x1)]
                    full = await s.js("JSON.stringify(lay.full)"); full = json.loads(full)
                    pu = float(await s.js('lay.pu||1'))     # paper units in mm (25.4 for inch layouts)
                    k = (full[2] - full[0]) * pu / ((max(xs) - min(xs)) / 2.8346)
                    k = min(max(k, 0.005), 2000) if not await s.js("!!meta.layouts[%d].ps" % li) else min(max(k, 0.005), 8)     # Model: lwK is the drawing units per plotted mm
                    await s.js("(()=>{const e=document.getElementById('lwK'); e.min=0.001; e.step='any'; e.max=2000; e.value=%f; e.oninput({target:e});})()" % k)
                    info['lwk'] = round(k, 2);
                    await asyncio.sleep(1.5)
                except Exception as ex:
                    info['lwk'] = str(ex)[:60]
            if os.environ.get('VC_LWKV'):     # experiment: fixed line weight factor
                await s.js("(()=>{const e=document.getElementById('lwK'); e.max=8; e.value=%s; e.oninput({target:e});})()" % os.environ['VC_LWKV']); await asyncio.sleep(1.5)
            await s.shot(png)
    asyncio.run(shoot())
    return compare(stem, li, info['name'], png, out, kind)


def compare(stem, li, lname, png, out, kind='fixed'):
    """score with two ink thresholds for the framing box (235; 248 also counts the faint 0-width pen hairlines of viewport frames that the oracle raster has at grey 204) and keep the better aligned result (AC1015_bda7ef24fd L2 .64/.58 -> .75/.67; the lighter box alone breaks AC1024_2196c910ba)"""
    if os.environ.get('VC_BBTHR'): return _compare(stem, li, lname, png, out, kind, int(os.environ['VC_BBTHR']), True)
    r1 = _compare(stem, li, lname, png, out, kind, 235, False)
    r2 = _compare(stem, li, lname, png, out, kind, 248, False)
    best = r2 if r2['p5a'] + r2['r5a'] > r1['p5a'] + r1['r5a'] + 0.01 else r1
    best['bbthr'] = 248 if best is r2 else 235
    _compare(stem, li, lname, png, out, kind, best['bbthr'], False)     # rewrite the side image of the chosen variant
    print(json.dumps(best)); return best


def _compare(stem, li, lname, png, out, kind, thr, emit):
    """score our rendering png against the oracle plot of layout lname (pdf pages are rasterised at 110 dpi)"""
    odir = os.path.join(ORA, stem)
    pdf = os.environ.get('VC_PDF') or os.path.join(odir, 'plots', '%s.%s.pdf' % (re.sub(r'[^\w.\-]', '_', lname), kind))     # VC_PDF: any plotted PDF as the reference
    if not os.path.exists(pdf):     # the oracle keeps some characters the sanitiser above replaces (parentheses, +, &): match on the letters and digits only
        import glob
        norm = lambda x: re.sub(r'[\W_]+', '', x).lower()
        for c in glob.glob(os.path.join(odir, 'plots', '*.%s.pdf' % kind)):
            if norm(os.path.basename(c)[:-len('.%s.pdf' % kind)]) == norm(lname): pdf = c; break
    if not os.path.exists(pdf):
        import glob
        c = glob.glob(os.path.join(odir, 'plots', '*.%s.pdf' % kind))
        raise SystemExit('no oracle pdf for %r; have %s' % (lname, [os.path.basename(x) for x in c]))
    base = os.path.join(out, '%s_L%d_ora' % (stem, li))
    subprocess.run(['pdftoppm', '-r', '110', '-png', '-singlefile', pdf, base], check=True)
    a = Image.open(png).convert('RGB'); b = Image.open(base + '.png').convert('RGB')
    ba, bb = ink_bbox(a, thr), ink_bbox(b, thr)
    if os.environ.get('VC_FULLPAGE'): ba, bb = (0, 0, a.width, a.height), (0, 0, b.width, b.height)     # both images are the whole sheet (pdfcompare.py): no ink-box framing
    if not ba or not bb: raise SystemExit('empty render: ours=%s oracle=%s' % (ba, bb))
    ca, cb = a.crop(ba), b.crop(bb)
    # fit ours into oracle crop size, preserving nothing: report aspect mismatch
    asp_a, asp_b = ca.width / ca.height, cb.width / cb.height
    if os.environ.get('VC_STRETCH'): ca = ca.resize(cb.size, Image.LANCZOS)
    else:     # uniform scale (a stray mark on one side changes the crop aspect; stretching would distort the whole drawing), centred on a white canvas, the shift search below does the rest
        k_ = min(cb.width / ca.width, cb.height / ca.height)
        cu = ca.resize((max(1, round(ca.width * k_)), max(1, round(ca.height * k_))), Image.LANCZOS)
        ca = Image.new('RGB', cb.size, 'white'); ca.paste(cu, ((cb.width - cu.width) // 2, (cb.height - cu.height) // 2))
    ka = np.asarray(ca).min(axis=2) < 195
    kb = np.asarray(cb).min(axis=2) < 195
    if not ka.any() or not kb.any(): raise SystemExit('empty render: no ink under the score threshold (ours=%d px, oracle=%d px; only faint frames)' % (ka.sum(), kb.sum()))
    def dil(m, r=2):
        im = Image.fromarray((m * 255).astype('uint8')).filter(ImageFilter.MaxFilter(2 * r + 1))
        return np.asarray(im) > 0
    da, db = dil(ka), dil(kb)
    prec = (ka & db).sum() / max(ka.sum(), 1)
    rec = (kb & da).sum() / max(kb.sum(), 1)
    da5, db5 = dil(ka, 5), dil(kb, 5)
    prec5 = (ka & db5).sum() / max(ka.sum(), 1); rec5 = (kb & da5).sum() / max(kb.sum(), 1)
    # aligned score: the two crops are framed by their ink bounding boxes, which differ when one side has extra far-away items; search scale (+-4 %) and shift
    # on 1/4 size masks (FFT cross-correlation) and rescore the full-size masks with the best transform
    def small(m): return np.asarray(Image.fromarray((m * 255).astype('uint8')).resize((m.shape[1] // 4, m.shape[0] // 4), Image.BOX)) > 40
    sa, sb = dil(small(ka) , 1), dil(small(kb), 1)
    H, W = sb.shape; FB = np.fft.rfft2(sb.astype(float))
    def search(scales):
      best = (-1, 1.0, 0, 0)
      for sc in scales:
          M = Image.fromarray((sa * 255).astype('uint8')).transform((W, H), Image.AFFINE, (1 / sc, 0, W / 2 * (1 - 1 / sc), 0, 1 / sc, H / 2 * (1 - 1 / sc)), Image.BILINEAR)
          A = np.asarray(M) > (100 if sc >= 0.7 else 12)     # a shrunk thin-line mask loses most of its intensity
          cc = np.fft.irfft2(np.fft.rfft2(A.astype(float)) * np.conj(FB), s=(H, W))
          k = int(np.argmax(cc)); dy, dx = divmod(k, W)
          if dy > H // 2: dy -= H
          if dx > W // 2: dx -= W
          score = cc.flat[k] / max(np.sqrt(A.sum() * sb.sum()), 1.0) * (1 - 0.12 * abs(np.log(sc)))     # cosine match with a prior for scale 1 (the crops are normally framed alike)
          if score > best[0]: best = (score, sc, dx, dy)
      return best
    best = search(np.exp(np.arange(np.log(0.12), np.log(8.0), 0.012)))
    best_near1 = search(np.exp(np.arange(np.log(0.94), np.log(1.07), 0.004)))     # the wide search sometimes locks on a wrong scale (AC1027_376d62a5ee Model 1.37 vs 1.05): also try the neighbourhood of 1 and keep the better score
    _, bs, bdx, bdy = best
    # cc peak at (dy, dx) means A shifted by (dy, dx) matches B... our mask must move by -(dx, dy) of the correlation convention: try both signs
    def apply(sc, dx, dy):
        im = Image.fromarray((ka * 255).astype('uint8')).transform(ca.size, Image.AFFINE, (1 / sc, 0, ca.width / 2 * (1 - 1 / sc) - dx * 4, 0, 1 / sc, ca.height / 2 * (1 - 1 / sc) - dy * 4), Image.BILINEAR)
        k2 = np.asarray(im) > (128 if sc >= 1 else 128 * sc)     # thin lines of a shrunk mask keep only a fraction of their intensity
        d2, d2b = dil(k2, 5), db5
        return (k2 & d2b).sum() / max(k2.sum(), 1), (kb & d2).sum() / max(kb.sum(), 1)
    cand = [apply(bs, sx * bdx, sy * bdy) for sx in (1, -1) for sy in (1, -1)]
    pa5, ra5 = max(cand, key=lambda t: t[0] + t[1])
    if best_near1[1] != bs:
        _, bs1, bdx1, bdy1 = best_near1
        c1 = max((apply(bs1, sx * bdx1, sy * bdy1) for sx in (1, -1) for sy in (1, -1)), key=lambda t: t[0] + t[1])
        if c1[0] + c1[1] > pa5 + ra5: pa5, ra5, bs, bdx, bdy = c1[0], c1[1], bs1, bdx1, bdy1
    diff = np.full(kb.shape + (3,), 255, 'uint8')
    diff[kb & ~da] = (220, 0, 0)      # only oracle (missing in ours)
    diff[ka & ~db] = (0, 0, 220)      # only ours (extra)
    diff[ka & kb] = (0, 0, 0)
    side = Image.new('RGB', (cb.width * 3 + 20, cb.height), 'white')
    side.paste(cb, (0, 0)); side.paste(ca, (cb.width + 10, 0)); side.paste(Image.fromarray(diff), (2 * cb.width + 20, 0))
    sp = os.path.join(out, '%s_L%d_side.png' % (stem, li)); side.save(sp)
    res = dict(file=stem, layout=lname, aspect_ours=round(asp_a, 3), aspect_oracle=round(asp_b, 3), ink_precision=round(float(prec), 3), ink_recall=round(float(rec), 3), p5=round(float(prec5), 3), r5=round(float(rec5), 3), p5a=round(float(pa5), 3), r5a=round(float(ra5), 3), align=[round(float(bs), 3), int(bdx) * 4, int(bdy) * 4], side=sp)
    if emit: print(json.dumps(res))
    return res



if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('file'); ap.add_argument('layout', type=int)
    ap.add_argument('--out', default=os.path.expanduser('~/review-compare-dwg'))
    ap.add_argument('--kind', default='fixed'); ap.add_argument('--port', type=int)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    run(a.file, a.layout, out=a.out, kind=a.kind, port=a.port)

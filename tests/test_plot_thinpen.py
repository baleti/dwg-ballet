"""Plot preview draws the real pen width: a 0.05 mm pen on a sheet is a faint line, a 0.5 mm pen is solid black (the screen floor of 0.18 mm only applies outside plot mode).
Synthetic: A3 layout with two horizontal paper-space lines on layers of lineweight 0.05 and 0.50 mm; renders in headless chromium (skipped without it or the template)."""
import os, sys, shutil, tempfile, asyncio, io, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tools'))
TPL = os.path.join(HERE, 'templates', 'blank_2000.dwg')
if not os.path.exists(TPL): TPL = os.path.expanduser('~/dwg-write/templates/blank_2000.dwg')


def _can():
    try:
        import aiohttp, numpy, PIL  # noqa
    except ImportError: return False
    return bool(shutil.which('chromium') and shutil.which('systemd-run') and os.path.exists(TPL))


@unittest.skipUnless(_can(), 'chromium / template missing')
class ThinPenTests(unittest.TestCase):
    def test_thin_pen_is_faint_thick_pen_is_solid(self):
        import numpy as np
        from PIL import Image
        import dwgdoc
        from cdp import Session
        d = dwgdoc.Doc(open(TPL, 'rb').read())
        d.add_layer('thin', lineweight=5); d.add_layer('thick', lineweight=50)
        lh = d.add_layout('A3'); blk = d.get(d.get(lh)['block'])['name']
        d.add_line((40, 100), (380, 100), block=blk, layer='thin')
        d.add_line((40, 200), (380, 200), block=blk, layer='thick')
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.dwg'); open(p, 'wb').write(d.save())

            async def shoot():
                async with Session(p, 3200, 2260) as s:
                    from dwgballet import build
                    li = next(i for i, l in enumerate(build.Doc(p).lays) if l['name'] == 'A3')
                    await s.open('clean=1&plot=1&noclip=1&fit=full', layout=li)
                    for _ in range(200):
                        if await s.js("document.body.classList.contains('clean') && typeof lay!=='undefined' && lay!==null && !raf"): break
                        await asyncio.sleep(0.3)
                    await asyncio.sleep(1)
                    return await s.shot()
            im = np.asarray(Image.open(io.BytesIO(asyncio.run(shoot()))).convert('L')).astype(int)
        rows = im.min(axis=1)       # darkest pixel per row
        self.assertLess(rows.min(), 60, 'the 0.5 mm line should be solid')
        ys = np.where(rows < 235)[0]
        thin = rows[ys[ys > ys.min() + 50]]      # rows of the second (0.05 mm) line, away from the antialiased edge of the first
        self.assertTrue(len(thin), 'the thin line must be drawn')
        self.assertGreater(thin.min(), 110, 'the 0.05 mm line should be faint, not black')


if __name__ == '__main__':
    unittest.main()

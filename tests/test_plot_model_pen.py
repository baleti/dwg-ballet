"""Plot preview of Model space draws the real pen: lwK carries the drawing units per plotted mm, so a 0.5 mm pen with lwK=100 is 50 units wide
(the screen style, 1.9 px per mm of lineweight regardless of scale, made it 6 x too heavy). Synthetic: one 10000 unit line on a 0.5 mm layer in Model (skipped without chromium or the template)."""
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
class ModelPenTests(unittest.TestCase):
    def test_model_pen_follows_lwk(self):
        import numpy as np
        from PIL import Image
        import dwgdoc
        from cdp import Session
        d = dwgdoc.Doc(open(TPL, 'rb').read())
        d.add_layer('pen', lineweight=50)
        d.add_line((0, 0), (10000, 0), layer='pen')
        d.add_line((0, 5000), (10000, 5000), layer='pen')
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.dwg'); open(p, 'wb').write(d.save())

            async def shoot():
                async with Session(p, 3200, 2260) as s:
                    await s.open('clean=1&plot=1&lwu=1&noclip=1&fit=full', layout=0)
                    for _ in range(200):
                        if await s.js("document.body.classList.contains('clean') && typeof lay!=='undefined' && lay!==null && !raf"): break
                        await asyncio.sleep(0.3)
                    await s.js("(()=>{const e=document.getElementById('lwK'); e.max=2000; e.value=100; e.oninput({target:e});})()")
                    await asyncio.sleep(1.5)
                    return await s.shot()
            im = np.asarray(Image.open(io.BytesIO(asyncio.run(shoot()))).convert('L')).astype(int)
        col = im[:, im.shape[1] // 2]
        ys = np.where(col < 128)[0]
        self.assertTrue(len(ys), 'the line must be drawn')
        run = 1
        for a, b in zip(ys, ys[1:]):
            if b != a + 1: break
            run += 1
        scale = im.shape[1] / 10000.0 * 0.9     # about 90 % of the width is the drawing
        self.assertAlmostEqual(run, 50 * scale, delta=max(4, 50 * scale * 0.5), msg='pen width %d px' % run)


if __name__ == '__main__':
    unittest.main()

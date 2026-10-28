"""MTEXT relative height codes multiply the current height: \\H0.16667x;...\\H5.9999x; is about 1 x (the second code used to be taken from the base height: 6 x, giant overlapping text).
Runs parseMtext of web/app.js in headless chromium (skipped without it or the template)."""
import os, sys, shutil, tempfile, asyncio, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tools'))
TPL = os.path.join(HERE, 'templates', 'blank_2000.dwg')
if not os.path.exists(TPL): TPL = os.path.expanduser('~/dwg-write/templates/blank_2000.dwg')


def _can():
    try:
        import aiohttp  # noqa
    except ImportError: return False
    return bool(shutil.which('chromium') and shutil.which('systemd-run') and os.path.exists(TPL))


@unittest.skipUnless(_can(), 'chromium / template missing')
class RelHeightTests(unittest.TestCase):
    def test_relative_heights_multiply(self):
        import dwgdoc
        from cdp import Session
        d = dwgdoc.Doc(open(TPL, 'rb').read())
        d.add_line((0, 0), (10, 10))
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.dwg'); open(p, 'wb').write(d.save())

            async def run():
                async with Session(p, 800, 600) as s:
                    await s.open('clean=1', layout=0)
                    for _ in range(100):
                        if await s.js("typeof parseMtext==='function'"): break
                        await asyncio.sleep(0.3)
                    return await s.js("JSON.stringify([parseMtext('\\\\H0.5x;\\\\H4x;a')[0][0].h, parseMtext('\\\\H2x;a{\\\\H3x;b}c')[0].map(r=>r.h), parseMtext('\\\\H2.5;a')[0][0].h])")
            import json
            r = json.loads(asyncio.run(run()))
        self.assertAlmostEqual(r[0], 2.0, places=6)
        self.assertEqual([round(x, 6) for x in r[1]], [2, 6, 2])
        self.assertTrue(r[2] > 0)


if __name__ == '__main__':
    unittest.main()

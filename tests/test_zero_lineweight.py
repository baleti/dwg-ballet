"""A layer lineweight of 0.00 mm is a hairline, not 'unset': the line must reach the client with lineweight 0.0 (it used to be replaced by the 0.25 mm default),
while a layer with the default lineweight still gets 0.25."""
import os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
TPL = os.path.join(HERE, 'templates', 'blank_2000.dwg')
if not os.path.exists(TPL): TPL = os.path.expanduser('~/dwg-write/templates/blank_2000.dwg')


@unittest.skipUnless(os.path.exists(TPL), 'template missing')
class ZeroLwTests(unittest.TestCase):
    def test_zero_layer_lineweight_stays_zero(self):
        import dwgdoc
        from dwgballet import build
        d = dwgdoc.Doc(open(TPL, 'rb').read())
        d.add_layer('hair', lineweight=0); d.add_layer('dflt')
        d.add_line((0, 0), (10, 0), layer='hair'); d.add_line((0, 5), (10, 5), layer='dflt')
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.dwg'); open(p, 'wb').write(d.save())
            doc = build.Doc(p); L = doc.layout(0)
        by = {doc.lnames[r[1]]: r[3] for r in L['prims'] if r[0] == 'l' and r[1] >= 0 and doc.lnames[r[1]] in ('hair', 'dflt')}
        self.assertEqual(by.get('hair'), 0.0)
        self.assertEqual(by.get('dflt'), 0.25)


if __name__ == '__main__':
    unittest.main()

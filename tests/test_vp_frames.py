"""Viewport frames: the layout JSON carries a frame row (vpb) for each viewport whose layer is plottable; the client draws them in plot mode as faint hairlines
(AutoCAD plots them although the layout flag 'plot viewport borders' is off). Synthetic A3 layout with one viewport on a plot layer and one on a non-plot layer."""
import os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
TPL = os.path.join(HERE, 'templates', 'blank_2000.dwg')
if not os.path.exists(TPL): TPL = os.path.expanduser('~/dwg-write/templates/blank_2000.dwg')


@unittest.skipUnless(os.path.exists(TPL), 'template missing')
class VpFrameTests(unittest.TestCase):
    def test_frame_rows_follow_layer_plot_flag(self):
        import dwgdoc
        from dwgballet import build
        d = dwgdoc.Doc(open(TPL, 'rb').read())
        d.add_layer('vp_plot'); d.add_layer('vp_noplot', plot=False)
        lh = d.add_layout('A3')
        d.add_viewport(lh, (100, 150), (150, 200), layer='vp_plot')
        d.add_viewport(lh, (300, 150), (100, 100), layer='vp_noplot')
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.dwg'); open(p, 'wb').write(d.save())
            doc = build.Doc(p)
            li = next(i for i, l in enumerate(doc.lays) if l['name'] == 'A3')
            L = doc.layout(li)
        rows = [r for r in L['prims'] if len(r) > 6 and r[0] == 'l' and r[6] in L['vpb']]
        self.assertEqual(len(L['vpb']), 2, 'both frames are in the layout (the client hides non-plot layers)')
        names = {doc.lnames[r[1]] for r in rows}
        self.assertEqual(names, {'vp_plot', 'vp_noplot'})
        self.assertTrue(all(r[3] == 0.0 for r in rows), 'zero-width pen')
        meta_layers = {l['n']: l for l in doc.layers()}
        self.assertFalse(meta_layers['vp_noplot']['plot']); self.assertTrue(meta_layers['vp_plot']['plot'])


if __name__ == '__main__':
    unittest.main()

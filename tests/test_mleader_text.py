"""MULTILEADER text: AutoCAD wraps it at the context text width and justifies it by the context alignment (right-aligned text ends at the leader landing).
AC1032_57263838b1 L2 (leader notes ran on in one line, left-aligned). Synthetic entity through the flattener."""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dwgballet.flat import Flattener
from dwgscene import Mat


class Stub(Flattener):
    def __init__(self): pass
    def resolve(self, e, ctx): return '0', (7, None, None), -1, 'Continuous'
    def style_of(self, e): return None
    def dash(self, *a): return None


def mleader(align, width):
    return {'kind': 'MULTILEADER', 'handle': 1, 'layer': '0', 'arrow_size': 0.0, 'leader_lines': [], 'strings': ['LONG NOTE TEXT'],
            'text_loc': (100.0, 50.0, 0.0), 'text_height': 2.5, 'text_width': width,
            'ctx': {'th': 2.5, 'scale': 1.0, 'width': width, 'alignment': align}}


def texts(e):
    out = []
    Stub()._entity(e, Mat(), set(), None, 1.0, 0, out)
    return [r for r in out if r[0] == 't']


class MleaderTextTests(unittest.TestCase):
    def test_width_and_right_alignment(self):
        t = texts(mleader(3, 40.0))[0]
        self.assertEqual(t[8]['hj'], 2); self.assertEqual(t[8]['w'], 40.0); self.assertEqual(t[8]['pa'], 'r')

    def test_left_default_and_centre(self):
        self.assertEqual(texts(mleader(1, 40.0))[0][8]['hj'], 0)
        self.assertEqual(texts(mleader(2, 40.0))[0][8]['hj'], 1)

    def test_no_width_no_wrap_key(self):
        self.assertNotIn('w', texts(mleader(1, 0.0))[0][8])

    def test_env_disables(self):
        os.environ['DWG_NO_MLWRAP'] = '1'
        try:
            o = texts(mleader(3, 40.0))[0][8]; self.assertEqual(o['hj'], 0); self.assertNotIn('w', o)
        finally: del os.environ['DWG_NO_MLWRAP']


if __name__ == '__main__':
    unittest.main()

"""MTEXT text frame (background flag bit 16) is drawn as an outline around the text extents; with fill bits (1/2) the fill is kept.
AC1032_57263838b1 L2: notes boxed in the AutoCAD plot, unboxed in the viewer."""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dwgballet.flat import Flattener
from dwgscene import Mat


class Stub(Flattener):
    def __init__(self): pass
    def style_of(self, e): return None


def mtext(bgf):
    return {'kind': 'MTEXT', 'handle': 1, 'ins': (10.0, 10.0, 0.0), 'xdir': (1.0, 0.0, 0.0), 'attachment': 1, 'width': 50.0, 'text_height': 2.5,
            'text': 'NOTE', 'ext_w': 20.0, 'ext_h': 4.0, 'bgflags': bgf, 'bg_scale': 1.3, 'bg_color': (0, None, 0), 'eed': []}


def rows(bgf):
    out = []
    Stub()._mtext(mtext(bgf), Mat(), '0', (7, None, None), out)
    return [r[0] for r in out]


class MtextFrameTests(unittest.TestCase):
    def test_frame_only(self):
        self.assertEqual(rows(16), ['l', 't'])

    def test_frame_and_fill(self):
        self.assertEqual(rows(19), ['h', 'l', 't'])

    def test_fill_only_and_plain(self):
        self.assertEqual(rows(3), ['h', 't']); self.assertEqual(rows(0), ['t'])


if __name__ == '__main__':
    unittest.main()

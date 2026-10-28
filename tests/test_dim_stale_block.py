"""A dimension whose stored graphics block lies far from its definition points (Revit exports: *D geometry at the world position of the final INSERT, 5e8 away)
is moved onto the definition points, like AutoCAD's regenerated dimension; a normal dimension block is left alone."""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dwgballet.flat import Flattener


class Stub(Flattener):
    def __init__(self, rows): self._rows = rows
    def flatten(self, *a, **k): return list(self._rows)


def dim(**kw):
    e = {'handle': 1, 'kind': 'DIM_LINEAR', 'pt13': (1000.0, 0.0, 0.0), 'pt14': (3000.0, 0.0, 0.0), 'text_mid': (2000.0, 300.0)}
    e.update(kw); return e


class DimStaleTests(unittest.TestCase):
    def test_far_block_is_moved(self):
        far = [('l', 1, 7, 0.25, 0, [5.18e8, 1.77e8, 5.18e8 + 2000, 1.77e8], 0)]
        sh = Stub(far)._dim_stale_shift(dim(), 'D1', 0)
        self.assertIsNotNone(sh)
        self.assertAlmostEqual((far[0][5][0] + far[0][5][2]) / 2 + sh[0], 2000, delta=1)

    def test_near_block_unchanged(self):
        near = [('l', 1, 7, 0.25, 0, [1000, 100, 3000, 100], 0)]
        self.assertIsNone(Stub(near)._dim_stale_shift(dim(), 'D2', 0))


if __name__ == '__main__':
    unittest.main()

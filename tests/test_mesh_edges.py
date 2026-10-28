"""Plan-view edges of polyface meshes (hidden edges via negative indices, out-of-range indices ignored) and M x N polygon mesh grid lines (open / closed)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dwgballet.flat import mesh_grid_lines, pface_edges


class PfaceTests(unittest.TestCase):
    PV = [(0, 0), (1, 0), (1, 1), (0, 1)]

    def test_quad_face_has_four_edges(self):
        e = pface_edges(self.PV, [{'idx': [1, 2, 3, 4]}])
        self.assertEqual(e, [[(0, 0), (1, 0)], [(1, 0), (1, 1)], [(1, 1), (0, 1)], [(0, 1), (0, 0)]])

    def test_negative_index_hides_the_edge_that_starts_there(self):
        e = pface_edges(self.PV, [{'idx': [1, -2, 3, 4]}])
        self.assertEqual(len(e), 3)
        self.assertNotIn([(1, 0), (1, 1)], e)

    def test_triangle_pads_with_zero_and_bad_indices_are_skipped(self):
        self.assertEqual(len(pface_edges(self.PV, [{'idx': [1, 2, 3, 0]}])), 3)
        self.assertEqual(pface_edges(self.PV, [{'idx': [1, 9, 3, 0]}]), [[(1, 1), (0, 0)]])    # only 3 -> 1 has both ends


class MeshTests(unittest.TestCase):
    G = [(i, j) for i in range(3) for j in range(4)]    # M=3 rows, N=4 columns

    def test_open_grid_line_counts(self):
        ls = mesh_grid_lines(self.G, 3, 4)
        self.assertEqual(len(ls), 3 + 4)
        self.assertEqual(ls[0], [(0, 0), (0, 1), (0, 2), (0, 3)])
        self.assertEqual(ls[3], [(0, 0), (1, 0), (2, 0)])

    def test_closed_directions_repeat_the_first_point(self):
        ls = mesh_grid_lines(self.G, 3, 4, m_closed=True, n_closed=True)
        self.assertEqual(ls[0][-1], ls[0][0]); self.assertEqual(len(ls[0]), 5)
        self.assertEqual(ls[3][-1], ls[3][0]); self.assertEqual(len(ls[3]), 4)


if __name__ == '__main__':
    unittest.main()

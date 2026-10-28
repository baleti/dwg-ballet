"""MULTILEADER with block content (balloon / tag): the block is placed by the context matrix and the attribute values (strings, paired with labels) are drawn,
a one-attribute tag centred on the block origin. AC1032_1602ec3f10 (120 leaders). Synthetic entity through the flattener with a recording flatten."""
import os, sys, types, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dwgballet.flat import Flattener
from dwgscene import Mat


class Stub(Flattener):
    def __init__(self, attdefs):
        self.by_owner = {7: attdefs}; self.calls = []
    def resolve(self, e, ctx): return '0', (7, None, None), -1, 'Continuous'
    def style_of(self, e): return None
    def dash(self, *a): return None
    def base_of(self, h): return (0.0, 0.0, 0.0)
    def flatten(self, name, mat, hide, ctx, dscale, depth, out): self.calls.append((name, mat))


def attdef(x, y):
    return {'kind': 'ATTDEF', 'handle': 9, 'ins': (x, y), 'align': (x, y), 'halign': 1, 'valign': 2, 'height': 2.0, 'text': 'REF', 'rot': 0.0, 'elev': 0.0, 'layer': '0'}


def leader(vals, labels):
    return {'kind': 'MULTILEADER', 'handle': 1, 'layer': '0', 'arrow_size': 0.0, 'leader_lines': [], 'strings': vals, 'block_handle': 7,
            'ctx': {'has_block': 1, 'bmat': [-50.0, 0, 0, 100.0, 0, 50.0, 0, 200.0, 0, 0, 50.0, 0, 0, 0, 0, 1]}, 'own': {'labels': labels}}


def run(e, attdefs):
    s = Stub(attdefs); out = []
    s._entity(e, Mat(), set(), types.SimpleNamespace(ltscale=1.0), 1.0, 0, out)
    return s, out


class MleaderBlockTests(unittest.TestCase):
    def test_block_placed_by_context_matrix(self):
        s, _ = run(leader([], []), [attdef(-2.29, -1.0)])
        name, m = s.calls[0]
        self.assertEqual(name, 7)
        self.assertEqual(m.apply(1.0, 1.0), (50.0, 250.0))

    def test_single_attribute_centred_on_origin(self):
        _, out = run(leader(['W3'], [(1, 0.0)]), [attdef(-2.29, -1.0)])
        t = [r for r in out if r[0] == 't'][0]
        self.assertEqual((t[3], t[4]), (100.0, 200.0)); self.assertEqual(t[7], 'W3'); self.assertEqual((t[8]['hj'], t[8]['vj']), (1, 2))

    def test_two_attributes_keep_their_positions(self):
        _, out = run(leader(['UF', '01'], [(1, 0.0), (2, 0.0)]), [attdef(0.0, 2.0), attdef(0.0, -2.0)])
        ts = [r for r in out if r[0] == 't']
        self.assertEqual([t[7] for t in ts], ['UF', '01']); self.assertNotEqual(ts[0][4], ts[1][4])

    def test_env_disables(self):
        os.environ['DWG_NO_MLBLOCK'] = '1'
        try: s, out = run(leader(['W3'], [(1, 0.0)]), [attdef(0.0, 0.0)])
        finally: del os.environ['DWG_NO_MLBLOCK']
        self.assertEqual(s.calls, []); self.assertEqual(out, [])


if __name__ == '__main__':
    unittest.main()

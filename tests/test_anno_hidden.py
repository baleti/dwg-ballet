"""Annotative objects (dimensions, leaders, hatches, blocks) are shown by AutoCAD only at their annotation scales: hidden in Model space when the current scale (CANNOSCALE) is not in the list.
Logic test with a stubbed scale list (the scale list itself is read from the object's context data; checked against the real drawings AC1027_46894df5d1 and AC1024_2196c910ba: Model extents equal AutoCAD's)."""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dwgballet.flat import Flattener


class Stub(Flattener):
    def __init__(self, scales, cur): self._sc = scales; self.anno_cur = cur
    def _anno_scales(self, e): return self._sc


ANNO = [(1001, b'AcadAnnotative'), (1000, b'AnnotativeData')]


def ent(kind='DIM_LINEAR'): return {'kind': kind, 'handle': 1, 'eed': ANNO}


class AnnoHiddenTests(unittest.TestCase):
    def test_hidden_when_scale_missing(self):
        self.assertTrue(Stub({0.01, 0.02}, 1.0)._anno_hidden(ent()))

    def test_visible_when_scale_listed(self):
        self.assertFalse(Stub({0.01, 1.0}, 1.0)._anno_hidden(ent()))

    def test_plain_object_and_text_untouched(self):
        self.assertFalse(Stub({0.01}, 1.0)._anno_hidden({'kind': 'LINE', 'handle': 1, 'eed': []}))
        self.assertFalse(Stub({0.01}, 1.0)._anno_hidden(ent('MTEXT')))

    def test_unknown_scale_list_keeps_object(self):
        self.assertFalse(Stub(None, 1.0)._anno_hidden(ent()))


if __name__ == '__main__':
    unittest.main()

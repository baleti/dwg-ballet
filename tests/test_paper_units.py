"""PlotPaperUnits = inches: the layout's paper-space coordinates are inches while the stored paper size is mm
(AC1027_376d62a5ee L1: A4 sheet drawn as 297 x 210 units around content that spans 11.4 x 8.0)."""
import os, sys, unittest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


class PaperUnitsTests(unittest.TestCase):
    def setUp(self):
        try:
            from dwgballet.build import Doc
        except ImportError as e:
            self.skipTest(str(e))
        self.paper = Doc.paper

    def test_inches_convert(self):
        w, h = self.paper({'paper': (210.0, 297.0), 'paper_units': 0, 'rotation': 1})
        self.assertAlmostEqual(w, 297 / 25.4, 3); self.assertAlmostEqual(h, 210 / 25.4, 3)

    def test_mm_unchanged(self):
        self.assertEqual(self.paper({'paper': (210.0, 297.0), 'paper_units': 1, 'rotation': 0}), (210.0, 297.0))

    def test_env_disables(self):
        os.environ['DWG_NO_INCHPAPER'] = '1'
        try: self.assertEqual(self.paper({'paper': (210.0, 297.0), 'paper_units': 0, 'rotation': 0}), (210.0, 297.0))
        finally: del os.environ['DWG_NO_INCHPAPER']


if __name__ == '__main__':
    unittest.main()

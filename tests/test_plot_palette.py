"""Plot preview uses the object-colour palette AutoCAD actually plots (measured from a synthetic 255-solid chart plotted by AutoCAD 2026 to PDF): web/app.js PLOT_ACI must equal tests/data/aci_plot_palette.json."""
import json, os, re, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PlotPaletteTests(unittest.TestCase):
    def test_palette_matches_measurement(self):
        pal = json.load(open(os.path.join(HERE, 'tests', 'data', 'aci_plot_palette.json')))
        js = open(os.path.join(HERE, 'web', 'app.js')).read()
        flat = [int(x) for x in re.search(r'const PLOT_ACI = \[([\d,]+)\]', js).group(1).split(',')]
        self.assertEqual(len(flat), 248 * 3)
        for i in range(8, 256):
            self.assertEqual(flat[(i - 8) * 3:(i - 8) * 3 + 3], pal[str(i)], i)
        self.assertEqual(pal['9'], [220, 220, 220]); self.assertEqual(pal['8'], [128, 128, 128])


if __name__ == '__main__':
    unittest.main()

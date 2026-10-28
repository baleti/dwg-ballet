import os, tempfile, unittest
os.environ['DWG_BALLET_JOURNAL'] = tempfile.mkdtemp()
from dwgballet import journal as J


class T(unittest.TestCase):
    def test_append_read_pop_clear_and_torn_line(self):
        p = '/x/a.dwg'; self.assertEqual(J.read(p), [])
        J.append(p, 'layer off a*'); J.append(p, 'layer freeze b'); self.assertEqual(J.read(p), ['layer off a*', 'layer freeze b'])
        J.pop(p); self.assertEqual(J.read(p), ['layer off a*'])
        open(J._file(p), 'a').write('{"t": 1, "cmd": "tor')                       # crash in the middle of a write
        self.assertEqual(J.read(p), ['layer off a*'])
        self.assertEqual(J.read('/x/other.dwg'), []); J.clear(p); self.assertEqual(J.read(p), [])


if __name__ == '__main__': unittest.main()

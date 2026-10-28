import os, tempfile, unittest
f = os.path.join(tempfile.mkdtemp(), 'aliases.pgp'); os.environ['DWG_BALLET_ALIASES'] = f
from dwgballet import aliases


class T(unittest.TestCase):
    def test_default_created_and_parsed(self):
        a = aliases.load(); self.assertTrue(os.path.exists(f))
        self.assertEqual(a['ze'], 'zoom e'); self.assertEqual(a['liso'], 'layer isolate')

    def test_user_edit_and_comments(self):
        open(f, 'w').write('; mine\nXX, *LAYER OFF   ; trailing\nbad line\nYY, NOSTAR\n')
        self.assertEqual(aliases.load(), {'xx': 'layer off'})


if __name__ == '__main__': unittest.main()

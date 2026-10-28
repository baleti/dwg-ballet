import os, tempfile, unittest
from dwgballet import savegate as S


class SaveGateRules(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.src = os.path.join(self.d, 'a.dwg')
        open(self.src, 'wb').write(b'AC1009' + b'\0' * 200)

    def test_refusals(self):
        with self.assertRaises(S.SaveError): S.save_as(self.src, os.path.join(self.d, 'b.txt'), {})            # extension
        with self.assertRaises(S.SaveError): S.save_as(self.src, self.src, {})                                 # the source itself
        ex = os.path.join(self.d, 'c.dwg'); open(ex, 'w').write('x')
        with self.assertRaises(S.SaveError): S.save_as(self.src, ex, {})                                       # existing file
        self.assertEqual(open(ex).read(), 'x')
        with self.assertRaises(S.SaveError): S.save_as(self.src, os.path.join(self.d, 'nodir', 'd.dwg'), {})  # folder missing

    def test_unsupported_version_and_changed_source(self):
        with self.assertRaises(S.SaveError) as c: S.save_as(self.src, os.path.join(self.d, 'e.dwg'), {})
        self.assertIn('AC1009', str(c.exception))
        fp = S.fingerprint(self.src); open(self.src, 'ab').write(b'1')
        with self.assertRaises(S.SaveError) as c: S.save_as(self.src, os.path.join(self.d, 'f.dwg'), {}, fp)
        self.assertIn('changed', str(c.exception))
        self.assertEqual([f for f in os.listdir(self.d) if f != 'a.dwg'], [])                                  # nothing left behind

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'set DWG_BALLET_TEST_DWG to a writable-version drawing for the verified round trip')
    def test_verified_roundtrip(self):
        src = os.environ['DWG_BALLET_TEST_DWG']; dst = os.path.join(self.d, 'out.dwg')
        import dwgdoc; name = next(iter(dwgdoc.Doc(open(src, 'rb').read()).layers()))
        r = S.save_as(src, dst, {name: {'off': True}}, S.fingerprint(src))
        self.assertTrue(os.path.exists(dst)); self.assertEqual(r['layers_changed'], 1)
        # overwrite of a copy: config flag on, backup made, file replaced, backup restorable
        cp = os.path.join(self.d, 'copy.dwg'); open(cp, 'wb').write(open(src, 'rb').read())
        S.CONFIG = os.path.join(self.d, 'cfg.json'); S.BACKUPS = os.path.join(self.d, 'bak'); open(S.CONFIG, 'w').write('{"allow_overwrite": true}')
        r2 = S.save_over(cp, {name: {'off': True}}, S.fingerprint(cp))
        self.assertTrue(os.path.exists(r2['backup'])); self.assertNotEqual(open(cp, 'rb').read(), open(src, 'rb').read())
        S.restore(r2['backup'], cp); self.assertEqual(open(cp, 'rb').read(), open(src, 'rb').read())

    def test_overwrite_off_by_default_and_backup_roundtrip(self):
        os.environ['DWG_BALLET_CONFIG'] = os.path.join(self.d, 'nocfg.json'); S.CONFIG = os.environ['DWG_BALLET_CONFIG']; S.BACKUPS = os.path.join(self.d, 'bak')
        with self.assertRaises(S.SaveError) as c: S.save_over(self.src, {})
        self.assertIn('disabled', str(c.exception))
        b = S.backup(self.src); self.assertEqual(open(b, 'rb').read(), open(self.src, 'rb').read())
        open(self.src, 'wb').write(b'changed'); S.restore(b, self.src); self.assertEqual(open(self.src, 'rb').read()[:6], b'AC1009')

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'needs DWG_BALLET_TEST_DWG')
    def test_disk_full_and_rename_failure_leave_nothing(self):
        import unittest.mock as M
        src = os.environ['DWG_BALLET_TEST_DWG']; before = open(src, 'rb').read(); dst = os.path.join(self.d, 'full.dwg')
        with M.patch('os.fsync', side_effect=OSError(28, 'No space left on device')):
            with self.assertRaises(OSError): S.save_as(src, dst, {})
        self.assertEqual(os.listdir(self.d), ['a.dwg'])                      # no target, no temp file
        with M.patch('os.rename', side_effect=OSError(5, 'I/O error')):
            with self.assertRaises(OSError): S.save_as(src, dst, {})
        self.assertEqual(os.listdir(self.d), ['a.dwg']); self.assertEqual(open(src, 'rb').read(), before)

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'needs DWG_BALLET_TEST_DWG')
    def test_kill_mid_save_never_leaves_a_partial_target(self):
        import signal, subprocess, sys, time
        src = os.environ['DWG_BALLET_TEST_DWG']; before = open(src, 'rb').read(); dst = os.path.join(self.d, 'killed.dwg')
        code = 'import sys,time,os; sys.path.insert(0, %r); from dwgballet import savegate as S; real = os.fsync\ndef slow(fd): time.sleep(30); real(fd)\nos.fsync = slow\nS.save_as(%r, %r, {})' % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), src, dst)
        p = subprocess.Popen([sys.executable, '-c', code])
        for _ in range(600):                                                 # wait until the temp file exists (write finished, fsync pending)
            if any(f.startswith('.killed.dwg.tmp') for f in os.listdir(self.d)): break
            time.sleep(0.1)
        p.send_signal(signal.SIGKILL); p.wait()
        self.assertFalse(os.path.exists(dst)); self.assertEqual(open(src, 'rb').read(), before)    # the only leftover is the temp file

    def test_lock_live_refuses_dead_taken_over(self):
        dst = os.path.join(self.d, 'l.dwg'); lk = os.path.join(self.d, '.l.dwg.lock')
        import subprocess, sys
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            open(lk, 'w').write(str(p.pid))
            with self.assertRaises(S.SaveError) as c: S.save_as(self.src, dst, {})
            self.assertIn('another save', str(c.exception))
        finally: p.kill(); p.wait()
        with self.assertRaises(S.SaveError) as c: S.save_as(self.src, dst, {})       # dead pid: lock taken over, then the normal refusal (AC1009)
        self.assertIn('AC1009', str(c.exception)); self.assertFalse(os.path.exists(lk))

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'needs DWG_BALLET_TEST_DWG')
    def test_erase_removes_exactly_the_requested_entities(self):
        import dwgmodel
        src = os.environ['DWG_BALLET_TEST_DWG']; buf = open(src, 'rb').read()
        hs = [e['handle'] for b, e in dwgmodel.Model(buf).entities() if e['kind'] == 'LINE' and b and b.lower() == '*model_space'][:3]
        if len(hs) < 3: self.skipTest('sample has fewer than 3 model-space lines')
        dst = os.path.join(self.d, 'er.dwg'); r = S.save_as(src, dst, {}, erase=hs)
        self.assertEqual(r['erased'], 3)
        after = {e['handle'] for b, e in dwgmodel.Model(open(dst, 'rb').read()).entities()}
        before = {e['handle'] for b, e in dwgmodel.Model(buf).entities()}
        self.assertEqual(before - after, set(hs)); self.assertEqual(after - before, set())
        with self.assertRaises(S.SaveError): S.save_as(src, os.path.join(self.d, 'er2.dwg'), {}, erase=[0x7FFFFFF0])

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'needs DWG_BALLET_TEST_DWG')
    def test_move_translates_exactly_the_requested_entities(self):
        import dwgmodel
        src = os.environ['DWG_BALLET_TEST_DWG']; buf = open(src, 'rb').read()
        ents = {e['handle']: e for b, e in dwgmodel.Model(buf).entities()}
        hs = [h for h, e in ents.items() if e['kind'] == 'LINE'][:2]
        if len(hs) < 2: self.skipTest('sample has fewer than 2 lines')
        dst = os.path.join(self.d, 'mv.dwg'); r = S.save_as(src, dst, {}, move=[{'hs': hs, 'dx': 12.5, 'dy': -3.0}])
        self.assertEqual(r['moved'], 2)
        after = {e['handle']: e for b, e in dwgmodel.Model(open(dst, 'rb').read()).entities()}
        for h in hs:
            self.assertAlmostEqual(after[h]['p1'][0] - ents[h]['p1'][0], 12.5, 6); self.assertAlmostEqual(after[h]['p1'][1] - ents[h]['p1'][1], -3.0, 6)
        self.assertEqual([h for h in ents if h not in hs and after[h] != ents[h] and not ({k for k in ents[h] if ents[h][k] != after[h].get(k)} <= {'prev', 'next'})], [])

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'needs DWG_BALLET_TEST_DWG')
    def test_move_of_inserts_carries_their_attributes(self):
        import dwgmodel
        src = os.environ['DWG_BALLET_TEST_DWG']; ents = {e['handle']: e for b, e in dwgmodel.Model(open(src, 'rb').read()).entities()}
        owners = {e.get('owner') for e in ents.values() if e['kind'] == 'ATTRIB'}
        hs = [h for h, e in ents.items() if e['kind'] == 'INSERT' and h in owners][:2]
        if not hs: self.skipTest('sample has no INSERT with attributes')
        r = S.save_as(src, os.path.join(self.d, 'att.dwg'), {}, move=[{'hs': hs, 'dx': 5, 'dy': 5}])
        self.assertEqual(r['moved'], len(hs)); self.assertGreaterEqual(r['moved_with'], len(hs))

    @unittest.skipUnless(os.environ.get('DWG_BALLET_TEST_DWG'), 'needs DWG_BALLET_TEST_DWG')
    def test_copy_adds_translated_duplicates_and_changes_nothing_else(self):
        import dwgmodel
        src = os.environ['DWG_BALLET_TEST_DWG']; buf = open(src, 'rb').read(); ents = {e['handle']: e for b, e in dwgmodel.Model(buf).entities()}
        hs = [h for h, e in ents.items() if e['kind'] == 'LINE'][:2]
        if len(hs) < 2: self.skipTest('sample has fewer than 2 lines')
        r = S.save_as(src, os.path.join(self.d, 'cp.dwg'), {}, move=[{'t': 'copy', 'hs': hs, 'dx': 100.0, 'dy': 50.0}])
        self.assertEqual(r['copied'], 2); self.assertEqual(r['moved'], 0)
        after = {e['handle']: e for b, e in dwgmodel.Model(open(os.path.join(self.d, 'cp.dwg'), 'rb').read()).entities()}
        new = [h for h in after if h not in ents]; self.assertEqual(len(new), 2)
        for h in hs: self.assertEqual(after[h]['p1'], ents[h]['p1'])                                     # originals untouched
        got = sorted((round(after[h]['p1'][0], 6), round(after[h]['p1'][1], 6)) for h in new)
        want = sorted((round(ents[h]['p1'][0] + 100.0, 6), round(ents[h]['p1'][1] + 50.0, 6)) for h in hs)
        self.assertEqual(got, want)


if __name__ == '__main__': unittest.main()

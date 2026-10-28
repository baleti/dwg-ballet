"""tests/browser/check_cmdline.py URL: drives the dwg-ballet command line with Playwright against a running server (dwg-ballet FILE --no-browser --port P).
Not part of the pytest run (needs a browser). Exits 1 on any failed check."""
import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); pg = b.new_page(viewport={'width': 1300, 'height': 800}); errs = []; bad = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5)
    def cmd(t): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(0.7); return pg.inner_text('#cmdOut')
    def check(name, ok):
        print(('ok   ' if ok else 'FAIL ') + name); ok or bad.append(name)
    n = pg.evaluate('meta.layers.length'); first = pg.evaluate('meta.layers[0].n'); on = lambda: pg.evaluate('lyOn.filter(x=>x).length')
    cmd('layer off *'); check('layer off *', on() == 0); cmd('layers allon'); check('layers allon', on() == n)
    cmd('liso ' + first); check('alias liso', on() == 1); cmd('lon *'); check('alias lon', on() == n)
    check('select kind', 'selected' in cmd('select //kind *text')); check('select none', cmd('select //layer ZZZ*').startswith('0 '))
    check('bad key', 'unknown key' in cmd('select //foo x')); check('unknown command', 'unknown command' in cmd('bogus'))
    check('model', cmd('model') == 'model space'); check('layout list', 'LAYOUT' in cmd('layout 99'))
    pg.focus('#cv'); pg.keyboard.press(':'); check('colon focus', pg.evaluate('document.activeElement.id') == 'cmdIn')
    check('no page errors', not errs); b.close(); sys.exit(1 if bad else 0)

import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); pg = b.new_page(viewport={'width': 1300, 'height': 800}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5)
    def cmd(t, w=1.0): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(w); return pg.inner_text('#cmdOut')
    cmd('model', 5); neg = lambda: pg.evaluate('lay.prims.concat(lay.mprims).filter(p => p[p.length-1] < 0).length')
    cmd('select //kind text //text *1*'); cmd('copy 3000 0'); a = neg(); print('copy rows', a)
    cmd('layout 1', 5); cmd('model', 5); b2 = neg(); print('after round trip', b2, 'ok' if a == b2 and a > 0 else 'FAIL')
    print('errors', errs); b.close()

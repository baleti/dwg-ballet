import sys, time
from playwright.sync_api import sync_playwright
out = sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); pg = b.new_page(viewport={'width': 1300, 'height': 800}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5)
    def cmd(t, w=1.0): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(w); return pg.inner_text('#cmdOut')
    rows = lambda: pg.evaluate('lay.prims.length + lay.mprims.length')
    n0 = rows(); print(cmd('select //kind text //text *1*')); print(cmd('copy 3000 0'), rows() - n0)
    print(cmd('undo'), rows() - n0); print(cmd('select //kind text //text *1*')); print(cmd('copy 3000 0'), rows() - n0)
    print(cmd('select //kind text //text *1*')); print(cmd('move 1 1')); cmd('layout 1', 4); cmd('model', 4); print('rows after layout round trip', rows() - n0)
    print(cmd('saveas ' + out, 40)); print('errors', errs); b.close()

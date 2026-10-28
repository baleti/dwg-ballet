import sys, time
from playwright.sync_api import sync_playwright
out = sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); pg = b.new_page(viewport={'width': 1300, 'height': 800}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5)
    def cmd(t, w=1.0): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(w); return pg.inner_text('#cmdOut')
    x0 = lambda: pg.evaluate("lay.prims.concat(lay.mprims).filter(p=>p[0]==='t').slice(0,40).map(p=>p[3]).reduce((a,b)=>a+b,0)")
    print(cmd('move 5 5')); print(cmd('select //kind text //text *1*')); a = x0(); print(cmd('move 1000 500'), x0() - a)
    print(cmd('undo'), x0() - a); print(cmd('select //kind text //text *1*')); print(cmd('move 1000 500'), x0() - a); n = pg.evaluate('moves[0].hs.length'); print('moved', n)
    print(cmd('layout 1', 4)); print(cmd('model', 4)); print('after layout switch', x0() - a)
    print(cmd('saveas ' + out, 40)); print('errors', errs); b.close()

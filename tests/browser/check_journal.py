import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); errs = []; bad = []
    def page():
        pg = b.new_page(viewport={'width': 1300, 'height': 800}); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5); return pg
    def cmd(pg, t, w=0.8): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(w); return pg.inner_text('#cmdOut')
    def check(n, ok): print(('ok   ' if ok else 'FAIL ') + n); ok or bad.append(n)
    pg = page(); n = pg.evaluate('meta.layers.length'); on = lambda: pg.evaluate('lyOn.filter(x=>x).length')
    cmd(pg, 'layer off a*'); off = n - on(); check('layer off a*', off > 0)
    cmd(pg, 'layer freeze 0-*'); check('undo 1', 'undone' in cmd(pg, 'undo') and n - on() == off)
    check('undo 2', 'undone' in cmd(pg, 'undo') and on() == n); check('undo empty', 'nothing' in cmd(pg, 'undo'))
    cmd(pg, 'layer off a*'); pg.close()                          # "crash": page closed without saving
    pg = page(); check('fresh page all on', on() == n)
    check('recover', 'replayed 1' in cmd(pg, 'recover') and n - on() == off)
    cmd(pg, 'undo'); check('undo after recover', on() == n)
    check('no page errors', not errs); b.close(); sys.exit(1 if bad else 0)

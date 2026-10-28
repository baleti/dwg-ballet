import sys, time
from playwright.sync_api import sync_playwright
out = sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); pg = b.new_page(viewport={'width': 1300, 'height': 800}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5)
    def cmd(t, w=1.0): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(w); return pg.inner_text('#cmdOut')
    print(cmd('erase'))                                  # nothing selected
    print(cmd('select //kind dim')); print(cmd('erase')); print('erased handles', pg.evaluate('erased.size'), 'selected', pg.inner_text('#sel'))
    print(cmd('undo')); print('after undo', pg.evaluate('erased.size')); print(cmd('select //kind text //text *1*')); print(cmd('erase')); n = pg.evaluate('erased.size'); print('erased', n)
    print(cmd('saveas ' + out, 40)); print('errors', errs); print('N', n); b.close()

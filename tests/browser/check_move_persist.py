import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu']); pg = b.new_page(viewport={'width': 1300, 'height': 800}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function('typeof meta !== "undefined" && meta && lay', timeout=90000); time.sleep(1.5)
    def cmd(t, w=1.0): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(w); return pg.inner_text('#cmdOut')
    cmd('model', 5)
    sig = "(() => { const p = lay.prims.concat(lay.mprims).filter(p => p[0] === 't').sort((a, b) => a[p_len(a)] - b[p_len(b)])[0]; return null })()"
    js = "(() => { const t = lay.prims.concat(lay.mprims).filter(p => p[0]==='t' && String(p[7]).includes('1')); t.sort((a,b)=>topOf(a)-topOf(b)); return t.slice(0,5).map(p=>[topOf(p), p[3]]); })()"
    base = pg.evaluate(js); cmd('select //kind text //text *1*'); print(cmd('move 777 0')); moved = pg.evaluate(js)
    print('moved by', [round(m[1]-a[1], 3) for a, m in zip(base, moved)])
    cmd('layout 1', 5); cmd('model', 5); again = pg.evaluate(js)
    print('after layout round trip, still moved by', [round(m[1]-a[1], 3) for a, m in zip(base, again)])
    print('errors', errs); b.close()

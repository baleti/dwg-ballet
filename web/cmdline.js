// command line: type a command (aliases as in CAD programs), Enter runs it, ':' or '/' focuses the line, Esc leaves it.
// Commands: ZOOM [E|EXTENTS|ALL] (Z, ZE), PAN (P), MODEL (MS), LAYOUT <name|n> (PS), LAYER ON|OFF|FREEZE|THAW|LOCK|UNLOCK|ISOLATE <pattern> (LA), LAYERS ALLON,
// SELECT //layer p //kind k //text t (picker DSL syntax), FIND <text> (F), MEASURE (DI, MEA), DARK / LIGHT, OPEN <path> (opens another drawing), HELP (?).
let CMD_ALIASES = {z: 'zoom', ze: 'zoom e', p: 'pan', ms: 'model', ps: 'layout', la: 'layer', layers: 'layer', f: 'find', di: 'measure', mea: 'measure', '?': 'help', o: 'open'};
let moves = [];      // {hs, dx, dy} moves of this session, re-applied when a layout is (re)loaded and sent to SAVEAS / SAVE!
function shiftRows(rows, hset, dx, dy) {
  for (const p of rows) {
    if (!hset.has(p[p.length - 1])) continue;
    if (p[0] === 'l') { const f = p[5]; for (let i = 0; i < f.length; i += 2) { f[i] += dx; f[i + 1] += dy; } }
    else if (p[0] === 'h') { for (const f of p[3]) for (let i = 0; i < f.length; i += 2) { f[i] += dx; f[i + 1] += dy; } }
    else { p[3] += dx; p[4] += dy; if (p[0] === 't' && p[8] && p[8].ac) for (const a of p[8].ac) { a[1] += dx; a[2] += dy; } }      // annotative text: the per-scale positions move too
  }
}
let copySeq = 0;
function cloneRows(rows, m) {       // copies of the rows of the source objects, shifted, under the pseudo handle (negative) of the copy
  const add = [];
  for (const p of rows) { const k = m.ids[p[p.length - 1]]; if (k === undefined) continue; const q = structuredClone(p); q[q.length - 1] = k; add.push(q); }
  const sub = new Set(add.map(q => q[q.length - 1])); shiftRows(add, sub, m.dx, m.dy); for (const q of add) rows.push(q);
}
function applyOp(layObj, m) {
  if (m.t === 'copy') { cloneRows(layObj.prims, m); cloneRows(layObj.mprims, m); }
  else { const hs = new Set(m.hs); shiftRows(layObj.prims, hs, m.dx, m.dy); shiftRows(layObj.mprims, hs, m.dx, m.dy); }
}
function undoOp(layObj, m) {
  if (m.t === 'copy') { const ids = new Set(Object.values(m.ids)); layObj.prims = layObj.prims.filter(p => !ids.has(p[p.length - 1])); layObj.mprims = layObj.mprims.filter(p => !ids.has(p[p.length - 1])); }
  else { const hs = new Set(m.hs); shiftRows(layObj.prims, hs, -m.dx, -m.dy); shiftRows(layObj.mprims, hs, -m.dx, -m.dy); }
}
function applyMoves(layObj) { for (const m of moves) applyOp(layObj, m); }
let erased = new Set();      // handles erased in this session (hidden at once, removed from the file by SAVEAS / SAVE!)
const cmdLine = {
  hist: [], hi: 0,
  say(t, err) { const o = $('cmdOut'); o.textContent = t; o.style.color = err ? 'var(--b-error)' : ''; },
  rx(p) { return new RegExp('^' + p.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$', 'i'); },
  snaps: [],       // undo stack: layer states before each state-changing command
  JOURNALED: new Set(['layer', 'layers', 'erase', 'move', 'copy']),
  snap() { return {on: [...lyOn], frz: [...lyFrz], lock: [...lyLock], er: new Set(erased), mv: moves.length}; },
  post(o) { return fetch('/api/journal', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(o)}).catch(() => {}); },
  async run(line, replay) {
    line = line.trim(); if (!line) return;
    const first = line.split(/\s+/)[0].toLowerCase(), base = (CMD_ALIASES[first] || first).split(' ')[0];
    if (this.JOURNALED.has(base) && !replay) { this.snaps.push(this.snap()); this.post({cmd: line}); }
    if (this.JOURNALED.has(base) && replay) this.snaps.push(this.snap());
    let [c, ...rest] = line.split(/\s+/); c = c.toLowerCase();
    let a = rest.join(' ');
    if (CMD_ALIASES[c]) { const x = CMD_ALIASES[c].split(' '); c = x[0]; a = (x.slice(1).join(' ') + ' ' + a).trim(); }
    const s = this;
    switch (c) {
      case 'zoom': if (!a || /^(e|extents|all|a)$/i.test(a)) { fit(); s.say('zoom extents'); } else s.say('ZOOM: only E / EXTENTS / ALL so far', true); break;
      case 'pan': $('handBtn').click(); s.say('pan'); break;
      case 'model': { const i = meta.layouts.findIndex(l => !l.ps); if (i < 0) return s.say('no model space', true); await openLayout(i); s.say('model space'); break; }
      case 'layout': {
        const L = meta.layouts; let i = /^\d+$/.test(a) ? Number(a) : L.findIndex(l => l.name.toLowerCase() === a.toLowerCase());
        if (i < 0 || i >= L.length) i = L.findIndex(l => l.name.toLowerCase().includes(a.toLowerCase()));
        if (!a || i < 0 || i >= L.length) return s.say('LAYOUT <name|number>: ' + L.map((l, j) => j + '=' + l.name).join(', '), true);
        await openLayout(i); s.say('layout ' + L[i].name); break; }
      case 'layer': {
        const m = a.match(/^(on|off|freeze|frz|thaw|lock|unlock|isolate|iso|allon)\s*(.*)$/i);
        if (!m) return s.say('LAYER ON|OFF|FREEZE|THAW|LOCK|UNLOCK|ISOLATE <name or pattern, * and ?>', true);
        const op = m[1].toLowerCase();
        if (op === 'allon') { meta.layers.forEach((l, i) => { lyOn[i] = true; lyFrz[i] = false; }); rebuildAfterLayerChange(); return s.say('all layers on'); }
        const re = s.rx(m[2].trim() || '*'), idx = []; meta.layers.forEach((l, i) => { if (re.test(l.n)) idx.push(i); });
        if (!idx.length) return s.say('no layer matches ' + m[2], true);
        if (op === 'isolate' || op === 'iso') meta.layers.forEach((l, i) => { lyOn[i] = idx.includes(i); if (idx.includes(i)) lyFrz[i] = false; });
        else for (const i of idx) { if (op === 'on') lyOn[i] = true; else if (op === 'off') lyOn[i] = false; else if (op === 'freeze' || op === 'frz') lyFrz[i] = true; else if (op === 'thaw') lyFrz[i] = false; else if (op === 'lock') lyLock[i] = true; else lyLock[i] = false; }
        rebuildAfterLayerChange(); s.say(op + ': ' + idx.length + ' layer' + (idx.length > 1 ? 's' : '')); break; }
      case 'find': $('findBox').value = a; $('findBox').dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'})); s.say('find ' + a); break;
      case 'measure': $('measBtn').click(); s.say('measure'); break;
      case 'dark': case 'light': { const d = c === 'dark'; $('dark').checked = d; $('dark').dispatchEvent(new Event('change')); s.say('model background ' + c); break; }
      case 'open': {
        if (!a) return s.say('OPEN <path to a .dwg>', true);
        const j = await (await fetch('/api/open', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path: a.replace(/^["']|["']$/g, '')})})).json();
        if (j.error) return s.say(j.error, true); location.href = '/'; break; }
      case 'select': {
        // SELECT //layer A-WALL* //kind text //text *door*  : the picker DSL surface syntax (//key value, ! negates, * and ? wildcards); all terms must hold
        const terms = [...a.matchAll(/\/\/(\w+)\s+([^\/]*?)(?=\s*\/\/|\s*$)/g)].map(m => ({k: m[1].toLowerCase(), neg: m[2].startsWith('!'), re: s.rx(m[2].replace(/^!/, '').trim())}));
        if (!terms.length) return s.say('SELECT //layer pattern //kind name //text pattern   (! negates, * ?)', true);
        const bad = terms.find(t => !['layer', 'kind', 'text'].includes(t.k)); if (bad) return s.say('SELECT: unknown key //' + bad.k + ' (layer, kind = block, hatch, curve, text, dim ...; text)', true);
        const hit = new Set();
        const test = p => { const ly = p[1] >= 0 ? meta.layers[p[1]].n : '0', kd = (lay.kinds && lay.kinds[topOf(p)]) || ({t: 'text', h: 'hatch', l: 'line'}[p[0]] || p[0]), tx = p[0] === 't' ? plainText(String(p[7])) : null;
          return terms.every(t => t.k === 'text' ? tx !== null && t.re.test(tx) !== t.neg : (t.k === 'layer' ? t.re.test(ly) : t.re.test(kd)) !== t.neg); };       // //text only applies to text rows (MTEXT codes stripped)
        for (const p of lay.prims) if (visibleRow(p, null) && test(p)) hit.add(topOf(p));
        for (const vp of lay.vps) for (const p of lay.mprims) if (visibleRow(p, vp.fzs) && test(p)) hit.add(topOf(p));
        setSelection(hit, false); s.say(hit.size + ' object' + (hit.size === 1 ? '' : 's') + ' selected'); break; }
      case 'saveas': {
        // SAVEAS <new file>: writes a verified copy with the current layer states (On / Freeze / Lock); never overwrites, never touches the source file
        if (!a) return s.say('SAVEAS <new file name or path>.dwg (a bare name goes next to the source)', true);
        s.say('saving (writing and verifying)...');
        const layers = {}; meta.layers.forEach((l, i) => { layers[l.n] = {off: !lyOn[i], frozen: !!lyFrz[i], locked: !!lyLock[i]}; });
        const r = await fetch('/api/saveas', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path: a.replace(/^["']|["']$/g, ''), layers, erase: [...erased], move: moves})}), j = await r.json();
        if (j.error) return s.say(j.error, true);
        s.say('saved ' + j.path + ' (' + j.entities + ' entities verified unchanged, ' + j.layers_changed + ' layer(s) changed, ' + (j.erased || 0) + ' erased, ' + (j.moved || 0) + ' moved, ' + (j.copied || 0) + ' copied)'); break; }
      case 'save!': {
        // SAVE!: overwrites the open file after a verified backup (disabled unless allow_overwrite is set in ~/.config/dwg-ballet/config.json)
        const layers = {}; meta.layers.forEach((l, i) => { layers[l.n] = {off: !lyOn[i], frozen: !!lyFrz[i], locked: !!lyLock[i]}; });
        const j = await (await fetch('/api/save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({layers, erase: [...erased], move: moves})})).json();
        if (j.error) return s.say(j.error, true);
        s.say('saved over the original; backup ' + j.backup); break; }
      case 'erase': {
        // ERASE: the selected objects (or, when replaying the journal, the hex handles in the line); shown as gone at once, removed from the file on SAVEAS / SAVE!
        const hs = (a ? a.split(',').map(x => parseInt(x, 16)).filter(Number.isFinite) : [...S]).filter(h => h > 0);
        if (!hs.length) return s.say('select objects first (SELECT ... or click), then ERASE', true);
        if (!a) { const last = this.snaps[this.snaps.length - 1]; this.post({undo: true}); this.post({cmd: 'erase ' + hs.map(h => h.toString(16)).join(',')}); }
        hs.forEach(h => erased.add(h)); clearSelection(true); invalidate(); s.say('erased ' + hs.length + ' object' + (hs.length > 1 ? 's' : '') + ' (saved with SAVEAS)'); break; }
      case 'move': case 'copy': {
        // MOVE dx dy / COPY dx dy: translate (or duplicate and translate) the selected objects by (dx, dy) drawing units; shown at once, applied and verified by SAVEAS / SAVE!
        const m = a.match(/^(-?[\d.]+)[ ,]+(-?[\d.]+)(?:\s+([0-9a-fA-F,]+))?$/);
        if (!m) return s.say(c.toUpperCase() + ' dx dy   (drawing units; works on the selected objects)', true);
        let hs = m[3] ? m[3].split(',').map(x => parseInt(x, 16)) : [...S];
        const skipped = hs.filter(h => h < 0).length; hs = hs.filter(h => h > 0);
        if (!hs.length) return s.say(skipped ? 'copies cannot be moved or copied again before they are saved' : 'select objects first, then ' + c.toUpperCase() + ' dx dy', true);
        const dx = parseFloat(m[1]), dy = parseFloat(m[2]);
        if (!m[3]) { this.post({undo: true}); this.post({cmd: c + ' ' + dx + ' ' + dy + ' ' + hs.map(h => h.toString(16)).join(',')}); }
        const op = {t: c, hs, dx, dy}; if (c === 'copy') { op.ids = {}; for (const h of hs) op.ids[h] = -(++copySeq); }
        applyOp(lay, op); moves.push(op);
        prepRows(lay.prims); prepRows(lay.mprims); rebuildSelItems(); invalidate(); s.say((c === 'copy' ? 'copied ' : 'moved ') + hs.length + ' object' + (hs.length > 1 ? 's' : '') + ' by ' + dx + ', ' + dy + ' (saved with SAVEAS)' + (skipped ? '; ' + skipped + ' unsaved copies skipped' : '')); break; }
      case 'undo': {
        const p = this.snaps.pop(); if (!p) return s.say('nothing to undo', true);
        p.on.forEach((v, i) => { lyOn[i] = v; lyFrz[i] = p.frz[i]; lyLock[i] = p.lock[i]; }); erased = p.er; while (moves.length > p.mv) undoOp(lay, moves.pop()); prepRows(lay.prims); prepRows(lay.mprims); clearSelection(true); rebuildAfterLayerChange(); this.post({undo: true}); s.say('undone (' + this.snaps.length + ' more)'); break; }
      case 'recover': {
        const cmds = await (await fetch('/api/journal')).json();
        if (!cmds.length) return s.say('journal is empty'); for (const l of cmds) await this.run(l, true); s.say('replayed ' + cmds.length + ' command(s) from the journal'); break; }
      case 'help': s.say('ZOOM E, PAN, MODEL, LAYOUT n, LAYER ON|OFF|FREEZE|THAW|LOCK|ISOLATE pattern, LAYERS ALLON, COPY dx dy, MOVE dx dy, ERASE, UNDO, RECOVER, SAVEAS file, FIND text, SELECT //layer p //kind k //text t, MEASURE, DARK, LIGHT, OPEN path'); break;
      default: s.say('unknown command: ' + c + ' (HELP lists them)', true);
    }
  },
  init() {
    const i = $('cmdIn');
    i.addEventListener('keydown', e => {
      e.stopPropagation();
      if (e.key === 'Enter') { const v = i.value; this.hist.push(v); this.hi = this.hist.length; i.value = ''; this.run(v).catch(x => this.say(String(x), true)); }
      else if (e.key === 'Escape') { i.value = ''; i.blur(); $('cv').focus(); }
      else if (e.key === 'ArrowUp' && this.hist.length) { this.hi = Math.max(0, this.hi - 1); i.value = this.hist[this.hi]; e.preventDefault(); }
      else if (e.key === 'ArrowDown') { this.hi = Math.min(this.hist.length, this.hi + 1); i.value = this.hist[this.hi] || ''; e.preventDefault(); }
    });
    document.addEventListener('keydown', e => { if ((e.key === ':' || e.key === '/') && !/input|select|textarea/i.test(document.activeElement.tagName) && !e.ctrlKey) { e.preventDefault(); i.focus(); } });
  }
};
fetch('/api/aliases').then(r => r.json()).then(a => { CMD_ALIASES = a; }).catch(() => {});      // ~/.config/dwg-ballet/aliases.pgp (acad.pgp style)
cmdLine.init();
try { new ResizeObserver(() => { if (typeof resize === 'function' && lay) { resize(); invalidate(); } }).observe($('cv')); } catch (_) {}      // keep the canvas bitmap in step with its box (layout changes after the first draw)

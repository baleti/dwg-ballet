"""gen_ballet_ui.py [CSS]: rewrite the dark :root tokens of ballet-ui.css from ~/.local/state/quickshell/scheme.json (the desktop's Material You scheme). Light tokens stay as shipped."""
import json, os, re, sys
css = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ballet-ui.css')
d = json.load(open(os.path.expanduser('~/.local/state/quickshell/scheme.json')))
m = {'--b-bg': d['background'], '--b-line': d['outlineVariant'], '--b-fg': d['onSurface'], '--b-fg2': d['outline'],
     '--b-accent': d['primary'], '--b-on-accent': d['onPrimary'], '--b-accent2': d['secondary'], '--b-error': d['error']}
s = open(css).read(); i = s.index(':root{'); j = s.index(';--b-canvas')
head = s[i:j]
for k, v in m.items(): head = re.sub(re.escape(k) + r':#[0-9a-fA-F]{6}', k + ':' + v, head)
open(css, 'w').write(s[:i] + head + s[j:]); print('tokens from scheme.json written')

"""Command aliases for the command line, ~/.config/dwg-ballet/aliases.pgp (acad.pgp style, user editable): `ALIAS, *COMMAND [arguments]` per line, `;` starts a comment.
Created with the defaults on first use; the file is never overwritten."""
import os
from . import plat

FILE = os.environ.get('DWG_BALLET_ALIASES') or os.path.join(plat.dirs.config_dir('dwg-ballet'), 'aliases.pgp')
DEFAULT = """; dwg-ballet command aliases: ALIAS, *COMMAND [arguments]   (edit freely; reload the page to apply)
Z,   *ZOOM
ZE,  *ZOOM E
P,   *PAN
MS,  *MODEL
PS,  *LAYOUT
LA,  *LAYER
LAYERS, *LAYER
F,   *FIND
DI,  *MEASURE
MEA, *MEASURE
O,   *OPEN
?,   *HELP
LOFF, *LAYER OFF
LON,  *LAYER ON
LISO, *LAYER ISOLATE
"""


def load():
    try:
        if not os.path.exists(FILE):
            os.makedirs(os.path.dirname(FILE), exist_ok=True); open(FILE, 'w').write(DEFAULT)
        text = open(FILE, encoding='utf-8', errors='replace').read()
    except OSError:
        text = DEFAULT
    out = {}
    for ln in text.splitlines():
        ln = ln.split(';', 1)[0].strip()
        if ',' not in ln: continue
        a, c = ln.split(',', 1); a, c = a.strip().lower(), c.strip()
        if a and c.startswith('*') and len(c) > 1: out[a] = c[1:].strip().lower()
    return out

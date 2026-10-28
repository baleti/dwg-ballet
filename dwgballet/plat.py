"""Cross-platform helpers (vendored rvtplat in _vendor/): browser launch, atomic replace with retry, per-user dirs."""
import os, sys
try: import rvtplat
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")); import rvtplat
from rvtplat import browser, fsio, dirs, proc, mem, paths

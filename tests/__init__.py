"""Unit tests for the DWG codecs."""

import os as _os, tempfile as _tf
_os.environ.setdefault('DWG_BALLET_RECENT', _os.path.join(_tf.mkdtemp(), 'recent.json'))      # tests must not touch the real recent-files list

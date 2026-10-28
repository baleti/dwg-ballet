"""Deprecated name: dwg-viewer is now dwg-ballet (package dwgballet). Importing dwgviewer gives dwgballet."""
import sys, warnings
import dwgballet
warnings.warn("dwgviewer is renamed dwgballet", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = dwgballet

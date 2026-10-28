"""Stage the dwg-ballet application files for the installers (no tests, corpus, caches, compiled Linux extensions).
usage: python packaging/stage.py OUT_DIR   ->  OUT_DIR/app/{dwgballet,web,ballet-ui,dwg*.py,...}, OUT_DIR/requirements.txt"""
import os, sys, shutil, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(out):
    app = os.path.join(out, 'app')
    if os.path.exists(app): shutil.rmtree(app)
    os.makedirs(app)
    ign = shutil.ignore_patterns('__pycache__', '*.pyc', '*.so', '*.dylib', '*.pyd.tmp', 'tests')
    for d in ('dwgballet', 'web', 'ballet-ui'):
        if os.path.isdir(os.path.join(ROOT, d)): shutil.copytree(os.path.join(ROOT, d), os.path.join(app, d), ignore=ign)
    for f in glob.glob(os.path.join(ROOT, '*.py')):
        b = os.path.basename(f)
        if b.startswith(('dwg', 'lz', 'r21')) and not b.startswith(('dwg2svg',)): shutil.copy2(f, app)
    shutil.copy2(os.path.join(ROOT, 'dwg2text.py'), app) if os.path.exists(os.path.join(ROOT, 'dwg2text.py')) else None
    shutil.copy2(os.path.join(ROOT, 'packaging', 'requirements-app.txt'), os.path.join(out, 'requirements.txt'))
    n = sum(len(fs) for _, _, fs in os.walk(app))
    print('staged %d files into %s' % (n, app))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'dist'))

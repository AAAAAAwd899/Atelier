"""Deterministic local build helpers. No network or publishing side effects."""
from pathlib import Path
import hashlib,json,zipfile,ast
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'src'
DIST=ROOT/'dist'

def version():
    return json.loads((SRC/'manifest.json').read_text())['human_version']

def runtime_digest(root=SRC):
    files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
           and p.suffix in ('.py','.js','.css','.json','.svg','.png','.webp') and 'user_files' not in p.relative_to(root).parts}
    return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def production_files():
    files=[]
    for p in sorted(SRC.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:continue
        rel=p.relative_to(SRC).as_posix()
        if 'user_files' in Path(rel).parts:
            if rel=='user_files/README.txt':files.append((p,rel))
            continue
        if p.suffix in ('.pyc','.pyo'):continue
        if p.suffix.lower() in ('.ttf','.otf','.woff','.woff2'):
            raise RuntimeError('Font files may not be distributed in this package')
        if p.suffix not in ('.py','.json','.js','.css','.md','.txt','.svg','.png','.webp') and p.name not in ('LICENSE','NOTICE','py.typed'):
            raise RuntimeError('Unapproved production asset: '+rel)
        if p.name in ('meta.json',) or p.suffix=='.ankiaddon':raise RuntimeError('Private/bundled install data found')
        files.append((p,rel))
    return files

def write_archive(destination, files):
    # Fixed metadata eliminates zip timestamps/permissions as sources of drift.
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p,name in sorted(files,key=lambda x:x[1]):
            if name.startswith('/') or '..' in Path(name).parts:raise ValueError(name)
            i=zipfile.ZipInfo(name,(2026,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16
            z.writestr(i,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(destination) as z:
        if z.testzip():raise RuntimeError('Archive CRC failed')

def build_installer(destination):
    manifest=json.loads((SRC/'manifest.json').read_text())
    if manifest['package']!='daedalus_atelier':raise RuntimeError('Private installer identity changed')
    tree=ast.parse((SRC/'core.py').read_text(encoding='utf8'))
    declared=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(k,ast.Name) and k.id=='VERSION' for k in n.targets))
    if declared!=version():raise RuntimeError('Version mismatch')
    files=production_files()
    for p,_ in files:
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    write_archive(destination,files)
    return files

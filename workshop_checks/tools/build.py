"""Build the real root-level installer; source archive is finalized after verification."""
from __future__ import annotations
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from addon.core import VERSION,PACKAGE
SKIP={'__pycache__','.pytest_cache','.git','dist','node_modules'}
DOCS=('FEATURES.md','PRIVACY.md','NATIVE_ACCEPTANCE.md','INTEGRATION_API.md','SOURCES_AND_LICENSES.md')
def include(p):
 return p.is_file() and not p.is_symlink() and not any(x in SKIP for x in p.relative_to(ROOT).parts) and p.suffix.lower() not in ('.pyc','.pyo','.ttf','.otf','.woff','.woff2','.ankiaddon','.zip','.sqlite','.sqlite3','.db')
def entry(z,name,data):
 i=zipfile.ZipInfo(name,(2026,9,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o644<<16;z.writestr(i,data)
def build(out):
 out.mkdir(parents=True,exist_ok=True);dest=out/f'Workshop_{VERSION}.ankiaddon'
 with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted((ROOT/'addon').rglob('*')):
   if include(p):entry(z,p.relative_to(ROOT/'addon').as_posix(),p.read_bytes())
  for name in ('README.md','LICENSE'):entry(z,name,(ROOT/name).read_bytes())
  for name in DOCS:entry(z,'docs/'+name,(ROOT/'docs'/name).read_bytes())
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  assert json.loads(z.read('manifest.json'))['package']==PACKAGE
  assert '__init__.py' in z.namelist() and not any(n.startswith('addon/') for n in z.namelist())
  assert 'vendor/pypdf/LICENSE' in z.namelist()
  for n in z.namelist():
   if n.endswith('.py'):compile(z.read(n),n,'exec')
 print(json.dumps({'installer':str(dest),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2))
 return dest
def source_archive(out):
 out.mkdir(parents=True,exist_ok=True);dest=out/f'Workshop_Source_{VERSION}.zip'
 with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(ROOT.rglob('*')):
   if include(p) and out not in p.parents:entry(z,'Workshop/'+p.relative_to(ROOT).as_posix(),p.read_bytes())
 print(json.dumps({'source':str(dest),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2))
 return dest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--source-only',action='store_true');a=p.parse_args()
 if a.source_only:source_archive(a.output.resolve())
 else:build(a.output.resolve())

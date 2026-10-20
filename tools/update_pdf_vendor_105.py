"""Reproduce the narrow 1.0.5 parser security update from a verified local wheel.

Does not download, install dependencies globally or change authoring-engine code.
"""
from pathlib import Path,PurePosixPath
import ast,hashlib,json,re,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
VERSION='6.21.1';SHA='553e2d42f5bb3bb2a785a7d3de8ef90bb7df74b5413eff5a7b4388007ea9254b'
wheel=Path(sys.argv[1]);assert hashlib.sha256(wheel.read_bytes()).hexdigest()==SHA
vendor=ROOT/'src/workshop/vendor/pypdf'
baseline=json.loads((ROOT/'baseline-1.0.2.json').read_text())
old={n:sha for n,sha in baseline.items() if n.startswith('workshop/vendor/pypdf/')}
with zipfile.ZipFile(wheel) as z:
    files={name[len('pypdf/'):]:z.read(name) for name in z.namelist() if name.startswith('pypdf/') and not name.endswith('/')}
    license_name=next(n for n in z.namelist() if n.endswith('.dist-info/licenses/LICENSE'))
    files['LICENSE']=z.read(license_name)
assert b'Redistribution and use' in files['LICENSE']
upstream_hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}
rewrites={}
for name,raw in list(files.items()):
    if not name.endswith('.py'):continue
    prefix='.'*len(PurePosixPath(name).parts)
    text,count=re.subn(r'(?m)^(\s*)from pypdf(?:\.([\w.]+))? import',lambda m:m[1]+'from '+prefix+(m[2] or '')+' import',raw.decode('utf8'))
    if count:
        text='# Atelier vendor adjustment: package imports are relative for namespace isolation.\n'+text
        files[name]=text.encode('utf8');rewrites[name]=count
for name,raw in files.items():
    p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
    assert p.suffix=='.py' or p.name in ('LICENSE','py.typed')
    if p.suffix=='.py':ast.parse(raw.decode('utf8'),filename=name)
# Retain byte-exact historical code for preservation assertions, not in runtime.
historic_path=ROOT/'tests/data/pypdf-590-baseline.json'
if not historic_path.exists():
    historic={}
    for name,sha in old.items():
        raw=(ROOT/'src'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
        historic[name]=raw.decode('utf8')
    historic_path.write_bytes((json.dumps(historic,separators=(',',':'))+'\n').encode())
retired=sorted(set(old)-{'workshop/vendor/pypdf/'+n for n in files})
for name,raw in files.items():
    dest=vendor/name;assert dest.resolve().is_relative_to(vendor.resolve())
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
for name in retired:
    dest=ROOT/'src'/name
    assert dest.resolve().is_relative_to(vendor.resolve()) and dest.suffix=='.py'
    dest.unlink(missing_ok=True)
record={'name':'pypdf','version':VERSION,'license':'BSD-3-Clause','wheel_sha256':SHA,
        'source':'https://pypi.org/project/pypdf/6.21.1/','patch_scope':'absolute package imports rewritten to namespaced relative imports only',
        'upstream_files':upstream_hashes,'namespace_import_rewrites':rewrites,
        'files':{'workshop/vendor/pypdf/'+n:hashlib.sha256(raw).hexdigest() for n,raw in sorted(files.items())},
        'retired_baseline_modules':retired,'engine_workflows_changed':False}
(ROOT/'PYPDF-VENDOR-6.21.1.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print('Verified upstream parser files',len(files),'retired private modules',len(retired))

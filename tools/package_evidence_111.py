"""Bounded current evidence; no owner profiles or published binaries."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist'
proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.11-Build.json').read_text())
assert proof['version']=='1.0.11' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-111.json','installer-extracted-111.json','folder-order-111-extracted.log','public-source-audit-111.json','native-onigiri-111.json','onigiri-coexistence-111.json','select-colors.json']]
for name in proof['browser_suites']:files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(V/(name+'.log') for name in ['atelier-unit','sprout-unit','workshop-unit'])
files.extend(ROOT/n for n in ['BRIEF-1.0.11.md','AUDIT-1.0.11.md','CHANGELOG-1.0.11.md','INSTALL-1.0.11.md','ASSET-PROVENANCE-1.0.3.md','output/native-folder-order-111/results.json'])
files.extend((ROOT/'screenshots/folder-order-110').glob('*.png'))
files.extend((ROOT/'screenshots/release-111').glob('*.png'))
assert all(p.is_file() for p in files)
dest=D/'Atelier-1.0.11-Evidence.zip';write_archive(dest,[(p,'Atelier-1.0.11-Evidence/'+p.relative_to(ROOT).as_posix()) for p in sorted(set(files))])
print(json.dumps({'files':len(set(files)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'owner_data_included':False}))

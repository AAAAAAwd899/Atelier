"""Current scoped release evidence; no owner collections or third-party runtime copies."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist'
proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.14-Build.json').read_text())
assert proof['version']=='1.0.14' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-114.json','installer-extracted-114.json','library-polish-114-extracted.json','library-polish-114-extracted.log','folder-order-114-extracted.log','native-onigiri-114.json','preservation-114.json','consumer-review-114.json','public-source-audit-114.json','github-114.json','qa-cleanup-114.json']]
for name in proof['browser_suites']:files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(V/(n+'.log') for n in ['atelier-unit','sprout-unit','workshop-unit','full-114','package-114','native-onigiri-114'])
files.extend(ROOT/n for n in ['BRIEF-1.0.14.md','AUDIT-1.0.14.md','INSTALL-1.0.14.md','CHANGELOG-1.0.14.md','ASSET-PROVENANCE-1.0.12.json','dist/Atelier-1.0.14-Build.json','dist/Atelier-1.0.14-Files.json'])
files.extend((V/'themes-114').glob('*.json'));files.extend((V/'themes-114').glob('Atelier-*.webm'));files.extend((ROOT/'screenshots/themes-114').glob('*.png'));files.extend((V/'retention-114').glob('*.json'))
assert all(p.is_file() for p in files)
dest=D/'Atelier-1.0.14-Evidence.zip';write_archive(dest,[(p,'Atelier-1.0.14-Evidence/'+p.relative_to(ROOT).as_posix()) for p in sorted(set(files))])
print(json.dumps({'files':len(set(files)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))

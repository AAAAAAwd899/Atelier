"""Current scoped release evidence; no owner collections or third-party runtime copies."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist'
proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.13-Build.json').read_text())
assert proof['version']=='1.0.13' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-113.json','installer-extracted-113.json','library-polish-113-extracted.json','library-polish-113-extracted.log','folder-order-113-extracted.log','native-onigiri-113.json','preservation-113.json','consumer-review-113.json','public-source-audit-113.json','github-113.json','qa-cleanup-113.json']]
for name in proof['browser_suites']:files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(V/(n+'.log') for n in ['atelier-unit','sprout-unit','workshop-unit','full-113','package-113','native-onigiri-113'])
files.extend(ROOT/n for n in ['BRIEF-1.0.13.md','AUDIT-1.0.13.md','INSTALL-1.0.13.md','CHANGELOG-1.0.13.md','ASSET-PROVENANCE-1.0.12.json','dist/Atelier-1.0.13-Build.json','dist/Atelier-1.0.13-Files.json'])
files.extend((V/'picker-113').glob('*.json'));files.extend((V/'picker-113').glob('Atelier-*.webm'));files.extend((ROOT/'screenshots/picker-113').glob('*.png'));files.extend((V/'retention-113').glob('*.json'))
assert all(p.is_file() for p in files)
dest=D/'Atelier-1.0.13-Evidence.zip';write_archive(dest,[(p,'Atelier-1.0.13-Evidence/'+p.relative_to(ROOT).as_posix()) for p in sorted(set(files))])
print(json.dumps({'files':len(set(files)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))

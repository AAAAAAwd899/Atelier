"""Bounded current evidence; no owner profiles or published binaries."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist'
proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.12-Build.json').read_text())
assert proof['version']=='1.0.12' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-112.json','installer-extracted-112.json','folder-order-112-extracted.log','public-source-audit-112.json','native-onigiri-112.json','onigiri-coexistence-112.json','library-polish-112-extracted.json','library-polish-112-extracted.log','preservation-112.json']]
for name in proof['browser_suites']:files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(V/(name+'.log') for name in ['atelier-unit','sprout-unit','workshop-unit'])
files.extend(ROOT/n for n in ['BRIEF-1.0.12.md','AUDIT-1.0.12.md','CHANGELOG-1.0.12.md','INSTALL-1.0.12.md','ASSET-PROVENANCE-1.0.3.md','output/native-folder-order-112/results.json'])
files.extend((ROOT/'screenshots/folder-order-110').glob('*.png'))
files.extend((ROOT/'screenshots/polish-112').glob('*.png'))
files.extend((ROOT/'screenshots/library-polish-112').glob('*.png'))
files.append(V/'polish-112/results.json')
files.append(V/'consumer-review-112.json')
files.extend(ROOT/n for n in ['ASSET-PROVENANCE-1.0.12.json','verification/motion-112.json','verification/dependency-advisories-112.json','verification/pdf-security-112.json','verification/motion-cleanup-112.json','PYPDF-VENDOR-6.21.4.json','output/polish-112-walkthrough/Atelier-1.0.12-Walkthrough.webm'])
files.extend((ROOT/'verification/retention-112').glob('*.json'))
files.extend(ROOT/n for n in ['verification/qa-scratch-cleanup-112.json','verification/qa-scratch-112-files.json.gz'])
files.extend((ROOT/'.recovery/metadata').glob('*'))
files.extend((ROOT/'workshop_checks/docs/authoring-110').glob('*.png'))
assert all(p.is_file() for p in files)
dest=D/'Atelier-1.0.12-Evidence.zip';write_archive(dest,[(p,'Atelier-1.0.12-Evidence/'+p.relative_to(ROOT).as_posix()) for p in sorted(set(files))])
print(json.dumps({'files':len(set(files)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'owner_data_included':False}))

"""Bounded release receipts and actual screenshots; no collection or credentials."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist'
proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.15-Build.json').read_text())
assert proof['version']=='1.0.15' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-115.json','installer-extracted-115.json','library-polish-115-extracted.json','social-115-extracted.json','native-onigiri-115.json','native-sharing-115.json','native-social-115.json','native-install-115.json','preservation-115.json','consumer-review-115.json','public-source-audit-115.json','github-115.json','qa-cleanup-115.json','qa-onigiri-cleanup-115.json','qa-install-cleanup-115.json','storage-budget-115.json']]
for name in proof['browser_suites']:
    files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(ROOT/n for n in ['BRIEF-1.0.15.md','AUDIT-1.0.15.md','INSTALL-1.0.15.md','CHANGELOG-1.0.15.md','ASSET-PROVENANCE-1.0.15.json','dist/Atelier-1.0.15-Build.json','dist/Atelier-1.0.15-Files.json'])
for folder,patterns in [(V/'social-115',['*.json','*.xml']), (V/'retention-115',['*.json']), (ROOT/'screenshots/social-115',['*.png']), (ROOT/'screenshots/native-social-115',['*.png'])]:
    for pattern in patterns:files.extend(folder.glob(pattern))
for name in ['atelier-unit','sprout-unit','workshop-unit','package-115','library-polish-115-extracted','folder-order-115-extracted','social-115-extracted']:
    files.append(V/(name+'.log'))
files.extend((ROOT/'output/native-social-115').glob('*-captured.json'))
files.extend(V.glob('*interrupted-115.log'))
files.extend(V/n for n in ['hosted-world-finish-115.json','github-ci-115-corrected.log','github-ci-115-picker.log','github-study-picker-115.log','aggregate-115.log'])
files.extend(V/n for n in ['qa-final-cleanup-115.json','qa-repeat-cleanup-115.json','native-install-115-stale-input-diagnosis.json','github-ci-115.log','github-ci-115-preflight.log','full-115.log','native-sharing-115.log','native-social-115.log','native-onigiri-115.log','native-install-115.log'])
assert all(p.is_file() for p in files),[str(p) for p in files if not p.is_file()]
dest=D/'Atelier-1.0.15-Evidence.zip'
write_archive(dest,[(p,'Atelier-1.0.15-Evidence/'+p.relative_to(ROOT).as_posix()) for p in sorted(set(files))])
print(json.dumps({'files':len(set(files)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))

"""Bounded current receipts, logs and real screenshots; excludes collections and credentials."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist'
proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.16-Build.json').read_text())
assert proof['version']=='1.0.16' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[]
for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-116.json','installer-extracted-116.json','library-polish-116-extracted.json','social-116-extracted.json','native-onigiri-116.json','native-sharing-116.json','native-social-116.json','native-install-116.json','preservation-116.json','consumer-review-116.json','public-source-audit-116.json','hosted-current-116.json','github-ci-final-116.log','polish-112/results.json','hosted-ci-116/verified.json']:
 files.append(V/n)
for name in proof['browser_suites']:
 files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
for folder,patterns in [(V/'publish-audit-116',['*.json','*.log']),(V/'social-116',['*.json','*.xml']),(V/'retention-116',['*.json']),(ROOT/'screenshots/native-social-116',['*.png']),(ROOT/'listing/ankiweb-1.0.16',['*.json'])]:
 for pattern in patterns:files.extend(folder.glob(pattern))
files.extend(ROOT/n for n in ['BRIEF-1.0.16.md','AUDIT-1.0.16.md','INSTALL-1.0.16.md','CHANGELOG-1.0.16.md','ASSET-PROVENANCE-1.0.15.json','dist/Atelier-1.0.16-Build.json','dist/Atelier-1.0.16-Files.json','output/accessibility/results.json','output/listing-native-116/capture-receipt.json','output/listing-native-116/host-report.json'])
files.extend((ROOT/'screenshots/polish-112').glob('*.png'))
files.extend((ROOT/'listing/ankiweb-1.0.16/screenshots').glob('*.png'))
assert all(p.is_file() for p in files),[str(p) for p in files if not p.is_file()]
for label,items in [('Evidence',files),('AnkiWeb-Listing-Kit',list((ROOT/'listing/ankiweb-1.0.16').rglob('*')))]:
 items=sorted(set(p for p in items if p.is_file()));dest=D/f'Atelier-1.0.16-{label}.zip'
 base=ROOT if label=='Evidence' else ROOT/'listing/ankiweb-1.0.16'
 write_archive(dest,[(p,f'Atelier-1.0.16-{label}/'+p.relative_to(base).as_posix()) for p in items])
 print(json.dumps({'artifact':dest.name,'files':len(items),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))

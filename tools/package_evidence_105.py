"""Bounded test evidence: no profiles, collections, owner backup or private data."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';proof=json.loads((V/'verified.json').read_text())
assert proof['runtime_sha256']==runtime_digest() and proof['version']=='1.0.5'
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-105.json']]
for name in proof['browser_suites']:
    files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(V/(name+'.log') for name in ['atelier-unit','sprout-unit','workshop-unit'])
files.extend(ROOT/n for n in ['AUDIT-1.0.5.md','ANKI-ADDON-COMPLIANCE-1.0.5.md','PYPDF-VENDOR-6.21.1.json'])
for n in ['output/native-install-105/results.json','output/native-onboarding-105/results.json','output/native-folder/results.json','output/native-io-105-26.09.3/results.json']:
    p=ROOT/n;r=json.loads(p.read_text());assert r['runtime_sha256']==runtime_digest() and r['anki']=='26.09.3' and not r['errors'] and all(r['checks'].values());files.append(p)
files.extend((ROOT/'screenshots/native-onboarding-105').glob('*.jpg'))
files.append(ROOT/'screenshots/native-onboarding-105/capture-review.json')
files.extend((ROOT/'screenshots/onboarding-105').glob('*.png'))
for name in ['question.png','answer.png','actual-size.png']:
    files.append(ROOT/'output/native-io-105-26.09.3'/name)
files=sorted(set(files));assert all(p.is_file() for p in files)
assert all(p.suffix in ['.json','.xml','.md','.log','.exit','.png','.jpg'] and 'private-backup' not in p.parts for p in files)
dest=ROOT/'dist/Atelier-1.0.5-Evidence.zip'
write_archive(dest,[(p,'Atelier-1.0.5-Evidence/'+p.relative_to(ROOT).as_posix()) for p in files])
receipt={'runtime_sha256':runtime_digest(),'files':len(files),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'profiles_or_owner_data_included':False}
(ROOT/'dist/Atelier-1.0.5-Evidence.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))

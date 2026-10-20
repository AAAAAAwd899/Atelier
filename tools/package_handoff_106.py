"""Package the bounded evidence and simple owner AnkiWeb upload kit."""
from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist';F=ROOT/'listing/ankiweb-1.0.6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((V/'verified.json').read_text())
build=json.loads((D/'Atelier-1.0.6-Build.json').read_text())
assert proof['version']=='1.0.6' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
assert build['full_automated_verification'] and proof['python_total']==1940 and proof['browser_total']==2893
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','anki-addon-106.json','listing-preview-106.json','consumer-review-106.json','public-source-audit-106.json','github-public-106.json']]
for name in proof['browser_suites']:
    files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend(V/(name+'.log') for name in ['atelier-unit','sprout-unit','workshop-unit'])
files.extend(ROOT/n for n in ['AUDIT-1.0.6.md','CHANGELOG-1.0.6.md','INSTALL-1.0.6.md','ANKI-ADDON-COMPLIANCE-1.0.5.md','PYPDF-VENDOR-6.21.1.json','ASSET-PROVENANCE-1.0.3.md'])
native=[]
for n in ['output/native-install-106/results.json','output/native-onboarding-106/results.json','output/native-clock-106/results.json','output/native-folder/results.json','output/native-io-106-26.09.3/results.json']:
    p=ROOT/n;r=json.loads(p.read_text());assert r['runtime_sha256']==runtime_digest() and r['anki']=='26.09.3' and not r['errors'] and all(r['checks'].values());files.append(p);native.append({'receipt':n,'checks':len(r['checks'])})
for folder in ['screenshots/native-clock-106','screenshots/listing-review-106','screenshots/onboarding-105']:
    files.extend((ROOT/folder).glob('*.png'))
files.extend(F.rglob('*'))
files=sorted(set(p for p in files if p.is_file()))
assert all(p.suffix in ['.json','.xml','.md','.log','.exit','.png','.html','.txt'] and 'private-backup' not in p.parts for p in files)
evidence=D/'Atelier-1.0.6-Evidence.zip'
write_archive(evidence,[(p,'Atelier-1.0.6-Evidence/'+p.relative_to(ROOT).as_posix()) for p in files])
receipt={'runtime_sha256':runtime_digest(),'files':len(files),'bytes':evidence.stat().st_size,'sha256':sha(evidence),'native':native,'native_total':sum(x['checks'] for x in native),'profiles_or_owner_data_included':False}
(D/'Atelier-1.0.6-Evidence.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
start=D/'Atelier-1.0.6-Upload-START-HERE.txt'
start.write_text('''ATELIER 1.0.6 - OWNER UPLOAD KIT

INSTALL OR SEND: Atelier-1.0.6.ankiaddon is the complete Anki add-on.
Install in Anki desktop: Tools > Add-ons > Install from file, then restart.
Do not upload this ZIP to Anki. Upload ONLY the .ankiaddon file.

PREPARE ANKIWEB: open listing/START-HERE.md. Copy title.txt and
description.html (description.txt is the plain-text alternative).
listing/preview.html lets you preview the text and screenshots locally.
listing/listing-fields.json contains support, license and compatibility fields.
listing/screenshots contains seven real native interface screenshots.

Public source and support: https://github.com/AAAAAAwd899/Atelier
The repository is public with Issues enabled. No AnkiWeb upload, website
deployment or public binary release has been performed. Account eligibility,
real numeric listing identity and migration from the private package remain
to be verified. Keep using the same listing for later updates.

Back up your collection and local Atelier work before updating. See INSTALL.md.
SHA256.txt verifies the installer and listing files. Source and detailed test
evidence are supplied as separate version-matched archives in the handoff.
''',encoding='utf8')
payload=[(start,'START-HERE.txt'),(D/'Atelier-1.0.6.ankiaddon','Atelier-1.0.6.ankiaddon'),(ROOT/'INSTALL-1.0.6.md','INSTALL.md')]
payload.extend((p,'listing/'+p.relative_to(F).as_posix()) for p in sorted(F.rglob('*')) if p.is_file())
checks=D/'Atelier-1.0.6-Upload-SHA256.txt';checks.write_text(''.join(sha(p)+'  '+n+'\n' for p,n in payload),encoding='utf8')
payload.append((checks,'SHA256.txt'))
kit=D/'Atelier-1.0.6-AnkiWeb-Listing-Kit.zip';write_archive(kit,payload)
full=D/'Atelier-1.0.6-Full-Publish-Package.zip'
write_archive(full,payload+[(D/'Atelier-1.0.6-Source.zip','Atelier-1.0.6-Source.zip'),(evidence,evidence.name),(D/'Atelier-1.0.6-Build.json','Atelier-1.0.6-Build.json'),(D/'Atelier-1.0.6-Evidence.json','Atelier-1.0.6-Evidence.json'),(D/'Atelier-1.0.6-SHA256.txt','Atelier-1.0.6-SHA256.txt')])
for p in [evidence,kit,full]:
    with zipfile.ZipFile(p) as z:assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))
with zipfile.ZipFile(kit) as z:
    assert hashlib.sha256(z.read('Atelier-1.0.6.ankiaddon')).hexdigest()==build['installer_sha256']
report={'version':'1.0.6','runtime_sha256':runtime_digest(),'native_checks':receipt['native_total'],'zip_crc_passed':True,'installer_source_bytes_equal':build['installer_source_bytes_equal'],'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in [D/'Atelier-1.0.6.ankiaddon',D/'Atelier-1.0.6-Source.zip',evidence,kit,full]}}
(D/'Atelier-1.0.6-Handoff.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))

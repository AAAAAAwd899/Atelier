"""Current bounded release evidence; no collection payloads or credentials."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import write_archive,runtime_digest
V=ROOT/'verification';D=ROOT/'dist';proof=json.loads((V/'verified.json').read_text());build=json.loads((D/'Atelier-1.0.18-Build.json').read_text())
assert proof['version']=='1.0.18' and proof['runtime_sha256']==runtime_digest()==build['runtime_sha256']
files=[V/n for n in ['verified.json','python-runtime.json','atelier-unit.xml','sprout-unit.xml','workshop-unit.xml','public-source-audit-118.json','listing-preview-118.json']]
for name in proof['browser_suites']:files.extend(V/(name+s) for s in ['.log','.exit','-results.json'])
files.extend((V/'onigiri-toolbar-118').glob('*.json'));files.extend((V/'onigiri-toolbar-118').glob('*.log'))
files.extend(ROOT/n for n in ['AUDIT-1.0.18.md','INSTALL-1.0.18.md','CHANGELOG-1.0.18.md','ASSET-PROVENANCE-1.0.18.json','dist/Atelier-1.0.18-Build.json','MANUAL_ACTIONS_REQUIRED.md'])
files.extend((ROOT/'listing/ankiweb-1.0.18').rglob('*'));files=[p for p in files if p.is_file()]
for label,items in [('Evidence',files),('AnkiWeb-Listing-Kit',[p for p in (ROOT/'listing/ankiweb-1.0.18').rglob('*') if p.is_file()])]:
 items=sorted(set(items));base=ROOT if label=='Evidence' else ROOT/'listing/ankiweb-1.0.18';dest=D/f'Atelier-1.0.18-{label}.zip'
 write_archive(dest,[(p,f'Atelier-1.0.18-{label}/'+p.relative_to(base).as_posix()) for p in items]);print(json.dumps({'artifact':dest.name,'files':len(items),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))

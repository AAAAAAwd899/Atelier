"""Exact cumulative runtime declaration and 1.0.14 preservation receipt."""
from pathlib import Path
import hashlib,json,subprocess,struct
from release_tools import ROOT,production_files,runtime_digest
baseline=json.loads((ROOT/'baseline-1.0.2.json').read_text())
files={n:hashlib.sha256(p.read_bytes()).hexdigest() for p,n in production_files()}
patch={'baseline':'Verified Atelier 1.0.2; cumulative reviewed upgrade through 1.0.15','changed':{n:h for n,h in files.items() if n in baseline and h!=baseline[n]},'added':{n:h for n,h in files.items() if n not in baseline},'removed':sorted(set(baseline)-set(files))}
(ROOT/'patch-115-changes.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8',newline='\n')
old=json.loads((ROOT/'dist/Atelier-1.0.14-Files.json').read_text())['files']
changed=[n for n in files if n in old and files[n]!=old[n]];added=[n for n in files if n not in old]
assert not set(old)-set(files),'An accepted runtime file was removed'
protected=[n for n in old if n.startswith(('sprout/','workshop/')) and n not in ('sprout/web/app.js','sprout/web/pip.js')]
assert all(old[n]==files[n] for n in protected),'A protected exam/card engine or original asset changed'
for n in ['folder_study.py','native_widgets.py','ownership.py','remotes.py','remote_model.py','figure_cache.py','focus_context.py','study_progress.py','quiet_navigation.py']:
 assert old[n]==files[n],n
art=json.loads((ROOT/'ASSET-PROVENANCE-1.0.15.json').read_text())
for a in art['assets']:
 data=(ROOT/a['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==a['sha256'];a['dimensions']=list(struct.unpack('>II',data[16:24]))
(ROOT/'ASSET-PROVENANCE-1.0.15.json').write_text(json.dumps(art,indent=2)+'\n',encoding='utf-8',newline='\n')
receipt={'baseline':'1.0.14 matching source/installer','runtime_sha256':runtime_digest(),'original_files_unchanged':len(old)-len(changed),'changed':changed,'added':added,'removed':[],'protected_original_engine_and_asset_files':len(protected),'note':'All non-presentation Sprout/Workshop files and original companion/world assets are byte-identical to 1.0.14. Sprout UI adds portrait selection and a narrowly adapted navigation action only. No scheduler, mask, remote, source/draft, saved-practice or third-party widget code was replaced.'}
(ROOT/'verification/preservation-115.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'changed':len(changed),'added':len(added),'removed':0,'protected':len(protected),'runtime':runtime_digest()}))

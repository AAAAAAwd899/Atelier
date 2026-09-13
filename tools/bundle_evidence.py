"""Assemble explicitly categorized runtime evidence; never include QA profiles."""
from pathlib import Path
import argparse, hashlib, json, shutil, sys, zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest,write_archive

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--proof-dir',type=Path,required=True);args=ap.parse_args()
    fingerprint=runtime_digest();proof=json.loads((args.proof_dir/'verified.json').read_text())
    assert proof['runtime_sha256']==fingerprint and proof['python_failed']==proof['python_skipped']==proof['browser_errors']==0
    out=ROOT/'dist/Atelier-1.0.3-Evidence';out.mkdir(parents=True,exist_ok=True)
    included=set();photos=[]
    def copy(src,rel):
        dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);included.add(rel)
    for component,count in [('matrix',360),('home-workflows',180),('planner',240),('card',120)]:
        folder=ROOT/'output/playwright'/('final-'+component);receipt=json.loads((folder/'results.json').read_text())
        assert receipt['runtime_sha256']==fingerprint and len(receipt['records'])==count and not receipt['errors']
        copy(folder/'results.json',f'browser/{component}/results.json')
        for row in receipt['records']:
            assert not row.get('horizontal_overflow',row.get('page_overflow',False))
            file=folder/row['file'];assert sha(file)==row['sha256']
            rel=f'browser/{component}/'+row['file'];copy(file,rel)
            photos.append({**row,'file':rel,'category':'Browser fixture','viewport':'×'.join(map(str,row['viewport']))})
    for name in ['native-desktop-25.09.5','native-io-25.09.5','native-folder']:
        folder=ROOT/'output'/name;receipt=json.loads((folder/'results.json').read_text())
        assert receipt['runtime_sha256']==fingerprint and not receipt['errors'] and all(receipt.get('checks',{}).values())
        assert len(receipt.get('captures',[]))=={'native-desktop-25.09.5':6,'native-io-25.09.5':3,'native-folder':0}[name]
        assert len(receipt.get('checks',{}))=={'native-desktop-25.09.5':0,'native-io-25.09.5':9,'native-folder':8}[name]
        if name=='native-io-25.09.5':
            stages={row['stage']:row['dom'] for row in receipt['captures']}
            assert stages['question']['canvasInk'][3]==255 and stages['answer']['canvasInk'][3]==0
            assert stages['question']['canvasVisibility']=='visible' and stages['question']['canvasOpacity']=='1'
        copy(folder/'results.json',f'native/{name}/results.json')
        for row in receipt.get('captures',[]):
            filename=row.get('path',row.get('stage','')+'.png');rel=f'native/{name}/'+filename
            copy(folder/filename,rel)
            photos.append({'file':rel,'world':row.get('diagnostics',{}).get('theme','midnight'),'screen':row.get('diagnostics',{}).get('page',row.get('stage','native')),'category':'Native Anki · Windows','viewport':'150% host scale','sha256':sha(folder/filename)})
    install=json.loads((ROOT/'output/native-install/results.json').read_text())
    assert install['runtime_sha256']==fingerprint and install['installer_sha256']==sha(ROOT/'dist/Atelier-1.0.3.ankiaddon') and not install['errors'] and len(install['checks'])==8 and all(install['checks'].values())
    copy(ROOT/'output/native-install/results.json','native/native-install/results.json')
    for folder in ['endurance','performance','accessibility','memory-followup']:
        for p in (ROOT/'output'/folder).glob('*.json'):copy(p,f'probes/{folder}/'+p.name)
    for name in ['composited-contrast.json','dependency-audit.json','dependency-audit-before.json','dependency-audit.log','exact-installer-unit.xml','exact-installer-unit.log','exact-installer.json','native-final-home.log','native-final-io.log','native-install.log','native-io-late-sizing-failure.json','native-io-profile-lock-failure.json','final-browser-verifier.log','exact-installer-browser.log','exact-installer-browser-before.log','authoring-home-supplement.log']:
        p=ROOT/'output'/name
        if p.exists():copy(p,'probes/'+name)
    video=ROOT/'output/playwright/final-walkthrough';record=json.loads((video/'recording.json').read_text());assert record['runtime_sha256']==fingerprint
    for name in ['recording.json','Atelier-1.0.3-Walkthrough.webm']:copy(video/name,'walkthrough/'+name)
    for name in ['midnight-widgets.png','rose-widgets.png','failure.json']:
        p=ROOT/'output/native-home-capture-timing-failure'/name
        if p.exists():copy(p,'failures/native-capture-timing/'+name)
    for p in args.proof_dir.rglob('*'):
        if p.is_file() and p.suffix in ('.json','.xml','.log','.exit','.png'):
            copy(p,'verification/'+p.relative_to(args.proof_dir).as_posix())
    # CI's other workflow screenshots include empty, error, long and dirty-form cases.
    ci_screens=args.proof_dir.parent/'screenshots'
    if ci_screens.exists():
        for p in ci_screens.rglob('*.png'):copy(p,'workflow-states/'+p.relative_to(ci_screens).as_posix())
    for name in ['AUDIT-1.0.3.md','CHANGELOG-1.0.3.md','INSTALL-1.0.3.md','baseline-1.0.2.json','patch-103-changes.json','MANUAL_ACTIONS_REQUIRED.md','ASSET-PROVENANCE-1.0.3.md']:
        copy(ROOT/name,'reports/'+name)
    for name in ['Atelier-1.0.3-Build.json','Atelier-1.0.3-Files.json']:copy(ROOT/'dist'/name,'reports/'+name)
    (out/'gallery-data.js').write_text('const captures='+json.dumps(photos,ensure_ascii=True)+';\n');included.add('gallery-data.js')
    (out/'index.html').write_text(GALLERY,encoding='utf8');included.add('index.html')
    record={'name':'Atelier','version':'1.0.3','runtime_sha256':fingerprint,'installer_sha256':sha(ROOT/'dist/Atelier-1.0.3.ankiaddon'),'source_sha256':sha(ROOT/'dist/Atelier-1.0.3-Source.zip'),'browser_default_captures':900,'native_captures':9,'owner_visual_acceptance':False,'limits':'See reports/AUDIT-1.0.3.md. Default palette captures are repeated cases, not independent integrations. Native evidence uses synthetic profiles. No generated UI images. Background asset provenance is separate.','files':{n:sha(out/n) for n in sorted(included)}}
    (out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n');included.add('manifest.json')
    assert not any((out/n).suffix in ('.anki2','.sqlite3','.key','.pem') for n in included)
    archive=ROOT/'dist/Atelier-1.0.3-Evidence.zip';write_archive(archive,[(out/n,'Atelier-1.0.3-Evidence/'+n) for n in included])
    with zipfile.ZipFile(archive) as z:assert len(z.namelist())==len(included) and not z.testzip()
    checksum=ROOT/'dist/Atelier-1.0.3-SHA256.txt';lines=[line for line in checksum.read_text().splitlines() if 'Evidence.zip' not in line];checksum.write_text('\n'.join(lines+[sha(archive)+'  '+archive.name])+'\n')
    print(json.dumps({'evidence_sha256':sha(archive),'files':len(included),'gallery_captures':len(photos),'bytes':archive.stat().st_size}))

GALLERY='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Atelier 1.0.3 — actual interface evidence</title><style>
*{box-sizing:border-box}body{margin:0;background:#101923;color:#edf3f7;font:16px/1.55 system-ui}header,main{max-width:1500px;margin:auto;padding:24px}h1{font:38px Georgia;margin:0}p{max-width:1000px;color:#c3d2df}a{color:#a9d7ff}label{display:inline-grid;gap:5px;margin:0 16px 12px 0}select,button{font:inherit;color:inherit;background:#243748;border:1px solid #8eabc1;padding:10px;border-radius:7px}button{cursor:pointer}select:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid #f5da91;outline-offset:3px}#grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:20px}figure{margin:0;border:1px solid #465f72;border-radius:10px;overflow:hidden;background:#1b2a36}figure img{display:block;width:100%;aspect-ratio:16/10;object-fit:contain;background:#0b1119}figcaption{padding:14px}small{display:block;color:#bdcdda}video{max-width:100%;width:900px}nav{margin:20px 0}#count{margin-right:20px}</style>
<header><h1>Atelier 1.0.3</h1><p>Actual interfaces for review. Browser fixtures use synthetic records and native API doubles; the native captures come from Anki 25.09.5 on Windows with separate synthetic profiles. Open an image for full-size inspection. The landscape assets are generated artwork; the interface screenshots and recording are real rendered output.</p><p><a href="reports/AUDIT-1.0.3.md">Test scope and remaining gates</a> · <a href="manifest.json">Hashes and evidence manifest</a> · <a href="verification/verified.json">Automated verification</a></p><details><summary>Watch the actual browser walkthrough</summary><video controls preload="none" src="walkthrough/Atelier-1.0.3-Walkthrough.webm"></video><p>Sample data; no audio; native commands are fixture doubles.</p></details></header><main><div id="filters"></div><nav><span id="count" role="status"></span><button id="previous">Previous</button> <button id="next">Next</button></nav><div id="grid"></div></main><script src="gallery-data.js"></script><script>
let page=0;const fields=['category','world','screen','viewport'],filters={};
for(const key of fields){const label=document.createElement('label');label.textContent=key[0].toUpperCase()+key.slice(1);const select=document.createElement('select');select.append(new Option('All',''));for(const value of [...new Set(captures.map(r=>r[key]))].sort())select.append(new Option(value,value));label.append(select);document.getElementById('filters').append(label);filters[key]=select;select.onchange=()=>{page=0;render()};}
function render(){const rows=captures.filter(r=>fields.every(k=>!filters[k].value||r[k]===filters[k].value));const first=page*24;const grid=document.getElementById('grid');grid.replaceChildren();for(const r of rows.slice(first,first+24)){const f=document.createElement('figure'),a=document.createElement('a'),img=document.createElement('img'),c=document.createElement('figcaption'),s=document.createElement('small');a.href=r.file;a.target='_blank';a.rel='noopener';img.src=r.file;img.loading='lazy';img.alt=r.world+' · '+r.screen+' · '+r.viewport;a.append(img);c.textContent=img.alt;s.textContent=r.category;c.append(s);f.append(a,c);grid.append(f)}document.getElementById('count').textContent=rows.length?`${first+1}–${Math.min(first+24,rows.length)} of ${rows.length}`:'No matching captures';document.getElementById('previous').disabled=page===0;document.getElementById('next').disabled=first+24>=rows.length;}
document.getElementById('previous').onclick=()=>{page--;render()};document.getElementById('next').onclick=()=>{page++;render()};render();</script></html>'''
if __name__=='__main__':main()

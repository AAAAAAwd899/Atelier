"""Focused audit evidence: actual historical/current browser captures, not mockups."""
from pathlib import Path
from PIL import Image
import base64,io,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist';S=ROOT/'screenshots/usability'
CASES=[
 ('home','Continue work on the home','after-home.png','Current build · drafts, saved practice and repairs near the top.'),
 ('drafts','Drafts & approval','drafts-inbox.png','Current build · one cross-project draft inbox, original approval flow.'),
 ('editor','Current-draft approval','after-card-studio.png','Current build · review beside the editor, no automatic publication.'),
 ('import','Project-scoped import','import-sources.png','Current build · original importers, explicit destination project.'),
 ('practice','Choose the intended exam','practice-plan-choice.png','Current build · unmatched or ambiguous focus never silently selects a different plan.'),
 ('narrow-home','Home in a narrow window','home-390.png','Current build · browser viewport test, not Windows DPI evidence.'),
 ('narrow-editor','Card Studio in a narrow window','card-studio-390.png','Current build · same controls and local draft, responsive layout.'),
 ('before-home','Before: buried draft route','before-home.png','Historical rc2 baseline · same test collection, before the usability corrections.'),
 ('before-editor','Before: separate editor workflow','before-card-studio.png','Historical rc2 baseline · not the current installer.')]
data=[];manifest=[]
for ident,title,name,caption in CASES:
 p=S/name;im=Image.open(p).convert('RGB');im.thumbnail((1440,2100));f=io.BytesIO();im.save(f,'WEBP',quality=88,method=3)
 data.append({'id':ident,'title':title,'caption':caption,'image':'data:image/webp;base64,'+base64.b64encode(f.getvalue()).decode()})
 manifest.append({'id':ident,'historical':ident.startswith('before-'),'source':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':Image.open(p).size})
html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier — Usability audit</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1c17;color:#e7eee6;font:15px/1.6 system-ui,sans-serif}main{max-width:1480px;margin:auto;padding:36px 24px}header{max-width:920px}small,p{color:#b7cabc}h1{font:500 clamp(30px,4vw,50px)/1.18 Georgia,serif;margin:12px 0}nav{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}button{font:inherit;font-size:13px;background:#183228;color:inherit;border:1px solid #3b604b;border-radius:9px;padding:10px 13px;cursor:pointer}button[aria-pressed=true]{background:#c1d398;color:#182a1a}button:focus-visible{outline:3px solid #d2e4ad;outline-offset:2px}h2{font-size:22px;margin:20px 0 6px}figure{margin:12px 0;border:1px solid #3b604b;border-radius:12px;overflow:hidden;background:#11271e}img{display:block;width:100%;height:auto}figcaption{padding:14px 18px;font-size:12px;color:#c8d7c8}footer{font-size:12px;margin-top:24px;padding-top:18px;border-top:1px solid #3b604b}#stage{max-width:1440px}body[data-narrow=true] #stage{max-width:520px}#version{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#c0d399}@media(max-width:600px){main{padding:22px 12px}nav{gap:6px}button{font-size:12px;padding:8px 10px}}
</style></head><body><main><header><span id="version">Atelier VERSION / Usability & debugging</span><h1>The right action,<br>where the work happens.</h1><p>Actual browser captures of the integrated app. Current screens show the audited routes, not a new theme concept. The two Before views are preserved rc2 evidence.</p></header><nav id="views" aria-label="Audit screens"></nav><section id="stage"><h2 id="title"></h2><figure><img id="capture" alt=""><figcaption id="caption"></figcaption></figure></section><footer>Fictional/sample data, real shipped frontend, explicit native/collection test doubles. Browser previews do not operate on your collection. Native Windows/Anki, real approval/Undo, image occlusion, media, Sync, Onigiri and display scaling still need acceptance testing. Nothing has been published.</footer></main><script>
const data=DATA;let current=0;const nav=document.getElementById('views');for(const [i,item] of data.entries()){const b=document.createElement('button');b.textContent=item.title;b.onclick=()=>{current=i;render()};nav.append(b)}function render(){const x=data[current];document.body.dataset.narrow=String(x.id.startsWith('narrow'));document.getElementById('title').textContent=x.title;document.getElementById('caption').textContent=x.caption;const im=document.getElementById('capture');im.alt=x.title+' — actual browser screenshot';im.src=x.image;for(const [i,b] of [...nav.children].entries())b.setAttribute('aria-pressed',String(i===current))}render();
</script></body></html>'''
version=json.loads((ROOT/'src/manifest.json').read_text())['human_version'];html=html.replace('VERSION',version).replace('DATA',json.dumps(data).replace('</','<\\/'))
(D/'Atelier-Usability-Audit.html').write_text(html)
(D/'Atelier-Usability-Visual-Evidence.json').write_text(json.dumps({'version':version,'captures':manifest},indent=2)+'\n')
for src,dest in [('after-home','Atelier-Audit-Home'),('drafts-inbox','Atelier-Drafts-Inbox'),('after-card-studio','Atelier-Audit-Card-Studio'),('import-sources','Atelier-Import-Sources'),('practice-plan-choice','Atelier-Practice-Plan-Choice'),('home-390','Atelier-Audit-Home-Narrow')]:shutil.copyfile(S/(src+'.png'),D/(dest+'.png'))
print('Nine focused audit captures, self-contained gallery and exported current screenshots.')

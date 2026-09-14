"""Combine fresh real screenshots into the complete ten-screen/world audit.
The gallery is a labelled screenshot viewer, not a native Anki simulator.
"""
from suite_fixtures import ROOT,worlds,core
from pathlib import Path
from PIL import Image,ImageDraw
import base64,io,json,hashlib,shutil
D=ROOT/'dist';S=ROOT/'screenshots'
VIEWS={
 'home':('Study desk','home-polish','home'),
 'library':('Library','home-polish','library'),
 'tools':('Anki tools','home-polish','tools'),
 'setup':('Exam setup','studio-polish','setup'),
 'practice':('Practice builder','studio-polish','practice'),
 'reviewer':('Reviewer','worlds','reviewer'),
 'results':('Results','session-polish','results'),
 'pip':('Pip setup','session-polish','pip'),
 'worlds':('World chooser','world-finish','chooser'),
 'sources':('Sources & Card Studio','complete','sources'),
}
def encoded(path):
 im=Image.open(path).convert('RGB');im.thumbnail((1440,1600));buf=io.BytesIO();im.save(buf,'WEBP',quality=87,method=3)
 return 'data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()
def main():
 proof=json.loads((ROOT/'verification/verified.json').read_text());assert proof['version']==core.VERSION
 audit=json.loads((ROOT/'verification/world-finish/results.json').read_text());assert not audit['errors']
 data=[];manifest=[]
 for w in worlds.CATALOG:
  row={k:w[k] for k in ['id','name','title','description','material','lighting']};row['screens']={}
  for view,(label,folder,suffix) in VIEWS.items():
   p=S/folder/f"{w['id']}-{suffix}.png";row['screens'][view]=encoded(p)
   manifest.append({'world':w['id'],'view':view,'source':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':list(Image.open(p).size)})
  data.append(row)
 for view,(label,folder,suffix) in VIEWS.items():
  sheet=Image.new('RGB',(1440,1320),'#e3e8e0');draw=ImageDraw.Draw(sheet)
  for i,w in enumerate(worlds.CATALOG):
   im=Image.open(S/folder/f"{w['id']}-{suffix}.png").convert('RGB');im.thumbnail((464,294))
   x=(i%3)*480+8;y=(i//3)*330+28;sheet.paste(im,(x,y));draw.text((x,y-20),w['name']+' / '+label,fill='#17271c')
  sheet.save(D/f'Atelier-Final-{view.title()}-Contact-Sheet.png')
 for source,dest in [('world-finish/forest-chooser.png','Atelier-World-Chooser.png'),('home-polish/forest-home.png','Atelier-Forest-Finish.png'),('home-polish/rose-home.png','Atelier-Rose-Finish.png'),('studio-polish/forest-setup.png','Atelier-Setup-Finish.png'),('world-finish/chooser-390.png','Atelier-World-Chooser-Narrow.png'),('worlds/forest-reviewer.png','Atelier-Reviewer-Finish.png')]:shutil.copyfile(S/source,D/dest)
 html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier / Every world, every workflow</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:linear-gradient(155deg,#091b17,#122522 60%,#142627);color:#e7eee7;margin:0;font:15px/1.65 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:40px 28px}header{max-width:920px}.kicker{font-size:11px;letter-spacing:1.6px;color:#bfd198}h1{font:500 clamp(30px,4vw,56px)/1.14 Georgia,serif;margin:14px 0 20px}p{color:#bed0c4;max-width:90ch}.bar{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:30px 0 20px}label{display:flex;gap:10px;align-items:center}select,button{font:inherit;color:inherit;background:#193529;border:1px solid #486755;padding:9px 14px;border-radius:10px;cursor:pointer}button[aria-pressed=true]{color:#1b311d;background:#c3d49d;border-color:#c3d49d}button:focus-visible,select:focus-visible{outline:3px solid #dae9b9;outline-offset:3px}nav{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:22px}.legend{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px 20px}h2{font:500 30px/1.35 Georgia,serif;margin:4px 0}#material{color:#bad0c0;font-size:13px}figure{margin:16px 0}img{display:block;width:100%;border:1px solid #446151;border-radius:12px;background:#10201a}figcaption{font-size:12px;color:#c6d4cc;margin:12px 0}.note{border-top:1px solid #426250;padding-top:18px;font-size:12px}#lighting{font-size:12px;border:1px solid #486755;padding:5px 9px;border-radius:6px}@media(max-width:620px){main{padding:22px 12px}nav button{font-size:12px;padding:8px 10px}select{max-width:220px}h2{font-size:24px}}
</style></head><body><main><header><span class="kicker">ATELIER / VERSION / STUDY, CREATE & ORGANIZE</span><h1>Different places.<br>The same familiar tools.</h1><p>CAPTURECOUNT current-interface captures: WORLDCOUNT worlds across the study desk, library, native toolkit launcher, exam setup, practice builder, reviewer, results, Pip setup, illustrated world chooser, and integrated Card Studio source library.</p></header><div class="bar"><label>World <select id="world" aria-label="Choose study world"></select></label><span id="lighting"></span></div><nav id="views" aria-label="Choose workflow screen"></nav><div class="legend"><h2 id="name"></h2><span id="material"></span></div><figure><img id="capture" alt=""><figcaption id="caption"></figcaption></figure><p class="note">Actual Chromium screenshots of the packaged code, with fictional sample data and explicit host/engine fixtures. This gallery switches images, not live exam records. The reviewer capture uses browser frames and synthetic native-shaped controls; the native Qt practice runner is not pictured. Pip uses its shipped animated fallback. The owner reported visual and primary testing passed. These captures are not independent native Windows, GPU, or third-party compatibility certification. No fonts, external tracking, or online assets are required.</p></main><script>
const data=DATA,labels=LABELS,select=document.getElementById('world'),nav=document.getElementById('views');let current=8,view='home';
for(const [i,w] of data.entries()){const o=document.createElement('option');o.value=i;o.textContent=w.name;select.append(o)}
for(const [id,label] of Object.entries(labels)){const b=document.createElement('button');b.textContent=label;b.dataset.view=id;b.onclick=()=>{view=id;render()};nav.append(b)}
function render(){const w=data[current];select.value=current;document.getElementById('name').textContent=w.name+' / '+w.title;document.getElementById('material').textContent=w.material;document.getElementById('lighting').textContent=(w.lighting==='dark'?'Dark':'Light')+' world';for(const b of nav.children)b.setAttribute('aria-pressed',String(b.dataset.view===view));const im=document.getElementById('capture');im.src=w.screens[view];im.alt=w.name+' — '+labels[view]+' — actual browser screenshot';document.getElementById('caption').textContent=labels[view]+' · Atelier VERSION · Fictional sample records / no native Windows claim';}select.onchange=()=>{current=Number(select.value);render()};render();
</script></body></html>'''.replace('VERSION',core.VERSION).replace('CAPTURECOUNT',str(len(manifest))).replace('WORLDCOUNT',str(len(data))).replace('DATA',json.dumps(data).replace('</','<\\/')).replace('LABELS',json.dumps({k:v[0] for k,v in VIEWS.items()}))
 (D/'Atelier-Complete-Gallery.html').write_text(html,encoding='utf-8')
 (D/'Atelier-Visual-Evidence.json').write_text(json.dumps({'version':core.VERSION,'runtime_sha256':proof['runtime_sha256'],'capture_count':len(manifest),'captures':manifest},indent=2)+'\n')
 print(f'{len(manifest)} real captures / final gallery / 10 contact sheets.')
if __name__=='__main__':main()

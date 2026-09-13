"""Publish actual web-session captures produced by the passing browser suite.
This is an image gallery, not a mocked native Qt runner. No fonts are bundled.
"""
from suite_fixtures import ROOT,worlds,core
from PIL import Image,ImageDraw
import base64,io,json,shutil
D=ROOT/'dist';S=ROOT/'screenshots/session-polish'

def encoded(path):
    im=Image.open(path).convert('RGB');im.thumbnail((1440,1100));b=io.BytesIO();im.save(b,format='WEBP',quality=87,method=3)
    return 'data:image/webp;base64,'+base64.b64encode(b.getvalue()).decode()

def main():
    proof=json.loads((ROOT/'verification/session-polish/results.json').read_text())
    assert proof['count']>0 and not proof['errors']
    D.mkdir(exist_ok=True)
    dataset=[{'id':w['id'],'name':w['name'],'title':w['title'],'screens':{v:encoded(S/f"{w['id']}-{v}.png") for v in ['results','question-detail','pip']}} for w in worlds.CATALOG]
    for source,target in [('forest-results','Atelier-Session-Results'),('forest-question-detail','Atelier-Question-Review'),('forest-pip','Atelier-Pip-Study'),('saved-session','Atelier-Saved-Session'),('results-390','Atelier-Results-Narrow'),('pip-390','Atelier-Pip-Narrow'),('rose-results','Atelier-Results-Rose')]:
        shutil.copyfile(S/(source+'.png'),D/(target+'.png'))
    template='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier · Study sessions & outcomes</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101d19;color:#e7eee7;font:15px/1.6 system-ui}main{max-width:1460px;margin:auto;padding:36px 24px}.kicker{font-size:11px;letter-spacing:1.5px;color:#bdce9e}h1{font:500 clamp(30px,4vw,54px)/1.15 Georgia,serif;margin:16px 0}p{max-width:80ch;color:#b4c7ba}nav{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}button{border:1px solid #45614e;border-radius:9px;background:#1a3025;color:inherit;font:inherit;padding:9px 13px;cursor:pointer}button[aria-pressed=true]{background:#bdd29c;color:#172c1f}button:focus-visible{outline:3px solid #e5ebc7;outline-offset:3px}h2{font:500 25px/1.4 Georgia,serif;margin-bottom:4px}img{display:block;width:100%;border:1px solid #45614e;border-radius:14px}.note{font-size:12px}#subtitle{font-size:12px;color:#b3c4b6}@media(max-width:600px){main{padding:22px 12px}button{font-size:12px;padding:8px 10px}}
</style></head><body><main><header><span class="kicker">ATELIER / VERSION / SESSION SLICE</span><h1>A clearer session.<br>A useful next step.</h1><p>The actual result overview, question-outcome details, and Pip session setup in all twelve worlds. Existing records and scheduling safeguards stay under the original engine.</p></header><nav id="themes" aria-label="Choose world"></nav><h2 id="title"></h2><span id="subtitle"></span><nav id="views" aria-label="Choose screen"></nav><img id="screen" alt=""><p class="note">36 actual Chromium captures of the packaged frontend with fictional data processed by the original assessment engine. This gallery switches screenshots; it is not an Anki collection. The native Qt practice-runner controls are not pictured or native-verified here. Install the .ankiaddon to test those controls in Anki. Native Windows/DPI, real card media, scheduling, and GPU Pip acceptance remain outstanding.</p></main><script>
const data=DATA,labels={results:'Results overview','question-detail':'Question details',pip:'Pip session setup'};let current=8,view='results';function render(){const w=data[current];document.getElementById('themes').replaceChildren(...data.map((x,i)=>{const b=document.createElement('button');b.textContent=x.name;b.setAttribute('aria-pressed',String(i===current));b.onclick=()=>{current=i;render()};return b}));document.getElementById('views').replaceChildren(...Object.entries(labels).map(([id,name])=>{const b=document.createElement('button');b.textContent=name;b.setAttribute('aria-pressed',String(id===view));b.onclick=()=>{view=id;render()};return b}));document.getElementById('title').textContent=w.name;document.getElementById('subtitle').textContent=w.title;const image=document.getElementById('screen');image.src=w.screens[view];image.alt=w.name+' / '+labels[view]+' — actual browser capture';}render();
</script></body></html>'''.replace('VERSION',core.VERSION).replace('DATA',json.dumps(dataset).replace('</','<\\/'))
    (D/'Atelier-Session-Gallery.html').write_text(template,encoding='utf-8')
    for view in ['results','pip']:
        sheet=Image.new('RGB',(1440,4*368),(235,239,231));draw=ImageDraw.Draw(sheet)
        for i,w in enumerate(worlds.CATALOG):
            im=Image.open(S/f"{w['id']}-{view}.png").convert('RGB');im.thumbnail((464,330));x=(i%3)*480+8;y=(i//3)*368+28
            sheet.paste(im,(x,y));draw.text((x,y-20),w['name']+' / '+view,fill=(27,38,30))
        sheet.save(D/f'Atelier-Session-{view.title()}-Contact-Sheet.png')
    print('36 actual result/Pip captures, gallery, contact sheets and supporting images assembled.')
if __name__=='__main__':main()

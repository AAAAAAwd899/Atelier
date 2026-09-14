"""Current-code Home/Library/Tools captures and portable 36-view gallery.
The screenshot gallery never connects to Anki. Data and bridges are synthetic.
"""
from suite_fixtures import *
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
from pathlib import Path
import base64, io, shutil, html as htmlmod
D=ROOT/'dist';D.mkdir(parents=True,exist_ok=True)
S=ROOT/'screenshots/home-polish';S.mkdir(parents=True,exist_ok=True)

def encoded(path):
    im=Image.open(path).convert('RGB');im.thumbnail((1440,1500));buf=io.BytesIO();im.save(buf,format='WEBP',quality=87,method=3)
    return 'data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()

def main():
    errors=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        p=b.new_page(viewport={'width':1440,'height':960});p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(home_suite('forest',page='library'));p.locator('.unified-topbar').wait_for()
        p.locator('[data-action=view][data-view=list]').click();p.wait_for_timeout(80)
        for id in ('10','20','21','22'):
            p.locator(f'.library-row[data-node="{id}"] .card-title').click()
        p.locator('.library-row').first.wait_for();p.screenshot(path=str(D/'Atelier-Library.png'),animations='disabled')
        p.locator('[data-action=up]').first.click();p.locator('.library-row .list-preview-toggle').first.click()
        p.screenshot(path=str(D/'Atelier-Folder-Preview.png'),animations='disabled');p.close()
        p=b.new_page(viewport={'width':390,'height':720});p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(home_suite('forest'));p.locator('.unified-topbar').wait_for();p.screenshot(path=str(D/'Atelier-Narrow-Desk.png'),animations='disabled');p.close()
        # Supplemental list/grid are produced by the same renderer as installation.
        p=b.new_page(viewport={'width':1440,'height':960});p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(home_suite('rose',page='library'));p.locator('.unified-topbar').wait_for();p.locator('[data-action=view][data-view=grid]').click();p.wait_for_timeout(60)
        p.screenshot(path=str(D/'Atelier-Library-Grid.png'),animations='disabled');p.close();b.close()
    assert not errors,errors
    for source,target in [('forest-home','Atelier-Study-Desk'),('forest-tools','Atelier-Anki-Toolkit'),('rose-home','Atelier-Rose-Desk'),('forest-deck-detail','Atelier-Deck-Detail'),('forest-tools-narrow','Atelier-Narrow-Tools')]:
        shutil.copyfile(S/(source+'.png'),D/(target+'.png'))
    (D/'Atelier-Home-Library-Tools-Preview.html').write_text(home_suite('forest'),encoding='utf-8')
    dataset=[{**w,'screens':{view:encoded(S/f"{w['id']}-{view}.png") for view in ('home','library','tools')}} for w in worlds.CATALOG]
    data=json.dumps(dataset).replace('</','<\\/')
    version=core.VERSION
    gallery='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier — Home, Library & Tools</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101c19;color:#e8eee5;font:15px/1.6 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:38px 26px}header{max-width:850px}.eyebrow{font-size:11px;letter-spacing:1.5px;color:#bace9c}h1{font:500 clamp(30px,4.2vw,56px)/1.15 Georgia,serif;letter-spacing:-1px;margin:16px 0}header p,.note{color:#b4c5b9;max-width:80ch}nav{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}button{border:1px solid #476550;border-radius:9px;padding:9px 14px;font:inherit;background:#182e24;color:#e8eee5;cursor:pointer}button:hover{background:#25402e}button[aria-pressed=true]{background:#bfd19c;color:#182916;border-color:#bfd19c}button:focus-visible{outline:3px solid #e4e6c0;outline-offset:3px}.legend{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}h2{font:28px Georgia,serif;margin:10px 0}.legend span{color:#b7c7b9}img{width:100%;display:block;border:1px solid #43634d;border-radius:15px}.note{font-size:12px}.badge{display:inline-block;font-size:11px;padding:4px 8px;border:1px solid #516c56;border-radius:6px}@media(max-width:620px){main{padding:23px 13px}button{padding:7px 10px;font-size:12px}nav{gap:6px}}
</style></head><body><main><header><div class="eyebrow">ATELIER / VERSION / EVERYDAY WORKFLOWS</div><h1>Less searching.<br>More studying.</h1><p>The redesigned study desk, true compact library, and searchable native toolkit. WORLDCOUNT visual worlds, consistent controls, and the existing exam engine.</p><span class="badge">CAPTURECOUNT current-interface screenshots</span></header><nav id="worlds" aria-label="Choose world"></nav><div class="legend"><h2 id="title"></h2><span id="subtitle"></span></div><nav id="views" aria-label="Choose screen"></nav><img id="display" alt=""><p class="note">Real Chromium captures of the packaged interface with fictional sample data and a synthetic bridge. This file switches screenshots; it is not a live Anki collection. Install the .ankiaddon to test in Anki. Native Windows/Qt verification remains outstanding.</p></main><script>
const data=DATA;let current=8,view='home';const labels={home:'Study desk',library:'Library · list view',tools:'Anki tools'};function render(){const world=data[current];document.getElementById('title').textContent=world.name;document.getElementById('subtitle').textContent=world.title;document.getElementById('worlds').replaceChildren(...data.map((w,i)=>{const b=document.createElement('button');b.textContent=w.name;b.setAttribute('aria-pressed',String(current===i));b.onclick=()=>{current=i;render()};return b}));document.getElementById('views').replaceChildren(...Object.entries(labels).map(([key,label])=>{const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-pressed',String(view===key));b.onclick=()=>{view=key;render()};return b}));const image=document.getElementById('display');image.src=world.screens[view];image.alt=world.name+' / '+labels[view]+' — actual browser screenshot';}render();
</script></body></html>'''.replace('VERSION',version).replace('WORLDCOUNT',str(len(dataset))).replace('CAPTURECOUNT',str(len(dataset)*3)).replace('DATA',data)
    (D/'Atelier-Home-Library-Tools-Gallery.html').write_text(gallery,encoding='utf8')
    for view in ('home','library','tools'):
        contact=Image.new('RGB',(1440,4*350),(235,237,230));draw=ImageDraw.Draw(contact)
        for i,w in enumerate(worlds.CATALOG):
            im=Image.open(S/f"{w['id']}-{view}.png").convert('RGB');im.thumbnail((464,310))
            x=i%3*480+8;y=i//3*350+30;contact.paste(im,(x,y));draw.text((x,y-20),w['name']+' / '+view,fill=(24,35,29))
        contact.save(D/f'Atelier-{view.title()}-Slice-Contact-Sheet.png')
    print('Home/Library/Tools gallery, current previews and supplemental navigation captures ready.')
if __name__=='__main__':main()

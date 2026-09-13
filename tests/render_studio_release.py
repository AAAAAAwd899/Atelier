"""Capture the current shipped UI with explicit fictional data. No generated mockup art."""
from planner_suite_fixture import *
from suite_fixtures import home_suite
from playwright.sync_api import sync_playwright
from PIL import Image,ImageDraw
import base64,io,shutil
D=ROOT/'dist';D.mkdir(exist_ok=True);SH=ROOT/'screenshots/studio-release';SH.mkdir(parents=True,exist_ok=True)
def data_image(path):
 im=Image.open(path).convert('RGB');im.thumbnail((1440,1100));buf=io.BytesIO();im.save(buf,format='WEBP',quality=87);return 'data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()
def main():
 errors=[];screens=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for theme in core.THEMES:
   p=b.new_page(viewport={'width':1440,'height':1040});p.on('pageerror',lambda e:errors.append(str(e)));expose(p)
   p.set_content(html(theme));p.locator('[data-action="new"]').first.click();p.locator('[data-field="name"]').fill('Clinical science · Exam 3');p.locator('[data-field="topics"]').fill('Core concepts, lecture notes and applied examples.\nFocus on explaining the answer, not just recognizing it.')
   p.locator('[data-action="next-step"]').click()
   for id in (11,12,13):p.locator(f'[data-special="choose-deck"][data-id="{id}"]').check()
   p.locator('[data-action="next-step"]').click();p.locator('[data-field="daily_minutes"]').fill('75')
   p.locator('[data-action="setup-step"][data-step="1"]').click();p.wait_for_timeout(80);p.screenshot(path=str(SH/(theme+'-setup.png')),animations='disabled')
   if theme=='forest':
    p.locator('[data-action="next-step"]').click();p.screenshot(path=str(D/'Atelier-Deck-Selection.png'),animations='disabled');p.locator('[data-action="next-step"]').click();p.screenshot(path=str(D/'Atelier-Study-Routine.png'),animations='disabled')
   p.close()
   p=b.new_page(viewport={'width':1440,'height':1040});p.on('pageerror',lambda e:errors.append(str(e)));expose(p);p.set_content(html(theme));p.locator('.es-top-nav [data-view="practice"]').click();p.wait_for_timeout(80);p.screenshot(path=str(SH/(theme+'-practice.png')),animations='disabled');p.close()
   screens.append({'id':theme,'name':next(w['name'] for w in worlds.CATALOG if w['id']==theme),'setup':data_image(SH/(theme+'-setup.png')),'practice':data_image(SH/(theme+'-practice.png'))})
  p=b.new_page(viewport={'width':620,'height':700});p.on('pageerror',lambda e:errors.append(str(e)));expose(p);p.set_content(html('forest'));p.locator('.suite-exams-toggle').click();p.locator('[data-action="new"]').first.click();p.locator('[data-field="name"]').fill('Clinical science · Exam 3');p.screenshot(path=str(D/'Atelier-Narrow-Setup.png'),animations='disabled');p.close()
  p=b.new_page(viewport={'width':1440,'height':950});p.set_content(home_suite('forest'));p.locator('.suite-plan').first.wait_for();p.screenshot(path=str(D/'Atelier-Home.png'),animations='disabled');p.close();b.close()
 assert not errors,errors
 for th,dest in [('forest','Atelier-Exam-Setup'),('rose','Atelier-Rose-Setup'),('obsidian','Atelier-Obsidian-Setup'),('midnight','Atelier-Midnight-Setup')]:shutil.copyfile(SH/(th+'-setup.png'),D/(dest+'.png'))
 shutil.copyfile(SH/'forest-practice.png',D/'Atelier-Practice-Builder.png')
 for view in ('setup','practice'):
  im=Image.new('RGB',(1440,4*340),(237,238,234));draw=ImageDraw.Draw(im)
  for i,s in enumerate(screens):
   shot=Image.open(SH/(s['id']+'-'+view+'.png')).convert('RGB');shot.thumbnail((468,306));x=(i%3)*480+6;y=(i//3)*340+26;im.paste(shot,(x,y));draw.text((x,y-18),s['name']+' / '+view,fill=(24,33,29))
  im.save(D/('Atelier-'+view.title()+'-Contact-Sheet.png'))
 gallery='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier Studio · Implemented redesign</title><style>
*{box-sizing:border-box}body{margin:0;background:#101c19;color:#e7eee7;font:15px/1.6 system-ui}main{max-width:1440px;margin:auto;padding:36px 24px}h1{font:500 clamp(30px,4vw,50px)/1.2 Georgia,serif}p{max-width:80ch;color:#b5c4b9}.row{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}button{font:inherit;border:1px solid #496354;color:#dce8dc;background:#1b3027;border-radius:9px;padding:9px 13px;cursor:pointer}button[aria-pressed=true]{background:#bed09b;color:#193020;border-color:#bed09b}button:focus-visible{outline:3px solid #e3eac8;outline-offset:3px}img{width:100%;height:auto;display:block;border:1px solid #496354;border-radius:16px}.note{font-size:12px}small{letter-spacing:1px;color:#bdce9f}
</style><main><small>ATELIER · 0.8.0-rc6 · STUDIO IMPLEMENTATION</small><h1>More room to think.<br>Less interface in the way.</h1><p>The implemented setup and practice-builder layouts, using the packaged frontend. One navigation header, a clearly grouped form, a live summary, and a stable setup action bar.</p><nav class="row" id="themes" aria-label="Choose theme"></nav><nav class="row" id="views" aria-label="Choose view"></nav><img id="screen" alt=""><p class="note">24 real Chromium captures with fictional sample exams. This gallery switches screenshots; it is not a live Anki collection or a native Windows/Qt capture. Install the .ankiaddon for actual Anki testing. No mockup image generation was used.</p></main><script>
const data=DATA;let current=8,view='setup';function render(){document.getElementById('themes').replaceChildren(...data.map((d,i)=>{const b=document.createElement('button');b.textContent=d.name;b.setAttribute('aria-pressed',String(current===i));b.onclick=()=>{current=i;render()};return b}));document.getElementById('views').replaceChildren(...Object.entries({setup:'Exam setup',practice:'Practice builder'}).map(([v,l])=>{const b=document.createElement('button');b.textContent=l;b.setAttribute('aria-pressed',String(view===v));b.onclick=()=>{view=v;render()};return b}));const im=document.getElementById('screen');im.src=data[current][view];im.alt=data[current].name+' — '+view+' — actual current browser rendering';}render();</script></html>'''.replace('DATA',json.dumps(screens)).replace('0.8.0-rc6',core.VERSION)
 (D/'Atelier-Studio-Gallery.html').write_text(gallery)
 print('24 Studio screenshots + narrow/home captured; no page errors.')
if __name__=='__main__':main()

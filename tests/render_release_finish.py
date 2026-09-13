from widget_route_helpers import open_original_provider
"""Render current code with labelled synthetic data; optional supplied art is preview-only.
No runtime assets are changed. Original widget-preservation tests use authored diagrams.
"""
import json,base64,shutil,hashlib,io
from pathlib import Path
from test_release_finish_browser import widget_fixture,core,ROOT,SRC,SH,BeautifulSoup
from suite_fixtures import home_suite
from playwright.sync_api import sync_playwright
from PIL import Image
D=ROOT/'dist';D.mkdir(exist_ok=True)
def page_fixture(theme):
 s=BeautifulSoup(widget_fixture(theme),'html.parser')
 art=SH/'supplied-reward-art.png'
 if art.exists():s.select_one('.restaurant-image')['src']='data:image/png;base64,'+base64.b64encode(art.read_bytes()).decode()
 # Native widget styles are represented here by a labelled provider fixture.
 st=s.new_tag('style');st.string='''.restaurant-info{display:grid;gap:10px}.restaurant-info h3,.restaurant-info p{margin:0}.restaurant-info progress{height:7px;width:100%;accent-color:#80a18a}.restaurant-info button{font:inherit;border:1px solid currentColor;border-radius:8px;padding:7px 10px;background:transparent;color:inherit;justify-self:start}.custom-live-widget{background:var(--ats-panel)!important;color:var(--ats-text)!important;border:1px solid var(--ats-line);font:14px/1.6 system-ui}.custom-live-widget input{background:var(--ats-bg);color:var(--ats-text);border:1px solid var(--ats-line);border-radius:8px;font:inherit}.custom-live-widget button{font:inherit;background:var(--ats-raised);color:var(--ats-text);border:1px solid var(--ats-line);padding:8px 14px;border-radius:8px}.custom-live-widget h3{margin:0 0 10px;font:600 16px system-ui}.fixture-label{font:11px/1.5 system-ui;color:var(--ats-muted);margin:20px 0 0}''';s.head.append(st)
 s.select_one('.restaurant-info p').string='Live rewards · sample data'
 s.select_one('.custom-live-widget h3').string='Your other widgets stay here'
 s.select_one('#retained-input')['value']='An example note · original input remains live'
 s.select_one('#retained-button').string='Widget action'
 lab=s.new_tag('p');lab['class']='fixture-label';lab.string='Preview • fictional counts and provider layout • reward artwork from supplied screenshot • no live Anki collection';s.select_one('.main-content').append(lab)
 return str(s)
def render():
 captures=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':900});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  for th in core.THEMES:
   p.close();p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)))
   p.set_content(page_fixture(th));p.locator('.nav-row').first.wait_for();open_original_provider(p);p.locator('[data-atelier-native-rail] .studio-rail').wait_for();p.wait_for_timeout(180)
   name=SH/('gallery-'+th+'-widgets.png');p.screenshot(path=str(name),animations='disabled');captures.append((th.title()+' · Widgets',name))
   if th=='ember':shutil.copy(name,D/'Atelier-Widgets.png')
  p.close();p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(page_fixture('ember'));p.locator('.nav-row').first.wait_for();open_original_provider(p);p.locator('.studio-rail').wait_for();p.set_viewport_size({'width':390,'height':820});p.screenshot(path=str(D/'Atelier-Widgets-Narrow.png'),animations='disabled')
  p.close();p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(home_suite('forest'));p.locator('.nav-row').first.wait_for();p.wait_for_timeout(140);p.screenshot(path=str(D/'Atelier-Home.png'),animations='disabled');captures.append(('Study desk',D/'Atelier-Home.png'))
  p.locator('.nav-row[data-action="study-progress"]').click();p.locator('.progress-summary').wait_for();p.screenshot(path=str(D/'Atelier-Study-Progress.png'),animations='disabled');captures.append(('Study progress · illustrative data',D/'Atelier-Study-Progress.png'));p.keyboard.press('Escape')
  p.locator('.nav-row[data-page="tools"]').click();p.locator('[data-action="native-tool"][data-command="export"]').click();p.locator('.export-row').first.wait_for();p.screenshot(path=str(D/'Atelier-Export-Chooser.png'),animations='disabled');captures.append(('Export selection',D/'Atelier-Export-Chooser.png'));b.close();assert not errors,errors
 for original,title,new in [('card-figures.png','Card Studio · lazy figures','Atelier-Card-Figures.png'),('destination.png','Destination search','Atelier-Card-Destination.png'),('pip-groups.png','Pip · active study groups','Atelier-Pip-Groups.png')]:
  shutil.copy(SH/original,D/new);captures.append((title,D/new))
 entries=[]
 for title,path in captures:
  im=Image.open(path).convert('RGB');im.thumbnail((1440,1400));buf=io.BytesIO();im.save(buf,'WEBP',quality=89,method=3);entries.append({'name':title,'image':'data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()})
 html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier 0.9.0-rc4 · Release finish</title><style>*{box-sizing:border-box}body{background:#111e1a;color:#e4ebe4;margin:0;font:15px/1.6 system-ui}main{max-width:1460px;margin:auto;padding:32px 24px}h1{font:500 clamp(30px,4vw,48px)/1.2 Georgia}p{max-width:100ch;color:#bbcabd}select{padding:12px;border:1px solid #58775d;background:#1e3528;color:#eef4e8;border-radius:10px;font:inherit;max-width:100%;margin:12px 0 22px}img{width:100%;display:block;border:1px solid #506c56;border-radius:12px}small{color:#bfcfc3}</style><main><h1>A calmer home.<br>Less waiting. Clearer next steps.</h1><p>Current 0.9.0-rc4 browser renders: twelve compact widget worlds, home, read-only progress, export/destination selection, figure loading and active-group Pip. Data and host interactions are illustrative. Native Windows Anki/Onigiri, Qt PDF, rewards and image decoding remain acceptance checks. The building artwork is cropped from the supplied screenshot; it is not a new runtime asset or a cloned game.</p><label>Screen <select id="pick"></select></label><img id="shot" alt=""><small id="caption"></small></main><script>const data=DATA;const p=document.getElementById('pick');for(let i=0;i<data.length;i++){let o=document.createElement('option');o.value=i;o.textContent=data[i].name;p.append(o)}function show(){let d=data[+p.value];document.getElementById('shot').src=d.image;document.getElementById('shot').alt=d.name;document.getElementById('caption').textContent=d.name+' · actual Chromium screenshot · sample data, not native Anki';}p.onchange=show;p.value=10;show();</script></html>'''.replace('DATA',json.dumps(entries).replace('</','<\/'))
 (D/'Atelier-Release-Finish-Gallery.html').write_text(html,encoding='utf8')
 (D/'Atelier-Widgets-Preview.html').write_text(page_fixture('ember'),encoding='utf8')
 (D/'Atelier-Release-Finish-Visuals.json').write_text(json.dumps({'version':core.VERSION,'images':[{'name':title,'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for title,p in captures],'source':'current renderer / sample data / provider fixture / supplied preview-only cropped building art'},indent=2)+'\n')
 print(len(captures),'current images')
if __name__=='__main__':render()

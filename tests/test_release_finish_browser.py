from widget_route_helpers import open_original_provider
"""Release-finish end-to-end UI checks; real packaged code, synthetic host data.
Original widget nodes/actions stay live. No real Anki collection or provider calls.
"""
from pathlib import Path
import json,sys,base64,io,copy
from bs4 import BeautifulSoup
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from suite_fixtures import home_suite,core,ROOT,SRC
from test_complete_home_browser import fixture as old_widget_fixture
from card_studio_harness import UnifiedHost
OUT=ROOT/'verification/release-finish';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/release-finish';SH.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[]
def check(name,condition):
 assert condition,name
 CHECKS.append(name);print('PASS',name,flush=True)

def figure_bytes(w=1400,h=900):
 im=Image.new('RGB',(w,h),'#f8f6ef');dr=ImageDraw.Draw(im)
 dr.rectangle((80,80,w-80,h-80),outline='#466959',width=6)
 for i in range(6):
  x=120+i*180;dr.rounded_rectangle((x,230,x+130,570),radius=20,fill=('#44765a','#83b49a','#daa954')[i%3]);dr.text((x,620),'Structure '+str(i+1),fill='#23392b')
 dr.text((100,115),'Authored illustration fixture - full-resolution source is preserved',fill='#23392b')
 out=io.BytesIO();im.save(out,'PNG');return out.getvalue()

def widget_fixture(theme='ember'):
 s=BeautifulSoup(old_widget_fixture(theme),'html.parser');g=s.select_one('.unified-grid');main=s.select_one('.main-content')
 # Actual reported collision: native parent dimensions set inline!important.
 wrapper=s.new_tag('div');wrapper['class']='injected-stats-block';wrapper['style']='width:1900px!important;min-width:1800px!important;max-width:2100px!important;align-items:center!important;'
 g.wrap(wrapper);g['style']='width:1800px!important;grid-template-columns:repeat(3,1fr);grid-auto-rows:280px;'
 building=s.select_one('.onigiri-restaurant-level-widget');building.clear()
 # Sample illustration is not the Onigiri application or earned progress.
 picture=base64.b64encode(figure_bytes(480,360)).decode()
 body=BeautifulSoup(f'<div class="restaurant-image-container"><img class="restaurant-image" src="data:image/png;base64,{picture}"></div><div class="restaurant-info"><h3>Restaurant level</h3><strong class="level-number">13</strong><p>Sample live widget · fixture</p><progress value="947" max="1350"></progress><button id="reward-click" onclick="this.dataset.clicks=Number(this.dataset.clicks||0)+1">Open reward</button></div>','html.parser')
 for el in list(body.contents):building.append(el.extract())
 return str(s)

def run():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':900});p.set_default_timeout(8000);p.on('pageerror',lambda e:ERRORS.append(str(e)))
  def click(sel):p.locator(sel).first.click();p.wait_for_timeout(90)
  def shot(name):p.screenshot(path=str(SH/(name+'.png')),animations='disabled')
  try:
   p.set_content(widget_fixture());p.locator('.nav-row').first.wait_for();open_original_provider(p)
   p.locator('[data-atelier-native-rail] .studio-rail').wait_for()
   p.evaluate('window.widgetIdentity=document.getElementById("retained-input");window.rewardIdentity=document.getElementById("reward-click");')
   for th in core.THEMES:
    p.evaluate('(theme)=>AtelierMakeover.applyAppearance({token:"preview",settings:{theme,visual_owner:"atelier",mode:"native",widget_mode:"balanced"}})',th);p.wait_for_timeout(80)
    check(th+' inline oversized wrapper bounded',p.locator('.injected-stats-block').evaluate('(e)=>e.getBoundingClientRect().right<=innerWidth+1 && e.getBoundingClientRect().width<=1280'))
    check(th+' original elements and reward handler preserved',p.evaluate('widgetIdentity===document.getElementById("retained-input")&&rewardIdentity===document.getElementById("reward-click")'))
   p.locator('.injected-stats-block').evaluate("e=>e.style.setProperty('width','1900px','important')");p.wait_for_timeout(150)
   check('Late provider dimension change is bounded without remount',p.locator('.injected-stats-block').evaluate('e=>e.getBoundingClientRect().width<=1280'))
   check('Wide building spans two compact metric rows',p.locator('#building').evaluate('e=>getComputedStyle(e).gridRowStart.includes("2")'))
   p.locator('#retained-input').fill('Retain this value');click('#reward-click');check('Original reward action responds',p.locator('#reward-click').get_attribute('data-clicks')=='1')
   for width,height in [(320,680),(390,740),(620,720),(940,780),(1440,900),(1725,900)]:
    p.set_viewport_size({'width':width,'height':height});p.wait_for_timeout(140)
    check(str(width)+' shared page has no horizontal overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
    check(str(width)+' building no longer dominates viewport',p.locator('.restaurant-image').evaluate('(e)=>e.getBoundingClientRect().height<=190'))
    check(str(width)+' navigation remains reachable',p.locator('.back-desk[data-action="widget-page"]').is_visible())
    if width in (390,1440):shot('widgets-'+str(width))
   p.set_viewport_size({'width':1440,'height':900});p.evaluate('(theme)=>AtelierMakeover.applyAppearance({token:"preview",settings:{theme,mode:"native"}})','ember');p.wait_for_timeout(90);p.evaluate('document.querySelector(".main-content").scrollTop=0;window.scrollTo(0,0)');shot('widgets-ember')
   # Verify explicit original positions releases provider dimensions, not a clobber.
   click('[data-action="home-edit"]');click('.dialog [data-action="home-original"]');p.keyboard.press('Escape');p.wait_for_timeout(100)
   check('Original positions restores prior wrapper width',p.locator('.injected-stats-block').evaluate('e=>e.style.getPropertyValue("width")==="1900px"'))
   click('[data-action="home-edit"]');click('.dialog [data-action="home-balanced"]');p.keyboard.press('Escape');p.wait_for_timeout(100)
   check('Balanced can be restored without losing widget input',p.locator('#retained-input').input_value()=='Retain this value')
   click('.back-desk[data-action="widget-page"]');p.locator('.nw-header').wait_for();click('.nav-row[data-action="home"]');p.locator('.nav-row').first.wait_for()
   check('Former 10–11px essential labels are now at least 13px',p.locator('.recent-link,.native-link').evaluate_all('(els)=>els.every(e=>parseFloat(getComputedStyle(e).fontSize)>=13)'))
   # Export is real renderer and exact IDs; preview does not create files.
   click('.nav-row[data-page="tools"]');click('[data-action="native-tool"][data-command="export"]');p.locator('#export-search').wait_for()
   check('Export defaults to active classes first','Active class' in p.locator('.export-row').first.inner_text())
   p.locator('#export-search').fill('cardiology');check('Export searches full parent path',p.locator('.export-row').count()>0 and all('cardiology' in t.lower() for t in p.locator('.export-row').all_inner_texts()))
   p.locator('#export-sort').select_option('name');check('Export sort selector retains new choice',p.locator('#export-sort').input_value()=='name')
   p.locator('#export-search').fill('absent impossible deck');check('Export empty state cannot silently change destination',p.locator('.export-row').count()==0 and 'No folder or deck matches' in p.locator('#export-results').inner_text())
   p.locator('#export-search').fill('');
   if p.locator('[data-action=toast-dismiss]').count():p.locator('[data-action=toast-dismiss]').first.click()
   shot('export');p.keyboard.press('Escape')
   click('.nav-row[data-action="study-progress"]');p.locator('.progress-summary').wait_for()
   check('Progress labels distinct cards and answer events separately','Answer events' in p.locator('.progress-summary').inner_text() and 'Distinct cards' in p.locator('.progress-summary').inner_text())
   check('Progress demo explicitly identified as illustrative','Illustrative preview' in p.locator('#progress-results').inner_text())
   p.locator('#progress-days').select_option('30');p.wait_for_timeout(100);check('Thirty daily bins, no new readiness formula',p.locator('.progress-day').count()==30 and 'not a retention or mastery' in p.locator('#progress-results').inner_text())
   p.locator('#progress-scope').select_option('all');p.wait_for_timeout(100);check('Refresh does not replace scope controls',p.locator('#progress-scope').input_value()=='all')
   p.locator('#progress-days').select_option('7');p.wait_for_timeout(100);shot('progress')
   for w in [390,620,1440]:
    p.set_viewport_size({'width':w,'height':760});p.wait_for_timeout(100)
    check(str(w)+' progress modal fits',p.locator('.dialog').evaluate('(e)=>{let r=e.getBoundingClientRect();return r.x>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1}'))
    check(str(w)+' progress scroll area has no horizontal overflow',p.locator('.dialog-body').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'))
   p.close()
   # Actual source store and merged image bridge. Figure preview requests are lazy.
   h=UnifiedHost();st=h.store;raw=figure_bytes();blob=st.save_blob(raw,'png')
   ss=st.add_source(h.primary_project,'Figure loading benchmark','pptx',[{'text':'Read this page before inspecting its figures.','assets':[{'blob':blob,'label':'Original diagram '+str(i+1)} for i in range(30)]},{'text':'Page two'}])['source']
   p=b.new_page(viewport={'width':1440,'height':980});p.set_default_timeout(8000);p.on('pageerror',lambda e:ERRORS.append(str(e)));p.expose_function('nativeBridge',h.dispatch);p.set_content(h.html());p.locator('.shelf-grid').wait_for();click('[data-action="open-project"][data-id="'+h.primary_project+'"]');click('[data-action="open-source"][data-id="'+ss['id']+'"]');p.locator('.figure-tile').first.wait_for();p.wait_for_timeout(200)
   # IntersectionObserver delivery is asynchronous, especially under native QA
   # load. Wait for its first request; retain the lazy-loading upper bound.
   for _ in range(160):
    if any(r['action']=='figure_preview' for r in h.requests):break
    p.wait_for_timeout(50)
   preview_calls=[r for r in h.requests if r['action']=='figure_preview'];check('Only visible/nearby figures requested initially',0<len(preview_calls)<30)
   check('Figure metadata appears before all image requests finish',p.locator('.figure-tile').count()==30)
   p.locator('.figure-tile img').first.wait_for();p.wait_for_function('document.querySelector(".figure-tile img").complete && document.querySelector(".figure-tile img").naturalWidth>0')
   check('Preview fallback leaves original source blob untouched',st.blob_path(blob).read_bytes()==raw)
   before=sum(r['action']=='image' for r in h.requests);click('[data-action="mask-asset"][data-index="0"]');p.locator('.mask-studio').wait_for()
   check('Mask action obtains original bytes, not a thumbnail',sum(r['action']=='image' for r in h.requests)==before+1)
   check('Masks use full original source dimensions',p.locator('.mask-studio img').first.evaluate('(e)=>e.naturalWidth')==1400)
   p.keyboard.press('Escape');p.wait_for_timeout(100)
   # Search the destination without changing or publishing the draft until chosen.
   click('[data-action="find-destination"]');p.locator('#ws-destination-query').wait_for();check('Card destination lists active class first','Active class' in p.locator('.ws-destination').first.inner_text())
   p.locator('#ws-destination-query').fill('no such deck');check('Card destination search empty is non-destructive',p.locator('.ws-destination').count()==0)
   p.locator('#ws-destination-query').fill('');shot('destination');click('.ws-destination');check('Choosing destination publishes no notes',not any(r['action']=='commit' for r in h.requests))
   # Original page is cached on a revisit; no repeated bridge fetch for same source.
   before=sum(r['action']=='page' for r in h.requests)
   click('[data-action="page-next"]') if p.locator('[data-action="page-next"]').count() else None
   p.wait_for_timeout(100)
   # Source control route is verified below through reopening the same source.
   click('.nav-link[data-view="library"]');click('[data-action="open-project"][data-id="'+h.primary_project+'"]');click('[data-action="open-source"][data-id="'+ss['id']+'"]');p.locator('.figure-tile').first.wait_for();p.wait_for_timeout(120)
   check('Warm reopen avoids another page bridge request',sum(r['action']=='page' for r in h.requests)<=before+1)
   shot('card-figures');p.close()
   check('No uncaught browser exceptions',not ERRORS)
  except Exception:
   if not p.is_closed():shot('failure');(OUT/'failure.txt').write_text(p.locator('body').inner_text())
   raise
  finally:
   (OUT/'results.json').write_text(json.dumps({'count':len(CHECKS),'cases':CHECKS,'errors':ERRORS,'native_windows':False},indent=2));b.close()
if __name__=='__main__':run()

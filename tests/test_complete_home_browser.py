from widget_route_helpers import open_original_provider
"""Home/Card Studio routes and balanced live widgets. Actual renderer, synthetic native widgets."""
from suite_fixtures import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification/complete-home';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/complete';SHOTS.mkdir(parents=True,exist_ok=True)

def fixture(theme='forest'):
 s=BeautifulSoup(home_suite(theme),'html.parser');boot=json.loads(s.find(id='atelier-bootstrap').string)
 boot['authoring']={'available':True,'projects':6,'drafts':3,'repairs':1};boot['demo']['authoring']=boot['authoring']
 s.find(id='atelier-bootstrap').string=core.json_for_html(boot)
 g=s.select_one('.unified-grid');frag=BeautifulSoup('<section class="onigiri-widget-container" id="building" style="grid-column:span 2;grid-row:span 2"><div class="onigiri-restaurant-level-widget"><h3>Restaurant level</h3><strong class="level-number">13</strong><p>Live reward widget test</p><button id="reward-click" onclick="this.dataset.clicks=Number(this.dataset.clicks||0)+1">Open reward</button><progress value="947" max="1350"></progress></div></section><section class="onigiri-widget-container" id="pace"><div class="stat-card"><h3>PACE</h3><p class="stat-value">24 s/card</p></div></section>','html.parser')
 for el in list(reversed(frag.contents)):g.insert(0,el.extract())
 st=s.new_tag('style');st.string='.onigiri-restaurant-level-widget{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;border:1px solid #5c6b45;border-radius:20px;padding:26px;background:#4b5937;color:#dfe7cc}.level-number{font-size:64px}';s.head.append(st)
 return str(s)

def main():
 checks=[];errors=[]
 def check(name,v):
  assert v,name
  checks.append(name);print('PASS',name,flush=True)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':960});p.set_default_timeout(6500);p.on('pageerror',lambda e:errors.append(str(e)))
  def click(sel):p.locator(sel).first.click();p.wait_for_timeout(150)
  def shot(name):p.screenshot(path=str(SHOTS/name),full_page=True)
  try:
   p.set_content(fixture());p.locator('.authoring-hub').wait_for()
   check('Authored Atelier mark is loaded',p.locator('img.brand-mark').evaluate('e=>e.complete&&e.naturalWidth>500&&e.naturalHeight>500'))
   check('Home has one contextual card workspace',p.locator('.authoring-hub').count()==1 and p.locator('.nav-row[data-action="authoring-open"]').count()==1)
   check('Project/draft counts project the same local data','6 source projects' in p.locator('.authoring-hub').inner_text() and '3 drafts' in p.locator('.authoring-hub').inner_text())
   p.evaluate("window.AtelierMakeover.updateAuthoring({token:'preview',authoring:{available:true,projects:7,drafts:4,repairs:2}})")
   check('Source changes update module without full render','7 source projects' in p.locator('.authoring-hub').inner_text())
   p.evaluate("window.AtelierMakeover.updateAuthoring({token:'old-page',authoring:{available:true,projects:99}})")
   check('Stale authoring reply is ignored','99 source projects' not in p.locator('.authoring-hub').inner_text())
   click('.authoring-hub [data-action="authoring-open"][data-view="studio"]')
   check('Home Create uses unified source entry','Card Studio' in p.locator('.app').inner_text());p.keyboard.press('Escape');p.wait_for_timeout(80)
   p.locator('.main').evaluate('(e)=>e.scrollTop=0');p.wait_for_timeout(100);shot('complete-home-forest.png')
   # Test bridge destinations independent of sample notice text.
   click('.lecture-name[data-id="221"]')
   check('Leaf has destination-aware creation',p.locator('[data-action="authoring-open"][data-deck="221"]').count()==1)
   # Visit the real existing widget DOM; save identity/handler/input state.
   p.evaluate('window.keptWidget=document.querySelector("#retained-input");window.keptButton=document.querySelector("#retained-button");window.widgetParent=keptWidget.parentElement;')
   open_original_provider(p)
   p.locator('[data-atelier-native-rail] .studio-rail').wait_for()
   check('Provider has a direct Atelier widgets return',p.locator('.back-desk[data-action="widget-page"]').count()==1)
   check('Widgets no longer show misleading hidden-sidebar instruction','Pin an exam from the sidebar' not in p.locator('[data-atelier-native-rail]').inner_text())
   for w in core.THEMES:
    p.evaluate('(t)=>AtelierMakeover.applyAppearance({token:"preview",settings:{theme:t,visual_owner:"atelier",mode:"native",widget_mode:"balanced"}})',w);p.wait_for_timeout(160)
    check(w+' balanced layout is active',p.locator('.unified-grid').get_attribute('data-atelier-balanced') in ('1','2','4'))
    check(w+' original input identity preserved',p.evaluate('keptWidget===document.querySelector("#retained-input")&&widgetParent===keptWidget.parentElement'))
   p.locator('#retained-input').fill('Live values survive arrangement')
   click('#retained-button');check('Original widget handler remains callable',p.locator('#retained-button').get_attribute('data-clicks')=='1')
   for width in (390,620,940,1440,1725):
    p.set_viewport_size({'width':width,'height':800});p.wait_for_timeout(220)
    check(str(width)+' widget page avoids horizontal overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
    check(str(width)+' known building bounded',p.locator('#building').evaluate('(e)=>e.getBoundingClientRect().width<=innerWidth+1'))
    check(str(width)+' balanced columns match width',p.locator('.unified-grid').get_attribute('data-atelier-balanced') in ('1','2','4'))
   p.set_viewport_size({'width':1440,'height':960});p.wait_for_timeout(150)
   click('[data-atelier-native-rail] [data-action="home-edit"]')
   check('Both layout choices are reachable',p.locator('.dialog [data-action="home-balanced"]').is_visible() and p.locator('.dialog [data-action="home-original"]').is_visible())
   click('.dialog [data-action="home-original"]')
   check('Original positions remove owned placement',p.locator('.unified-grid').get_attribute('data-atelier-balanced') is None)
   click('[data-atelier-native-rail] [data-action="home-edit"]');click('.dialog [data-action="home-balanced"]')
   check('Balanced reapplies from real control',p.locator('.unified-grid').get_attribute('data-atelier-balanced') is not None)
   click('[data-atelier-native-rail] .more-tools summary');p.keyboard.press('Escape')
   check('Escape closes new tools popup',p.locator('.more-tools').get_attribute('open') is None)
   # Removing a shortcut does not alter native widget state.
   old=p.locator('[data-atelier-native-rail] .exam').count();click('[data-atelier-native-rail] [data-action="finish-study"]')
   check('Widget shortcut removal is one click',p.locator('[data-atelier-native-rail] .exam').count()==old-1)
   check('Removal does not discard live widget input',p.locator('#retained-input').input_value()=='Live values survive arrangement')
   click('.back-desk[data-action="widget-page"]');click('.sidebar [data-action="home"]')
   check('Direct return lands on desk, not Library',p.locator('.layout[data-page="desk"]').count()==1)
   check('Original widget never cloned/moved',p.evaluate('keptWidget===document.querySelector("#retained-input")&&keptButton===document.querySelector("#retained-button")&&keptWidget.parentElement===widgetParent'))
   check('No browser errors',not errors)
  except Exception:
   shot('home-failure.png');(OUT/'failure.txt').write_text(p.locator('body').inner_text());raise
  finally:
   (OUT/'results.json').write_text(json.dumps({'count':len(checks),'cases':checks,'errors':errors,'native_windows':False},indent=2));b.close()
 print('TOTAL',len(checks))
if __name__=='__main__':main()

"""Routes with a provider already loaded and an old saved native view.
Uses the shipped renderer, live-style JS bridge, actual upgrade helper, and a
provider-shaped fixture. This is not Windows/Qt or Onigiri native execution.
"""
from pathlib import Path
import copy,json,importlib
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from test_native_widgets_browser import native_fixture
from fixtures import ROOT,SRC,core,guard
from widget_route_helpers import open_original_provider
nw=importlib.import_module('atelier_testing.native_widgets')
OUT=ROOT/'verification/widget-routing';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/widget-routing';SH.mkdir(parents=True,exist_ok=True)

def route_fixture(owner='atelier',mode='workspace',migrate=False,onigiri=True,theme='ember',page='desk',missing=False):
 s=BeautifulSoup(native_fixture(theme,onigiri=onigiri,page=page),'html.parser')
 boot=json.loads(s.find(id='atelier-bootstrap').string)
 cfg={**boot['settings'],'visual_owner':owner,'mode':mode}
 p=core.profile_settings({**boot['profile'],'surfaces_version':1})
 if migrate:
  cfg,p,recovered=nw.widget_route_upgrade(cfg,p)
  if recovered:boot['ui']={'page':'widgets','location':'0','query':'','filter':'all'}
 boot['settings']=cfg;boot['profile']=p
 boot['demo']['settings']=dict(cfg);boot['demo']['profile']=copy.deepcopy(p)
 s.find(id='atelier-bootstrap').string=core.json_for_html(boot)
 br=next(x for x in s.find_all('script') if 'window.widgetCalls=[]' in (x.string or ''))
 t=br.string
 begin=t.index('window.widgetSaved=')+len('window.widgetSaved=');end=t.index(';window.widgetFailPrefs',begin)
 t=t[:begin]+core.json_for_html(boot['demo'])+t[end:]
 t=t.replace('window.widgetFailPrefs=false;', 'window.widgetFailPrefs=false;window.widgetFailSettings=false;')
 t=t.replace("else if(req.action==='settings'){Object.assign(widgetSaved.settings,d);result=widgetSaved.settings;}","else if(req.action==='settings'){if(widgetFailSettings){widgetFailSettings=false;error='Fixture settings are read-only. Your original view is unchanged.';}else{Object.assign(widgetSaved.settings,d);result=JSON.parse(JSON.stringify(widgetSaved.settings));}}")
 br.string=t
 # Use exactly the production prepaint function for the effective bootstrap.
 for node in list(s.find_all('script')):
  if 'window.AtelierPaint=Object.freeze' in (node.string or ''):node.decompose()
 for key in ['atelier-paint-style','atelier-shared-style']:
  node=s.find(id=key)
  if node:node.decompose()
 for el in list(BeautifulSoup(guard.home_guard(cfg),'html.parser').contents):s.head.append(el.extract())
 if missing:
  for node in list(s.find_all('script')):
   if (node.string or '').startswith('/* Atelier-owned widgets,'):node.decompose()
 return str(s)

def run():
 checks=[];errors=[]
 def check(name,v):
  assert v,name
  checks.append(name);print('PASS',name,flush=True)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':950});p.set_default_timeout(6500);p.on('pageerror',lambda e:errors.append(str(e)))
  def ready(html):
   p.goto('about:blank')  # New document: mirrors Anki webview replacement
   p.set_content(html)
   p.wait_for_function('window.AtelierMakeover?.diagnostics().loaded===true')
   p.wait_for_timeout(80)
  def click(sel):p.locator(sel).first.click();p.wait_for_timeout(90)
  def diag():return p.evaluate('AtelierMakeover.diagnostics()')
  def native():p.locator('.native-widgets').wait_for();p.locator('.nw-metrics').wait_for()
  def provider():p.locator('.studio-rail').wait_for()
  try:
   ready(route_fixture(mode='native',migrate=True));native()
   check('rc5 saved Atelier provider view upgrades to own Widgets on first opening',diag()['surface']=='atelier-widgets')
   check('Original provider exists but cannot paint over the built-in page',p.locator('.modern-main-menu').count()==1 and p.evaluate('getComputedStyle(document.body).opacity==="0"') and p.locator('.native-widgets').is_visible())
   check('Upgrade keeps owner selection',p.evaluate('widgetSaved.settings.visual_owner')=='atelier')
   check('Only three top widget actions',p.locator('.nw-toolbar button').all_text_contents()==['Quick study','Practice exam','More tools'])
   check('Built-in page explains its independence','Onigiri not required' in p.locator('.native-widgets').inner_text())
   p.screenshot(path=str(SH/'upgraded-widgets.png'),animations='disabled')
   # Old configuration without an upgrade demonstrates the legacy route. A
   # visible return now goes to Widgets directly, not a menu within a menu.
   ready(route_fixture(mode='native'));provider()
   check('Provider heading cannot be confused with built-in Widgets',p.locator('.studio-rail .wordmark').inner_text()=='Onigiri rewards & widgets')
   check('Direct back-to-Widgets control is visible without opening More tools',p.locator('.back-desk[data-action="widget-page"]').is_visible())
   check('Provider layout editor is labelled separately','provider' in p.locator('.heading [data-action="home-edit"]').inner_text())
   p.evaluate('window.kept=document.querySelector("#retained-input");window.keptParent=kept.parentElement;')
   p.locator('#retained-input').fill('Preserved provider input')
   click('.back-desk[data-action="widget-page"]');native()
   check('Provider header return opens owned Widgets',diag()['surface']=='atelier-widgets' and diag()['mode']=='workspace')
   check('Return keeps original provider nodes and input',p.evaluate('kept===document.querySelector("#retained-input")&&kept.parentElement===keptParent&&kept.value==="Preserved provider input"'))
   check('Heading receives focus after route',p.evaluate('document.querySelector("#atelier-root").shadowRoot.activeElement?.tagName')=='H1')
   p.wait_for_timeout(180)
   check('Anki redraw state records Widgets',p.evaluate('widgetCalls.filter(x=>x.action==="ui").at(-1).data.page')=='widgets')
   p.evaluate('AtelierMakeover.reload()');native();p.wait_for_timeout(100)
   check('Home refresh cannot revert a completed Widgets navigation',diag()['surface']=='atelier-widgets')
   click('.nw-toolbar [data-action="nw-tools"]')
   check('Onigiri opening is explicitly called original page','Onigiri rewards — original page' in p.locator('.nw-tools-list').inner_text())
   click('[data-action="nw-original"]');provider()
   check('Explicit provider command still opens original reward content',diag()['surface']=='original-provider' and p.locator('#retained-input').input_value()=='Preserved provider input')
   click('#retained-button');check('Original provider handler remains active',p.locator('#retained-button').get_attribute('data-clicks')=='1')
   p.screenshot(path=str(SH/'explicit-provider.png'),animations='disabled')
   click('.back-desk[data-action="widget-page"]');native()
   click('.nw-header [data-action="nw-arrange"]')
   check('Built-in Arrange opens the built-in catalog, never provider arrangement',p.locator('.nw-arranged-list').count()==1 and p.locator('.home-widget-list').count()==0)
   p.keyboard.press('Escape')
   for theme in core.THEMES:
    ready(route_fixture(theme=theme))
    click('.sidebar .native-link[data-action="widget-page"]');native()
    check(theme+' sidebar Widgets is the owned page with Onigiri loaded',diag()['surface']=='atelier-widgets')
    check(theme+' provider rail is not visible behind it',not p.locator('.studio-rail').is_visible() if p.locator('.studio-rail').count() else True)
    click('.sidebar [data-action="home"]')
    click('.help-strip [data-action="widget-page"]');native()
    check(theme+' footer uses the same owned destination',diag()['surface']=='atelier-widgets' and p.locator('.help-strip [data-action="native"]').count()==0)
   # Passive owner means their saved appearance is not rewritten, even when
   # accessing Atelier Widgets temporarily through its companion dock.
   for owner in ['onigiri','external']:
    ready(route_fixture(owner=owner,mode='native',migrate=True))
    check(owner+' owner not automatically migrated into Atelier',diag()['mode']=='native' and p.locator('.companion-dock').is_visible())
    snap=p.evaluate('nativeSnapshot()')
    click('.dock-details summary');click('.dock-popover [data-action="widget-page"]');native()
    check(owner+' companion can open built-in Widgets without changing ownership',p.evaluate('widgetSaved.settings.visual_owner')==owner and diag()['surface']=='atelier-widgets')
    click('.nw-toolbar [data-action="nw-tools"]');click('[data-action="nw-original"]')
    p.locator('.companion-dock').wait_for();p.wait_for_timeout(100)
    check(owner+' roundtrip restores exact original markup/colors/geometry',p.evaluate('nativeSnapshot()')==snap)
   for onigiri in [False,True]:
    ready(route_fixture(onigiri=onigiri))
    check(str(onigiri)+' stale external Widgets call ignored',p.evaluate('AtelierMakeover.openWidgets({token:"old-page"})') is False and diag()['page']=='desk')
    check(str(onigiri)+' trusted current page Widgets call succeeds',p.evaluate('AtelierMakeover.openWidgets({token:"preview"})') is True)
    native();check(str(onigiri)+' direct call reaches builtin page',diag()['surface']=='atelier-widgets')
   # A failed settings write must not claim to have entered the new page.
   ready(route_fixture(mode='native'));provider();p.evaluate('widgetFailSettings=true')
   click('.back-desk[data-action="widget-page"]')
   check('Failed mode save keeps original provider visible and reports error',diag()['surface']=='original-provider' and 'read-only' in p.locator('.toast').inner_text())
   click('.back-desk[data-action="widget-page"]');native()
   check('Retry can enter Widgets after failed save',diag()['surface']=='atelier-widgets')
   # A settings reply from an older click cannot defeat a newer click.
   ready(route_fixture(mode='native'));p.evaluate('widgetDelay=180')
   p.locator('.back-desk[data-action="widget-page"]').click()
   p.locator('.sidebar [data-action="home"]').first.click()
   p.wait_for_timeout(450)
   check('A later Study desk click wins over a pending widget transition',diag()['page']=='desk' and diag()['mode']=='workspace')
   # Missing optional JS must report failure, never call the provider fallback.
   ready(route_fixture(missing=True));click('.sidebar .native-link[data-action="widget-page"]')
   check('Missing Widgets component fails explicitly, without provider substitution',diag()['page']=='desk' and diag()['mode']=='workspace' and 'could not load' in p.locator('.toast').inner_text())
   # Test real pointer targets at the sizes associated with the previous report.
   for width,height in [(320,540),(390,740),(620,650),(940,760),(1440,900),(1725,900)]:
    p.set_viewport_size({'width':width,'height':height})
    ready(route_fixture(mode='native'))
    click('.back-desk[data-action="widget-page"]');native()
    check(str(width)+' direct provider-return target opens Widgets',diag()['surface']=='atelier-widgets')
    check(str(width)+' owned page contains its toolbar and content',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+2'))
    click('.nw-header [data-action="nw-arrange"]');p.locator('.nw-arranged-list').wait_for()
    check(str(width)+' Arrange opens owned dialog and Save remains hit-testable',p.locator('[data-action="nw-save"]').evaluate('e=>{const r=e.getBoundingClientRect();return e.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest("button")===e}'))
    p.keyboard.press('Escape')
    if width==390:p.screenshot(path=str(SH/'widgets-390.png'),animations='disabled')
   check('No uncaught script errors',not errors)
  except Exception:
   p.screenshot(path=str(SH/'failure.png'),animations='disabled');raise
  finally:b.close()
 report={'version':core.VERSION,'count':len(checks),'checks':checks,'errors':errors,'native_windows_verified':False,'fixture':'Current renderer, production upgrade helper, live-style bridge and provider-shaped DOM'}
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
 print('CHECKS',len(checks))
if __name__=='__main__':run()

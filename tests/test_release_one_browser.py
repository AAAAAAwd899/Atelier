"""Release-copy checks using packaged UI; browser/collection bridges are fixtures."""
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from suite_fixtures import ROOT,core
from test_native_widgets_browser import native_fixture
import planner_suite_fixture as pf
OUT=ROOT/'verification/release-one';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/release-one';SH.mkdir(parents=True,exist_ok=True)
def main():
 checks=[];errors=[]
 def check(name,v):
  assert v,name
  checks.append(name);print('PASS',name,flush=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=browser.new_page(viewport={'width':1440,'height':950});p.set_default_timeout(9000);p.on('pageerror',lambda e:errors.append(str(e)))
  def close():p.keyboard.press('Escape');p.wait_for_timeout(100)
  try:
   p.set_content(native_fixture('forest'));p.locator('.nw-toolbar').wait_for()
   check('Current version displayed on Widgets', core.VERSION in p.locator('.brand').inner_text() and p.evaluate('AtelierMakeover.version')==core.VERSION)
   check('Accepted three-action toolbar retained',p.locator('.nw-toolbar button').all_text_contents()==['Quick study','Practice exam','More tools'])
   p.screenshot(path=str(SH/'Atelier-1.0-Widgets.png'),animations='disabled')
   p.locator('.nw-toolbar [data-action="nw-tools"]').click();p.locator('.nw-tools-list').wait_for()
   check('Everyday tools retain dispatch identifiers',sorted(p.locator('.nw-tools-list [data-command]').evaluate_all('(els)=>els.map(e=>e.dataset.command)'))==['add','browse','sync'])
   check('Sync exclusion remains visible','local widget notes or layouts' in p.locator('.dialog').inner_text());close()
   for theme in core.THEMES:
    p.evaluate('(theme)=>AtelierMakeover.applyAppearance({token:"preview",settings:{theme}})',theme)
    p.locator('.nw-header [data-action="appearance"]').click();p.locator('.dialog').wait_for()
    check(theme+' consumer explanation visible','Exam Studio is included.' in p.locator('.dialog').inner_text())
    check(theme+' world choices retained',p.locator('[data-theme-choice]').count()==len(core.THEMES))
    check(theme+' settings fit without horizontal scrolling',p.locator('.dialog-body').evaluate('(e)=>e.scrollWidth<=e.clientWidth+2'));close()
   for w in [390,620,1100,1650]:
    p.set_viewport_size({'width':w,'height':760});p.wait_for_timeout(120)
    p.locator('.nw-header [data-action="appearance"]').click();p.locator('.dialog').wait_for()
    p.locator('#setting-review-context').scroll_into_view_if_needed()
    check(str(w)+' context options fit',p.locator('.dialog-body').evaluate('(e)=>e.scrollWidth<=e.clientWidth+2'))
    p.locator('.dialog-footer [data-action="close-dialog"]').click();p.wait_for_timeout(50)
    check(str(w)+' widgets fit',p.locator('.main').evaluate('(e)=>e.scrollWidth<=e.clientWidth+2'))
   # Dispatch the installed-handler error path with a missing exam component.
   # This is a handler fixture, not an invented visible navigation control.
   soup=BeautifulSoup(native_fixture('forest'),'html.parser')
   cfg=json.loads(soup.find(id='atelier-bootstrap').string)
   cfg['integrations']['exam_sprout']=False
   soup.find(id='atelier-bootstrap').string=json.dumps(cfg)
   for node in soup.select('#es-countdowns'):node.decompose()
   p.set_content(str(soup));p.locator('.nw-toolbar').wait_for()
   p.evaluate('''()=>{delete window.ExamSproutCountdown;document.getElementById('es-countdowns')?.remove();const b=document.createElement('button');b.dataset.action='sprout-practice';b.id='release-missing-engine-test';b.style.cssText='position:fixed;top:12px;left:12px;z-index:2147483000;background:white;color:black;padding:12px';b.textContent='Fixture missing component';document.querySelector('#atelier-root').shadowRoot.querySelector('.app').append(b);}''')
   p.locator('#release-missing-engine-test').click();p.locator('.dialog').wait_for()
   check('Installed error does not call the app a preview','Your work has not been changed.' in p.locator('.dialog').inner_text() and 'interface preview' not in p.locator('.dialog').inner_text())
   check('Installed error has a normal Close action',p.locator('.dialog-footer button').inner_text()=='Close');close()
   p.close()
   p=browser.new_page(viewport={'width':1440,'height':1000});p.set_default_timeout(12000);p.on('pageerror',lambda e:errors.append(str(e)));pf.expose(p)
   p.set_content(pf.html('forest'));p.locator('.es-top-nav [data-view="settings"]').wait_for();p.locator('.es-top-nav [data-view="settings"]').click();p.locator('.es-about').wait_for()
   text=p.locator('.es-about').inner_text()
   check('Exam Studio no longer says preview','Exam Studio · included with Atelier' in text and 'Preview release' not in text)
   check('Integrated planner help names the correct menu','Exam Studio stays available from Tools → Atelier.' in p.locator('#es-app').inner_text())
   check('Local exam backup boundary remains visible','Anki Sync does not include this data' in p.locator('#es-app').inner_text())
   p.locator('.es-about').scroll_into_view_if_needed();p.screenshot(path=str(SH/'Atelier-1.0-Exam-Settings.png'),animations='disabled');p.close()
   check('No browser exceptions',not errors)
  except Exception:
   if not p.is_closed():p.screenshot(path=str(SH/'failure.png'),animations='disabled')
   raise
  finally:
   (OUT/'results.json').write_text(json.dumps({'version':core.VERSION,'count':len(checks),'cases':checks,'errors':errors,'native_windows_verified':False},indent=2)+'\n');browser.close()
if __name__=='__main__':main()

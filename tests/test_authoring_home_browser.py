"""Embedded Card Studio launcher with the exact current Atelier home renderer.
Uses authored sample data; no native Anki process or collection is connected.
"""
from suite_fixtures import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification/authoring-home';OUT.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[]
CSS=(SRC/'workshop/web/home.css').read_text()
JS=(SRC/'workshop/web/home.js').read_text()
MARKUP='<section id="ws-home"><button data-ws-open><span><strong>Card Studio</strong><small>Read, mask, and make cards</small></span><span aria-hidden="true">→</span></button></section>'
def check(name,condition):
 assert condition,name
 CHECKS.append(name);print('PASS',name,flush=True)
def main():
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  for theme in core.THEMES:
   page=browser.new_page(viewport={'width':1440,'height':960});page.on('pageerror',lambda e:ERRORS.append(str(e)))
   page.set_content(home_suite(theme));page.locator('.suite-plan').first.wait_for()
   page.evaluate('window.calls=[];window.pycmd=(m)=>calls.push(m)')
   page.add_style_tag(content=CSS);page.add_script_tag(content=JS)
   page.evaluate('(html)=>WorkshopHome.mount(html)',MARKUP)
   check(theme+' current advertised slot used',page.locator('#ws-home').evaluate('(e)=>e.slot==="atelier-widgets"&&e.parentElement.id==="atelier-root"'))
   before=page.locator('.suite-plan').count()
   page.locator('[data-ws-open]').click()
   check(theme+' exactly one Card Studio request',page.evaluate('calls.filter(x=>x==="workshop:open").length')==1)
   for _ in range(5):page.evaluate('WorkshopHome.mount()')
   check(theme+' remount keeps original exam links and controls',page.locator('#ws-home').count()==1 and page.locator('.suite-plan').count()==before and page.locator('.unified-topbar [data-command="add"]').is_visible())
   if theme=='forest':
    for width in (390,680,940):
     page.set_viewport_size({'width':width,'height':800})
     check(str(width)+' library and launcher do not overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and page.locator('#ws-home').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'))
    page.set_viewport_size({'width':1440,'height':960})
    page.screenshot(path=str(OUT/'Atelier_Integrated_Home.png'),full_page=True)
    page.evaluate('window.keepLauncher=document.getElementById("ws-home");document.body.classList.remove("atelier-home");WorkshopHome.mount();')
    check('Classic view restores original launcher position',page.locator('#ws-home').evaluate('(e)=>!e.hasAttribute("slot")&&e.parentElement.id!=="atelier-root"'))
    page.evaluate('document.body.classList.add("atelier-home");WorkshopHome.mount();')
    check('Returning to Atelier keeps node and one handler',page.evaluate('keepLauncher===document.getElementById("ws-home")'))
   page.close()
  check('No uncaught errors in actual combined home',not ERRORS)
  browser.close()
 (OUT/'results.json').write_text(json.dumps({'count':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'native_windows':False,'fixture':'actual current Atelier home + embedded Workshop launcher; synthetic data'},indent=2))
 print('TOTAL',len(CHECKS))
if __name__=='__main__':main()

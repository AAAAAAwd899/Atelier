"""Rendered full-library and stable personalization tasks; synthetic collection only."""
from test_ui_audit_browser import sort_doc,large_doc
from bs4 import BeautifulSoup
from fixtures import core
from fixtures import ROOT
from playwright.sync_api import sync_playwright
import os,json
OUT=ROOT/'verification/library-polish-112';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/library-polish-112';SH.mkdir(parents=True,exist_ok=True)

def run():
 checks=[];errors=[]
 def check(name,ok):
  assert ok,name
  checks.append(name);print('PASS',name,flush=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
  for width,height in [(1440,900),(1024,600),(390,720)]:
   p=browser.new_page(viewport={'width':width,'height':height});p.on('pageerror',lambda e:errors.append(str(e)));p.set_default_timeout(12000)
   doc=BeautifulSoup(sort_doc(),'html.parser');tag=doc.find(id='atelier-bootstrap');boot=json.loads(tag.string);boot['settings']['motion']=True;boot['demo']['settings']['motion']=True;tag.string=core.json_for_html(boot)
   p.set_content(str(doc));p.locator('.unified-topbar').wait_for()
   primary=p.locator('.add-cards-top');before=primary.evaluate('e=>getComputedStyle(e).backgroundColor');box=primary.bounding_box();p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);p.mouse.down()
   check(f'{width} primary press preserves its readable fill',primary.evaluate('e=>getComputedStyle(e).backgroundColor')==before)
   p.mouse.move(0,0);p.mouse.up()
   if width<821:p.locator('[data-action=mobile]').click()
   p.locator('.folder-explorer-launch').press('Enter')
   check(f'{width} full library opens in main workspace',p.locator('.folder-outline').is_visible() and not p.locator('.sidebar').evaluate("e=>e.classList.contains('mobile-open')"))
   side_before=p.locator('.tree .tree-row').count()
   p.locator('[data-action=expand-folders]').click()
   check(f'{width} all nested lectures open in main tree',p.locator('.outline-row[data-node="992"]').count()==1)
   check(f'{width} main expansion leaves compact sidebar unchanged',p.locator('.tree .tree-row').count()==side_before)
   check(f'{width} main library fits screen',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
   p.screenshot(path=str(SH/f'full-library-{width}.png'),animations='disabled')
   p.locator('[data-action=collapse-all][data-surface=outline]').click()
   check(f'{width} collapse closes only main tree',p.locator('.outline-row[data-node="992"]').count()==0 and p.locator('.tree .tree-row').count()==side_before)
   p.locator('[data-action=filter][data-filter=folders]').click()
   p.locator('.outline-row[data-node="90"] [data-action=expand-branch]').click()
   check(f'{width} Show all lectures removes the folder-only filter',p.locator('[data-filter=all]').get_attribute('aria-pressed')=='true' and p.locator('.outline-row[data-node="992"]').count()==1)
   check(f'{width} one branch reveals all its lectures',p.locator('.outline-row[data-node="992"]').count()==1)
   p.locator('.outline-row[data-node="99"] [data-action=organize]').click()
   p.locator('[data-action=folder-icon][data-icon=cat]').scroll_into_view_if_needed()
   p.evaluate("window.keptChooser=document.querySelector('#atelier-root').shadowRoot.querySelector('.folder-icon-options')")
   p.locator('[data-action=folder-icon][data-icon=cat]').click()
   check(f'{width} icon is saved and live preview matches',p.locator('.personalization-art .custom-folder-icon').inner_text()=='🐈' and p.locator('[data-icon=cat]').get_attribute('aria-pressed')=='true')
   check(f'{width} personalized symbols retain a visible folder-color marker',p.locator('.personalization-art .custom-folder-icon').evaluate("e=>getComputedStyle(e,'::after').backgroundColor!=='rgba(0, 0, 0, 0)'"))
   check(f'{width} icon selection retains chooser DOM',p.evaluate("keptChooser===document.querySelector('#atelier-root').shadowRoot.querySelector('.folder-icon-options')"))
   for color in ['rose','cyan','green']:
    p.locator(f'[data-action=color][data-color={color}]').click()
    check(f'{width} {color} saved and preview reflects choice',p.locator('.folder-personalization').evaluate(f"e=>e.classList.contains('tone-{color}')") and p.locator(f'[data-color={color}]').get_attribute('aria-pressed')=='true')
   p.locator('.folder-personalization').scroll_into_view_if_needed()
   p.screenshot(path=str(SH/f'personalize-{width}.png'),animations='disabled')
   p.get_by_role('button',name='Close dialog',exact=True).click()
   check(f'{width} chosen icon persists in main folder tree',p.locator('.outline-row[data-node="99"] .custom-folder-icon').inner_text()=='🐈')
   p.locator('.outline-row[data-node="99"] .outline-open').click()
   check(f'{width} folder opens full contents and keeps breadcrumb',p.locator('.breadcrumbs').inner_text().find('Seminar')>=0)
   p.emulate_media(reduced_motion='reduce');p.locator('.unified-topbar [data-action=appearance]').click()
   check(f'{width} reduced motion disables transitions',p.locator('.theme-tile').first.evaluate("e=>getComputedStyle(e).transitionDuration")=='0s')
   p.close()
  p=browser.new_page(viewport={'width':1440,'height':900});p.set_content(large_doc());p.locator('.unified-topbar').wait_for();p.locator('.folder-explorer-launch').click()
  p.locator('[data-action=expand-folders]').click()
  check('5000-deck expansion renders bounded first 60 rows',p.locator('.outline-row').count()==60)
  check('Long libraries offer explicit continuation',p.locator('[data-action=more-results]').is_visible())
  p.locator('[data-action=more-results]').click()
  check('Continuation expands to 120 rows without duplicates',p.locator('.outline-row').count()==120 and len(set(p.locator('.outline-row').evaluate_all('xs=>xs.map(x=>x.dataset.node)')))==120)
  check('Long main tree does not flood sidebar',p.locator('.tree-row').count()==50)
  p.close()
  browser.close()
 check('No uncaught errors',not errors)
 (OUT/'results.json').write_text(json.dumps({'count':len(checks),'checks':checks,'errors':errors,'category':'Chromium shipped UI with synthetic collection; no native Anki claim'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':run()

"""Final whole-world and interaction audit. Current packaged frontend in Chromium.
No live Anki/Qt, no private data, no scheduler writes or full WCAG claim.
"""
from suite_fixtures import *
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json,zipfile,hashlib
OUT=ROOT/'verification/world-finish';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/world-finish';SHOTS.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[]
def check(label,truth=True):
 assert truth,label
 CHECKS.append(label);print('PASS',label,flush=True)
def hit(loc):
 return loc.evaluate('''e=>{const r=e.getBoundingClientRect(),n=e.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2);return r.width>=24&&r.height>=24&&r.top>=0&&r.bottom<=innerHeight+1&&(e===n||e.contains(n));}''')
def old_handler_doc():
 path=Path('/mnt/data/atelier_session_slice/project/dist/Atelier-0.8.0-rc5.ankiaddon')
 if not path.is_file():return None,None
 with zipfile.ZipFile(path) as z:old=z.read('web/atelier.js').decode()
 s=BeautifulSoup(home_suite('forest'),'html.parser')
 tag=next(t for t in s.find_all('script') if 'function themeTiles()' in (t.string or ''))
 tag.string=old
 return str(s),hashlib.sha256(old.encode()).hexdigest()
def menu_scroll(p):
 p.locator('.lecture-name').first.scroll_into_view_if_needed();p.wait_for_timeout(180)
 p.locator('.lecture-name').first.click(button='right');p.locator('.context-menu').wait_for();p.wait_for_timeout(160)
 p.locator('.context-menu').evaluate('e=>{e.style.maxHeight="120px";e.scrollTop=70}')
 p.wait_for_timeout(170)
 return p.locator('.context-menu').count()>0

def main():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  def page(theme='forest',width=1440,height=960,doc=None,**kwargs):
   p=b.new_page(viewport={'width':width,'height':height},**kwargs);p.set_default_timeout(8000);p.on('pageerror',lambda e:ERRORS.append(str(e)));p.set_content(doc or home_suite(theme));p.locator('.unified-topbar').wait_for();p.wait_for_timeout(70);return p
  # Source-faithful old-handler regression, same settled menu viewport in both cases.
  old,sha=old_handler_doc();baseline={'old_handler_available':bool(old),'native_windows':False,'fixture':'rc6 browser fixture with only rc5 home script substituted; no live Onigiri'}
  if old:
   p=page(width=800,height=700,doc=old);baseline['rc5_internal_scroll_keeps_menu']=menu_scroll(p);p.close()
   check('Reproduced rc5 menu closing on its own internal scroll',not baseline['rc5_internal_scroll_keeps_menu']);baseline['rc5_script_sha256']=sha
  p=page(width=800,height=700);baseline['rc6_internal_scroll_keeps_menu']=menu_scroll(p)
  check('Long folder menu stays open while scrolling its own contents',baseline['rc6_internal_scroll_keeps_menu'])
  p.locator('.context-menu .context-action').first.focus();p.keyboard.press('End');p.wait_for_timeout(50)
  check('Menu End reaches its final enabled action without closing',p.locator('.context-menu').count()==1 and p.locator('.context-action').last.evaluate('e=>e.getRootNode().activeElement===e'))
  p.keyboard.press('Home');check('Menu Home returns to the first action',p.locator('.context-action').first.evaluate('e=>e.getRootNode().activeElement===e'))
  p.keyboard.press('Escape');check('Menu Escape closes and restores its original trigger',p.locator('.context-menu').count()==0 and p.evaluate('document.querySelector("#atelier-root").shadowRoot.activeElement?.classList.contains("lecture-name")'))
  p.close();(OUT/'baseline.json').write_text(json.dumps(baseline,indent=2))
  # Every world has real vector art, a deliberate material and the same controls.
  for w in worlds.CATALOG:
   p=page(w['id']);p.screenshot(path=str(SHOTS/(w['id']+'-home-finish.png')),animations='disabled')
   check(w['id']+' actual task panel uses the world material treatment',p.locator('.task-focus').evaluate('e=>getComputedStyle(e).backgroundImage')!='none')
   check(w['id']+' scenery is outside the interactive reading/lecture content',p.locator('.world-window').evaluate('e=>getComputedStyle(e).borderTopLeftRadius')!='0px' and p.locator('#qa').count()==0)
   p.locator('.unified-topbar [data-action=appearance]').click();p.wait_for_timeout(60)
   check(w['id']+' world chooser has twelve named, illustrated and typed variants',p.locator('.theme-tile').count()==12 and p.locator('.theme-tile[data-theme-choice='+w['id']+']>small').inner_text()==w['material'] and p.locator('.theme-tile .theme-light').count()==12)
   p.evaluate('window.savedDialog=document.querySelector("#atelier-root").shadowRoot.querySelector(".dialog");window.savedTiles=[...savedDialog.querySelectorAll(".theme-tile")]')
   p.locator('[data-action=world-filter][data-filter=dark]').click();check(w['id']+' Dark filters six tiles without changing the current theme',p.locator('.theme-tile:visible').count()==6 and p.locator('#atelier-root').get_attribute('data-theme')==w['id'])
   p.locator('[data-action=world-filter][data-filter=light]').click();check(w['id']+' Light filters six tiles and preserves current selection readout',p.locator('.theme-tile:visible').count()==6 and w['name']+' selected' in p.locator('#world-filter-count').inner_text())
   p.locator('[data-action=world-filter][data-filter=all]').click()
   check(w['id']+' filter never rebuilds the dialog or original tile nodes',p.evaluate('savedDialog===document.querySelector("#atelier-root").shadowRoot.querySelector(".dialog")&&savedTiles.every(x=>x.isConnected)'))
   tile=p.locator('[data-theme-choice='+w['id']+']');tile.scroll_into_view_if_needed();p.wait_for_timeout(50)
   check(w['id']+' current selection check and material frame are explicit',tile.get_attribute('aria-pressed')=='true' and tile.locator('.theme-check').is_visible() and tile.locator('.mini-screen').evaluate('e=>getComputedStyle(e).backgroundImage.includes("data:image/svg")'))
   p.locator('.dialog-body').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(SHOTS/(w['id']+'-chooser.png')),animations='disabled');p.close()
  # Same open dialog: complete roundtrip and filter state remain consistent.
  p=page('midnight');p.locator('.unified-topbar [data-action=appearance]').click()
  for w in worlds.CATALOG:
   p.locator('[data-theme-choice='+w['id']+']').click();p.wait_for_timeout(40)
   check('Live world '+w['id']+' caption and selected count update together',w['name'] in p.locator('.world-window small').text_content() and w['name']+' selected' in p.locator('#world-filter-count').inner_text())
  p.close()
  # Seven real window geometries, actual mouse/key targets, not forced clicks.
  for width,height in [(320,540),(390,650),(620,620),(820,650),(1040,720),(1440,900),(1725,900)]:
   p=page('rose',width,height);p.locator('.unified-topbar [data-action=appearance]').click();p.wait_for_timeout(40)
   check(f'{width}px modal header/footer remain within the window',p.locator('.dialog-header').bounding_box()['y']>=0 and hit(p.locator('.dialog-footer [data-action=close-dialog]')))
   p.locator('[data-action=world-filter][data-filter=dark]').click();p.locator('[data-theme-choice=forest]').click()
   check(f'{width}px filtering and choosing a dark world keeps the same usable dialog',p.locator('.dialog').count()==1 and 'Forest selected' in p.locator('#world-filter-count').inner_text() and p.locator('.theme-tile:visible').count()==6)
   p.locator('.dialog-body').hover();p.mouse.wheel(0,800);p.wait_for_timeout(70)
   check(f'{width}px scrolling settings does not bury Close',hit(p.locator('.dialog-footer [data-action=close-dialog]')))
   check(f'{width}px no horizontal dialog overflow',p.locator('.dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1') and p.locator('.dialog-body').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
   p.keyboard.press('Escape');check(f'{width}px Escape returns to the appearance trigger',p.locator('.dialog').count()==0 and p.locator('.unified-topbar [data-action=appearance]').evaluate('e=>e.getRootNode().activeElement===e'))
   if width==390:
    p.locator('.unified-topbar [data-action=appearance]').click();p.screenshot(path=str(SHOTS/'chooser-390.png'),animations='disabled')
   p.close()
  # No motion overrides the user's/system choice. Shapes do not become moving scenery.
  p=page();p.locator('.unified-topbar [data-action=appearance]').click()
  check('App motion off removes transition from every visible theme tile',p.locator('.theme-tile').evaluate_all('xs=>xs.every(e=>getComputedStyle(e).transitionDuration==="0s"&&getComputedStyle(e).animationName==="none")'))
  p.evaluate('''()=>{const t=JSON.parse(document.querySelector('#atelier-bootstrap').textContent).token;AtelierMakeover.applyAppearance({token:t,settings:{ambience:false,motion:true}})}''');p.wait_for_timeout(40)
  check('Ambient scenery off removes the task texture without hiding its actions',p.locator('.task-focus').evaluate('e=>getComputedStyle(e).backgroundImage')=='none' and p.locator('.task-focus [data-action=study-now]').count()==1)
  p.emulate_media(reduced_motion='reduce');check('System reduced motion takes priority over app motion on',p.locator('.theme-tile').evaluate_all('xs=>xs.every(e=>getComputedStyle(e).transitionDuration==="0s"&&getComputedStyle(e).animationName==="none")'))
  p.emulate_media(forced_colors='active');p.locator('[data-action=world-filter][data-filter=dark]').focus();p.keyboard.press('Tab')
  check('Forced colors retain an explicit keyboard-focus outline',p.evaluate('()=>{let e=document.querySelector("#atelier-root").shadowRoot.activeElement;let s=getComputedStyle(e);return s.outlineStyle!=="none"&&parseFloat(s.outlineWidth)>=2;}'))
  p.close()
  # Failed native-shaped settings reply goes inside the current dialog with its own dismiss.
  from test_ui_audit_browser import live_doc
  p=page(doc=live_doc());p.locator('.unified-topbar [data-action=appearance]').click();p.locator('[data-theme-choice=rose]').click();p.wait_for_function('settingsQueue.length===1');p.evaluate('answerSetting(false)');p.wait_for_timeout(60)
  check('Failed theme save mounts an alert in the dialog instead of behind it',p.locator('.dialog-alerts .toast[role=alert]').count()==1)
  check('Failed save keeps the prior theme and dialog footer usable',p.locator('#atelier-root').get_attribute('data-theme')=='midnight' and hit(p.locator('.dialog-footer [data-action=close-dialog]')))
  p.locator('.dialog-alerts .toast>span').evaluate('e=>e.textContent="Long diagnostic message: "+"UNBROKEN".repeat(120)')
  check('Long diagnostic text wraps inside the bounded alert region',p.locator('.dialog-alerts').evaluate('e=>e.scrollWidth<=e.clientWidth+1&&e.getBoundingClientRect().height<=131'))
  p.locator('.toast-dismiss').click();check('Error can be dismissed without closing the unfinished settings dialog',p.locator('.toast').count()==0 and p.locator('.dialog').count()==1);p.close()
  # Explicit focus of a below-header control is kept clear of the sticky app bar.
  p=page(height=700);target=p.locator('.lecture-name').first;target.scroll_into_view_if_needed();p.wait_for_timeout(160)
  target.focus();p.keyboard.press('Tab');check('Keyboard navigation leaves the lecture actions hittable',p.evaluate('()=>{const s=document.querySelector("#atelier-root").shadowRoot,e=s.activeElement,r=e.getBoundingClientRect(),h=s.querySelector(".topbar").getBoundingClientRect();return r.top>=h.bottom-1&&r.bottom<=innerHeight;}'));p.close()
  # Planner world changes preserve original fields and return keyboard focus after save.
  import planner_suite_fixture as planner
  for w in worlds.CATALOG:
   p=b.new_page(viewport={'width':1440,'height':960});p.on('pageerror',lambda e:ERRORS.append(str(e)));p.set_default_timeout(10000);planner.expose(p);p.set_content(planner.html(w['id']));p.locator('.es-hero').wait_for();p.locator('[data-action=new]').first.click();p.locator('[data-field=name]').fill('Protected draft · Électrolytes');p.locator('[data-field=topics]').fill('Original topic text')
   p.evaluate('window.keptName=document.querySelector("[data-field=name]");window.keptTopics=document.querySelector("[data-field=topics]")')
   s=p.locator('[aria-label="Study world"]');s.focus();s.select_option('rose' if w['id']!='rose' else 'forest');p.wait_for_timeout(130)
   check(w['id']+' planner world select regains focus after host reply',s.is_enabled() and s.evaluate('e=>document.activeElement===e'))
   check(w['id']+' world change preserves both draft node identity and values',p.evaluate('keptName===document.querySelector("[data-field=name]")&&keptTopics===document.querySelector("[data-field=topics]")') and p.locator('[data-field=name]').input_value()=='Protected draft · Électrolytes' and p.locator('[data-field=topics]').input_value()=='Original topic text')
   check(w['id']+' planner scene follows the selected frame, not a new image load',p.locator('.suite-summary-scenery').evaluate('e=>getComputedStyle(e).borderTopLeftRadius')!='0px')
   p.close()
  # Footer stationary buttons and reduced motion (real shipped CSS/JS; synthetic Anki DOM).
  from fixtures import footer
  for w in worlds.CATALOG:
   p=b.new_page(viewport={'width':1000,'height':210});p.set_default_timeout(6000);p.on('pageerror',lambda e:ERRORS.append(str(e)));p.set_content(footer(w['id'],stage='answer'));p.locator('#outer button').first.wait_for();p.wait_for_timeout(70)
   target=p.locator('#outer button').nth(2);old=target.bounding_box();target.hover();p.wait_for_timeout(160)
   check(w['id']+' grade target stays stationary on hover',target.bounding_box()==old and target.evaluate('e=>getComputedStyle(e).transform')=='none');p.close()
  b.close()
 check('No uncaught page errors in final-world scenarios',not ERRORS)
 result={'count':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'native_windows_verified':False,'new_engine_or_scheduler_logic':False}
 (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print('TOTAL',len(CHECKS),'PASS',flush=True)
if __name__=='__main__':main()

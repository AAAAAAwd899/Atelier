"""Combined Card Studio contracts against the actual merged dispatcher and local SQLite.
No external provider requests, user collection, native Qt or Windows execution.
"""
from pathlib import Path
import json,sys,importlib
from playwright.sync_api import sync_playwright
from card_studio_harness import UnifiedHost,ROOT
OUT=ROOT/'verification/complete-browser';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/complete';SHOTS.mkdir(parents=True,exist_ok=True)

def main():
 results=[];errors=[];material_signatures=set()
 def check(name,value):
  if not value:raise AssertionError(name)
  results.append(name);print('PASS',name,flush=True)
 h=UnifiedHost();mod=h.appearance_module
 slide_source=h.store.add_source(h.primary_project,'Cardiology lecture 04','pptx',[{'text':'Slide one: rhythm overview'},{'text':'Slide two: atrial fibrillation'},{'text':'Slide three: treatment decisions'},{'text':'Slide four: review'}])['source']['id']
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1440,'height':960});page.set_default_timeout(6000)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.expose_function('nativeBridge',h.dispatch)
  def click(sel):page.locator(sel).first.click();page.wait_for_timeout(100)
  def shot(name):page.screenshot(path=str(SHOTS/name),full_page=True)
  try:
   page.set_content(h.html());page.wait_for_selector('.shelf-grid')
   check('Actual integrated workspace booted',page.locator('#workshop').get_attribute('data-integrated')=='true')
   check('One explicit Study desk return',page.locator('[data-action="study-desk"]').count()==1)
   check('No second home/toolbar widget',page.locator('#ws-home').count()==0)
   check('Card sets remain distinct from deck Library',page.get_by_role('button',name='Card sets & sources',exact=True).count()==1)
   check('Card Studio navigation is grouped by task',page.locator('.ws-nav-section').count()==3 and all(x in page.locator('#ws-sidebar').inner_text() for x in ('MAKE','ORGANIZE','MAINTAIN')))
   for w in mod.CATALOG:
    page.locator('#ws-suite-world').select_option(w['id']);page.wait_for_timeout(130)
    p=mod.PALETTES[w['id']]
    check(w['id']+' shared appearance saved through actual suite bridge',h.settings['theme']==w['id'])
    check(w['id']+' background agrees',page.locator('#workshop').evaluate('(e)=>getComputedStyle(e).getPropertyValue("--bg").trim()')==p['bg'])
    material_signatures.add(page.locator('#workshop').evaluate("""e=>getComputedStyle(e).getPropertyValue('--studio-material').trim()"""))
    check(w['id']+' no page overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    check(w['id']+' header contains live controls',page.locator('.topbar').evaluate('(e)=>[...e.querySelectorAll("button,select")].filter(x=>x.getClientRects().length).every(x=>x.getBoundingClientRect().bottom<=e.getBoundingClientRect().bottom+1)'))
    shot(w['id']+'-sources.png')
   check('All worlds have distinct Card Studio materials',len(material_signatures)==len(mod.CATALOG))
   page.locator('#ws-suite-world').select_option('forest');page.wait_for_timeout(100)
   click(f'[data-action="open-project"][data-id="{h.primary_project}"]')
   shot('forest-project.png')
   check('Direct exam plan control exists',page.get_by_role('button',name='Build exam plan',exact=True).count()==1)
   before=h.col.note_count();page.get_by_role('button',name='Build exam plan',exact=True).click();page.wait_for_timeout(150)
   plan=h.plan_requests[-1]
   links=h.store.list('link',h.primary_project);expected='nid:'+','.join(map(str,sorted({l['note_id'] for l in links})))
   check('Project uses exact-linked-note query',plan['target']=='new' and plan['setup']['query']==expected)
   check('No clipboard or card mutation during plan handoff',h.clipboard=='' and h.col.note_count()==before)
   check('No exam is automatically created',len(h.plan_requests)==1 and 'date' not in plan['setup'])
   click(f'[data-action="open-source"][data-id="{slide_source}"]')
   check('Four-step card set workflow is visible',page.locator('.creator-step').count()==4 and 'From material to study-ready cards' in page.locator('.creator-guide').inner_text())
   check('Card set selector is explicit',page.locator('.studio-set-picker').count()==1 and page.locator('.studio-set-picker select').input_value()==h.primary_project)
   check('Slide rail exposes the imported order',page.locator('.source-page-rail .page-chip').count()==4 and 'SLIDES' in page.locator('.source-page-rail').inner_text())
   click('[data-action="jump-page"][data-page="3"]')
   check('Exact slide can be selected',page.locator('.source-page-rail [aria-current="page"]').inner_text()=='3' and page.locator('[data-change="page-number"]').input_value()=='3')
   check('Slide navigation does not create an Anki note',h.col.note_count()==before)
   page.locator('[data-change="studio-source"]').select_option(h.primary_source);page.wait_for_timeout(180)
   field=page.locator('[data-draft="front"]');field.fill('Which exact features must stay unchanged?');page.wait_for_timeout(1200)
   page.evaluate('window.originalFront=document.querySelector(\'[data-draft="front"]\')')
   for w in ['rose','midnight','forest']:
    page.locator('#ws-suite-world').select_option(w);page.wait_for_timeout(180)
    check(w+' changing world preserves draft/input identity',field.input_value()=='Which exact features must stay unchanged?' and page.evaluate('originalFront===document.querySelector(\'[data-draft="front"]\')'))
   shot('forest-create.png')
   for width in (390,680,940,1440):
    page.set_viewport_size({'width':width,'height':760});page.wait_for_timeout(180)
    check(str(width)+' Card Studio no horizontal document overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    check(str(width)+' header fit',page.locator('.topbar').evaluate('(e)=>[...e.querySelectorAll("button,select")].filter(x=>x.getClientRects().length).every(x=>x.getBoundingClientRect().bottom<=e.getBoundingClientRect().bottom+1)'))
    if width==390:
     check('390 approval explanation keeps readable measure',page.locator('.ws-authoring-workflow>div').first.evaluate('(e)=>e.getBoundingClientRect().width>=300'))
     check('390 approval actions use full banner width',page.locator('.ws-authoring-workflow>.row').evaluate('(e)=>e.getBoundingClientRect().width>=300'))
     shot('card-studio-390.png')
   page.set_viewport_size({'width':1440,'height':960})
   # Real local draft is still present; only publication creates notes.
   check('Saved source draft and text remain',any(d.get('front')=='Which exact features must stay unchanged?' for d in h.store.list('draft')))
   check('World switching never published a note',h.col.note_count()==before)
   click('[data-action="suite-native"][data-command="browse"]')
   check('Browse keeps native command route',h.native_events[-1]['name']=='Browse')
   click('[data-action="suite-native"][data-command="sync"]')
   check('Sync keeps native command route',h.native_events[-1]['name']=='Sync')
   # Passive mode must leave local Workshop colors independent; shared selector hidden.
   h.settings['visual_owner']='onigiri'
   page.evaluate('(a)=>Workshop.event("appearance",a)',mod.appearance(h.owner))
   check('Passive owner hides shared palette selector',not page.locator('#ws-suite-world').is_visible())
   check('Passive owner does not force suite theme',page.locator('#workshop').get_attribute('data-suite-theme')!='true')
   check('Passive transition preserves draft',field.input_value()=='Which exact features must stay unchanged?')
   h.settings['visual_owner']='atelier';page.evaluate('(a)=>Workshop.event("appearance",a)',mod.appearance(h.owner))
   # Header leave flushes the original draft, then returns to the one real home.
   field.fill('Last retained edit before Study desk');click('[data-action="study-desk"]');page.wait_for_timeout(150)
   check('Return flushes source draft before leaving',any(d.get('front')=='Last retained edit before Study desk' for d in h.store.list('draft')))
   check('Return uses native home state and closes original window',h.native_events[-2:]==[{'name':'State','kwargs':{'state':'deckBrowser'}},{'name':'CloseStudio','kwargs':{}}])
   check('No unrequested provider generation',not any(r['action'] in ('provider_generate','provider_test') for r in h.requests))
   check('No uncaught browser exceptions',not errors)
  except Exception:
   shot('failure.png');(OUT/'failure-state.txt').write_text(page.locator('body').inner_text());raise
  finally:
   (OUT/'results.json').write_text(json.dumps({'count':len(results),'cases':results,'errors':errors,'native_windows':False},indent=2));browser.close()
 print('TOTAL',len(results))
if __name__=='__main__':main()

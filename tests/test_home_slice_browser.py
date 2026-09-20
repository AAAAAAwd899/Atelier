"""Fresh Home/Library/Tools slice. Actual shipped frontend, sample collection.
No native Qt, scheduler writes or user-profile access is represented by these tests.
"""
from suite_fixtures import *
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
OUT=ROOT/'verification/home-polish';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/home-polish';SHOTS.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[]
def check(label,value=True):
 assert value,label
 CHECKS.append(label);print('PASS',label,flush=True)

def doc(theme='forest',page='desk',change=None):
 soup=BeautifulSoup(home_suite(theme,page=page),'html.parser');tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
 if change:change(boot)
 tag.string=core.json_for_html(boot);return str(soup)

def overflow(p):return p.evaluate("()=>{const m=document.querySelector('#atelier-root').shadowRoot.querySelector('.main');return m.scrollWidth>m.clientWidth+1;}")
def hit(loc):
 return loc.evaluate('''e=>{const r=e.getBoundingClientRect(),at=e.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2);return r.width>=24&&r.height>=28&&r.y>=0&&r.bottom<=innerHeight+1&&!!at&&(at===e||e.contains(at));}''')

def run():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),args=['--no-sandbox'])
  def page(html=None,width=1440,height=960):
   p=b.new_page(viewport={'width':width,'height':height});p.set_default_timeout(9000);p.on('pageerror',lambda e:ERRORS.append(str(e)))
   p.set_content(html or doc());p.locator('.unified-topbar').wait_for();p.wait_for_timeout(60);return p
  # All worlds: new composition and no dictionary/key/name drift.
  for w in worlds.CATALOG:
   p=page(doc(w['id']))
   continuation=p.locator('.task-focus [data-action="study-now"]');last=p.evaluate("AtelierMakeover.diagnostics().lastStudied")
   check(w['id']+' Continue targets the actual last eligible lecture',continuation.count()==1 and continuation.get_attribute('data-id')==last)
   check(w['id']+' compact desk exposes lectures ahead of planning modules',p.locator('.task-focus').bounding_box()['height']<400 and p.evaluate("()=>{const r=document.querySelector('#atelier-root').shadowRoot;return !!(r.querySelector('.library').compareDocumentPosition(r.querySelector('.suite-exams'))&Node.DOCUMENT_POSITION_FOLLOWING)}"))
   check(w['id']+' home retains recent, saved and direct practice access',p.locator('.desk-revisit .revisit-column').count()==2 and p.locator('.task-focus [data-action=focus-practice]').count()==1 and not overflow(p))
   p.screenshot(path=str(SHOTS/(w['id']+'-home.png')),animations='disabled')
   p.locator('[data-page=library]').first.click();check(w['id']+' Library prioritizes the full folder tree',p.locator('.side-studies').count()==0 and p.locator('.tree').count()==1 and p.locator('.tree-row').count()>0)
   p.locator('[data-action=view][data-view=list]').click();p.wait_for_timeout(80)
   check(w['id']+' true list retains names, actions and stationary targets',p.locator('.library-row').count()>0 and p.locator('.library-row .row-counts').count()==p.locator('.library-row').count() and not overflow(p))
   check(w['id']+' list-view switch retains keyboard focus',p.evaluate("document.querySelector('#atelier-root').shadowRoot.activeElement?.dataset.view")== 'list')
   p.screenshot(path=str(SHOTS/(w['id']+'-library.png')),animations='disabled')
   p.locator('[data-page=tools]').first.click()
   check(w['id']+' toolkit has all 19 routes and a context-aware search',p.locator('.tool-entry').count()==19 and p.locator('#atelier-search').get_attribute('aria-label')=='Search Anki tools')
   p.locator('#atelier-search').fill('media')
   check(w['id']+' tools search never falls back to deck search',p.locator('.tool-entry').count()>=1 and p.locator('.tools-page [data-command=check_media]').count()==1 and p.locator('#card-list').count()==0)
   p.locator('#atelier-search').fill('');p.locator('[data-category=maintenance]').click()
   check(w['id']+' category updates count and preserves keyboard target',p.locator('.tool-entry').count()==3 and p.evaluate("document.querySelector('#atelier-root').shadowRoot.activeElement?.dataset.category")=='maintenance')
   p.locator('[data-category=all]').click();p.screenshot(path=str(SHOTS/(w['id']+'-tools.png')),animations='disabled');p.close()
  # Tool filters, search, disabled route clarity and native dispatch once.
  def unavailable(boot):boot['nativeTools']['check_media']=False
  p=page(doc(page='tools',change=unavailable))
  p.locator('#atelier-search').fill('medía');check('Accent-insensitive tool search reaches unavailable route with explanation',p.locator('[data-command=check_media]').is_disabled() and p.locator('#tool-unavailable-check_media').is_visible())
  p.locator('#atelier-search').fill('no such tool 81231');check('Tool empty state is truthful and resettable',p.locator('.tools-empty h3').inner_text()=='No tools match that search.')
  p.locator('[data-action=reset-tools]').click();check('Reset returns all categories, clears input and focuses search',p.locator('.tool-entry').count()==19 and p.locator('#atelier-search').input_value()=='' and p.evaluate("document.querySelector('#atelier-root').shadowRoot.activeElement?.id")=='atelier-search')
  p.evaluate("window.calls=[];window.addEventListener('atelier:preview-native',e=>calls.push(e.detail.command))")
  p.locator('.tools-page [data-command=add]').click();p.locator('.dialog').wait_for();check('Searchable native tile dispatches once to existing native route',p.evaluate('calls')==['add']);p.close()
  # Continuation scope and no-backlog empty focus.
  def missing(boot):
   for profile in (boot['profile'],boot['demo']['profile']):profile['last_studied']='999999999'
  p=page(doc(change=missing));check('Deleted previous lecture offers Quick study rather than stale Continue',p.locator('.task-focus [data-action=study-now]').count()==0 and p.locator('.task-focus [data-action=quick-session]').count()==1);p.close()
  def outside(boot):
   for profile in (boot['profile'],boot['demo']['profile']):profile['last_studied']='61'
  p=page(doc(change=outside));check('Old/out-of-focus deck does not become a Continue target',p.locator('.task-focus [data-action=study-now]').count()==0);p.close()
  def none(boot):
   for profile in (boot['profile'],boot['demo']['profile']):profile.update(studies=[],focus_enabled=True,selected_study='all')
  p=page(doc(change=none));check('Finishing last focus never fills headline from old backlog',p.locator('.task-focus [data-action=study-now]').count()==0 and p.locator('.focus-metric').count()==0 and p.locator('.lecture-row').count()==0);p.close()
  # Inline previews operate without navigation, retain normal native/context actions.
  p=page(doc(page='library'));p.locator('[data-action=view][data-view=list]').click();p.wait_for_timeout(60)
  row=p.locator('.library-row').filter(has=p.locator('[data-action=peek]')).first
  id=row.get_attribute('data-node');loc=p.evaluate('AtelierMakeover.diagnostics().location')
  row.locator('.list-preview-toggle').click();check('Inline list preview reveals children without entering the folder',p.locator('.library-row-preview').count()==1 and p.evaluate('AtelierMakeover.diagnostics().location')==loc)
  row=p.locator('.library-row[data-node="'+id+'"]');row.locator('.card-title').focus();p.keyboard.press('Shift+F10');check('Keyboard context menu remains available on new rows',p.locator('.context-menu').count()==1);p.keyboard.press('Escape')
  row.locator('.card-title').click();check('Opening a row enters that exact existing folder',p.evaluate('AtelierMakeover.diagnostics().location')==id)
  p.locator('[data-action=up]').first.click();check('Parent shortcut returns to root',p.evaluate('AtelierMakeover.diagnostics().location')=='0')
  p.locator('.library-orientation [data-action=navigate]').click();check('Last folder returns to the just-visited folder',p.evaluate('AtelierMakeover.diagnostics().location')==id)
  p.locator('[data-action=filter][data-filter=folders]').click();check('Empty folder-only filter does not claim the deck has no children',p.locator('.empty h3').inner_text()=='Nothing matches this view.')
  p.locator('[data-action=filter][data-filter=all]').last.click();p.locator('.library-row .card-title').first.click();check('Opening a leaf offers native review, browse, options and plan routes',p.locator('.deck-detail').is_visible() and p.locator('.deck-detail [data-action=browse]').count()==1 and p.locator('.deck-detail [data-action=options]').count()==1)
  p.screenshot(path=str(SHOTS/'forest-deck-detail.png'),animations='disabled');p.close()
  # Long nested names remain readable in list/card views, no horizontal overflow.
  def long(boot):
   for n in boot['demo']['nodes']:
    n['name']='薬学 — '+n['name']+' · Detailed pharmacology and clinical application / 2026';n['path']='University::Semester::Very long course title::'+n['name']
  p=page(doc(page='library',change=long),width=900,height=720);p.locator('[data-action=view][data-view=list]').click();p.wait_for_timeout(60)
  check('Long Unicode list names remain full text without horizontal overflow',not overflow(p) and '薬学' in p.locator('.library-row .card-title').first.inner_text());p.close()
  # Actual hit testing after main scroll and short/narrow viewport.
  for width,height in [(320,540),(390,650),(620,700),(820,740),(1024,600),(1250,760),(1725,900)]:
   p=page(width=width,height=height)
   sidebar_fit=p.evaluate('''()=>{if(innerWidth<=820)return true;const r=document.querySelector('#atelier-root').shadowRoot,h=r.querySelector('.side-hud'),s=r.querySelector('.side-scroll'),b=r.querySelector('.side-bottom'),box=b.getBoundingClientRect();return h.nextElementSibling===s&&s.nextElementSibling===b&&s.clientHeight>=48&&box.top>=0&&box.bottom<=innerHeight+1&&getComputedStyle(s,'::-webkit-scrollbar').width==='12px'&&getComputedStyle(s,'::-webkit-scrollbar-track').backgroundColor!=='rgba(0, 0, 0, 0)'}''')
   check(f'{width} Home contains all essential controls',not overflow(p) and sidebar_fit and all(hit(p.locator('.unified-topbar [data-command="'+k+'"]')) for k in ('add','browse','sync')))
   if width==1024:p.screenshot(path=str(SHOTS/'forest-sidebar-compact-1024x600.png'),animations='disabled')
   p.locator('.task-focus [data-action=choose-lectures]').click();p.wait_for_timeout(90)
   check(f'{width} Browse lectures clears the actual sticky header',p.evaluate("()=>{const r=document.querySelector('#atelier-root').shadowRoot,t=r.querySelector('#lecture-board')||r.querySelector('.library');return t.getBoundingClientRect().top>=r.querySelector('.unified-topbar').getBoundingClientRect().bottom-1}"))
   p.evaluate("document.querySelector('#atelier-root').shadowRoot.querySelector('.main').scrollTop=800")
   check(f'{width} sticky header remains clickable after scrolling',all(hit(p.locator('.unified-topbar [data-command="'+k+'"]')) for k in ('add','browse','sync')))
   # Menu / nav drawer on small windows is opened explicitly.
   if width<=820:p.locator('[data-action=mobile]').click()
   p.locator('.nav-group [data-page=library]').click();p.locator('[data-action=view][data-view=list]').click();p.wait_for_timeout(80)
   check(f'{width} list is contained and keeps every per-row action',not overflow(p) and p.locator('.library-row-actions [data-action=study]').count()==p.locator('.library-row').count())
   if width<=820:p.locator('[data-action=mobile]').click()
   p.locator('.nav-group [data-page=tools]').click();p.locator('#atelier-search').fill('import')
   check(f'{width} tools filters and search remain usable',not overflow(p) and p.locator('.tools-page [data-command=import]').count()==1)
   p.locator('.tools-page [data-command=import]').scroll_into_view_if_needed()
   check(f'{width} visible native tile target is not covered by sticky header',hit(p.locator('.tools-page [data-command=import]')))
   if width==390:p.screenshot(path=str(SHOTS/'forest-tools-narrow.png'),animations='disabled')
   p.close()
  check('No uncaught errors in Home/Library/Tools tests',not ERRORS)
  b.close()
 OUT.joinpath('results.json').write_text(json.dumps({'count':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'native_windows_verified':False},indent=2))
 print('TOTAL',len(CHECKS),'PASS')
if __name__=='__main__':run()

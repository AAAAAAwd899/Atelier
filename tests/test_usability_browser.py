"""Cross-surface usability audit of the exact frontend with real local model/store.
Native window openings and collections are explicit doubles, not Windows evidence.
"""
from pathlib import Path
import sys, json, copy
from playwright.sync_api import sync_playwright
from suite_fixtures import ROOT,core,home_suite,BeautifulSoup
from card_studio_harness import UnifiedHost
OUT=ROOT/'verification/usability-audit';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/usability';SHOTS.mkdir(parents=True,exist_ok=True)

def home(theme='forest',**patch):
 s=BeautifulSoup(home_suite(theme),'html.parser');boot=json.loads(s.find(id='atelier-bootstrap').string)
 # One deliberate folder focus, even though another saved exam also exists.
 boot['profile']['selected_study']='cardio';boot['profile']['focus_enabled']=True
 boot['profile']['studies']=[dict(x,active=x['id']=='cardio') for x in boot['profile']['studies']]
 boot['suite']['draft']={'exam_id':'micro','questions':50,'at':17,'phase':'answering','timed':False}
 if 'plans' in patch:boot['suite']['plans']=patch.pop('plans')
 if 'profile' in patch:boot['profile'].update(patch.pop('profile'))
 boot['demo']['profile']=copy.deepcopy(boot['profile'])
 boot['demo']['suite']=copy.deepcopy(boot['suite'])
 boot.update(patch);s.find(id='atelier-bootstrap').string=core.json_for_html(boot)
 return str(s)

def main():
 checks=[];errors=[]
 def check(n,v):
  assert v,n
  checks.append(n);print('PASS',n,flush=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=browser.new_page(viewport={'width':1440,'height':900});p.set_default_timeout(5500);p.on('pageerror',lambda e:errors.append(str(e)))
  def clk(sel):p.locator(sel).first.click();p.wait_for_timeout(110)
  def shot(n):p.screenshot(path=str(SHOTS/(n+'.png')),full_page=True)
  def boot_home(**kwargs):
   p.set_content(home(**kwargs));p.locator('.workflow-inbox').wait_for()
   p.evaluate('window.routeLog=[];addEventListener("atelier:preview-suite",e=>routeLog.push({kind:"suite",...e.detail}));addEventListener("atelier:preview-authoring",e=>routeLog.push({kind:"authoring",...e.detail}));')
  try:
   boot_home()
   check('Saved practice named from its real stored exam, not current focus','Microbiology' in p.locator('.workflow-inbox .saved-work').inner_text())
   check('Saved position is visible','17 / 50' in p.locator('.workflow-inbox').inner_text())
   check('Draft inbox and saved practice visible without scroll',p.locator('.workflow-inbox').evaluate('(e)=>e.getBoundingClientRect().top>=0&&e.getBoundingClientRect().bottom<innerHeight'))
   check('Correct inbox view on both home entry points',p.locator('.authoring-hub [data-view="drafts"]').count()==1 and p.locator('.workflow-inbox [data-view="drafts"]').count()==1)
   shot('after-home')
   clk('.workflow-inbox [data-view="drafts"]');check('Home draft click dispatches actual drafts page',p.evaluate('routeLog.at(-1)')=={'kind':'authoring','view':'drafts'})
   p.keyboard.press('Escape');clk('.workflow-inbox [data-view="import"]');check('Source import has dedicated route, not new blank draft',p.evaluate('routeLog.at(-1)')=={'kind':'authoring','view':'import'})
   p.keyboard.press('Escape');clk('.workflow-inbox .saved-work');check('Saved practice uses existing practice/resume page',p.evaluate('routeLog.at(-1)')=={'kind':'suite','view':'practice','id':''})
   p.keyboard.press('Escape');clk('[data-action="focus-practice"]')
   check('Focus practice opens matching plan rather than previously selected plan',p.evaluate('routeLog.at(-1)')=={'kind':'suite','view':'practice','id':'pharm3'})
   # Multiple records with same folder do not use first or last silently.
   plans=[{'id':'one','name':'Review A','deck_ids':['22'],'archived':False},{'id':'two','name':'Review B','deck_ids':['22','221'],'archived':False,'filtered':True}]
   boot_home(plans=plans);clk('[data-action="focus-practice"]')
   check('Equivalent parent/child plans require an explicit choice',p.locator('.dialog [data-action="practice-pick"]').count()==2 and p.evaluate('routeLog.length')==0)
   check('Filtered plan is disclosed in chooser','Search-filtered' in p.locator('.dialog').inner_text())
   clk('[data-action="practice-pick"][data-id="two"]');check('Choosing preserves canonical exam identity and filter',p.evaluate('routeLog.at(-1)')=={'kind':'suite','view':'practice','id':'two'})
   boot_home(plans=[{'id':'other','name':'Other course','deck_ids':['24'],'archived':False}]);clk('[data-action="focus-practice"]')
   check('No scope match never opens unrelated practice automatically',p.locator('.practice-plan-picker').count()==1 and not p.evaluate('routeLog'))
   check('Unmatched scope explains focus versus saved plans','Focus folders and exam plans are separate' in p.locator('.dialog').inner_text())
   shot('practice-plan-choice')
   boot_home(plans=[]);clk('[data-action="focus-practice"]');check('No plans yields a route to setup, not dead end',p.locator('.dialog [data-view="overview"]').is_visible() and 'No saved exam plans yet' in p.locator('.dialog').inner_text())
   for width,height in [(390,740),(620,720),(940,760),(1440,900)]:
    p.set_viewport_size({'width':width,'height':height});boot_home()
    check(f'{width} home inbox remains contained',p.locator('.workflow-inbox').evaluate('(e)=>e.getBoundingClientRect().right<=innerWidth+1') and p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
    for sel in ['.workflow-inbox [data-view="drafts"]','.workflow-inbox [data-view="import"]','.workflow-inbox .saved-work']:
     l=p.locator(sel);l.scroll_into_view_if_needed()
     check(f'{width} {sel} real click target',l.evaluate('(e)=>{const r=e.getBoundingClientRect(),n=e.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===n||e.contains(n)}'))
    if width==390:shot('home-390')
   p.close()
   # Real bundled workspace/store: visible review path, first run, source context.
   h=UnifiedHost();p=browser.new_page(viewport={'width':1440,'height':900});p.set_default_timeout(5500);p.on('pageerror',lambda e:errors.append(str(e)));p.expose_function('nativeBridge',h.dispatch);p.set_content(h.html());p.locator('.shelf-grid').wait_for()
   before=h.col.note_count()
   clk('.nav-link[data-view="drafts"]')
   check('Drafts route lists all existing uncommitted drafts',p.locator('.ws-inbox-record').count()==len([d for d in h.store.list('draft') if d.get('status')!='committed']))
   check('Draft row exposes project AND Anki destination','To:' in p.locator('.ws-draft-meta').first.inner_text())
   shot('drafts-inbox')
   first=h.store.list('draft')[0];clk(f'[data-action="edit-draft"][data-id="{first["id"]}"]')
   check('Single draft approval is in visible editor header',p.locator('[data-action="approve-current"]').evaluate('(e)=>e.getBoundingClientRect().bottom<innerHeight'))
   check('Draft versus publication is explicit','Saving a draft does not add cards' in p.locator('.ws-authoring-workflow').inner_text())
   shot('after-card-studio')
   p.locator('[data-draft="front"]').fill('Audit one exact new note?');p.locator('[data-draft="back"]').fill('Only after confirmation.');clk('[data-action="approve-current"]')
   p.locator('#ws-approve-check').wait_for()
   preflight=next(r for r in reversed(h.requests) if r['action']=='preflight')
   check('Review current saves one real draft then original preflight',len(preflight['payload']['draft_ids'])==1 and any(d['front']=='Audit one exact new note?' for d in h.store.list('draft')))
   check('Preflight creates no notes',h.col.note_count()==before)
   clk('#ws-dialog [data-action="confirm-modal"]');check('Publication without final checkbox is refused',h.col.note_count()==before and p.locator('#ws-dialog [role="alert"]').count()>0)
   clk('#ws-dialog [data-action="close-modal"]');check('Cancel preserves saved draft and original card count',h.col.note_count()==before and p.locator('[data-draft="front"]').input_value()=='Audit one exact new note?')
   # Same original consent still permits commit.
   clk('[data-action="approve-current"]');p.locator('#ws-approve-check').check();clk('#ws-dialog [data-action="confirm-modal"]');p.wait_for_timeout(250)
   check('Explicit approval publishes once via original engine',h.col.note_count()==before+1 and len([r for r in h.requests if r['action']=='commit'])==1)
   # The fixture has six projects; the recent sidebar intentionally shows only
   # five, ordered by update time then UUID. Use the full project library, not
   # an assumption that this particular project is one of those five shortcuts.
   clk('.nav-link[data-view="library"]');p.locator('.shelf-grid').wait_for()
   # Source A must NOT accompany an unsourced draft on reopening.
   clk(f'[data-action="open-project"][data-id="{h.primary_project}"]');clk(f'[data-action="open-source"][data-id="{h.primary_source}"]')
   p.locator('[data-draft="front"]').fill('Unsourced question after a read');p.locator('[data-draft="back"]').fill('No attribution has been selected.');clk('[data-action="save-draft"]')
   d=next(d for d in h.store.list('draft') if d['front']=='Unsourced question after a read')
   check('Source not implicitly attached merely by reading',not d.get('source_id'))
   clk('.nav-link[data-view="drafts"]');clk(f'[data-action="edit-draft"][data-id="{d["id"]}"]')
   check('Reopening unsourced draft clears previous source selection',p.locator('[data-change="studio-source"]').input_value()=='')
   check('Previous source page is not falsely shown',p.locator('#ws-source-paper').count()==0)
   # Generic Create after project change must not keep previous project's draft.
   projects=h.store.list('project');other=next(x for x in projects if x['id']!=h.primary_project)
   clk('.nav-link[data-view="library"]');p.locator('.shelf-grid').wait_for()
   clk(f'[data-action="open-project"][data-id="{other["id"]}"]');clk('.nav-link[data-view="studio"]')
   check('Create from new project no longer edits former project draft',p.locator('[data-change="studio-project"]').input_value()==other['id'] and p.locator('[data-draft="front"]').input_value()=='')
   check('Prior draft is retained in original project',h.store.get('draft',d['id'])['project_id']==h.primary_project)
   # Source draft flush before navigating directly to full planner.
   p.locator('[data-draft="front"]').fill('Saved before planner handoff');p.locator('[data-draft="back"]').fill('A real local draft');clk('.suite-header-actions [data-action="suite-open"]')
   check('Visible planner shortcut opens the existing overview route',h.plan_requests[-1]['target']=='overview')
   check('Planner handoff flushes draft without publishing',any(x['front']=='Saved before planner handoff' for x in h.store.list('draft')) and h.col.note_count()==before+1)
   # Paginated inbox. Selection is bounded and changes of scope clear hidden picks.
   template={k:v for k,v in d.items() if k not in ('id','revision','created_at','updated_at')}
   for i in range(31):h.store.save_draft(dict(template,front=f'Pagination audit {i:02}',back='An unapproved answer'))
   p.evaluate('Workshop.event("refresh",{})');p.wait_for_timeout(100);clk('.nav-link[data-view="drafts"]')
   p.locator('[data-input="draft-query"]').fill('Pagination audit');p.wait_for_timeout(100)
   check('Inbox rendering bounded to 25 without truncating total','31 unapproved drafts' in p.locator('#ws-inbox-results').inner_text() and p.locator('.ws-inbox-record').count()==25)
   clk('[data-action="select-draft-page"]');check('Select page selects only displayed 25 drafts',p.locator('[data-check="draft"]:checked').count()==25 and p.locator('#ws-selected-draft-count').inner_text()=='25 selected')
   clk('[data-action="draft-page"][data-page="1"]');check('Next page exposes remaining six',p.locator('.ws-inbox-record').count()==6 and 'Page 2 of 2' in p.locator('.ws-draft-pagination').inner_text())
   p.locator('[data-input="draft-query"]').fill('Pagination audit 00');p.wait_for_timeout(100)
   check('Filter clears hidden selections and resets page',p.locator('.ws-inbox-record').count()==1 and p.locator('#ws-selected-draft-count').inner_text()=='0 selected' and p.locator('[data-action="approve-inbox"]').is_disabled())
   search=p.locator('[data-input="draft-query"]');search.fill('No result <literal>');p.wait_for_timeout(80)
   check('Filtering keeps typing focus',search.evaluate('(e)=>document.activeElement===e'))
   check('Empty filter does not claim data lost','No drafts in this view' in p.locator('#ws-inbox-results').inner_text() and len(h.store.list('draft'))>=31)
   search.fill('Pagination audit');p.wait_for_timeout(80);p.locator('[data-change="draft-project"]').select_option(other['id']);p.wait_for_timeout(80)
   check('Project filter and text search combine',p.locator('.ws-inbox-record').count()==0)
   p.locator('[data-change="draft-project"]').select_option('all');search.fill('Pagination audit 00');p.wait_for_timeout(80);clk('[data-action="select-draft-page"]');clk('[data-action="approve-inbox"]');p.locator('#ws-approve-check').wait_for()
   check('Inbox batch uses original approval and exact selected ID',len(next(r for r in reversed(h.requests) if r['action']=='preflight')['payload']['draft_ids'])==1)
   clk('#ws-dialog [data-action="close-modal"]')
   # Import is project scoped; opening/canceling file picker creates no data.
   clk('.nav-link[data-view="import"]');check('Import route separates source files and Anki deck packages','Anki deck package' in p.locator('#ws-page').inner_text() and p.locator('[data-change="import-project"]').count()==1)
   shot('import-sources');original_sources=len(h.store.list('source'));clk('[data-action="import-file"]')
   check('Canceling original file picker leaves source and notes intact',len(h.store.list('source'))==original_sources and h.col.note_count()==before+1)
   p.locator('[data-change="import-project"]').select_option(h.primary_project);clk('[data-action="paste-source"]');p.locator('#ws-source-title').fill('Audit direct import');p.locator('#ws-source-text').fill('Keep this exact passage as a local source.');clk('#ws-dialog [data-action="confirm-modal"]');p.locator('#ws-source-paper').wait_for()
   check('Direct source import lands beside original editable draft','Keep this exact passage' in p.locator('#ws-source-paper').inner_text() and p.locator('[data-draft="front"]').is_visible())
   check('Direct import respects chosen project and does not publish',h.store.list('source')[0]['project_id']==h.primary_project and h.col.note_count()==before+1)
   p.locator('[data-draft="front"]').fill('World-switch draft stays put');p.locator('[data-draft="back"]').fill('Pending remains local.');p.evaluate('window.keptField=document.querySelector("[data-draft=front]")')
   for theme in core.THEMES:
    p.locator('#ws-suite-world').select_option(theme);p.wait_for_timeout(100)
    check(theme+' authoring world switch preserves actual editor node',p.evaluate('keptField===document.querySelector("[data-draft=front]")') and p.locator('[data-draft="front"]').input_value()=='World-switch draft stays put')
    check(theme+' workflow toolbar avoids horizontal overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and p.locator('[data-action="approve-current"]').is_visible())
   for width,height in [(390,740),(620,720),(940,760),(1440,900)]:
    p.set_viewport_size({'width':width,'height':height})
    for view,expected in [('drafts','.ws-draft-filters'),('import','.ws-import-card'),('studio','.ws-authoring-workflow')]:
     clk('.nav-link[data-view="'+view+'"]')
     check(f'{width} {view} reachable and contained',p.locator(expected).is_visible() and p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
     check(f'{width} {view} toolbar reserves content height',p.locator('.topbar').evaluate('(e)=>[...e.querySelectorAll("button,select")].filter(n=>n.getClientRects().length).every(n=>n.getBoundingClientRect().bottom<=e.getBoundingClientRect().bottom+1)'))
    if width==390:shot('card-studio-390')
   p.set_viewport_size({'width':1440,'height':900});clk('[data-action="command"]')
   check('Command menu labelled as actions, not global search','Actions & tools' in p.locator('[data-action="command"]').first.inner_text())
   check('Actions palette offers newly visible workflows',p.locator('#ws-dialog [data-value="drafts"]').count()==1 and p.locator('#ws-dialog [data-value="import"]').count()==1)
   check('Source authoring audit makes no AI/provider request',not any(r['action'].startswith('provider_') for r in h.requests))
   p.keyboard.press('Escape');h.settings['visual_owner']='onigiri';p.evaluate('(a)=>Workshop.event("appearance",a)',h.appearance_module.appearance(h.owner));clk('.nav-link[data-view="settings"]')
   check('Bundled passive settings hide ineffective standalone home controls',p.locator('[data-setting="show_home"]').count()==0 and p.locator('[data-setting="show_toolbar"]').count()==0)
   check('Passive planner appearance no longer claims it can match inactive Atelier','Match Atelier' not in p.locator('#ws-page').inner_text() and p.locator('[data-action="theme"][data-value="atelier"]').inner_text().strip()=='Follow Anki')
   check('Existing independent appearance controls remain',p.locator('[data-action="theme"]').count()==4)
   repair=h.store.flag(100,'Audit repair lifecycle',h.primary_project)
   p.evaluate('Workshop.event("refresh",{})');p.wait_for_timeout(100);clk('.nav-link[data-view="improve"]')
   check('Repair help names the actual registered reviewer menu','Atelier · Needs attention' in p.locator('.repair-side').inner_text() and 'Workshop · Needs attention' not in p.locator('.repair-side').inner_text())
   clk('[data-action="repair-resolve"][data-id="'+repair['id']+'"]');clk('[data-action="repair-tab"][data-value="resolved"]')
   check('Resolve uses original local repair state',h.store.get('repair',repair['id'])['status']=='resolved')
   clk('[data-action="repair-reopen"][data-id="'+repair['id']+'"]');clk('[data-action="repair-tab"][data-value="open"]')
   check('Reopen is wired through the grouped handler without changing cards',h.store.get('repair',repair['id'])['status']=='open' and p.locator('[data-action="repair-resolve"][data-id="'+repair['id']+'"]').count()==1 and h.col.note_count()==before+1)
   p.close()
   # Zero projects: explicit creation resumes original requested destination.
   for target in ('studio','import'):
    fresh=UnifiedHost(sample=False);fresh.workspace.initial_view=target;fresh.workspace.controller.preferred_deck=1
    p=browser.new_page(viewport={'width':1360,'height':900});p.set_default_timeout(5500);p.on('pageerror',lambda e:errors.append(str(e)));p.expose_function('nativeBridge',fresh.dispatch);p.set_content(fresh.html());p.locator('[data-action="new-project"]').first.wait_for()
    check('First-run '+target+' has no silently invented project',not fresh.store.list('project'))
    clk('[data-action="new-project"]');p.locator('#ws-project-title').fill('Audit first source volume');clk('#ws-dialog [data-action="confirm-modal"]')
    check('First-run '+target+' resumes requested workflow',p.locator('[data-draft="front"]' if target=='studio' else '[data-change="import-project"]').count()==1)
    check('First-run '+target+' creation alone writes no notes',fresh.col.note_count()==0)
    p.close()
   # Failed local saves and active sessions block navigation without losing the draft.
   fail=UnifiedHost();fail.workspace.initial_view='studio';fail_actions=set()
   def dispatch(message):
    m=json.loads(message.split(':',1)[1])
    if m['action'] in fail_actions:
     fail.requests.append(m)
     return {'id':m['id'],'error':'Audit: local storage is unavailable. Your draft is still open.'}
    return fail.dispatch(message)
   p=browser.new_page(viewport={'width':1360,'height':900});p.set_default_timeout(5500);p.on('pageerror',lambda e:errors.append(str(e)));p.expose_function('nativeBridge',dispatch);p.set_content(fail.html());p.locator('[data-draft="front"]').wait_for()
   fail_actions.add('save_draft');p.locator('[data-draft="front"]').fill('Keep this on a failed save');p.locator('[data-draft="back"]').fill('Do not approve or leave.');clk('[data-action="approve-current"]')
   check('Failed draft save prevents preflight and publishing',not any(r['action'] in ('preflight','commit') for r in fail.requests))
   check('Failed draft save leaves text and an accessible error',p.locator('[data-draft="front"]').input_value()=='Keep this on a failed save' and p.locator('[role="alert"]').count()>0)
   clk('.suite-header-actions [data-action="suite-open"]');check('Failed save blocks cross-tool navigation',not fail.plan_requests)
   fail_actions.clear();clk('[data-action="approve-current"]');p.locator('#ws-approve-check').wait_for();clk('#ws-dialog [data-action="close-modal"]')
   check('Retry keeps exact draft and reaches original approval',any(d['front']=='Keep this on a failed save' for d in fail.store.list('draft')))
   fail._exam_sprout_controller.runner=object();clk('.suite-header-actions [data-action="suite-open"]')
   check('Active practice still blocks opening a competing planner',not fail.plan_requests and p.locator('[data-draft="front"]').input_value()=='Keep this on a failed save')
   check('Global all-drafts label agrees with sidebar count',p.locator('.ws-authoring-workflow [data-view="drafts"]').inner_text().startswith('All drafts ('+str(len([d for d in fail.store.list('draft') if d.get('status')!='committed']))))
   check('Shared Sync glyph is not refresh glyph',p.locator('.suite-header-actions [data-command="sync"] svg[data-icon="sync"]').count()==1)
   p.close()
   check('No uncaught audit browser exceptions',not errors)
  except Exception:
   if not p.is_closed():
    shot('audit-failure');(OUT/'failure.txt').write_text(p.locator('body').inner_text())
   raise
  finally:
   (OUT/'results.json').write_text(json.dumps({'count':len(checks),'cases':checks,'errors':errors,'native_windows':False},indent=2));browser.close()
 print('TOTAL',len(checks),flush=True)
if __name__=='__main__':main()

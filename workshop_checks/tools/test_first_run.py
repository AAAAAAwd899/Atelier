"""First-run acceptance with NO sample data; actual production UI and Python dispatcher."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from ui_harness import Host,ROOT,HTML
h=Host(sample=False);checks=[];errors=[]
def check(name,value):
 assert value,name
 checks.append(name);print('PASS',name,flush=True)
def click(p,selector):p.locator(selector).first.click();p.wait_for_timeout(85)
html=HTML.replace('<link rel="stylesheet" href="/web/app.css">','<style>'+(ROOT/'addon/web/app.css').read_text()+'</style>')
for f in ('icons.js','art.js','app.js'):html=html.replace('<script src="/web/'+f+'"></script>','<script>'+(ROOT/'addon/web'/f).read_text()+'</script>')
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1360,'height':940});p.set_default_timeout(5000)
 p.expose_function('nativeBridge',h.dispatch);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html);p.wait_for_selector('[data-action="new-project"]')
 check('Real first run has no example project or collection notes',not h.store.list('project') and h.col.note_count()==0)
 check('First run is not labelled as sample library','SAMPLE LIBRARY' not in p.locator('body').inner_text())
 check('Living Library has a designed actionable empty state',p.get_by_text('Every library starts with a volume.').count()==1)
 (ROOT/'docs/screenshots').mkdir(parents=True,exist_ok=True);p.screenshot(path=str(ROOT/'docs/screenshots/Workshop_First_Run.png'),full_page=True)
 for view in ('studio','find','improve','media','settings'):
  click(p,'[data-action="nav"][data-view="'+view+'"]')
  check('Empty '+view+' stays usable',p.locator('#ws-page').inner_text().strip()!='' and not errors)
 click(p,'[data-action="nav"][data-view="library"]');click(p,'[data-action="new-project"]');click(p,'[data-action="confirm-modal"]')
 check('An empty project title cannot be committed',not h.store.list('project'))
 p.locator('#ws-project-title').fill('My first volume');p.locator('#ws-project-description').fill('A careful beginning.');click(p,'[data-action="choose-cover"][data-value="celestial"]');click(p,'[data-action="confirm-modal"]')
 check('First project persists the chosen binding',h.store.list('project')[0]['cover']=='celestial')
 click(p,'[data-action="paste-source"]');p.locator('#ws-source-title').fill('A source worth keeping');p.locator('#ws-source-text').fill('A source reference records where a statement originated. It does not certify the statement.')
 click(p,'[data-action="confirm-modal"]');p.wait_for_selector('#ws-source-paper')
 check('First source opens beside a real editable draft',p.locator('#ws-source-paper').inner_text().startswith('A source reference') and p.locator('[data-draft="front"]').count()==1)
 p.locator('[data-draft="front"]').fill('What does a source reference establish?');p.locator('[data-draft="back"]').fill('Where the statement originated, not its correctness.');click(p,'[data-action="save-draft"]')
 check('Saving a draft does not create a native card',len(h.store.list('draft'))==1 and h.col.note_count()==0)
 click(p,'[data-action="nav"][data-view="library"]')
 check('First real volume appears on the shelf',p.locator('.folio').count()==1 and p.get_by_text('My first volume').count()>0)
 click(p,'[data-action="open-project"]');click(p,'[data-action="archive-project"]')
 click(p,'[data-action="nav"][data-view="library"]');click(p,'[data-action="library-tab"][data-value="archived"]')
 check('Archiving preserves sources and unfinished drafts',p.locator('.folio').count()==1 and len(h.store.list('source'))==1 and len(h.store.list('draft'))==1)
 check('No uncaught first-run exceptions',not errors)
 b.close()
(ROOT/'docs/first-run-results.json').write_text(json.dumps({'count':len(checks),'checks':checks,'page_errors':errors,'native_anki':False,'sample_data':False},indent=2))
print(json.dumps({'passed':len(checks),'errors':errors,'expected_validation_errors':h.errors},indent=2))

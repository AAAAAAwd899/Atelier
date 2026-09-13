from pathlib import Path
import sys,json
from suite_fixtures import home_suite,ROOT
from card_studio_harness import UnifiedHost
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification/usability-audit';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/usability';SHOTS.mkdir(parents=True,exist_ok=True)

def main():
 results={};h=UnifiedHost()
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':900});p.set_default_timeout(6000)
  p.set_content(home_suite());p.locator('.authoring-hub').wait_for();p.wait_for_timeout(150)
  results['home_drafts_route']=p.locator('.authoring-hub [data-view="studio"]').all_text_contents()
  results['draft_button_bottom']=p.locator('.authoring-hub').evaluate('(e)=>e.getBoundingClientRect().bottom')
  results['saved_session_top_route']=p.locator('.main-inner > .workflow-inbox').count()
  p.screenshot(path=str(SHOTS/'before-home.png'))
  q=b.new_page(viewport={'width':1440,'height':900});q.set_default_timeout(6000);q.expose_function('nativeBridge',h.dispatch);q.set_content(h.html());q.locator('.shelf-grid').wait_for()
  q.locator(f'[data-action="open-project"][data-id="{h.primary_project}"]').first.click();q.locator(f'[data-action="open-source"][data-id="{h.primary_source}"]').click();q.locator('[data-draft="front"]').wait_for();q.wait_for_timeout(200)
  results['direct_current_draft_approval']=q.locator('[data-action="approve-current"]').count()
  results['drafts_nav']=q.locator('.nav-link[data-view="drafts"]').count()
  q.screenshot(path=str(SHOTS/'before-card-studio.png'))
  # Reproduce unsourced draft retaining stale source page from the previously open draft.
  qs=q.locator('[data-draft="front"]');qs.fill('Unsourced audit draft');q.locator('[data-draft="back"]').fill('Expected no source');q.wait_for_timeout(1300)
  saved=next(x for x in h.store.list('draft') if x.get('front')=='Unsourced audit draft')
  q.locator(f'[data-action="open-project"][data-id="{h.primary_project}"]').first.click();q.wait_for_timeout(100)
  q.locator(f'[data-action="edit-draft"][data-id="{saved["id"]}"]').click();q.wait_for_timeout(180)
  results['unsourced_draft_shows_previous_source']=q.locator('[data-change="studio-source"]').input_value()!=''
  # Cmd dialog is navigation not search. Record label truthfulness.
  q.locator('[data-action="command"]').first.click();q.wait_for_timeout(100)
  results['command_dialog_text']=q.locator('#ws-dialog').inner_text()
  b.close()
 (OUT/'baseline-rc2.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__': main()

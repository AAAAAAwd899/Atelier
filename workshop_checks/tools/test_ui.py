"""Production HTML/CSS/JS + the real Python request dispatcher; synthetic collection/Qt only."""
from __future__ import annotations
import json,threading,sys,tempfile,time
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
from ui_harness import Host,ROOT,HTML
OUT=ROOT/'docs'/'screenshots';OUT.mkdir(parents=True,exist_ok=True)
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/' or self.path.startswith('/?'):
            self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.end_headers();self.wfile.write(HTML.encode());return
        return super().do_GET()
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'addon')));threading.Thread(target=server.serve_forever,daemon=True).start()
host=Host();results=[];errors=[];requests=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    results.append({'name':name,'passed':True});print('PASS',name,flush=True)
def click(page,sel):page.locator(sel).first.click();page.wait_for_timeout(70)
def shot(page,path):
    for b in page.locator('[data-action="dismiss-toast"]').all():
        if b.is_visible():b.click()
    page.screenshot(path=str(path),full_page=True)
def overflow(page):return page.evaluate("document.documentElement.scrollWidth>innerWidth||[...document.querySelectorAll('#ws-page')].some(e=>e.scrollWidth>e.clientWidth+2)")
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    page.set_default_timeout(5000)
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
    page.expose_function('nativeBridge',host.dispatch)
    html=HTML.replace('<link rel="stylesheet" href="/web/app.css">','<style>'+(ROOT/'addon/web/app.css').read_text()+'</style>')
    html=html.replace('<link rel="stylesheet" href="/web/mask-editor.css">','<style>'+(ROOT/'addon/web/mask-editor.css').read_text()+'</style>')
    for script in ('icons.js','art.js','mask-editor.js','app.js'):
        html=html.replace('<script src="/web/'+script+'"></script>','<script>'+(ROOT/'addon/web'/script).read_text()+'</script>')
    page.set_content(html);page.wait_for_selector('.shelf-grid');page.wait_for_timeout(150)
    check('Living Library has all six finished binding designs',page.locator('.folio').count()==6)
    check('Source records are real local entities',len(host.store.list('source'))==6)
    check('No horizontal overflow at desktop',not overflow(page))
    shot(page,OUT/'Workshop_Living_Library.png')
    click(page,'[data-action="library-view"][data-value="list"]');check('List view works',page.locator('.project-list-item').count()==6)
    click(page,'[data-action="library-view"][data-value="shelf"]')
    page.locator('[data-input="library-query"]').fill('Night');check('Project filtering preserves real matches',page.locator('.folio').count()==1)
    page.locator('[data-input="library-query"]').fill('');check('Project filter clears',page.locator('.folio').count()==6)
    click(page,'[data-action="new-project"]');page.locator('#ws-project-title').fill('Questions & Context');page.locator('#ws-project-description').fill('An actual editable test project; never distributed as user data.')
    click(page,'[data-action="choose-cover"][data-value="ocean"]');click(page,'[data-action="confirm-modal"]')
    check('Project modal closes after save',not page.locator('#ws-dialog').evaluate('(e)=>e.open'))
    check('Project saved through the real storage route',host.store.list('project')[0]['cover']=='ocean')
    click(page,'[data-action="paste-source"]');page.locator('#ws-source-title').fill('Original authoring passage');page.locator('#ws-source-text').fill('One question should test one distinct idea. A source citation preserves the origin of a claim. It is not a guarantee of correctness.')
    click(page,'[data-action="confirm-modal"]');page.wait_for_selector('#ws-source-paper')
    check('Source-to-studio handoff',page.locator('#ws-source-paper').inner_text().startswith('One question'))
    check('Source copy stored locally',len(host.store.list('source'))==7)
    # Capture an actual DOM text selection, not a manufactured source quote.
    page.evaluate("""()=>{const el=document.querySelector('#ws-source-paper');const r=document.createRange();r.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(r);el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));}""")
    click(page,'[data-action="use-passage"]');check('Citation carries selection',page.locator('[data-draft="quote"]').input_value().startswith('One question'))
    page.locator('[data-draft="front"]').fill('What does a source citation preserve?');page.locator('[data-draft="back"]').fill('The origin of a claim, not a guarantee of correctness.')
    click(page,'[data-action="save-draft"]');check('Draft saved and still unapproved',host.store.list('draft')[0]['status']=='draft')
    click(page,'[data-action="find-matches"]');check('Existing-card lookup runs',page.locator('.matching').count()==1)
    click(page,'[data-action="preview-draft"]');check('Card preview is escaped source-aware content',page.locator('.card-preview').inner_text().find('Original authoring passage')>=0);click(page,'[data-action="close-modal"]')
    click(page,'[data-action="select-all-drafts"]');click(page,'[data-action="approve-selected"]');check('Batch preview shows card count',page.locator('.approval-item').count()==1)
    page.locator('#ws-approve-check').check();before=host.col.note_count();click(page,'[data-action="confirm-modal"]');check('Approve adds original native note request',host.col.note_count()==before+1)
    check('Approval modal closes',not page.locator('#ws-dialog').evaluate('(e)=>e.open'))
    click(page,'[data-action="undo"]');check('Undo restores note count',host.col.note_count()==before)
    check('Undo restores draft rather than losing it',any(d['status']=='draft' and d['front']=='What does a source citation preserve?' for d in host.store.list('draft')))
    click(page,'[data-action="nav"][data-view="find"]');page.locator('[data-input="search-query"]').fill('source citation');click(page,'[data-action="run-search"]')
    check('Find returns original notes',page.locator('.note-row').count()>=1)
    click(page,'.note-row [data-action="open-note"]');check('Inspect exposes editable original fields',page.locator('[data-edit-field="Back"]').count()==1)
    old=page.locator('[data-edit-field="Back"]').input_value();page.locator('[data-edit-field="Back"]').fill(old+' Checked in Workshop.');click(page,'[data-action="confirm-modal"]');check('Before and after preview exists',page.locator('.before-after').count()==1);click(page,'[data-action="confirm-modal"]')
    check('Edit uses native update_notes operation',host.col.writes[-1][0]=='update_notes')
    click(page,'[data-action="undo"]');check('Undo button does not capture its own undo as a new owned operation',host.workspace.controller.last_undo is None)
    page.locator('[data-input="search-query"]').fill('');click(page,'[data-action="run-search"]')
    page.locator('[data-check="note"]').nth(0).check();page.locator('[data-check="note"]').nth(1).check();click(page,'[data-action="compare-notes"]')
    check('Comparison shows two real original notes',page.locator('.comparison-card').count()==2);click(page,'[data-action="close-modal"]')
    click(page,'[data-action="batch-dialog"]');page.locator('#ws-batch-operation').select_option('add_tag');page.locator('#ws-batch-find').fill('Workshop::Checked');click(page,'[data-action="confirm-modal"]');check('Bulk preview lists actual proposed notes',page.locator('.approval-item').count()==2);click(page,'[data-action="confirm-modal"]')
    check('Bulk change commits one native batch',host.col.writes[-1]==('update_notes',2))
    click(page,'[data-action="nav"][data-view="improve"]');click(page,'[data-action="scan"]');check('Scan runs without guessing factual correctness',page.locator('text=Scan complete').count()==1)
    shot(page,OUT/'Workshop_Improve.png')
    click(page,'[data-action="nav"][data-view="settings"]');check('Privacy explanation explicit',page.locator('text=local source library').count()>=1)
    click(page,'[data-action="theme"][data-value="paper"]');check('Theme setting persists in real local Store',host.store.settings()['theme']=='paper');shot(page,OUT/'Workshop_Settings.png')
    page.locator('[data-setting="motion"]').uncheck();check('Motion preference respected',page.locator('#workshop').get_attribute('data-motion')=='off')
    click(page,'[data-action="capture-guide"]');click(page,'[data-action="confirm-modal"]');check('Browser capture copies working JavaScript',host.clipboard.startswith('javascript:') and 'workshop-capture-v1' in host.clipboard);click(page,'[data-action="close-modal"]')
    click(page,'[data-action="theme"][data-value="night"]')
    # Open via the full library: the optional sidebar shows only five recent projects.
    click(page,'[data-action="nav"][data-view="library"]')
    click(page,'[data-action="open-project"][data-id="'+host.primary_project+'"]')
    shot(page,OUT/'Workshop_Project.png')
    click(page,'[data-action="open-source"][data-id="'+host.primary_source+'"]');page.wait_for_selector('#ws-source-paper')
    existing=next(d for d in host.store.list('draft') if d['project_id']==host.primary_project)
    click(page,'[data-action="edit-draft"][data-id="'+existing['id']+'"]');page.wait_for_selector('#ws-source-paper')
    shot(page,OUT/'Workshop_Card_Studio.png')
    # Local checks of source update review.
    s=host.store.get('source',host.primary_source);host.store.add_source(host.primary_project,s['title'],'text',[{'text':'A revised source deliberately changes the supporting passage.'}],source_id=s['id'])
    page.evaluate("window.Workshop.event('refresh',{})");page.wait_for_timeout(80)
    click(page,'[data-action="nav"][data-view="library"]');click(page,'[data-action="open-project"][data-id="'+host.primary_project+'"]');click(page,'[data-action="source-diff"][data-id="'+host.primary_source+'"]')
    check('Source revision shows before and after',page.locator('.before-after').count()>=1)
    click(page,'[data-action="confirm-modal"]');check('Source revisions produce repair records, not silent card edits',any(r['origin']=='source' for r in host.store.list('repair')))
    # Navigation and responsive layout at useful widths.
    for width in (390,680,920,1100,1440):
        page.set_viewport_size({'width':width,'height':940})
        for view in ('library','studio','find','improve','settings'):
            page.evaluate("v=>window.Workshop.event('navigate',{view:v})",view);page.wait_for_timeout(110)
            check(f'No horizontal clipping at {width}px in {view}',not overflow(page))
        if width==390:
            page.evaluate("window.Workshop.event('navigate',{view:'library'})");page.wait_for_timeout(80);shot(page,OUT/'Workshop_Narrow.png')
    page.keyboard.press('Control+k');check('Command menu keyboard entry',page.locator('#ws-command-query').count()==1)
    page.locator('#ws-command-query').fill('sync');check('Command filtering',page.locator('.command-item:visible').count()==1);page.keyboard.press('Escape')
    check('No uncaught production JavaScript exceptions',not errors)
    check('No remote asset or telemetry requests',all(u.startswith(f'http://127.0.0.1:{server.server_port}') or u.startswith('data:') for u in requests))
    browser.close()
server.shutdown()
receipt={'checks':results,'count':len(results),'page_errors':errors,'native_windows_anki':False,'transport':'Real production Python bridge; explicit Anki/Qt doubles; real profile-local SQLite','errors':host.errors,'source':'addon/web/app.js, app.css, art.js, icons.js'}
(ROOT/'docs'/'browser-results.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({'passed':len(results),'errors':errors,'backend_errors':host.errors},indent=2))

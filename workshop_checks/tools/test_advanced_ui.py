"""Feature acceptance through the packaged UI/bridge. Optional-provider transport is mocked."""
from pathlib import Path
import json,sys
from playwright.sync_api import sync_playwright
from ui_harness import Host,ROOT,HTML
h=Host();checks=[];errors=[];provider_calls=[]
def check(name,value):
    assert value,name
    checks.append(name);print('PASS',name,flush=True)
def click(p,sel):p.locator(sel).first.click();p.wait_for_timeout(65)
html=HTML.replace('<link rel="stylesheet" href="/web/app.css">','<style>'+(ROOT/'addon/web/app.css').read_text()+'</style>')
for f in ('icons.js','art.js','mask-editor.js','app.js'):html=html.replace('<script src="/web/'+f+'"></script>','<script>'+(ROOT/'addon/web'/f).read_text()+'</script>')
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1350,'height':1000})
 p.set_default_timeout(5000);p.on('pageerror',lambda e:errors.append(str(e)));p.expose_function('nativeBridge',h.dispatch);p.set_content(html);p.wait_for_selector('.folio')
 # Successful discard and live refresh after external native note-type/deck changes.
 click(p,'[data-action="open-project"][data-id="'+h.primary_project+'"]');before=len(h.store.list('draft'));click(p,'[data-action="discard-draft"]');click(p,'[data-action="confirm-modal"]')
 check('Discard is a real confirmation, not a dead action',len(h.store.list('draft'))==before-1)
 click(p,'[data-action="refresh-workspace"]');check('Refresh reloads native catalogs',h.requests[-1]['action']=='load')
 click(p,'[data-action="open-source"][data-id="'+h.primary_source+'"]');p.wait_for_selector('#ws-source-paper')
 click(p,'[data-action="card-style"][data-value="cloze"]');p.locator('[data-draft="front"]').fill('A source citation preserves the origin of a claim.')
 p.locator('[data-draft="front"]').evaluate('(e)=>{e.focus();e.setSelectionRange(32,38)}');click(p,'[data-action="make-cloze"]')
 check('Cloze command edits the actual selected phrase','{{c1::' in p.locator('[data-draft="front"]').input_value())
 click(p,'[data-action="save-draft"]');click(p,'[data-action="preview-draft"]');check('Cloze preview is inspectable',p.locator('.card-preview').count()==1);click(p,'[data-action="close-modal"]')
 # Manual core is independent of an AI key.
 click(p,'[data-action="ai-drafts"]');check('Disabled AI offers settings without sending anything',p.locator('#ws-dialog-title').inner_text()=='Provider assistance is optional.');click(p,'[data-action="close-modal"]')
 # Enable a loopback endpoint, mock transport only; production parsing/consent remain in use.
 h.store.set_settings({'ai_enabled':True,'ai_endpoint':'http://127.0.0.1:1234/v1','ai_model':'fixture-chat','embedding_model':'fixture-embedding'})
 def post(settings,route,payload,approved=False):
    assert approved
    provider_calls.append({'route':route,'payload':payload})
    if route=='chat/completions':
      src=json.loads(payload['messages'][1]['content'])['source']
      return {'choices':[{'message':{'content':json.dumps({'cards':[{'front':'What should remain with an authored card?','back':'Its source, supporting passage, and conditions.','quote':src[:90],'context':'Check the original before approving.'}]})}}]}
    return {'data':[{'index':i,'embedding':[.1+.01*i]*8} for i in range(len(payload['input']))]}
 h.workspace.controller.provider._post=post
 click(p,'[data-action="refresh-workspace"]')
 # Exact source quotation provides an inspectable provider request.
 p.evaluate("()=>{const e=document.querySelector('#ws-source-paper'),r=document.createRange();r.selectNodeContents(e);getSelection().removeAllRanges();getSelection().addRange(r);e.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));}")
 click(p,'[data-action="use-passage"]');click(p,'[data-action="ai-drafts"]')
 check('AI request names its destination before sending','127.0.0.1' in p.locator('#ws-dialog').inner_text())
 click(p,'[data-action="confirm-modal"]');check('Provider stays untouched without text consent',not provider_calls)
 p.locator('#ws-share-consent').check();click(p,'[data-action="confirm-modal"]');check('One approved request reaches mocked transport',len(provider_calls)==1)
 check('Source support is an explicit quote check',p.locator('text=Quotation found in selected text').count()==1)
 native_count=h.col.note_count();click(p,'[data-action="confirm-modal"]');ai=next(d for d in h.store.list('draft') if d['origin']=='ai')
 check('AI returns only unapproved local drafts',not ai['verified'] and h.col.note_count()==native_count)
 click(p,'[data-action="edit-draft"][data-id="'+ai['id']+'"]');p.locator('[data-draft="verified"]').check();p.locator('[data-draft="back"]').fill('Changed after checking.')
 check('Changing AI content visibly removes old approval',not p.locator('[data-draft="verified"]').is_checked())
 # Masking delegates original pixels; inline source images are actual bytes.
 from PIL import Image
 image=h.directory/'figure.png';Image.new('RGB',(320,240),(218,230,208)).save(image);h.files=[str(image)]
 p.locator('summary').filter(has_text='Images & audio').click();click(p,'[data-action="attach-file"]');check('Attachment preview decodes actual selected file',p.locator('img.preview-media').evaluate('(e)=>e.naturalWidth')==320)
 p.locator('#ws-attachment-alt').fill('Test source figure');click(p,'[data-action="confirm-modal"]');check('Image attachment is saved with accessible description',any(d['media'] and d['media'][0]['alt']=='Test source figure' for d in h.store.list('draft')))
 # Local source exports/imports go through the actual file format and produce new projects.
 click(p,'[data-action="nav"][data-view="settings"]');h.savepath=str(h.directory/'portable.wslibrary');click(p,'[data-action="export-library"]');check('Portable library export creates a real archive',Path(h.savepath).is_file())
 n=len(h.store.list('project'));h.files=[h.savepath];click(p,'[data-action="import-library"]');check('Import adds projects, never overwrites them',len(h.store.list('project'))==n*2)
 # Semantic retrieval is explicitly a rerank of the shown candidates, not a hidden collection upload.
 click(p,'[data-action="nav"][data-view="find"]');p.locator('[data-input="search-query"]').fill('source citation');click(p,'[data-action="run-search"]');click(p,'[data-action="semantic"]')
 calls=len(provider_calls);click(p,'[data-action="confirm-modal"]');check('Semantic request also requires per-request consent',len(provider_calls)==calls)
 p.locator('#ws-share-consent').check();click(p,'[data-action="confirm-modal"]');check('Embedding rerank keeps native note identities',provider_calls[-1]['route']=='embeddings' and p.locator('.note-row').count()>0)
 # Manual repair of an overpacked question: new drafts, no inherited learning.
 click(p,'.note-row [data-action="open-note"]');click(p,'[data-action="split-note"]');native_count=h.col.note_count();draft_count=len(h.store.list('draft'))
 for i in (1,2):p.locator('[data-split="q'+str(i)+'"]').fill('Separate target '+str(i)+'?');p.locator('[data-split="a'+str(i)+'"]').fill('Its separate supported answer.')
 click(p,'[data-action="confirm-modal"]');check('Split creates two drafts and no learned/duplicate notes',len(h.store.list('draft'))==draft_count+2 and h.col.note_count()==native_count)
 # Empty source state and denied native actions stay recoverable, no app-wide exception.
 click(p,'[data-action="nav"][data-view="improve"]');click(p,'[data-action="repair-resolve"]');check('Repair resolution persists',any(r['status']=='resolved' for r in h.store.list('repair')))
 click(p,'[data-action="repair-tab"][data-value="resolved"]');click(p,'[data-action="repair-reopen"]');check('A resolved repair can be reopened',all(r['status']=='open' for r in h.store.list('repair')))
 check('No uncaught exceptions in advanced production flows',not errors)
 b.close()
(ROOT/'docs'/'advanced-browser-results.json').write_text(json.dumps({'count':len(checks),'checks':checks,'page_errors':errors,'provider_transport':'mocked; no external service or credentials used','native_anki':False},indent=2))
print(json.dumps({'passed':len(checks),'errors':errors,'expected_validation_errors':h.errors},indent=2))

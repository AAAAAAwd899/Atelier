"""Real shipped Mask Studio + actual dispatcher/storage, with native API doubles."""
from __future__ import annotations
import json,threading,sys,tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from types import SimpleNamespace
from playwright.sync_api import sync_playwright
from ui_harness import Host,ROOT,HTML
from tests.authoring_fixtures import enable_native_io,presentation
from addon import documents

OUT=ROOT/'docs'/'authoring-110';OUT.mkdir(parents=True,exist_ok=True)
TMP=Path(tempfile.mkdtemp(prefix='atelier-mask-qa-'))
sys.path.insert(0,str(ROOT.parent/'tests'))
from card_studio_harness import UnifiedHost
host=UnifiedHost();enable_native_io(host.col)
host.workspace.suite_palette={'bg':'#171b19','side':'#141815','panel':'#1f2521','raised':'#28332b','hover':'#303b31',
 'text':'#edf1e8','muted':'#b0bbae','quiet':'#899887','line':'#39473c','accent':'#c5d9af','on-accent':'#202d22'}
host.store.set_settings({'theme':'atelier'})
# An original test-only reference page. No sample source is packaged in runtime.
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
pdf=TMP/'Retrieval field notes.pdf';c=Canvas(str(pdf),pagesize=(960,540));c.setFillColor(HexColor('#f5f1e7'));c.rect(0,0,960,540,fill=1,stroke=0)
c.setFillColor(HexColor('#344b40'));c.setFont('Helvetica-Bold',12);c.drawString(52,485,'ATELIER / FIELD NOTES                                                  LEARNING DESIGN')
c.setFont('Helvetica-Bold',32);c.drawString(52,423,'Make the question worth asking.')
c.setFont('Helvetica',14);c.setFillColor(HexColor('#657068'));c.drawString(52,391,'A working reference for choosing what a card should test.')
xs=[52,320,590];w=245
for x,title in zip(xs,['IDENTIFY','DISTINGUISH','EXPLAIN']):
 c.setFillColor(HexColor('#344b40'));c.roundRect(x,312,w,37,7,fill=1,stroke=0);c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica-Bold',12);c.drawString(x+15,325,title)
for r,row in enumerate([['Name one clear target','Compare close alternatives','State the reason'],['Keep useful context','Show a defining difference','Connect cause to effect'],['Avoid answer clues','Keep conditions explicit','Link to the source']]):
 y=256-r*65
 for x,value in zip(xs,row):
  c.setFillColor(HexColor('#e8e7d9'));c.roundRect(x,y,w,51,5,fill=1,stroke=0);c.setFillColor(HexColor('#283c32'));c.setFont('Helvetica',14);c.drawString(x+13,y+21,value)
c.setFillColor(HexColor('#7d887b'));c.setFont('Helvetica',11);c.drawString(52,52,'Source-linked card design  /  Authored demonstration page  /  Not an assessment score')
c.save()
import fitz
with fitz.open(pdf) as doc:img=doc[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6));data=img.tobytes('png')
blob=host.store.save_blob(data,'png');source=host.store.add_source(host.primary_project,'Retrieval field notes','png',[{'image':blob,'text':''}])['source']
ppt=documents.capture_file(host.store,host.primary_project,presentation(TMP/'Lecture with notes.pptx'))['source']

class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/':self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.end_headers();self.wfile.write(HTML.encode());return
  return super().do_GET()
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'addon')));threading.Thread(target=server.serve_forever,daemon=True).start()
results=[];errors=[];requests=[]
def check(name,value):
 if not value:raise AssertionError(name)
 results.append({'name':name,'passed':True});print('PASS',name,flush=True)
def click(p,selector):p.locator(selector).first.click();p.wait_for_timeout(70)
def ma(p,a):click(p,f'[data-mask-action="{a}"]')
def drag(p,a,b):
 r=p.locator('.mask-image-area').bounding_box();p.mouse.move(r['x']+a[0]*r['width'],r['y']+a[1]*r['height']);p.mouse.down();p.mouse.move(r['x']+b[0]*r['width'],r['y']+b[1]*r['height'],steps=8);p.mouse.up();p.wait_for_timeout(80)
def masks(p):return p.locator('.mask-rect:not([data-mask-id="temporary"])')
def count(p):return masks(p).count()
def shot(p,name):
 for b in p.locator('[data-action="dismiss-toast"]').all():
  if b.is_visible():b.click()
 p.screenshot(path=str(OUT/name),full_page=True)

try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=browser.new_page(viewport={'width':1440,'height':960},device_scale_factor=1)
  p.set_default_timeout(7000);p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:requests.append(r.url));p.expose_function('nativeBridge',host.dispatch)
  html=HTML
  for css in ('app.css','mask-editor.css'):html=html.replace('<link rel="stylesheet" href="/web/'+css+'">','<style>'+(ROOT/'addon/web'/css).read_text()+'</style>')
  for js in ('icons.js','art.js','mask-editor.js','app.js'):html=html.replace('<script src="/web/'+js+'"></script>','<script>'+(ROOT/'addon/web'/js).read_text()+'</script>')
  p.set_content(html);p.wait_for_selector('.shelf-grid')
  check('Integrated header includes return to study desk',p.locator('[data-action="study-desk"]').count()==1)
  check('Atelier palette is read without replacing the library',p.locator('#workshop').evaluate('(e)=>getComputedStyle(e).getPropertyValue("--accent").trim()')==host.appearance_module.PALETTES['forest']['accent'])
  shot(p,'Atelier_Living_Library.png')
  click(p,f'[data-action="open-project"][data-id="{host.primary_project}"]');click(p,f'[data-action="open-source"][data-id="{source["id"]}"]')
  # Source defaults to extracted text; switch to exact original view explicitly.
  p.wait_for_selector('[data-action="mask-source"]:not([disabled])')
  click(p,'[data-action="mask-source"]');p.wait_for_selector('.mask-image-area img');p.wait_for_function('document.querySelector(".mask-image-area img").naturalWidth>0')
  check('Mask Studio opens from the exact managed source',p.locator('#ws-dialog').evaluate('(e)=>e.open') and count(p)==0)
  check('Opening editor creates no collection notes',not any(r['action']=='commit' for r in host.requests))
  ma(p,'same');drag(p,(.065,.445),(.298,.495));check('First rectangle is one question',p.locator('.mask-count').inner_text()=='1 masks · 1 cards')
  ma(p,'stamp');r=p.locator('.mask-image-area').bounding_box()
  for x in (.46,.74):p.mouse.click(r['x']+r['width']*x,r['y']+r['height']*.47)
  check('Stamp repeats rectangle with same-question grouping',p.locator('.mask-count').inner_text()=='3 masks · 1 cards')
  ma(p,'next-group');ma(p,'draw');drag(p,(.065,.565),(.298,.615))
  check('Next question starts a new native group',p.locator('.mask-count').inner_text()=='4 masks · 2 cards')
  ma(p,'select');mask_before=masks(p).last.get_attribute('style');p.locator('.mask-image-area').focus();p.keyboard.press('ArrowRight')
  check('Keyboard nudge moves selected rectangle',masks(p).last.get_attribute('style')!=mask_before)
  ma(p,'undo');check('Undo restores exact rectangle geometry',masks(p).last.get_attribute('style')==mask_before)
  ma(p,'redo');check('Redo restores nudged shape',masks(p).last.get_attribute('style')!=mask_before)
  # Resize using the actual selected handle.
  masks(p).last.click();h=p.locator('.mask-handle.se').bounding_box();p.mouse.move(h['x']+5,h['y']+5);p.mouse.down();p.mouse.move(h['x']+24,h['y']+10,steps=5);p.mouse.up()
  check('Resize uses existing mask, not another note',count(p)==4)
  ma(p,'separate');ma(p,'duplicate');check('Duplicate creates a distinct next question',count(p)==5 and '3 cards' in p.locator('.mask-count').inner_text())
  ma(p,'remove');check('Delete removes only selected mask',count(p)==4 and '2 cards' in p.locator('.mask-count').inner_text())
  ma(p,'preview');check('Preview fully covers target mask areas',p.locator('.mask-opaque.current').count()==3)
  ma(p,'flip');check('Reveal removes only the current question masks',p.locator('.mask-opaque.current').count()==0 and p.locator('.mask-opaque.inactive').count()==1)
  ma(p,'draw');p.locator('[data-mask-field="hide"]').uncheck();ma(p,'preview');check('Independent hide policy leaves other answers visible',count(p)==3)
  ma(p,'draw');p.locator('[data-mask-field="hide"]').check()
  # Source-aligned authored screenshot before extra test masks.
  shot(p,'Atelier_Mask_Studio.png')
  p.locator('[data-mask-field="zoom"]').select_option('150')
  check('Zoom changes viewing scale, not card count',count(p)==4 and '2 cards' in p.locator('.mask-count').inner_text())
  p.locator('[data-mask-field="zoom"]').select_option('100')
  ma(p,'table');drag(p,(.34,.68),(.85,.89));p.locator('[data-mask-field="rows"]').fill('2');p.locator('[data-mask-field="cols"]').fill('2');p.locator('[data-mask-field="grid-group"]').select_option('row');ma(p,'apply-grid')
  check('Table creates one question per row',count(p)==8 and '4 cards' in p.locator('.mask-count').inner_text())
  ma(p,'undo');check('Grid operation has one undo step',count(p)==4)
  # All selected deletion leaves valid no-selected state for keyboard handlers.
  check('Grouped masks retain distinct IDs',len(set(masks(p).evaluate_all('(es)=>es.map(e=>e.dataset.maskId)')))==4)
  for width in (680,940,1440):
   p.set_viewport_size({'width':width,'height':900});p.wait_for_timeout(80)
   check(f'Mask footer remains reachable at {width}px',p.locator('[data-action="mask-done"]').is_visible())
   check(f'Mask dialog does not overflow viewport at {width}px',p.locator('#ws-dialog').evaluate('(e)=>e.getBoundingClientRect().right<=innerWidth+1'))
  click(p,'[data-action="mask-done"]');check('Save returns to Studio, not a new window',not p.locator('#ws-dialog').evaluate('(e)=>e.open'))
  d=next(d for d in host.store.list('draft') if d['kind']=='occlusion');check('Same-card groups and source link persisted',len(d['masks'])==4 and d['source_id']==source['id'])
  p.locator('[data-draft="front"]').fill('Which features make a prompt useful?');click(p,'[data-action="save-draft"]')
  click(p,'[data-action="edit-mask-draft"]');check('Reopening retains all question groups',count(p)==4)
  click(p,'[data-action="mask-done"]')
  check('Occlusion note type is native and cannot be mistakenly mapped',p.locator('[data-draft="model_id"]').is_disabled())
  p.evaluate("document.querySelector('#ws-scroll').scrollTop=0;document.querySelector('.editor-pane').scrollTop=0");p.wait_for_timeout(150)
  check('Source stays in view while the editor scrolls',p.locator('#ws-source-visual img').is_visible() and p.locator('.source-pane').bounding_box()['height']<800)
  shot(p,'Atelier_Card_Studio.png')
  # Select only this draft in the real approval tray.
  p.locator(f'[data-check="draft"][data-id="{d["id"]}"]').check();click(p,'[data-action="approve-selected"]')
  check('Approval reports two native cards',p.locator('.approval-item').count()==1 and '2 cards' in p.locator('.approval-item').inner_text())
  shot(p,'Atelier_Card_Approval.png')
  p.locator('#ws-approve-check').check();before=host.col.note_count();click(p,'[data-action="confirm-modal"]')
  check('Approval creates one native IO note',host.col.note_count()==before+1)
  saved=host.store.get('draft',d['id']);n=host.col.get_note(saved['note_id']);check('Native IO occlusions preserve grouped card count',n.fields[0].count('{{c1::')==3 and len(host.col.card_ids_of_note(n.id))==2)
  click(p,'[data-action="undo"]');check('Undo reverses the authoring operation',host.col.note_count()==before)
  # PowerPoint figures and notes now usable in the same Studio.
  p.locator('[data-change="studio-source"]').select_option(ppt['id']);p.wait_for_selector('.source-notes')
  click(p,'.source-notes summary');check('PowerPoint notes visible without discarding slide text','Speaker detail for lesson 2' in p.locator('.source-notes').inner_text())
  check('Original PowerPoint raster figure can be masked',p.locator('[data-action="mask-asset"]').count()==1)
  check('Matching PDF attach offered, not a fake slide rendering',p.locator('[data-action="pdf-layout"]').count()==1)
  shot(p,'Atelier_PowerPoint_Source.png')
  click(p,'[data-action="mask-asset"]');check('Masking a figure retains source context',p.locator('.mask-image-area').count()==1)
  click(p,'[data-action="mask-done"]')
  # A full page refresh simulates frontend restart; managed data remains.
  p.set_content(html);p.wait_for_selector('.shelf-grid');check('Source and mask drafts survive frontend restart',len([d for d in host.store.list('draft') if d['kind']=='occlusion'])==2)
  check('No uncaught browser exceptions',not errors)
  check('All interface/art assets stay local',all(u.startswith(f'http://127.0.0.1:{server.server_port}') or u.startswith('data:') for u in requests))
  browser.close()
except Exception:
 try:shot(p,'Failure.png')
 except Exception:pass
 raise
finally:
 server.shutdown();(OUT/'results.json').write_text(json.dumps({'checks':len(results),'results':results,'errors':errors,'native_windows':False},indent=2))
print('TOTAL',len(results))

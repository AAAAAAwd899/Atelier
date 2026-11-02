"""Real shipped picker: open composition, bounded varied motion, stable task targets."""
from pathlib import Path
import sys,os,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tools')]
import render_polish_112 as ui
from verify_release import verification_env
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
os.environ.update(verification_env());OUT=ROOT/'verification/picker-113';OUT.mkdir(parents=True,exist_ok=True);SH=ROOT/'screenshots/picker-113';SH.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];traces=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
def open_picker(p):
 p.locator('.folder-explorer-launch').click();p.locator('[data-action=expand-folders]').click();p.locator('.outline-row[data-node="22"] [data-action=organize]').click()
with sync_playwright() as w:
 b=w.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
 c=b.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(OUT),record_video_size={'width':1440,'height':1000});p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.route('**/*',ui.assets);p.set_content(ui.doc('forest'));p.locator('.world-window').wait_for();open_picker(p)
 check('All 25 choices retained',p.locator('.folder-icon-options button').count()==25)
 check('No fieldset border',p.locator('.folder-icon-picker').evaluate('e=>getComputedStyle(e).borderTopWidth')=='0px')
 check('No nested preview border',p.locator('.folder-personalization').evaluate('e=>getComputedStyle(e).borderTopWidth')=='0px' and p.locator('.personalization-art').evaluate('e=>getComputedStyle(e).borderTopWidth')=='0px')
 check('Idle tiles are transparent without visible borders',p.locator('[data-icon=cat]').evaluate('e=>{const s=getComputedStyle(e);return s.borderTopColor==="rgba(0, 0, 0, 0)"&&s.backgroundColor==="rgba(0, 0, 0, 0)"}'))
 for key,expected in [('books','atelier-object-sway'),('physics','atelier-object-orbit'),('cat','atelier-object-peek')]:
  tile=p.locator(f'[data-action=folder-icon][data-icon={key}]');tile.scroll_into_view_if_needed();box=tile.bounding_box();tile.hover();symbol=tile.locator('.picker-symbol');samples=[]
  for delay in [45,120,170]:
   p.wait_for_timeout(delay);samples.append(symbol.evaluate('e=>({transform:getComputedStyle(e).transform,animation:getComputedStyle(e).animationName,iterations:getComputedStyle(e).animationIterationCount})'))
   
   if key=='cat':p.screenshot(path=str(SH/f'cat-motion-{delay}.png'))
   after=tile.bounding_box();check(key+' stable hit target '+str(delay),all(abs(after[k]-box[k])<.1 for k in box))
  p.wait_for_timeout(1900);check(key+' settles without an idle loop',symbol.evaluate('e=>getComputedStyle(e).transform')=='none')
  check(key+' actual varied artwork transform',len(set(x['transform'] for x in samples))>1)
  check(key+' intentional finite motion',all(x['animation']==expected and x['iterations']=='2' for x in samples));traces.append({'icon':key,'samples':samples})
 tile.click();preview=p.locator('.personalization-art .folder-symbol');check('Saved selection greets in preview',preview.evaluate('e=>getComputedStyle(e).animationName')=='atelier-object-greet')
 check('Selected tile has persistent checkmark',tile.evaluate('e=>getComputedStyle(e,"::after").content').strip('"')=='✓')
 check('Saved selection remains announced',p.locator('.folder-personalization').inner_text().find('Saved')>=0)
 p.locator('.folder-personalization').evaluate('e=>{const sc=e.closest(".dialog-body");sc.scrollTop+=e.getBoundingClientRect().top-sc.getBoundingClientRect().top-12}');p.mouse.move(10,10);p.screenshot(path=str(SH/'forest-picker.png'),animations='disabled');p.wait_for_timeout(800)
 p.keyboard.press('Tab');tile=p.locator('[data-icon=music]');tile.focus();check('Keyboard focus triggers object motion',tile.locator('.picker-symbol').evaluate('e=>getComputedStyle(e).animationName')=='atelier-object-sway')
 p.emulate_media(reduced_motion='reduce');tile.hover();check('Reduced motion disables artwork animation',tile.locator('.picker-symbol').evaluate('e=>getComputedStyle(e).animationName')=='none');tile.click();check('Reduced motion disables preview flourish',preview.evaluate('e=>getComputedStyle(e).animationName')=='none')
 p.emulate_media(reduced_motion='no-preference');p.evaluate('document.querySelector("#atelier-root").setAttribute("data-motion","off")');tile.hover();check('Atelier motion-off disables artwork animation',tile.locator('.picker-symbol').evaluate('e=>getComputedStyle(e).animationName')=='none')
 video=p.video;video_path=Path(video.path());p.close();c.close();new=OUT/'Atelier-1.0.13-Picker-Motion.webm';new.unlink(missing_ok=True);video_path.rename(new)
 for theme in ui.core.THEMES:
  for width,height in ([(1440,1000),(390,720)] if theme in ['rose','obsidian'] else [(1440,1000)]):
   p=b.new_page(viewport={'width':width,'height':height});p.on('pageerror',lambda e:errors.append(str(e)));p.route('**/*',ui.assets);p.set_content(ui.doc(theme));p.locator('.world-window').wait_for()
   if width<821:p.locator('[data-action=mobile]').click()
   open_picker(p);p.locator('[data-icon=cat]').click();p.mouse.move(0,0);p.locator('.folder-personalization').evaluate('e=>{const sc=e.closest(".dialog-body");sc.scrollTop+=e.getBoundingClientRect().top-sc.getBoundingClientRect().top-12}');p.screenshot(path=str(SH/f'{theme}-picker-{width}.png'),animations='disabled')
   check(f'{theme} {width} no horizontal spill',p.locator('.folder-icon-options').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
   check(f'{theme} {width} choices remain usable',all(x['width']>=44 and x['height']>=44 for x in p.locator('.folder-icon-options button').evaluate_all('xs=>xs.map(x=>({width:x.getBoundingClientRect().width,height:x.getBoundingClientRect().height}))')))
   check(f'{theme} {width} Done remains reachable',p.get_by_role('button',name='Done',exact=True).is_visible());p.get_by_role('button',name='Done',exact=True).click();p.close()
 b.close()
check('No page errors',not errors)
report={'runtime_sha256':runtime_digest(),'count':len(checks),'checks':checks,'errors':errors,'motion_traces':traces,'video':new.relative_to(ROOT).as_posix(),'video_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'category':'shipped UI and packaged raster assets; synthetic records in headless Chromium; no native desktop capture claim'}
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'checks':len(checks),'errors':errors,'video':report['video']}))

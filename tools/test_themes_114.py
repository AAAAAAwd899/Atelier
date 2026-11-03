"""Actual shipped theme chooser: reactive art, stable targets and finite motion."""
from pathlib import Path
import os,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tools')]
import render_polish_112 as ui
from verify_release import verification_env
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
os.environ.update(verification_env());OUT=ROOT/'verification/themes-114';OUT.mkdir(parents=True,exist_ok=True);SH=ROOT/'screenshots/themes-114';SH.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];traces=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
def pose(tile):return tile.locator('.mini-screen').evaluate('e=>({transform:getComputedStyle(e,"::before").transform,animation:getComputedStyle(e,"::before").animationName,iterations:getComputedStyle(e,"::before").animationIterationCount,glint:getComputedStyle(e,"::after").opacity,filter:getComputedStyle(e,"::before").filter,response:getComputedStyle(e.parentElement).getPropertyValue("--world-response").trim()})')
with sync_playwright() as w:
 b=w.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
 c=b.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(OUT),record_video_size={'width':1440,'height':1000});p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.route('**/*',ui.assets);p.set_content(ui.doc('forest'));p.locator('.unified-topbar [data-action=appearance]').click()
 check('All seventeen worlds remain available',p.locator('.theme-tile').count()==17)
 p.evaluate('window.originalWorldTiles=[...document.querySelector("#atelier-root").shadowRoot.querySelectorAll(".theme-tile")]')
 for theme in ui.core.THEMES:
  tile=p.locator(f'[data-theme-choice="{theme}"]');tile.scroll_into_view_if_needed();p.mouse.move(0,0);before=tile.bounding_box();label=tile.locator('.tile-label').bounding_box();rest=pose(tile)['transform'];tile.hover();samples=[]
  for delay in [45,100,170]:
   p.wait_for_timeout(delay);samples.append(pose(tile));now=tile.bounding_box();now_label=tile.locator('.tile-label').bounding_box()
   check(theme+' stable tile '+str(delay),all(abs(before[k]-now[k])<.1 for k in before))
   check(theme+' stable label '+str(delay),all(abs(label[k]-now_label[k])<.1 for k in label))
   if theme=='forest' and delay in [45,170]:tile.screenshot(path=str(SH/f'forest-motion-{delay}.png'))
  check(theme+' scene really animates',len(set(x['transform'] for x in samples))>1)
  check(theme+' finite world-specific motion',all(x['animation']==x['response'] and x['iterations']=='2' for x in samples))
  check(theme+' light sweep is visible',any(float(x['glint'])>0 for x in samples))
  p.wait_for_timeout(2300);check(theme+' art returns to rest',pose(tile)['transform']==rest)
  grid=p.locator('.theme-tile').evaluate_all('xs=>xs.map(x=>[x.offsetLeft,x.offsetTop,x.offsetWidth,x.offsetHeight])');tile.click()
  check(theme+' selected and saved',tile.get_attribute('aria-pressed')=='true' and p.locator('#atelier-root').get_attribute('data-theme')==theme)
  check(theme+' no selection grid jitter',grid==p.locator('.theme-tile').evaluate_all('xs=>xs.map(x=>[x.offsetLeft,x.offsetTop,x.offsetWidth,x.offsetHeight])'))
  check(theme+' selection feedback animates',tile.locator('.theme-check').evaluate('e=>getComputedStyle(e).animationName')=='atelier-world-chosen')
  check(theme+' original scene and readable material retained',tile.locator('.mini-screen').evaluate('e=>getComputedStyle(e).backgroundImage.includes(".png")') and bool(tile.locator('small').inner_text()))
  p.mouse.move(0,0);tile.screenshot(path=str(SH/f'{theme}-selected.png'),animations='disabled');traces.append({'theme':theme,'samples':samples})
 check('Selection retained every original tile node',p.evaluate('originalWorldTiles.every(x=>x.isConnected)'))
 tile=p.locator('[data-theme-choice=forest]');tile.scroll_into_view_if_needed();p.keyboard.press('Tab');tile.focus();check('Keyboard focus gives the same scenery response',pose(tile)['animation']=='atelier-world-canopy')
 p.emulate_media(reduced_motion='reduce');tile.hover();check('Reduced motion freezes scene and sweep',pose(tile)['animation']=='none' and pose(tile)['transform']=='none' and pose(tile)['glint']=='0');tile.click();check('Reduced motion freezes selection flourish',tile.locator('.theme-check').evaluate('e=>getComputedStyle(e).animationName')=='none')
 p.emulate_media(reduced_motion='no-preference');p.evaluate('document.querySelector("#atelier-root").setAttribute("data-motion","off")');tile.hover();check('Atelier motion-off freezes scenery',pose(tile)['animation']=='none' and pose(tile)['transform']=='none')
 p.evaluate('document.querySelector("#atelier-root").setAttribute("data-motion","on")');p.locator('.dialog-body').evaluate('e=>e.scrollTop=0');p.mouse.move(0,0);p.screenshot(path=str(SH/'world-chooser-desktop.png'),animations='disabled')
 video=p.video;vp=Path(video.path());p.close();c.close();video_path=OUT/'Atelier-1.0.14-Reactive-Worlds.webm';video_path.unlink(missing_ok=True);vp.rename(video_path)
 for width,height in [(390,720),(1024,600)]:
  p=b.new_page(viewport={'width':width,'height':height});p.route('**/*',ui.assets);p.set_content(ui.doc('rose'));p.locator('.unified-topbar [data-action=appearance]').click();tile=p.locator('[data-theme-choice=obsidian]');tile.scroll_into_view_if_needed();before=tile.bounding_box();tile.click()
  check(str(width)+' theme picker fits horizontally',p.locator('.themes').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
  check(str(width)+' saved choice keeps its target',all(abs(tile.bounding_box()[k]-before[k])<.1 for k in before))
  check(str(width)+' original choices and close control retained',p.locator('.theme-tile').count()==17 and p.get_by_role('button',name='Close dialog',exact=True).is_visible())
  p.locator('.dialog-body').evaluate('e=>e.scrollTop=0');p.mouse.move(0,0);p.screenshot(path=str(SH/f'world-chooser-{width}.png'),animations='disabled');p.close()
 b.close()
check('No uncaught page errors',not errors)
r={'runtime_sha256':runtime_digest(),'count':len(checks),'checks':checks,'errors':errors,'motion_traces':traces,'video':video_path.relative_to(ROOT).as_posix(),'video_sha256':hashlib.sha256(video_path.read_bytes()).hexdigest(),'category':'shipped UI with packaged art and synthetic data; recorded Chromium, no native desktop screenshot claim'}
(OUT/'results.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({'checks':len(checks),'errors':errors,'video':r['video']}))

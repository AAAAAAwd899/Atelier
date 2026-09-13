"""Current packaged UI / deterministic rendering checks, not Windows Anki tests."""
from pathlib import Path
import sys,json,shutil,base64,io
from PIL import Image,ImageChops
import numpy as np
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import test_ui_096 as old
WEB=ROOT/'addon/web';OUT=ROOT/'docs/readiness-097';OUT.mkdir(exist_ok=True)
CHECKS=[];ERRORS=[]
def check(n,ok=True):
    assert ok,n;CHECKS.append(n);print('PASS',n,flush=True)

def run():
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling'])
  page=browser.new_page(viewport={'width':1440,'height':1060},device_scale_factor=1.25)
  page.on('pageerror',lambda e:ERRORS.append(str(e)));page.set_default_timeout(15000)
  page.route('**/*',old.route);page.expose_function('fixtureCommand',old.f.bridge)
  page.set_content(old.html());page.locator('.es-focus-row').first.wait_for();page.locator('.pip-card[data-pip-renderer="webgl2"]').wait_for()
  page.evaluate('window.keptCanvas=document.querySelector(".pip-canvas");window.initialPip=PipCompanion.info()[0]')
  page.locator('[data-action="refresh"]').click();page.wait_for_timeout(400)
  check('Plan refresh preserves the same canvas and motion clock',page.evaluate('keptCanvas===document.querySelector(".pip-canvas")&&PipCompanion.info()[0].time>=initialPip.time'))
  if page.locator('[data-action="toggle-rows"]').count():
   page.locator('[data-action="toggle-rows"]').click()
   check('Expand deck priorities preserves the living scene',page.evaluate('keptCanvas===document.querySelector(".pip-canvas")'))
  for _ in range(12):page.evaluate('PipCompanion.mount()')
  check('Repeated mount keeps a single context',page.evaluate('PipCompanion.info().length===1&&keptCanvas===document.querySelector(".pip-canvas")'))
  page.locator('[data-pip-action="pet"]').click()
  page.locator('[data-action="refresh"]').click()
  check('Page refresh does not rewind an active interaction',page.evaluate('PipCompanion.info()[0].action==="pet"&&keptCanvas===document.querySelector(".pip-canvas")'))
  page.screenshot(path=str(OUT/'Exam_Sprout_Planner.png'),full_page=True)
  page.locator('[data-pip-action="pause"]').click();page.wait_for_timeout(200)
  frames=old.info(page)['frames'];page.wait_for_timeout(300)
  check('Paused scene stays frozen, not continuously repainted',old.info(page)['frames']==frames)
  page.locator('[data-pip-action="pause"]').click()
  page.locator('[data-pip-action="water"]').click();page.evaluate('PipCompanion.pause()')
  stopped=old.info(page)['time'];page.wait_for_timeout(3350)
  check('Hidden interaction is not ended by a wall-clock timer',old.info(page)['time']==stopped and old.info(page)['action']=='water')
  page.evaluate('PipCompanion.resume()');page.wait_for_timeout(120)
  check('Interaction resumes from its paused scene time',old.info(page)['time']>=stopped and old.info(page)['action']=='water')
  # Fresh calm pose for the released screenshot; no artwork substitution.
  page.locator('[data-view="settings"]').first.click();page.locator('[data-view="overview"]').first.click()
  page.locator('.pip-card[data-pip-renderer="webgl2"]').wait_for();page.wait_for_timeout(300)
  page.evaluate('PipCompanion.pause()');page.screenshot(path=str(OUT/'Exam_Sprout_Planner.png'),full_page=True);page.evaluate('PipCompanion.resume()')
  for width in (1366,1180,940,720,620,390):
   page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(90)
   check(f'{width}px page fits horizontally',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
  page.set_viewport_size({'width':1180,'height':900});page.wait_for_timeout(200)
  page.locator('[data-view="practice"]').first.click()
  check('Leaving plan releases all companion contexts',page.evaluate('PipCompanion.info().length===0'))
  page.screenshot(path=str(OUT/'Exam_Sprout_Exam_Setup.png'),full_page=True)
  page.locator('[data-view="settings"]').first.click()
  for theme in ('inherit','sage','lavender','peach','rose','sky','midnight'):
   page.locator(f'[data-action="theme"][data-value="{theme}"]').click();page.wait_for_timeout(60)
   check(f'{theme} preset applies',page.get_attribute('#es-app','data-theme')==theme)
  page.screenshot(path=str(OUT/'Exam_Sprout_Settings.png'),full_page=True)
  check('No background external service requests',not old.REMOTE)
  page.close()
  # Direct renderer checks using actual GL / shaders, no mocked drawing API.
  page=browser.new_page(viewport={'width':360,'height':396},device_scale_factor=1)
  page.on('pageerror',lambda e:ERRORS.append(str(e)))
  page.set_content('<style>body{margin:0}canvas{width:300px;height:330px}</style><canvas></canvas>')
  page.add_script_tag(path=str(WEB/'pip-scene.js'))
  def create(stage=1,batch=True):
   page.evaluate('''o=>{window.scene?.dispose();document.querySelector('canvas').replaceWith(document.createElement('canvas'));window.scene=new PipScene.Scene(document.querySelector('canvas'),{stage:o.stage,batch:o.batch,capture:true});scene.setPaused(true);scene.render(0);}''',{'stage':stage,'batch':batch})
  def capture():
   return np.asarray(Image.open(io.BytesIO(base64.b64decode(page.evaluate('scene.canvas.toDataURL().split(",")[1]')))).convert('RGBA')).astype(float)
  geometries=[]
  for stage in (1,2,3,4):
   create(stage,False);a=capture();original=page.evaluate('scene.info()')
   create(stage,True);b=capture();batched=page.evaluate('scene.info()')
   check(f'Stage {stage}: identical triangles and less submission work',batched['triangles']==original['triangles'] and batched['nodes']<original['nodes'])
   check(f'Stage {stage}: batching preserves appearance',np.abs(a-b).mean()<.65)
   check(f'Stage {stage}: no GL errors',page.evaluate('scene.gl.getError()===scene.gl.NO_ERROR'))
   geometries.append({'stage':stage,'before_nodes':original['nodes'],'after_nodes':batched['nodes'],'triangles':batched['triangles'],'mean_pixel_difference':float(np.abs(a-b).mean())})
  check('Small standard-density image is supersampled',page.evaluate('scene.canvas.width===450&&scene.canvas.height===495'))
  before=page.evaluate('scene.info().resizes');page.evaluate('for(let i=0;i<40;i++)scene.resize()')
  check('Unchanged resize never clears the backing buffer',page.evaluate('scene.info().resizes')==before)
  # Deterministic rAF timestamps show no legacy 30Hz every-other-frame gate.
  metrics=page.evaluate('''()=>{scene.stop();scene.setPaused(true);const originalRAF=window.requestAnimationFrame,originalCAF=window.cancelAnimationFrame;let id=0;const jobs=new Map();window.requestAnimationFrame=fn=>{jobs.set(++id,fn);return id};window.cancelAnimationFrame=i=>jobs.delete(i);const before=scene.info();scene.setPaused(false);for(let i=0;i<=60;i++){const entry=[...jobs][0];if(!entry)throw Error('Lost animation frame');jobs.delete(entry[0]);entry[1](1000+i*1000/60);}scene.stop();window.requestAnimationFrame=originalRAF;window.cancelAnimationFrame=originalCAF;scene.setPaused(true);return {frames:scene.draws-before.frames,seconds:scene.time-before.time};}''')
  check('60Hz timestamps produce 60Hz pose updates, not 30Hz skips',metrics['frames']==61 and abs(metrics['seconds']-1)<.005)
  check('Pause/resume does not reset animation time',page.evaluate('(()=>{const t=scene.time;scene.setPaused(false);scene.setPaused(true);return t===scene.time})()'))
  # Freeze navigation / visibility and validate lifecycle re-entry.
  page.evaluate('scene.setHidden(true)');check('Hidden scene has no pending animation frame',page.evaluate('scene.raf===0'))
  page.evaluate('scene.dispose()');check('Disposed scene releases mesh resources',page.evaluate('scene.disposed&&scene.resources.length===0&&scene.raf===0'))
  browser.close()
 check('No uncaught exceptions in readiness browser pass',not ERRORS)
 (ROOT/'docs/ui-097-results.json').write_text(json.dumps({'checks':CHECKS,'count':len(CHECKS),'errors':ERRORS,'geometry':geometries,'frame_clock_test':metrics,'native_anki':False,'renderer':'Chromium software WebGL2'},indent=2))
 print('TOTAL',len(CHECKS),flush=True)
if __name__=='__main__':run()

"""Production UI + real WebGL2 renderer; synthetic collection/Anki bridge.
Run under Xvfb with Chromium. Does not claim native Anki/Qt/Windows validation.
"""
from pathlib import Path
import sys,json,shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import test_ui as f
from addon.core import PracticeSession
WEB=ROOT/'addon/web';OUT=ROOT/'docs/screenshots-096';OUT.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[];CALLS=[];REMOTE=[]
f.NIGHT=True;f.STORE.save_settings({**f.STORE.state['settings'],'theme':'midnight'})
original=f.command

def command(action,p):
    CALLS.append((action,p))
    if action in ('study','focus','back_to_anki'):return {'started':True}
    if action=='review_misses':return {'started':True,'native_ui_mock':True}
    if action=='start':
        if p.get('token') not in f.PENDING:raise ValueError('Expired sample')
        return {'started':True,'native_ui_mock':True}
    out=original(action,p)
    if action=='load':out['asset_base']='/_addons/exam_sprout/web'
    return out
f.command=command

def html():
    css=''.join((WEB/x).read_text() for x in ('app.css','countdown.css','pip.css'))
    js=';'.join((WEB/x).read_text() for x in ('countdown.js','pip-scene.js','pip.js','app.js'))
    return '<!doctype html><html lang="en"><head><base href="http://sprout.test/"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main id="es-app"></main><script>window.pycmd=m=>window.fixtureCommand(JSON.parse(m.slice(12))).then(window.ExamSprout.receive);</script><script>'+js+'</script></body></html>'

def route(req):
    url=req.request.url
    if '/_addons/exam_sprout/web/' not in url:
        REMOTE.append(url);return req.fulfill(status=403,body='Blocked by test: unexpected network')
    path=(WEB/url.split('/web/',1)[1]).resolve()
    if WEB.resolve() in path.parents and path.is_file():req.fulfill(path=str(path))
    else:req.fulfill(status=404,body='Missing packaged asset')

def check(name,ok=True):
    assert ok,name;CHECKS.append(name);print('PASS',name,flush=True)
def info(page):return page.evaluate('PipCompanion.info()[0]')
def advances(page):
    before=info(page)['frames'];page.wait_for_function('(n)=>PipCompanion.info()[0]?.frames>n',arg=before,timeout=10000);return True
def overview(page):
    page.locator('.es-top-nav [data-view="overview"]').click()
    page.locator('.es-focus-row').first.wait_for();page.locator('.pip-card[data-pip-renderer="webgl2"]').wait_for()
def paused_frames(page):
    # Permit a one-off resize/static redraw, then verify no ongoing frame loop.
    page.wait_for_timeout(300)
    before=info(page)['frames'];page.wait_for_timeout(180);return info(page)['frames']-before

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1020},device_scale_factor=1)
        page.on('pageerror',lambda e:ERRORS.append(str(e)));page.set_default_timeout(10000)
        page.route('**/*',route);page.expose_function('fixtureCommand',f.bridge)
        page.set_content(html());page.locator('.es-focus-row').first.wait_for();page.locator('.pip-card[data-pip-renderer="webgl2"]').wait_for()
        check('Real local WebGL2 scene, not static portrait',info(page)['renderer']=='WebGL2' and info(page)['triangles']>50000)
        check('Only one active scene',len(page.evaluate('PipCompanion.info()'))==1)
        check('Fallback hidden when live canvas succeeds',not page.locator('.pip-image').is_visible() and page.locator('.pip-canvas').is_visible())
        check('No mixed-model progression pictures',page.locator('.es-growth-steps img').count()==0 and page.locator('.es-growth-steps span').count()==4)
        check('Blink/breath/leaf animation advances',advances(page))
        for action in ('study','focus','browse'):
            page.locator(f'.es-focus-actions [data-action="{action}"]').first.click();page.wait_for_timeout(60)
            check('Distinct '+action+' bridge route',CALLS[-1][0]==action)
        before=json.dumps(f.STORE.state,sort_keys=True)
        page.locator('[data-pip-action="pet"]').click();check('Pet rig is active',info(page)['action']=='pet')
        page.locator('[data-pip-action="water"]').click();check('Water rig is active',info(page)['action']=='water')
        page.locator('.pip-touch').click();check('Greeting uses a separate animation',info(page)['action']=='greet')
        check('Interactions never alter grades/progress/storage',json.dumps(f.STORE.state,sort_keys=True)==before)
        box=page.locator('.pip-touch').bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+50,y,steps=8);page.mouse.up()
        check('Character can be dragged without dragging the page',page.locator('.pip-touch').is_visible())
        page.locator('[data-pip-action="pause"]').click();page.wait_for_function('PipCompanion.info()[0]?.paused === true')
        check('User pause stops requestAnimationFrame',paused_frames(page)==0)
        check('User pause persisted in settings',f.STORE.state['settings']['animate_pip'] is False)
        page.locator('[data-pip-action="pause"]').click();page.wait_for_function('PipCompanion.info()[0]?.paused === false')
        check('Resume persisted and animates',f.STORE.state['settings']['animate_pip'] is True and advances(page))
        page.emulate_media(reduced_motion='reduce');page.wait_for_function('PipCompanion.info()[0]?.paused===true')
        check('Reduced motion stops live animation',info(page)['paused'] and paused_frames(page)==0)
        page.emulate_media(reduced_motion='no-preference');page.evaluate('PipCompanion.pause()')
        check('Native host hide pauses rendering',paused_frames(page)==0)
        page.evaluate('PipCompanion.resume()');page.wait_for_timeout(60)
        check('Native host resume restores scene',not info(page)['hidden'])
        check('Hidden buffers are redrawn on return',page.locator('.pip-canvas').is_visible())
        page.emulate_media(reduced_motion='reduce');page.wait_for_function('PipCompanion.info()[0].paused');page.screenshot(path=str(OUT/'Exam_Sprout_Planner.png'),full_page=True)
        page.emulate_media(reduced_motion='no-preference')
        for width in (1440,1100,940,720,620,390):
            page.set_viewport_size({'width':width,'height':980});page.wait_for_timeout(80)
            check(f'{width}px overview has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            if width==390:page.screenshot(path=str(OUT/'Exam_Sprout_Narrow.png'),full_page=True)
        page.set_viewport_size({'width':1280,'height':1020});page.evaluate('window.scrollTo(0,0)')
        page.locator('[data-action="edit"]').click();page.locator('[data-action="next-step"]').click()
        check('Navigation disposes the WebGL scene',len(page.evaluate('PipCompanion.info()'))==0)
        page.locator('[data-bulk="confidence"]').select_option('1');page.locator('[data-action="apply-bulk"][data-kind="confidence"]').click()
        check('Bulk confidence applies to all selected',page.locator('select[data-special="confidence"]:enabled').evaluate_all('els=>els.every(e=>e.value==="1")'))
        page.locator('[data-bulk="emphasis"]').fill('2');page.locator('[data-action="apply-bulk"][data-kind="emphasis"]').click()
        check('Bulk emphasis applies to all selected',page.locator('input[data-special="emphasis"]:enabled').evaluate_all('els=>els.every(e=>e.value==="2")'))
        page.screenshot(path=str(OUT/'Exam_Sprout_Deck_Setup.png'),full_page=True)
        page.locator('[data-action="cancel-form"]').click();page.locator('[data-action="confirm-modal"]').click()
        overview(page)
        check('Returning creates one working fresh scene',len(page.evaluate('PipCompanion.info()'))==1)
        page.locator('.es-top-nav [data-view="practice"]').click()
        for size in (0,501):
            page.locator('[data-practice="size"]').fill(str(size));page.locator('[data-action="prepare"]').click()
            check(f'Invalid {size}-card request rejected',page.locator('#es-modal[open]').count()==0)
        page.locator('[data-practice="size"]').fill('100');page.locator('[data-practice="weighting"]').select_option('custom')
        for did,w in ((11,50),(12,30),(13,20)):page.locator(f'[data-weight="{did}"]').fill(str(w))
        page.screenshot(path=str(OUT/'Exam_Sprout_Exam_Setup.png'),full_page=True)
        page.locator('[data-action="prepare"]').click();page.locator('#es-modal[open]').wait_for()
        numbers=list(map(int,page.locator('.es-allocation-row strong').all_inner_texts()))
        check('Weighted mixed exam draws exactly 100 cards',sum(numbers)==100)
        check('50/30/20 proportions within coverage reservation rounding',all(abs(a-b)<=1 for a,b in zip(numbers,[50,30,20])))
        check('No opaque deck-ID warning spam','Deck 11 has no eligible' not in page.locator('#es-modal').inner_text())
        page.screenshot(path=str(OUT/'Exam_Sprout_Exam_Allocation.png'))
        page.locator('[data-action="confirm-modal"]').click();page.wait_for_timeout(80)
        check('Start uses a validated sample token',CALLS[-1][0]=='start' and CALLS[-1][1]['token'] in f.PENDING)
        e,sample,kind,mins=f.PENDING[CALLS[-1][1]['token']]
        session=PracticeSession(e.id,sample.cards[:8]);session.save_response('My retained answer');session.submit()
        while session.phase!='finished':session.grade(0 if session.index==0 else .5 if session.index==1 else 1)
        result=session.result();f.STORE.add_result(result)
        page.evaluate('(p)=>ExamSprout.event("result",p)',{'state':f.STORE.state,'result':result});page.locator('#es-modal[open]').wait_for();page.wait_for_timeout(160)
        check('Result modal survives asynchronous plan refresh',page.locator('#es-modal[open]').count()==1)
        check('Original cards and misses are retained',len(result['items'])==8 and result['items'][0]['grade']==0)
        page.screenshot(path=str(OUT/'Exam_Sprout_Result.png'))
        page.locator('[data-action="review-misses"]').click();page.wait_for_timeout(60)
        check('Review misses routes to native card review, not Browse',CALLS[-1][0]=='review_misses')
        page.locator('.es-top-nav [data-view="settings"]').click()
        check('Response saving remains explicit opt-in',not page.locator('[data-setting="remember_answers"]').is_checked())
        check('Reviewer hide and planner hide are independent',all(page.locator(f'[data-setting="{k}"]').count()==1 for k in ('reviewer_pip','show_pip')))
        page.locator('[data-setting="show_pip"]').uncheck();page.wait_for_timeout(80);page.locator('.es-top-nav [data-view="overview"]').click();page.locator('.es-focus-row').first.wait_for()
        check('Hidden companion fully removes scene',page.locator('.pip-card').count()==0 and not page.evaluate('PipCompanion.info().length'))
        page.locator('.es-top-nav [data-view="settings"]').click();page.locator('[data-setting="show_pip"]').check();page.wait_for_timeout(80)
        for theme in ('inherit','sage','lavender','peach','rose','sky','midnight'):
            page.locator(f'[data-action="theme"][data-value="{theme}"]').click();page.wait_for_function('(t)=>document.querySelector("#es-app").dataset.theme===t',arg=theme)
            check(theme+' theme remains functional',f.STORE.state['settings']['theme']==theme)
        page.screenshot(path=str(OUT/'Exam_Sprout_Settings.png'),full_page=True)
        overview(page)
        for i in range(6):
            page.locator('.es-top-nav [data-view="practice"]').click();check(f'Round {i+1}: no scene retained on practice page',not page.evaluate('PipCompanion.info().length'))
            overview(page);check(f'Round {i+1}: single newly mounted live scene',len(page.evaluate('PipCompanion.info()'))==1)
        # Simulate a real GPU context loss: graceful same-model animation fallback.
        page.evaluate('document.querySelector(".pip-canvas").getContext("webgl2").getExtension("WEBGL_lose_context").loseContext()')
        page.locator('.pip-card[data-pip-renderer="fallback"]').wait_for();page.wait_for_function('document.querySelector(".pip-image").complete && document.querySelector(".pip-image").naturalWidth>0')
        check('Context loss switches to packaged exact-model art',page.locator('.pip-image').is_visible() and not page.locator('.pip-canvas').is_visible())
        page.locator('[data-pip-action="water"]').click();check('Fallback watering is interactive',page.locator('.pip-image').get_attribute('src').endswith('-water.webp'))
        page.emulate_media(reduced_motion='reduce');page.wait_for_function('document.querySelector(".pip-image").src.endsWith(".png")');check('Fallback reduced motion uses still',page.locator('.pip-image').get_attribute('src').endswith('.png'))
        page.emulate_media(reduced_motion='no-preference')
        # A failed renderer on a new page must not prevent any study UI.
        page.set_content(html().replace('<main id="es-app">','<script>const orig=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,...a){return t==="webgl2"?null:orig.call(this,t,...a)};</script><main id="es-app">'))
        page.locator('.es-focus-row').first.wait_for();page.locator('.pip-card[data-pip-renderer="fallback"]').wait_for()
        check('GPU unavailable leaves full planner usable',page.locator('[data-action="study"]').count()==3)
        page.locator('[data-action="back-to-anki"]').click();page.wait_for_timeout(60);check('Back to Anki action stays reachable',CALLS[-1][0]=='back_to_anki')
        check('No external network requests',not REMOTE)
        check('No uncaught JavaScript exceptions',not ERRORS)
        browser.close()
    (ROOT/'docs/ui-096-results.json').write_text(json.dumps({'checks':len(CHECKS),'passed':CHECKS,'errors':ERRORS,'unexpected_network':REMOTE,'real_webgl2':True,'anki_bridge':'synthetic, not native','native_windows_anki':False},indent=2))
if __name__=='__main__':run()

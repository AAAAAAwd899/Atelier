"""Production web assets with synthetic Anki bridge. NOT a native Anki test."""
from pathlib import Path
import sys, json, shutil, base64
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
import test_ui as f
from addon.core import PracticeSession, CardInfo
from addon.session_tools import growth_signal
OUT=ROOT/'docs/screenshots-095';OUT.mkdir(parents=True,exist_ok=True)
WEB=ROOT/'addon/web';CHECKS=[];ERRORS=[];CALLS=[]
f.NIGHT=True
f.STORE.save_settings({**f.STORE.state['settings'],'theme':'midnight'})
original=f.command

def command(action,p):
    CALLS.append((action,p))
    if action in ('study','focus','back_to_anki'):return {'started':True}
    if action=='review_misses':return {'empty':True,'message':'No missed cards in this sample result.'}
    out=original(action,p)
    if action=='load':out['asset_base']='/_addons/exam_sprout/web'
    return out
f.command=command

def html():
    css=''.join((WEB/x).read_text() for x in ['app.css','countdown.css','pip.css'])
    js=';'.join((WEB/x).read_text() for x in ['countdown.js','pip.js','app.js'])
    return '<!doctype html><html><head><base href="http://sprout.test/"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main id="es-app"></main><script>window.pycmd=m=>window.fixtureCommand(JSON.parse(m.slice(12))).then(window.ExamSprout.receive);</script><script>'+js+'</script></body></html>'

def route(req):
    path=req.request.url.split('/web/',1)[-1]
    p=(WEB/path).resolve()
    if WEB.resolve() in p.parents and p.is_file():req.fulfill(path=str(p))
    else:req.fulfill(status=404,body='')

def check(name,ok=True):
    assert ok,name;CHECKS.append(name);print('PASS',name,flush=True)

def run():
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        page=b.new_page(viewport={'width':1440,'height':980});page.on('pageerror',lambda e:ERRORS.append(str(e)));page.set_default_timeout(6000)
        page.route('**/_addons/exam_sprout/web/**',route);page.expose_function('fixtureCommand',f.bridge)
        page.set_content(html());page.locator('.es-focus-row').first.wait_for()
        check('Distinct study, focus practice and browse actions', all(page.locator(f'.es-focus-actions [data-action="{a}"]').count()==3 for a in ['study','focus','browse']))
        for a in ['study','focus','browse']:
            page.locator(f'.es-focus-actions [data-action="{a}"]').first.click();page.wait_for_timeout(100)
            check('Click routes to '+a, CALLS[-1][0]==a)
        page.wait_for_function('Array.from(document.querySelectorAll(".pip-image")).every(i=>i.complete&&i.naturalWidth>0)')
        check('Pip is rendered 3D raster art, not an SVG',page.locator('.pip-image').count()==1 and page.locator('.es-companion-panel svg').count()==0)
        src=page.locator('.pip-image').get_attribute('src');check('Idle uses packaged animated WebP',src.endswith('-idle.webp'))
        page.locator('[data-pip-action="pet"]').last.click();check('Pet plays its own animation',page.locator('.pip-image').get_attribute('src').endswith('-pet.webp'))
        page.locator('[data-pip-action="water"]').click();check('Water plays its own animation',page.locator('.pip-image').get_attribute('src').endswith('-water.webp'))
        before=page.locator('.es-pip-progress>strong').inner_text()
        page.locator('[data-pip-action="pet"]').last.click();check('Playing does not inflate study signal',page.locator('.es-pip-progress>strong').inner_text()==before)
        page.locator('[data-pip-action="pause"]').click();check('Pause uses a static PNG',page.locator('.pip-image').get_attribute('src').endswith('.png'))
        page.locator('[data-pip-action="pause"]').click();check('Resume restores idle animation',page.locator('.pip-image').get_attribute('src').endswith('-idle.webp'))
        page.emulate_media(reduced_motion='reduce');page.wait_for_function('document.querySelector(".pip-image").src.endsWith(".png")');check('Reduced motion keeps real static art',page.locator('.pip-image').get_attribute('src').endswith('.png'))
        page.emulate_media(reduced_motion='no-preference');page.evaluate('window.PipCompanion.pause()')
        page.screenshot(path=str(OUT/'Exam_Sprout_Overview.png'))
        for width in [1440,1100,940,720,620,390]:
            page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(60)
            check(f'{width}px overview does not overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            if width==390:page.screenshot(path=str(OUT/'Exam_Sprout_Narrow.png'),full_page=True)
        page.set_viewport_size({'width':1220,'height':950})
        page.locator('[data-action="edit"]').click();page.locator('[data-action="next-step"]').click()
        page.locator('[data-bulk="confidence"]').select_option('1');page.locator('[data-action="apply-bulk"][data-kind="confidence"]').click()
        check('Set-all confidence changes all selected rows',page.locator('select[data-special="confidence"]:enabled').evaluate_all('els=>els.every(e=>e.value==="1")'))
        page.locator('[data-bulk="emphasis"]').fill('2');page.locator('[data-action="apply-bulk"][data-kind="emphasis"]').click()
        check('Set-all emphasis changes all selected rows',page.locator('input[data-special="emphasis"]:enabled').evaluate_all('els=>els.every(e=>e.value==="2")'))
        page.screenshot(path=str(OUT/'Exam_Sprout_Deck_Setup.png'))
        page.locator('[data-action="cancel-form"]').click();page.locator('[data-action="confirm-modal"]').click()
        page.locator('.es-top-nav [data-action="nav"][data-view="practice"]').click()
        page.locator('[data-practice="size"]').fill('100');page.locator('[data-action="prepare"]').click()
        check('Practice allocation is a 100-card sample', '100 cards' in page.locator('.es-modal h2').inner_text())
        check('No raw deck-ID error spam in sample', 'has no eligible cards after' not in page.locator('.es-modal').inner_text())
        page.screenshot(path=str(OUT/'Exam_Sprout_Practice_Allocation.png'))
        page.locator('[data-action="close-modal"]').click();page.locator('[data-action="nav"][data-view="settings"]').click()
        check('Pip and local response-retention settings available',all(page.locator(f'[data-setting="{k}"]').count()==1 for k in ['show_pip','reviewer_pip','animate_pip','remember_answers']))
        check('Responses are opt-in',not page.locator('[data-setting="remember_answers"]').is_checked())
        page.screenshot(path=str(OUT/'Exam_Sprout_Settings.png'),full_page=True)
        for theme in ['inherit','sage','lavender','peach','rose','sky','midnight']:
            page.locator(f'[data-action="theme"][data-value="{theme}"]').click();page.wait_for_timeout(80)
            check(theme+' theme remains selectable',page.locator('#es-app').get_attribute('data-theme')==theme)
        page.locator('[data-action="back-to-anki"]').click();check('Back to Anki has a dedicated action',CALLS[-1][0]=='back_to_anki')
        check('No uncaught browser errors',not ERRORS)
        b.close()
    (ROOT/'docs/ui-095-results.json').write_text(json.dumps({'checks':len(CHECKS),'passed':CHECKS,'errors':ERRORS,'native_anki':False},indent=2))
if __name__=='__main__':run()

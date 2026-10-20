"""Real Chromium + shipped tour, synthetic collection; not native Anki evidence."""
from pathlib import Path
import json,os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from suite_fixtures import home_suite,core,ROOT,worlds

OUT=ROOT/'verification/onboarding';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/onboarding-105';SH.mkdir(parents=True,exist_ok=True)

def document(theme='forest',owner='atelier',status='new',page='desk'):
    soup=BeautifulSoup(home_suite(theme,owner,page),'html.parser')
    tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
    marker={'version':0 if status=='new' else 1,'status':status}
    boot['profile']['onboarding']=marker;boot['demo']['profile']['onboarding']=marker
    boot['showOnboarding']=True;tag.string=core.json_for_html(boot)
    return str(soup)

def main():
    checks=[];errors=[]
    def check(name,ok):
        assert ok,name
        checks.append(name)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        def page(**kwargs):
            p=browser.new_page(**kwargs)
            p.route('http://atelier-tour.invalid/',lambda r:r.fulfill(content_type='text/html',body='<html><head></head><body></body></html>'))
            p.goto('http://atelier-tour.invalid/')
            return p
        for width,height,theme in [(1440,900,'forest'),(1024,600,'obsidian'),(390,700,'rose'),(320,600,'linen')]:
            p=page(viewport={'width':width,'height':height},reduced_motion='reduce')
            p.on('pageerror',lambda e:errors.append(str(e)))
            p.set_content(document(theme));p.locator('.tour-card').wait_for()
            before=p.evaluate("JSON.stringify(JSON.parse(localStorage.getItem('atelier-preview-v070')))")
            check(f'{width} first-run offer and optional skip',p.locator('#tour-title').inner_text()=='A quick look around Atelier.' and p.locator('[data-action="tour-skip"]').count()==2)
            check(f'{width} background inert and keyboard captured',p.locator('#atelier-root').evaluate('e=>e.shadowRoot.querySelector(".frame").inert'))
            p.screenshot(path=str(SH/f'{theme}-welcome-{width}.png'),animations='disabled')
            p.locator('[data-action="tour-next"]').click()
            for index in range(12):
                card=p.locator('.tour-card');card.wait_for()
                geo=card.evaluate('e=>{const r=e.getBoundingClientRect();return {fit:r.left>=14&&r.top>=14&&r.right<=innerWidth-14&&r.bottom<=innerHeight-14,overflow:e.scrollWidth>e.clientWidth+1}}')
                if not geo['fit'] or geo['overflow']:p.screenshot(path=str(SH/f'failure-{width}-step-{index+1}.png'));print(geo)
                check(f'{width} step {index+1} contained and readable',geo['fit'] and not geo['overflow'])
                check(f'{width} step {index+1} highlights a visible real control',p.locator('.tour-spotlight').is_visible())
                check(f'{width} step {index+1} target task matches tour state',p.evaluate('AtelierMakeover.diagnostics().tourStep')==index)
                if index in (2,3,9) and width in (1440,390):p.screenshot(path=str(SH/f'{theme}-step-{index+1}-{width}.png'),animations='disabled')
                if index==2:
                    p.locator('[data-action="tour-back"]').click();check(f'{width} Back revisits prior step',p.evaluate('AtelierMakeover.diagnostics().tourStep')==1)
                    p.locator('[data-action="tour-next"]').click()
                p.locator('[data-action="tour-next"]').click()
            check(f'{width} completion offers real next tasks',p.locator('[data-action="tour-task"]').count()==3)
            p.locator('[data-action="tour-next"]').click();p.locator('.tour-card').wait_for(state='detached')
            p.wait_for_function("JSON.parse(localStorage.getItem('atelier-preview-v070')).profile.onboarding.status==='completed'")
            check(f'{width} completed tour changes only help marker',p.evaluate('''before=>{const a=JSON.parse(before),b=JSON.parse(localStorage.getItem('atelier-preview-v070'));delete a.profile.onboarding;delete b.profile.onboarding;return JSON.stringify(a)===JSON.stringify(b)}''',before))
            check(f'{width} prior page restored and background unlocked',p.evaluate('AtelierMakeover.diagnostics().page')=='desk' and not p.locator('#atelier-root').evaluate('e=>e.shadowRoot.querySelector(".frame").inert'))
            p.evaluate('AtelierMakeover.openTour()');p.locator('[data-action="tour-next"]').click()
            p.locator('[data-action="tour-next"]').focus();p.keyboard.press('Tab')
            check(f'{width} keyboard focus wraps inside tour',p.locator('#atelier-root').evaluate('e=>e.shadowRoot.activeElement.dataset.action')=='tour-skip')
            p.keyboard.press('Escape');p.locator('.tour-card').wait_for(state='detached')
            p.wait_for_function("JSON.parse(localStorage.getItem('atelier-preview-v070')).profile.onboarding.status==='skipped'")
            check(f'{width} Escape dismisses and replay remains available',p.locator('[data-action="guided-tour"]').count()>0)
            p.set_content(document(theme));p.wait_for_function('AtelierMakeover.diagnostics().loaded')
            check(f'{width} saved dismissal prevents another automatic offer',p.locator('.tour-card').count()==0)
            p.close()
        # Keep the original design/third-party ownership free of onboarding overlays.
        for owner in ['external','onigiri','ask']:
            p=page();p.set_content(document(owner=owner));p.wait_for_timeout(300)
            check(f'{owner} original ownership has no automatic tour',p.locator('.tour-card').count()==0);p.close()
        # The guide inherits the palette for every accepted world.
        for theme in core.THEMES:
            p=page(viewport={'width':1440,'height':900});p.set_content(document(theme));p.locator('.tour-card').wait_for()
            check(f'{theme} guide uses readable themed surfaces',p.locator('.tour-card').evaluate('e=>{const s=getComputedStyle(e);return s.color!==s.backgroundColor&&s.borderTopWidth==="2px"}'))
            p.close()
        # An explicit final task opens the existing multi-parent scope editor.
        p=page();p.set_content(document());p.locator('.tour-card').wait_for()
        for _ in range(13):p.locator('[data-action="tour-next"]').click()
        p.locator('[data-action="tour-task"][data-task="focus"]').click();p.locator('#study-form').wait_for()
        check('Choose study folders opens the existing multi-parent picker',p.locator('#deck-picker').is_visible())
        p.close();browser.close()
    check('No uncaught browser errors',not errors)
    (OUT/'results.json').write_text(json.dumps({'version':core.VERSION,'category':'Chromium fixture; synthetic library','count':len(checks),'checks':checks,'errors':errors},indent=2)+'\n')
    print('PASS onboarding',len(checks))

if __name__=='__main__':main()

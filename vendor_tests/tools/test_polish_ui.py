"""Additional 0.9.1 presentation tests. Production components, synthetic data."""
from __future__ import annotations
import json
import shutil
from copy import deepcopy
from playwright.sync_api import sync_playwright
import test_ui as t
from addon.core import THEMES
from addon.widget import countdown_html

OUT=t.OUT
CHECKS=[]

def check(name, value):
    assert value,name
    CHECKS.append(name)
    print('PASS',name,flush=True)

def host_html(theme='inherit',dark=False,compact=True):
    t.STORE.save_settings({**t.STORE.state['settings'],'theme':theme,'compact':compact})
    bg,fg,link=('#252633','#f0edf5','#c3b9e7') if dark else ('#fcfcfd','#303745','#736690')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    body{{margin:0;padding:0;background:{bg};color:{fg};--link:{link};font:14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
    .host{{max-width:740px;margin:0 auto;padding:32px 28px}}
    .tag{{text-align:center;font-size:10px;letter-spacing:1.4px;opacity:.65;margin-bottom:30px;text-transform:uppercase}}
    .nav{{display:flex;justify-content:center;gap:30px;margin-bottom:40px;font-size:13px}}
    .row{{display:flex;justify-content:space-between;align-items:center;padding:17px 12px;border-bottom:1px solid #8883}}
    .row small{{opacity:.6}}.caption{{text-align:center;opacity:.6;font-size:10px;margin:20px 0 0;line-height:1.7}}
    { (t.ROOT/'addon/web/countdown.css').read_text() }
    </style></head><body><div class="host"><div class="tag">Production countdown · sample deck-screen host</div><div class="nav"><span>Decks</span><span>Add</span><span>Browse</span><span>Stats</span><span>Sync</span><span>Exams</span></div><div class="row" id="host-sentinel">Pharmacotherapy<small>45 due</small></div><div class="row">Microbiology<small>22 due</small></div><div class="row">Clinical skills<small>8 due</small></div>{countdown_html(t.STORE)}<div class="caption">Actual add-on component with sample exams. Not an installed Anki screenshot.</div></div><script>window.pycmd=m=>window.lastCommand=m;</script><script>{(t.ROOT/'addon/web/countdown.js').read_text()}</script></body></html>'''

def run():
    errors=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        page=b.new_page(viewport={'width':1100,'height':1140},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.expose_function('fixtureCommand',t.bridge)
        for night in (False,True):
            t.NIGHT=night
            t.STORE.save_settings({**t.STORE.state['settings'],'theme':'inherit'})
            page.set_content(t.page_html());page.locator('.es-focus-row').first.wait_for()
            page.screenshot(path=str(OUT/('Exam Sprout - Dark planner.png' if night else 'Exam Sprout - Planner.png')))
            page.locator('nav [data-view="settings"]').click()
            for theme in THEMES:
                page.locator(f'[data-action="theme"][data-value="{theme}"]').click()
                page.wait_for_function('(theme)=>document.querySelector("#es-countdowns")?.dataset.theme===theme',arg=theme)
                check(f'{theme} live preview matches saved theme ({"dark" if night else "light"})',page.locator('#es-countdowns').get_attribute('data-theme')==t.STORE.state['settings']['theme'])
                check(f'{theme} live preview is inert ({night})',page.locator('#es-countdowns').evaluate('(e)=>e.inert'))
            # New presets render the entire planner, not just a color swatch.
            for theme in ['rose','sky','midnight']:
                page.locator(f'[data-action="theme"][data-value="{theme}"]').click()
                page.wait_for_function('(theme)=>document.querySelector("#es-app")?.dataset.theme===theme',arg=theme)
                page.locator('nav [data-view="overview"]').click();page.locator('.es-focus-row').first.wait_for()
                check(f'{theme} planner retains 3 priority rows ({night})',page.locator('.es-focus-row').count()==3)
                page.screenshot(path=str(OUT/f'Exam Sprout - {theme.title()} {"dark" if night else "light"}.png'))
                page.locator('nav [data-view="settings"]').click()
        page.locator('[data-action="theme"][data-value="rose"]').click()
        page.wait_for_function('document.querySelector("#es-countdowns").dataset.theme==="rose"')
        page.locator('[data-setting="compact"]').uncheck()
        page.wait_for_function('document.querySelector("#es-countdowns").dataset.compact==="false"')
        check('Expanded preview shows the actual exam date',page.locator('#es-countdowns .es-chip-sub').first.is_visible())
        page.locator('[data-setting="show_countdown"]').uncheck()
        page.wait_for_function('document.querySelector(".es-preview-stage > p").textContent.includes("hidden")')
        check('Hidden countdown keeps live appearance preview',page.locator('#es-countdowns').is_visible() and countdown_html(t.STORE)=='')
        page.locator('[data-setting="show_countdown"]').focus();page.keyboard.press('Space')
        page.wait_for_timeout(120)
        check('Keyboard focus survives toggle save',page.evaluate('document.activeElement.dataset.setting')=='show_countdown')
        check('Space key restored visible countdown',t.STORE.state['settings']['show_countdown'])
        page.locator('[data-setting="max_countdowns"]').select_option('1')
        page.wait_for_timeout(150)
        check('Count limit uses the actual Python renderer',page.locator('#es-countdowns .es-chip').count()==1 and '+1 more' in page.locator('#es-countdowns').inner_text())
        page.locator('[data-setting="max_countdowns"]').select_option('2');page.wait_for_timeout(100)
        page.locator('[data-setting="compact"]').check();page.wait_for_timeout(100)
        for width in [360,560,780,1100]:
            page.set_viewport_size({'width':width,'height':1100})
            page.locator('nav [data-view="overview"]').click();page.locator('.es-focus-row').first.wait_for()
            check(f'Planner fits {width}px without horizontal overflow',t.overflow(page))
            page.locator('nav [data-view="settings"]').click()
            check(f'Settings and preview fit {width}px without horizontal overflow',t.overflow(page))
        t.NIGHT=False;t.STORE.save_settings({**t.STORE.state['settings'],'theme':'inherit'})
        page.set_content(t.page_html());page.locator('.es-focus-row').first.wait_for()
        page.locator('nav [data-view="settings"]').click()
        page.screenshot(path=str(OUT/'Exam Sprout - Settings.png'),full_page=True)
        page.locator('nav [data-view="overview"]').click();page.set_viewport_size({'width':560,'height':1100})
        page.screenshot(path=str(OUT/'Exam Sprout - Narrow planner.png'),full_page=True)
        # Direct production widget tests. Its CSS must leave host geometry/colors alone.
        page.set_viewport_size({'width':880,'height':510})
        for theme in THEMES:
            for dark in (False,True):
                page.set_content(host_html(theme,dark));page.locator('#es-countdowns [data-bound]').count()
                check(f'{theme} widget detects {"dark" if dark else "light"} host',page.locator('#es-countdowns').get_attribute('data-dark')==str(dark).lower())
                check(f'{theme} widget compact height ({dark})',page.locator('.es-chip').first.bounding_box()['height']<=52)
                page.locator('.es-chip').first.click()
                check(f'{theme} widget click opens correct exam ({dark})',page.evaluate('window.lastCommand')=='exam-sprout:open:pharm3')
        for dark in (False,True):
            page.set_content(host_html('inherit',dark))
            sentinel=page.locator('#host-sentinel').evaluate('(e)=>{const c=getComputedStyle(e);return {color:c.color,font:c.font,padding:c.padding,border:c.borderBottom}}')
            page.evaluate('document.querySelectorAll("style").forEach(e=>e.textContent=e.textContent.slice(0,e.textContent.indexOf("/* Every selector")))')
            after=page.locator('#host-sentinel').evaluate('(e)=>{const c=getComputedStyle(e);return {color:c.color,font:c.font,padding:c.padding,border:c.borderBottom}}')
            check(f'Widget CSS leaves host styles unchanged ({dark})',sentinel==after)
        page.set_content(host_html('rose',False,False))
        page.screenshot(path=str(OUT/'Exam Sprout - Rose countdown.png'))
        page.set_content(host_html('inherit',True,True))
        page.screenshot(path=str(OUT/'Exam Sprout - Dark countdown.png'))
        page.emulate_media(reduced_motion='reduce');page.locator('.es-chip').first.hover()
        check('Reduced-motion preference disables widget movement',page.locator('.es-chip').first.evaluate('(e)=>getComputedStyle(e).transform')=='none')
        page.emulate_media(reduced_motion='no-preference')
        # Invalid timestamps stay legible instead of yielding NaN or stale labels.
        page.locator('[data-deadline]').first.evaluate('(e)=>e.dataset.deadline="invalid"')
        page.evaluate('window.ExamSproutCountdown.mount()')
        check('Invalid date has an explicit fallback',page.locator('[data-deadline]').first.inner_text()=='Check date')
        page.locator('[data-deadline]').first.evaluate('(e)=>e.dataset.deadline="2000-01-01T00:00"');page.evaluate('window.ExamSproutCountdown.mount()')
        check('Expired widget does not display a negative countdown',page.locator('[data-deadline]').first.inner_text()=='Exam time')
        page.set_content(host_html('inherit',False,True));page.screenshot(path=str(OUT/'Exam Sprout - Countdown.png'))
        check('No uncaught browser errors in polish tests',not errors)
        b.close()
    report={'suite':'0.9.2 production presentation regression checks','checks_passed':len(CHECKS),'checks':CHECKS,'javascript_errors':errors,'native_anki_tested':False}
    (t.ROOT/'docs/polish-results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':run()

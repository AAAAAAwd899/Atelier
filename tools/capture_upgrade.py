"""Capture the shipped frontend with fictional fixtures, never native Anki claims."""
from pathlib import Path
import sys, json, time, statistics
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
from suite_fixtures import home_suite
from playwright.sync_api import sync_playwright

def run(label):
    out=ROOT/'output'/'playwright'/label
    out.mkdir(parents=True, exist_ok=True)
    errors=[]; timings=[]; records=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER'))
        for theme in ['midnight','rose','forest']:
            for width,height in [(1440,900),(1280,720),(390,720)]:
                page=browser.new_page(viewport={'width':width,'height':height})
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.set_content(home_suite(theme))
                page.locator('.unified-topbar').wait_for()
                for destination in ['desk','widgets']:
                    if destination=='widgets':
                        if width<821:page.locator('[data-action="mobile"]').first.click()
                        page.locator('.sidebar [data-action="widget-page"]').click()
                    page.wait_for_timeout(200)
                    name=f'{theme}-{destination}-{width}x{height}.png'
                    page.screenshot(path=str(out/name),animations='disabled')
                    bounds=page.locator('.main').evaluate('(e)=>({width:e.clientWidth,scroll:e.scrollWidth})')
                    records.append({'capture':name,'bounds':bounds,'overflow':bounds['scroll']>bounds['width']+2})
                page.close()
        page=browser.new_page(viewport={'width':1440,'height':900})
        page.set_content(home_suite('midnight'))
        for i in range(24):
            target='library' if i%2 else 'desk'
            start=time.perf_counter()
            page.locator('.nav-group [data-action="home"]' if target=='desk' else '.nav-group [data-page="library"]').click()
            page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            if i>3:timings.append((time.perf_counter()-start)*1000)
        browser.close()
    report={'category':'browser fixture; fictional data; real shipped frontend','label':label,'errors':errors,'captures':records,
            'navigation_ms':{'n':len(timings),'median':statistics.median(timings),'p95':sorted(timings)[int(len(timings)*.95)-1],'includes':'Playwright click and two frames; same local host'}}
    (out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':run(sys.argv[1])

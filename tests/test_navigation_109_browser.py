"""Navigation/icon/motion coverage of shipped UI; fictional collection only."""
from test_ui_audit_browser import sort_doc
from suite_fixtures import home_suite,worlds
from fixtures import ROOT
from playwright.sync_api import sync_playwright
import os,json
OUT=ROOT/'verification/navigation-109';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/navigation-109';SH.mkdir(parents=True,exist_ok=True)

def run():
    checks=[];errors=[]
    def check(name,ok):
        assert ok,name
        checks.append(name);print('PASS',name,flush=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
        for width,height in [(1440,900),(1024,600),(390,720)]:
            p=browser.new_page(viewport={'width':width,'height':height});p.set_default_timeout(9000);p.on('pageerror',lambda e:errors.append(str(e)))
            p.set_content(sort_doc());p.locator('.unified-topbar').wait_for()
            for selector in ['.decks-top','.add-cards-top','.browse-top','.stats-top','.sync-top','.addon-tools-top']:
                check(f'{width} visible {selector}',p.locator('.anki-commandbar '+selector).is_visible())
            check(f'{width} header fits viewport',p.locator('.unified-topbar').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
            check(f'{width} header leaves room for the library',p.locator('.unified-topbar').bounding_box()['height']<(170 if width<600 else 140))
            p.locator('.decks-top').click();p.locator('[data-view=outline]').click()
            p.locator('.outline-row[data-node="90"] [data-action=expand]').click()
            check(f'{width} outline shows children without leaving the folder',p.locator('.outline-row[data-node="99"]').count()==1)
            p.locator('.outline-row[data-node="99"] [data-action=expand]').click()
            check(f'{width} hierarchy preserves nested children',p.locator('.outline-row[data-node="992"]').count()==1)
            check(f'{width} outline stays within viewport',p.locator('.folder-outline').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
            p.screenshot(path=str(SH/f'folder-outline-{width}.png'),animations='disabled')
            p.locator('.outline-row[data-node="99"] [data-action=organize]').click()
            p.locator('[data-action=folder-icon][data-icon=bow]').click();p.wait_for_timeout(150)
            check(f'{width} icon selection saved and visible in chooser',p.locator('[data-action=folder-icon][data-icon=bow]').get_attribute('aria-pressed')=='true')
            p.get_by_role('button',name='Close dialog',exact=True).click()
            check(f'{width} icon appears in outline',p.locator('.outline-row[data-node="99"] .custom-folder-icon').inner_text()=='🎀')
            p.locator('.outline-row[data-node="99"] [data-action=organize]').click();p.locator('[data-action=folder-icon][data-icon=default]').click();p.get_by_role('button',name='Close dialog',exact=True).click()
            check(f'{width} reset restores original folder artwork',p.locator('.outline-row[data-node="99"] .custom-folder-icon').count()==0)
            p.locator('.unified-topbar [data-action=appearance]').click();body=p.locator('.dialog-body');body.evaluate('e=>e.scrollTop=180')
            positions=p.locator('.theme-tile').evaluate_all('xs=>xs.map(e=>({x:e.offsetLeft,y:e.offsetTop,w:e.offsetWidth,h:e.offsetHeight}))')
            for theme in ['rose','forest','obsidian','castle']:
                tile=p.locator('[data-theme-choice="'+theme+'"]');tile.evaluate('e=>e.click()');p.wait_for_timeout(220)
                current=p.locator('.theme-tile').evaluate_all('xs=>xs.map(e=>({x:e.offsetLeft,y:e.offsetTop,w:e.offsetWidth,h:e.offsetHeight}))')
                check(f'{width} {theme} selection keeps tile geometry',positions==current)
            p.screenshot(path=str(SH/f'stable-worlds-{width}.png'),animations='disabled')
            p.close()
        browser.close()
    check('No uncaught errors',not errors)
    (OUT/'results.json').write_text(json.dumps({'count':len(checks),'checks':checks,'errors':errors,'category':'Chromium synthetic collection; not native Anki'},indent=2)+'\n')
if __name__=='__main__':run()

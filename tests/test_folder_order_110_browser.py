from test_ui_audit_browser import sort_doc
from fixtures import ROOT,core
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os,json
OUT=ROOT/'verification/folder-order-110';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/folder-order-110';SH.mkdir(parents=True,exist_ok=True)

def document():
    soup=BeautifulSoup(sort_doc(),'html.parser');tag=soup.find(id='atelier-bootstrap');b=json.loads(tag.string)
    b['demo']['nodes'].append({'id':'200','name':'Second course','path':'Second course','parent':'0','children':[],'depth':0,'review':0,'learn':0,'new':7,'filtered':False})
    tag.string=core.json_for_html(b);return str(soup)

def run():
    checks=[];errors=[]
    def check(label,ok):assert ok,label;checks.append(label);print('PASS',label,flush=True)
    with sync_playwright() as w:
        browser=w.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
        for width,height in [(1440,900),(1024,600),(390,720)]:
            p=browser.new_page(viewport={'width':width,'height':height});p.set_default_timeout(9000);p.on('pageerror',lambda e:errors.append(str(e)))
            p.set_content(document());p.locator('.decks-top').click();p.locator('[data-view=list]').click()
            p.locator('.library-row[data-node="200"] .exam-pin').click()
            check(f'{width} direct Set exam activates the exact row',p.locator('.library-row[data-node="200"] .exam-pin').inner_text()=='Exam active' and len(p.evaluate('AtelierMakeover.diagnostics().activeStudies'))==2)
            p.locator('[data-action=arrange-order]').click();p.locator('[data-action=order-up][data-id="200"]').click()
            check(f'{width} reorder preview moves selected course',p.locator('.arrange-row').first.get_attribute('data-order-id')=='200')
            p.get_by_role('button',name='Cancel',exact=True).click()
            check(f'{width} Cancel preserves original order',p.locator('.library-row').first.get_attribute('data-node')=='90')
            p.locator('[data-action=arrange-order]').click();p.locator('[data-action=order-top][data-id="200"]').click()
            p.screenshot(path=str(SH/f'arrange-{width}.png'),animations='disabled')
            p.locator('[data-action=order-save]').click();p.locator('.dialog').wait_for(state='detached')
            check(f'{width} saved custom root order appears immediately',p.locator('.library-row').first.get_attribute('data-node')=='200' and p.locator('#atelier-sort').input_value()=='custom')
            p.locator('.library-row[data-node="90"] [data-action=navigate]').first.click();p.locator('[data-action=arrange-order]').click()
            p.locator('[data-action=order-top][data-id="91"]').click();p.locator('[data-action=order-save]').click();p.locator('.dialog').wait_for(state='detached')
            check(f'{width} lecture order is saved separately',p.locator('.library-row').first.get_attribute('data-node')=='91')
            p.locator('.breadcrumbs [data-page="library"]').click()
            check(f'{width} root order survives nested ordering',p.locator('.library-row').first.get_attribute('data-node')=='200')
            p.locator('[data-view=outline]').click()
            check(f'{width} outline uses the same saved root order',p.locator('.outline-row').first.get_attribute('data-node')=='200')
            check(f'{width} explicit exam action remains available in outline',p.locator('.outline-row[data-node="90"] .exam-pin').is_visible())
            check(f'{width} custom-order controls do not overflow',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
            p.screenshot(path=str(SH/f'custom-order-{width}.png'),animations='disabled')
            p.locator('[data-action=arrange-order]').click();p.locator('[data-action=order-reset]').click();p.locator('.dialog').wait_for(state='detached')
            check(f'{width} name order can be restored',p.locator('.outline-row').first.get_attribute('data-node')=='90')
            p.close()
        browser.close()
    check('No uncaught errors',not errors)
    (OUT/'results.json').write_bytes((json.dumps({'count':len(checks),'checks':checks,'errors':errors,'category':'shipped frontend with synthetic collection; no native Anki claim'},indent=2)+'\n').encode())
if __name__=='__main__':run()

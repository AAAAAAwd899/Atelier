"""Capture the actual live-change fix and ordering controls; sample data only."""
from test_ui_audit_browser import home_suite, sort_doc, ROOT
from playwright.sync_api import sync_playwright
import json

def main():
    dist=ROOT/'dist';dist.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        p=b.new_page(viewport={'width':1440,'height':960});errors=[]
        p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(home_suite('midnight'));p.locator('.world-window').wait_for()
        p.locator('.unified-topbar [data-action=appearance]').click()
        p.locator('[data-theme-choice=rose]').click();p.wait_for_timeout(160)
        p.locator('[data-action=close-dialog]').first.click();p.wait_for_timeout(100)
        result=p.locator('.world-window').evaluate('e=>({world:e.dataset.world,name:e.querySelector("small").textContent,title:e.querySelector("strong").textContent})')
        assert result=={'world':'rose','name':'Rose Quartz','title':'The secret garden'},result
        p.screenshot(path=str(dist/'Atelier-Live-Theme-Fix.png'),animations='disabled')
        p.set_content(sort_doc());p.locator('#atelier-sort').wait_for();p.locator('#atelier-sort').select_option('name');p.wait_for_timeout(80)
        p.locator('.library').scroll_into_view_if_needed()
        p.screenshot(path=str(dist/'Atelier-Lecture-Sorting.png'),animations='disabled')
        assert not errors,errors
        (ROOT/'verification/ui-audit/live-capture.json').write_text(json.dumps({'from':'midnight','after':result,'errors':errors,'renderer':'Chromium; fictional data; not native Anki'},indent=2))
        b.close()
    print('Captured successful Midnight-to-Rose transition and hierarchical sort controls.')
if __name__=='__main__':main()

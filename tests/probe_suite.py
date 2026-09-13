from suite_fixtures import *
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 p=b.new_page(viewport={'width':1440,'height':1000});errs=[]
 p.on('pageerror',lambda e:errs.append(str(e)))
 p.set_content(home_suite());p.wait_for_timeout(800)
 p.screenshot(path=str(ROOT/'screenshots/probe-forest.png'),full_page=True)
 print('errors',errs,'boot',p.evaluate('document.getElementById("atelier-bootstrap").textContent.slice(0,200)'))
 print('actions',p.locator('.unified-topbar [data-action="native-tool"]').count())
 p.locator('[data-action="page"][data-page="tools"]').first.click();p.screenshot(path=str(ROOT/'screenshots/probe-tools.png'),full_page=True)
 print('tools',p.locator('.tools-grid').count())
 p.set_content(home_suite('rose'));p.wait_for_timeout(500);p.screenshot(path=str(ROOT/'screenshots/probe-rose.png'),full_page=True)
 b.close()

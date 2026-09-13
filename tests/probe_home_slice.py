from suite_fixtures import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'screenshots/home-polish';OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 p=b.new_page(viewport={'width':1440,'height':960});p.on('pageerror',lambda e:print('PAGEERROR',e));p.set_content(home_suite('forest'))
 p.locator('.suite-plan').first.wait_for();p.screenshot(path=str(OUT/'forest-home.png'))
 p.locator('[data-page=library]').first.click();p.screenshot(path=str(OUT/'forest-library.png'))
 p.locator('.deck-card .card-title').first.click();p.locator('[data-action=view][data-view=list]').click();p.wait_for_timeout(80);p.screenshot(path=str(OUT/'forest-list.png'))
 p.locator('[data-page=tools]').first.click();p.screenshot(path=str(OUT/'forest-tools.png'))
 p.locator('#atelier-search').fill('media');p.screenshot(path=str(OUT/'forest-tool-search.png'))
 p.close();b.close()

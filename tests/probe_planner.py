from planner_suite_fixture import *
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 p=b.new_page(viewport={'width':1440,'height':1020});p.set_default_timeout(10000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)));expose(p)
 p.set_content(html());p.locator('.es-readiness-grade').wait_for();p.wait_for_timeout(1000);p.emulate_media(reduced_motion='reduce');p.screenshot(path=str(ROOT/'screenshots/probe-planner.png'),full_page=True)
 p.locator('.es-top-nav [data-view="practice"]').click();p.screenshot(path=str(ROOT/'screenshots/probe-practice.png'),full_page=True)
 p.locator('.suite-tool-links [data-command="add"]').click();p.wait_for_timeout(100);print('errs',errors,'calls',CALLS[-2:]);print('overflow',p.evaluate('document.documentElement.scrollWidth>innerWidth'))
 b.close()

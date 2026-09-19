"""Card Studio release wording in the real frontend with local test-only records."""
import json
from playwright.sync_api import sync_playwright
from card_studio_harness import UnifiedHost,ROOT
OUT=ROOT/'verification/release-one-card';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/release-one';SH.mkdir(parents=True,exist_ok=True)
def main():
 checks=[];errors=[]
 def check(name,v):
  assert v,name
  checks.append(name)
 host=UnifiedHost()
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':950});p.set_default_timeout(10000);p.on('pageerror',lambda e:errors.append(str(e)));p.expose_function('nativeBridge',host.dispatch)
  try:
   p.set_content(host.html());p.locator('.shelf-grid').wait_for()
   check('Card Studio accessible name is correct',p.locator('#ws-sidebar').get_attribute('aria-label')=='Card Studio navigation')
   p.locator('.nav-link[data-view="settings"]').click();p.locator('.settings-layout').wait_for()
   check('Single card-building workflow explained','You do not need a separate card-building add-on.' in p.locator('#ws-page').inner_text())
   check('Card Studio no longer advertises an engineering candidate','Card Studio · included with Atelier' in p.locator('#ws-page').inner_text() and 'engineering candidate' not in p.locator('#ws-page').inner_text())
   check('Provider consent retained','explicit text-sharing approval' in p.locator('#ws-page').inner_text())
   for width in [1440,940,390]:
    p.set_viewport_size({'width':width,'height':900});p.wait_for_timeout(100)
    check(str(width)+' settings no document overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
   p.set_viewport_size({'width':1440,'height':950});p.screenshot(path=str(SH/'Atelier-1.0-Card-Settings.png'),animations='disabled')
   check('No provider requests made',not any(x['action'].startswith('provider_') for x in host.requests))
   check('No script errors',not errors)
  finally:
   (OUT/'results.json').write_text(json.dumps({'version':'1.0.0','count':len(checks),'cases':checks,'errors':errors},indent=2)+'\n');b.close()
if __name__=='__main__':main()

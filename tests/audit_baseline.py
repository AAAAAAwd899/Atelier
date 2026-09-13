from suite_fixtures import *
from playwright.sync_api import sync_playwright
import json,re
OUT=ROOT/'verification/ui-audit';OUT.mkdir(exist_ok=True)
findings={}
# UTF-8 strictly read; flag common decoding corruption, not ordinary accented language.
hits=[]
for p in SRC.rglob('*'):
 if p.suffix not in ('.py','.js','.css','.json','.md','.txt','.svg'):continue
 text=p.read_text(encoding='utf-8',errors='strict')
 for number,line in enumerate(text.splitlines(),1):
  if re.search(r'\ufffd|Ã[\x80-\xbf]|Â[\xa0-\xbf]|â[€™œž“”]|ðŸ',line):hits.append({'file':str(p.relative_to(SRC)),'line':number,'snippet':line[:120]})
findings['encoding_suspects']=hits
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 p=b.new_page(viewport={'width':1440,'height':1000});p.set_content(home_suite('midnight'));p.locator('.world-window').wait_for()
 p.locator('.unified-topbar [data-action=appearance]').click();p.locator('[data-theme-choice=rose]').click();p.wait_for_timeout(200);p.locator('[data-action=close-dialog]').first.click()
 findings['theme_after_live_change']=p.evaluate("()=>({theme:AtelierMakeover.theme().name,label:document.querySelector('#atelier-root').shadowRoot.querySelector('.world-window').innerText})")
 p.screenshot(path=str(OUT/'before-live-theme.png'),animations='disabled')
 p.locator('[data-page=tools]').first.click()
 findings['tool_icons']=p.locator('.tool-tile').evaluate_all("nodes=>nodes.map(n=>({command:n.dataset.command,path:n.querySelector('svg')?.innerHTML}))")
 p.close();b.close()
(OUT/'baseline.json').write_text(json.dumps(findings,indent=2))
print(json.dumps(findings,indent=2))

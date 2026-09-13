"""Current code renders only; no fabricated native dialog or hardware screenshot."""
from suite_fixtures import *
from playwright.sync_api import sync_playwright
import html,hashlib
D=ROOT/'dist';D.mkdir(exist_ok=True);captures=[]
def record(path):captures.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
main=card('forest','basic').replace('What makes an effective study session?','What is the next step in this process?')
bar=footer('forest','question','old',True)
content='''<!doctype html><html><head><meta charset="utf-8"><title>Atelier 1.0.1 reviewer fixture</title><style>html,body{margin:0;background:#0b1e18;height:100%;font:12px system-ui;color:#c7d7cb}.note{height:35px;box-sizing:border-box;padding:9px 18px}.layout{display:grid;grid-template-rows:minmax(0,1fr) 86px;height:calc(100vh - 35px)}iframe{border:0;width:100%;height:100%;min-height:0}</style></head><body><div class="note">Atelier 1.0.1 · Browser-rendered test card · No live Anki collection</div><main class="layout"><iframe title="Card" srcdoc="'''+html.escape(main,quote=True)+'''"></iframe><iframe title="Native-shaped answer controls" srcdoc="'''+html.escape(bar,quote=True)+'''"></iframe></main></body></html>'''
(D/'Atelier-1.0.1-Reviewer-Preview.html').write_text(content)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 p=b.new_page(viewport={'width':1280,'height':760});p.set_content(content);p.wait_for_timeout(300)
 path=D/'Atelier-1.0.1-Reviewer.png';p.screenshot(path=str(path));record(path)
 p.close();p=b.new_page(viewport={'width':1280,'height':820});p.set_content(home_suite(page='tools'));p.wait_for_timeout(200)
 assert p.locator('[data-action="remote-open"]').count()==1
 path=D/'Atelier-1.0.1-Remote-Entry.png';p.screenshot(path=str(path));record(path)
 p.locator('[data-action="remote-open"]').click();p.get_by_text('The installed add-on opens Remote controls',exact=False).wait_for()
 p.locator('[data-action="toast-dismiss"]').click() if p.locator('[data-action="toast-dismiss"]').count() else p.keyboard.press('Escape')
 p.locator('#atelier-search').fill('remote');p.wait_for_timeout(250)
 assert p.get_by_role('button',name='Set up remote controls',exact=True).is_visible()
 path=D/'Atelier-1.0.1-Remote-Search.png';p.screenshot(path=str(path));record(path)
 p.close();b.close()
import sys
sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
(D/'Atelier-1.0.1-Visual-Evidence.json').write_text(json.dumps({'runtime_sha256':runtime_digest(),'captures':captures,'native_windows_or_macos':False},indent=2)+'\n')
print('Rendered',len(captures))

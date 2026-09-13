"""Fresh screenshot assets from shipped code. No generative UI or live collection."""
from pathlib import Path
import sys,json,hashlib,html,base64,subprocess
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist';S=ROOT/'screenshots/1.0.2';D.mkdir(exist_ok=True);S.mkdir(parents=True,exist_ok=True)
from playwright.sync_api import sync_playwright

def asset(mode):
 if mode=='card':
  from card_studio_harness import UnifiedHost
  h=UnifiedHost(theme='rose')
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':960});p.expose_function('nativeBridge',h.dispatch);p.set_content(h.html());p.locator('.shelf-grid').wait_for()
   p.locator(f'[data-action="open-project"][data-id="{h.primary_project}"]').first.click();p.locator(f'[data-action="open-source"][data-id="{h.primary_source}"]').first.click()
   p.locator('[data-draft="front"]').fill('What makes a useful recall question?');p.locator('[data-draft="back"]').fill('A clear prompt that tests one idea, with enough context to explain what is being asked.')
   p.wait_for_timeout(450);p.screenshot(path=str(D/'Atelier-1.0.2-Rose-Card-Studio.png'),animations='disabled');b.close()
 elif mode=='practice':
  import planner_suite_fixture as f
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':1040});f.expose(p);p.set_content(f.html('tidal'));p.locator('.es-readiness-grade').wait_for()
   p.locator('.es-top-nav [data-view="practice"]').click();p.locator('[data-practice="size"]').wait_for();p.wait_for_timeout(400);p.screenshot(path=str(D/'Atelier-1.0.2-Tidal-Practice.png'),animations='disabled');b.close()
 else:
  from suite_fixtures import home_suite,card,footer,core
  from test_native_widgets_browser import native_fixture
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
   p=b.new_page(viewport={'width':1440,'height':960});p.set_content(home_suite('forest'));p.locator('.task-focus').wait_for();p.wait_for_timeout(150);p.screenshot(path=str(D/'Atelier-1.0.2-Forest-Home.png'),animations='disabled');p.close()
   p=b.new_page(viewport={'width':1440,'height':960});p.set_content(home_suite('glacier'));p.locator('[data-action="study"][data-id="22"]').first.click();p.locator('#folder-study-order').wait_for();p.screenshot(path=str(D/'Atelier-1.0.2-Folder-Shuffle.png'),animations='disabled');p.close()
   p=b.new_page(viewport={'width':1440,'height':960});p.set_content(native_fixture('midnight'));p.locator('.nw-metrics').wait_for();p.wait_for_timeout(150);p.screenshot(path=str(D/'Atelier-1.0.2-Midnight-Widgets.png'),animations='disabled');p.close()
   main=card('ember','basic').replace('What makes an effective study session?','What is the next step in this process?');bar=footer('ember','question','old',True)
   content='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Atelier 1.0.2 — Reviewer preview</title><style>html,body{margin:0;background:#211613;height:100%;font:12px system-ui;color:#e8d2bc}.note{height:35px;box-sizing:border-box;padding:9px 18px}.layout{display:grid;grid-template-rows:minmax(0,1fr) 90px;height:calc(100vh - 35px)}iframe{border:0;width:100%;height:100%;min-height:0}</style><body><div class="note">Atelier 1.0.2 · Sample card · Browser-rendered controls, not a live Anki session</div><main class="layout"><iframe title="Sample card" srcdoc="'''+html.escape(main,quote=True)+'''"></iframe><iframe title="Sample answer controls" srcdoc="'''+html.escape(bar,quote=True)+'''"></iframe></main></body></html>'''
   (D/'Atelier-1.0.2-Reviewer-Preview.html').write_text(content)
   p=b.new_page(viewport={'width':1280,'height':760});p.set_content(content);p.wait_for_timeout(300);p.screenshot(path=str(D/'Atelier-1.0.2-Ember-Reviewer.png'),animations='disabled');p.close();b.close()

if __name__=='__main__':
 if len(sys.argv)>1:asset(sys.argv[1])
 else:
  for mode in ['home','card','practice']:subprocess.run([sys.executable,__file__,mode],check=True)

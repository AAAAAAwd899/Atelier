from pathlib import Path
import sys,os,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from suite_fixtures import home_suite,core
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
    for theme in core.THEMES:
        p=b.new_page(viewport={'width':1440,'height':900});p.set_content(home_suite(theme));p.locator('.quiet-focus h1').wait_for()
        print(theme,p.locator('.quiet-focus').evaluate('e=>({font:getComputedStyle(e.querySelector("h1")).fontFamily,radius:getComputedStyle(e).borderRadius,worldRadius:getComputedStyle(e).getPropertyValue("--world-radius"),art:getComputedStyle(e.querySelector(".world-window")).backgroundImage.slice(0,110)})'),flush=True);p.close()
    b.close()

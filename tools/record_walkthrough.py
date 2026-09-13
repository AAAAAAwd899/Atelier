"""Record actual browser interactions with the shipped frontend and sample data."""
from pathlib import Path
import sys,json,os
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/playwright/final-walkthrough';OUT.mkdir(parents=True,exist_ok=True)
steps=[]
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
    ctx=b.new_context(viewport={'width':1440,'height':900},record_video_dir=str(OUT),record_video_size={'width':1440,'height':900});p=ctx.new_page()
    def pause(label):steps.append(label);p.wait_for_timeout(2000)
    p.set_content(home_suite('midnight'));p.locator('.unified-topbar').wait_for();pause('Midnight Study desk, explicitly labelled sample data')
    p.locator('.nav-group [data-page="library"]').click();pause('Open the Library')
    p.locator('[data-action="view"][data-view="list"]').click();pause('Switch to list view')
    p.locator('.unified-topbar [data-action="appearance"]').click();pause('Open the twelve existing worlds')
    p.locator('[data-theme-choice="forest"]').click();pause('Switch the live interface to Forest')
    p.locator('[data-action="close-dialog"]').first.click();p.locator('.sidebar [data-action="widget-page"]').click();pause('Open built-in Widgets')
    p.locator('[data-action="nw-arrange"]').first.click();pause('Inspect the actual widget arrangement controls')
    p.locator('[data-action="close-dialog"]').first.click();p.locator('.nav-row[data-action="study-progress"]').click();pause('Open scoped study progress')
    p.locator('[data-action="close-dialog"]').first.click();p.locator('.nav-group [data-page="tools"]').click();pause('Native tools remain reachable')
    video=p.video;ctx.close();video.save_as(str(OUT/'Atelier-1.0.3-Walkthrough.webm'));b.close()
(OUT/'recording.json').write_text(json.dumps({'runtime_sha256':runtime_digest(),'category':'actual browser interactions; sample records; native commands are fixture doubles','steps':steps,'audio':False},indent=2)+'\n')

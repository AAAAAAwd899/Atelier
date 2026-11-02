"""Short actual UI interaction recording; synthetic collection, no native-window claim."""
from pathlib import Path
import sys,os,json,hashlib,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tools')]
import render_polish_112 as ui
from verify_release import verification_env
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
os.environ.update(verification_env())
OUT=ROOT/'output/polish-112-walkthrough';OUT.mkdir(parents=True,exist_ok=True)
V=ROOT/'verification';frames=[]
with sync_playwright() as w:
 b=w.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
 c=b.new_context(viewport={'width':1440,'height':900},record_video_dir=str(OUT),record_video_size={'width':1440,'height':900});p=c.new_page();p.route('**/*',ui.assets);p.set_content(ui.doc('forest'));p.locator('.world-window').wait_for();p.wait_for_timeout(350)
 p.locator('.folder-explorer-launch').click();p.wait_for_timeout(250);p.locator('[data-action=expand-folders]').click();p.wait_for_timeout(350)
 p.locator('.outline-row[data-node="22"] [data-action=organize]').click();p.locator('[data-action=folder-icon][data-icon=cat]').scroll_into_view_if_needed()
 tile=p.locator('[data-action=folder-icon][data-icon=cat]');before=tile.bounding_box();tile.hover()
 for delay in [0,60,160]:
  if delay:p.wait_for_timeout(delay)
  frames.append({'stage':'icon-hover','delay_ms':delay,'box':tile.bounding_box(),'filter':tile.locator('.folder-symbol').evaluate('e=>getComputedStyle(e).filter')})
 tile.click();p.locator('[data-action=color][data-color=green]').click();p.locator('.folder-personalization').scroll_into_view_if_needed();p.wait_for_timeout(500);p.screenshot(path=str(OUT/'selection-after.png'))
 p.get_by_role('button',name='Close dialog',exact=True).click();p.locator('.unified-topbar [data-action=appearance]').click();p.locator('[data-theme-choice=rose]').scroll_into_view_if_needed();p.screenshot(path=str(OUT/'theme-before.png'));positions=p.locator('.theme-tile').evaluate_all('xs=>xs.map(x=>[x.offsetLeft,x.offsetTop,x.offsetWidth,x.offsetHeight])')
 p.locator('[data-theme-choice=rose]').click();p.wait_for_timeout(180);after=p.locator('.theme-tile').evaluate_all('xs=>xs.map(x=>[x.offsetLeft,x.offsetTop,x.offsetWidth,x.offsetHeight])');assert positions==after;p.screenshot(path=str(OUT/'theme-after.png'));p.wait_for_timeout(350);p.get_by_role('button',name='Close dialog',exact=True).click();p.wait_for_timeout(350)
 video=p.video;path=Path(video.path());p.close();c.close();b.close()
assert all(abs(f['box'][k]-before[k])<0.1 for f in frames for k in ['x','y','width','height'])
assert frames[-1]['filter']=='brightness(1.08)'
report={'runtime_sha256':runtime_digest(),'category':'recorded shipped UI in Chromium with sample data; no native Windows capture','video':str(path.relative_to(ROOT)),'video_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'icon_frames':frames,'theme_tile_geometry_unchanged':positions==after,'checks':2,'errors':[]}
(V/'motion-112.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'video':report['video'],'checks':2,'errors':[]}))

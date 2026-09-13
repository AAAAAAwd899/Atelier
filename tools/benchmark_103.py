"""Same-host source/baseline browser timings, with fictional 5,000-deck input."""
from pathlib import Path
import sys,os,json,time,statistics,inspect
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from fixtures import core,SRC
import atelier_testing.worlds as worlds
if not inspect.signature(worlds.home_css).parameters:
    original=worlds.home_css;worlds.home_css=lambda package=None:original()
from suite_fixtures import home_suite
from bs4 import BeautifulSoup
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/performance';OUT.mkdir(parents=True,exist_ok=True)
def summary(v):return {'n':len(v),'median_ms':statistics.median(v),'p95_ms':sorted(v)[max(0,__import__('math').ceil(len(v)*.95)-1)]}
timings={'open':[],'navigation':[],'search_5000':[]}
doc=home_suite('midnight');large=BeautifulSoup(home_suite('midnight',page='library'),'html.parser');boot=json.loads(large.find(id='atelier-bootstrap').string)
nodes=[{'id':str(900000+i),'parent':'0','name':f'Lecture {i:05d}','path':f'Lecture {i:05d}','new':3,'learn':1,'review':4,'filtered':False} for i in range(5000)]
boot['demo']['nodes']=nodes;large.find(id='atelier-bootstrap').string=core.json_for_html(boot)
settle='''async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}'''
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
    for i in range(5):
        p=b.new_page(viewport={'width':1440,'height':900});start=time.perf_counter();p.set_content(doc);p.locator('.unified-topbar').wait_for();p.evaluate(settle);timings['open'].append((time.perf_counter()-start)*1000);p.close()
    p=b.new_page(viewport={'width':1440,'height':900});p.set_content(doc);p.locator('.unified-topbar').wait_for()
    for i in range(34):
        start=time.perf_counter();p.locator('.nav-group [data-action="home"]' if i%2 else '.nav-group [data-page="library"]').click();p.evaluate(settle)
        if i>=4:timings['navigation'].append((time.perf_counter()-start)*1000)
    p.close();p=b.new_page(viewport={'width':1440,'height':900});p.set_content(str(large));p.locator('.unified-topbar').wait_for()
    for i in range(10):
        target=4999-i;start=time.perf_counter();p.locator('#atelier-search').fill(f'Lecture {target:05d}');p.locator(f'.deck-card[data-node="{900000+target}"]').wait_for();p.evaluate(settle);timings['search_5000'].append((time.perf_counter()-start)*1000)
    p.close();b.close()
record={'category':'browser fixture timings; same local Windows host','version':core.VERSION,'runtime_sha256':runtime_digest(SRC),'raw_ms':timings,'summary':{k:summary(v) for k,v in timings.items()},'limitations':'Cold document open means HTML through controls/fonts/two frames, not native Anki startup or disk-cold scenic decoding. Navigation includes automation click and two frames. Search includes the production debounce and paint. Other task processes may be active; these are not isolated-host acceptance thresholds.'}
(OUT/(sys.argv[1]+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record['summary'],indent=2))

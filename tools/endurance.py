"""Thirty-minute retained-DOM/listener probe of the shipped home browser fixture."""
from pathlib import Path
import os,sys,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite,core
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/endurance';OUT.mkdir(parents=True,exist_ok=True)
report={'category':'browser fixture endurance; synthetic data; no native/hardware claim','runtime_sha256':runtime_digest(),'duration_target_seconds':1800,'samples':[],'errors':[],'forced_gc_before_samples':True}
start=time.monotonic()
def save():
    report['elapsed_seconds']=time.monotonic()-start;(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
    p=b.new_page(viewport={'width':1280,'height':720});p.on('pageerror',lambda e:report['errors'].append(str(e)));p.set_content(home_suite('midnight'));p.locator('.unified-topbar').wait_for();cdp=p.context.new_cdp_session(p);cdp.send('Performance.enable')
    cycle=0
    try:
        while time.monotonic()-start<1800:
            began=time.monotonic()
            p.locator('.nav-group [data-action="home"]').click();p.locator('.nav-group [data-page="library"]').click();p.locator('.unified-topbar [data-action="appearance"]').click();p.locator(f'[data-theme-choice="{list(core.THEMES)[cycle%len(core.THEMES)]}"]').click();p.locator('[data-action="close-dialog"]').first.click();p.locator('.sidebar [data-action="widget-page"]').click()
            if cycle%6==0:
                cdp.send('HeapProfiler.collectGarbage');metrics={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
                report['samples'].append({'elapsed':time.monotonic()-start,'cycle':cycle,'heap_bytes':metrics.get('JSHeapUsedSize'),**cdp.send('Memory.getDOMCounters')});save();print('Sample',cycle,flush=True)
            cycle+=1;p.wait_for_timeout(max(0,10000-(time.monotonic()-began)*1000))
        report['completed']=True;report['cycles']=cycle
        assert runtime_digest()==report['runtime_sha256'],'Runtime changed during endurance'
    except Exception:
        import traceback;report['errors'].append(traceback.format_exc());report['completed']=False
    finally:save();b.close()

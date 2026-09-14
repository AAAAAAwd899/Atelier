"""Investigate observed browser heap growth after warmup; no native RAM claim."""
from pathlib import Path
import collections,json,os,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite,core
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/memory-followup';OUT.mkdir(parents=True,exist_ok=True)
report={'runtime_sha256':runtime_digest(),'category':'accelerated synthetic browser route/theme probe; heap snapshots after forced GC','samples':[],'errors':[]}
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'));p=b.new_page(viewport={'width':1280,'height':720});p.on('pageerror',lambda e:report['errors'].append(str(e)))
    p.set_content(home_suite('midnight'));p.locator('.unified-topbar').wait_for();cdp=p.context.new_cdp_session(p)
    chunks=[];cdp.on('HeapProfiler.addHeapSnapshotChunk',lambda x:chunks.append(x['chunk']))
    def snapshot(label):
        chunks.clear();cdp.send('HeapProfiler.collectGarbage');cdp.send('HeapProfiler.takeHeapSnapshot',{'reportProgress':False})
        data=json.loads(''.join(chunks));chunks.clear();meta=data['snapshot']['meta'];fields=meta['node_fields'];stride=len(fields);nodes=data['nodes'];types=meta['node_types'][0];totals=collections.Counter();counts=collections.Counter()
        for at in range(0,len(nodes),stride):
            kind=types[nodes[at+fields.index('type')]];totals[kind]+=nodes[at+fields.index('self_size')];counts[kind]+=1
        row={'label':label,'bytes_by_node_type':dict(totals),'counts_by_node_type':dict(counts),'runtime_heap':cdp.send('Runtime.getHeapUsage'),'dom':cdp.send('Memory.getDOMCounters')};report['samples'].append(row)
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(label,row['runtime_heap'],flush=True)
    for cycle in range(288):
        p.locator('.nav-group [data-action="home"]').click();p.locator('.nav-group [data-page="library"]').click();p.locator('.unified-topbar [data-action="appearance"]').click();p.locator(f'[data-theme-choice="{list(core.THEMES)[cycle%len(core.THEMES)]}"]').click();p.locator('[data-action="close-dialog"]').first.click();p.locator('.sidebar [data-action="widget-page"]').click()
        if cycle in (47,143,287):snapshot('cycle-'+str(cycle+1))
    report['completed']=True;report['cycles']=288;assert runtime_digest()==report['runtime_sha256'];(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');b.close()

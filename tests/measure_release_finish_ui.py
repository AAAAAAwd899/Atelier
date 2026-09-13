"""Targeted synthetic frontend timing/readability probe; not native Anki performance."""
import sys,time,json,statistics
from test_ui_audit_browser import large_doc,BeautifulSoup,core,ROOT
from suite_fixtures import home_suite
from playwright.sync_api import sync_playwright

def run():
 s=BeautifulSoup(large_doc(),'html.parser');tag=s.find(id='atelier-bootstrap');boot=json.loads(tag.string)
 boot['profile']['studies']=[{'id':'course35','name':'Active course','active':True,'deck_ids':['10034'],'date':''}];boot['demo']['profile']=boot['profile'];tag.string=core.json_for_html(boot)
 values=[];errors=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)))
  p.set_content(str(s));p.locator('.nav-row').first.wait_for();p.locator('.nav-row[data-page=tools]').click()
  for i in range(5):
   t=time.perf_counter();p.locator('[data-action=native-tool][data-command=export]').click();p.locator('.export-row').first.wait_for();elapsed=(time.perf_counter()-t)*1000
   assert 'Active class' in p.locator('.export-row').first.inner_text();assert p.locator('.export-row').count()==50
   values.append(elapsed);p.keyboard.press('Escape')
  p.set_content(home_suite('forest'));p.locator('.nav-row').first.wait_for()
  sizes=p.evaluate("""()=>[...document.getElementById('atelier-root').shadowRoot.querySelectorAll('button')].map(e=>({text:e.textContent.trim(),size:parseFloat(getComputedStyle(e).fontSize)})).filter(x=>/^(Due|Recent|Saved|Add study|See all folders|Widgets|New deck|New folder|Browse folder)/.test(x.text))""")
  assert all(x['size']>=13 for x in sizes),sizes
  assert not errors;browser=b.version;b.close()
 out={'version':core.VERSION,'browser':browser,'platform':'Linux headless Chromium, synthetic 5000-deck collection; driver/paint waiting included',
 'export_open_ms':values,'median_export_open_ms':statistics.median(values),'visible_export_rows':50,'active_class_ranked_first':True,
 'functional_label_sizes':sizes,'errors':errors,'limits':'Not Windows startup/DPI, native collection retrieval/export time, PDF render time, GPU or long-duration memory evidence.'}
 (ROOT/'verification/release-finish/ui-probe.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':run()

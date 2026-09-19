"""The existing exam form receives exact source scopes without auto-saving or widening."""
from planner_suite_fixture import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification/plan-handoff';OUT.mkdir(parents=True,exist_ok=True)
def main():
 checks=[];errors=[]
 def check(n,v):assert v,n;checks.append(n)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':960});expose(p);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html('forest'));p.locator('[data-action="new"]').first.wait_for()
  # deck ID from the original fixture is used rather than a made-up target.
  data=command('load',{});did=data['decks'][0]['id'];query='nid:1700000000001,1700000000002'
  p.evaluate('(v)=>ExamSprout.event("suite-navigate",v)',{'view':'new','setup':{'name':'Source-linked preparation','deck_ids':[str(did)],'query':query}})
  p.locator('[data-field="name"]').wait_for();check('Direct handoff fills the canonical new exam draft',p.locator('[data-field="name"]').input_value()=='Source-linked preparation')
  check('No automatic save during handoff',not any(a=='save_exam' for a,_ in CALLS))
  p.locator('[data-action="next-step"]').click();check('Exact source covering deck is selected',p.locator('[data-special="choose-deck"]:checked').count()==1)
  p.locator('[data-action="next-step"]').click();q=p.locator('[data-field="query"]')
  check('Exact note filter survives all original setup steps',q.input_value()==query)
  p.locator('[data-action="save"]').click();p.locator('.es-form').wait_for(state='detached')
  saved=next(v for a,v in reversed(CALLS) if a=='save_exam')
  check('Original final save retains exact note filter',saved['query']==query and len(saved['scopes'])==1 and str(saved['scopes'][0]['deck_id'])==str(did))
  check('No browser errors',not errors);b.close()
 (OUT/'results.json').write_text(json.dumps({'count':len(checks),'cases':checks,'errors':errors},indent=2));print(checks)
if __name__=='__main__':main()

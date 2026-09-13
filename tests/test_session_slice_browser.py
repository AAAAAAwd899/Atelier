"""Current packaged result/Pip frontend + actual stored-session engine.
Native Qt runner geometry is NOT emulated by these Chromium tests.
"""
from planner_suite_fixture import *
from playwright.sync_api import sync_playwright
from addon.core import CardInfo
from addon.exam_session import ExamSession
from addon.drafts import save_draft,draft_summary,discard_draft
import copy
OUT=ROOT/'verification/session-polish';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/session-polish';SH.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[];FAILURES={};EMPTY=False
BASE=original.command

def dispatched(a,p):
 if a in FAILURES:raise ValueError(FAILURES[a])
 if a=='review_misses':
  CALLS.append((a,p))
  return {'empty':True,'message':'No misses in this session.'} if EMPTY else {'started':True,'native_mock':True}
 return BASE(a,p)
original.command=dispatched

def check(n,v=True):
 assert v,n
 CHECKS.append(n);print('PASS',n,flush=True)

def hit(p,sel):
 return p.locator(sel).first.evaluate('''e=>{let r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,t=document.elementFromPoint(x,y);return r.width>0&&r.height>0&&x>=0&&y>=0&&x<innerWidth&&y<innerHeight&&!!t&&(e===t||e.contains(t))}''')

def result(n=60,partial=False):
 s=ExamSession('pharm3',[CardInfo(i+1,i+1,[11,12,13][i%3]) for i in range(n)],'exam',0)
 for i in range(n):
  s.enter()
  if i%7:
   s.save_response('Example written reasoning '+str(i));s.set_confidence(3 if i%3 else 2)
  if i%5==0:s.flags.add(s.current.id)
  if i+1<n:s.go(1)
 s.submit()
 for i in range(n if not partial else n//2):
  s.set_error('concept' if i%4==0 else 'none')
  s.grade(0 if i%7==0 or i%4==0 else .5 if i%3==0 else 1)
 return s.result(interrupted=partial)

def show(p,r):
 state=copy.deepcopy(original.STORE.state)
 state['history']=[*state.get('history',[]),r]
 p.evaluate('(payload)=>ExamSprout.event("result",payload)',{'state':state,'result':r})
 p.locator('#es-modal[open][data-view="results"]').wait_for();p.wait_for_timeout(80)


def layout(p):
 return p.evaluate('''()=>{let d=document.querySelector('#es-modal'),h=d.querySelector('.suite-modal-heading'),f=d.querySelector('.es-modal-actions'),s=d.querySelector('.suite-modal-scroll');let r=e=>e.getBoundingClientRect();return {fits:r(d).top>=-1&&r(d).bottom<=innerHeight+1&&r(d).left>=-1&&r(d).right<=innerWidth+1,scroll:s.scrollWidth<=s.clientWidth+1,separated:r(h).bottom<=r(s).top+1&&r(s).bottom<=r(f).top+1,actions:[...f.querySelectorAll('button')].every(e=>r(e).top>=r(f).top&&r(e).bottom<=r(f).bottom+1)}}''')

def run():
 global EMPTY
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  def page(th='forest',w=1440,h=1000,enabled=True):
   p=b.new_page(viewport={'width':w,'height':h});p.set_default_timeout(30000);p.on('pageerror',lambda e:ERRORS.append(str(e)))
   expose(p);p.set_content(html(th,enabled));p.locator('.es-hero').wait_for();p.wait_for_timeout(100);return p
  r=result();before=copy.deepcopy(r)
  for th in core.THEMES:
   p=page(th);show(p,r)
   g=layout(p);check(th+' result header, body and footer reserve separate space',all(g.values()))
   check(th+' stored score and denominator shown without new grading',p.locator('.es-big-score').inner_text()==str(r['percent'])+'%' and str(r['total'])+' selected cards' in p.locator('.suite-result-hero').inner_text())
   check(th+' result never implies an exam-grade guarantee','not a predicted exam score' in p.locator('#es-modal').inner_text())
   check(th+' result actions are visible before scrolling',all(hit(p,f'[data-action="{a}"]') for a in ['review-all','review-misses','export-result','close-modal']))
   p.screenshot(path=str(SH/f'{th}-results.png'),animations='disabled')
   p.locator('#suite-result-filter').select_option('confident')
   check(th+' question filter keeps confident misses only',p.locator('[data-result-question]').count()>0 and all('Confident miss' in x for x in p.locator('[data-result-question]').all_inner_texts()))
   check(th+' original result was not mutated',r==before)
   p.locator('.suite-modal-scroll').evaluate('e=>e.scrollTop=e.scrollHeight');p.wait_for_timeout(30)
   check(th+' footer stays hit-testable after scrolling',hit(p,'[data-action="review-misses"]'))
   p.screenshot(path=str(SH/f'{th}-question-detail.png'),animations='disabled')
   p.keyboard.press('Escape');p.locator('[data-action="pip-study"]').first.click()
   p.locator('#es-pip-count').fill('45')
   check(th+' original Pip default and bound retained',p.locator('#es-teach-new').is_checked() and p.locator('#es-pip-count').get_attribute('max')=='500')
   p.evaluate('window.pipInput=document.getElementById("es-pip-count")')
   p.locator('#es-teach-new').uncheck()
   check(th+' rehearsal mode changes only presentation and checkbox',p.locator('#suite-pip-mode strong').inner_text()=='Rehearsal only' and p.evaluate('window.pipInput===document.getElementById("es-pip-count")') and p.locator('#es-pip-count').input_value()=='45')
   check(th+' Pip start and cancel stay reachable',hit(p,'[data-action="begin-pip-study"]') and hit(p,'[data-action="close-modal"]'))
   p.screenshot(path=str(SH/f'{th}-pip.png'),animations='disabled');p.close()
  # Huge result history with original question numbers; bounded table even at 500.
  p=page();large=result(500);show(p,large)
  check('500-question result initially renders only 25 rows',p.locator('[data-result-question]').count()==25)
  p.locator('[data-action="result-page"][data-delta="1"]').click()
  check('Next page retains original question numbers',p.locator('[data-result-question]').first.get_attribute('data-result-question')=='26')
  check('Native button focus remains on paging action',p.evaluate('document.activeElement?.dataset.action')=='result-page')
  p.locator('#suite-result-filter').select_option('flagged')
  check('Filter resets pagination and preserves original question IDs',p.locator('[data-result-question]').first.get_attribute('data-result-question')=='1' and 'Page 1' in p.locator('#suite-result-range').inner_text())
  p.locator('#suite-result-filter').select_option('all')
  # Theme change while results open preserves the modal, score, and current filter.
  p.evaluate('window.modalBefore=document.getElementById("es-modal");window.AtelierWorlds.configure({theme:"rose"})')
  check('World change does not remount result dialog',p.evaluate('window.modalBefore===document.getElementById("es-modal")') and p.locator('#suite-result-filter').input_value()=='all')
  FAILURES['review_misses']='Could not open original cards. Result is preserved.'
  p.locator('[data-action="review-all"]').click();p.locator('.es-toast').wait_for()
  check('Native review failure keeps result open and error visible',p.locator('#es-modal').get_attribute('open') is not None and hit(p,'.es-toast'))
  FAILURES.clear();EMPTY=True
  p.locator('[data-action="review-misses"]').click();p.wait_for_timeout(80)
  check('Empty review selection preserves the result',p.locator('#es-modal').get_attribute('open') is not None and 'No misses' in p.locator('.es-toast').inner_text())
  EMPTY=False;before_calls=len(CALLS);p.locator('[data-action="review-all"]').click();p.wait_for_timeout(60)
  check('Original-card review uses displayed result identity',CALLS[-1]==('review_misses',{'id':'pharm3','result_id':large['id'],'filter':'all'}))
  check('Successful original-card launch closes only the dialog',not p.locator('#es-modal').is_visible());p.close()
  # Narrow, short, and scaled CSS viewports. These are not native Windows DPI tests.
  for w,h in [(320,540),(390,650),(620,500),(900,650),(1320,720),(1725,900)]:
   p=page(w=w,h=h);show(p,r);g=layout(p)
   check(f'{w}x{h} results fit and do not overlap',all(g.values()))
   check(f'{w}x{h} results primary actions remain hittable',hit(p,'[data-action="review-misses"]') and hit(p,'[data-action="dismiss-dialog"]'))
   p.locator('.suite-modal-scroll').hover();p.mouse.wheel(0,1500);p.wait_for_function('document.querySelector(".suite-modal-scroll").scrollTop>0',timeout=4000)
   check(f'{w}x{h} content scrolls without burying footer',p.locator('.suite-modal-scroll').evaluate('e=>e.scrollTop')>0 and hit(p,'[data-action="export-result"]'))
   p.screenshot(path=str(SH/f'results-{w}.png'),animations='disabled')
   p.locator('[data-action="close-modal"]').click();p.locator('[data-action="pip-study"]').first.click()
   check(f'{w}x{h} Pip footer and heading fit',all(layout(p).values()) and hit(p,'[data-action="begin-pip-study"]'))
   p.locator('#es-pip-count').fill('501');p.locator('[data-action="begin-pip-study"]').click()
   check(f'{w}x{h} invalid Pip size error appears in modal top layer',p.locator('.suite-modal-alerts .es-toast').count()==1 and hit(p,'.es-toast'))
   p.locator('#es-pip-count').fill('30');p.locator('#es-teach-new').uncheck()
   check(f'{w}x{h} valid choice recovers without losing input',p.locator('#suite-pip-mode strong').inner_text()=='Rehearsal only' and hit(p,'[data-action="begin-pip-study"]'))
   p.screenshot(path=str(SH/f'pip-{w}.png'),animations='disabled');p.close()
  # Resume is actual saved-session summary; no synthetic autosave.
  saved=ExamSession('pharm3',[CardInfo(i+1,i+1,11) for i in range(40)],'exam',90);saved.go(7);saved.save_response('Saved reasoning')
  save_draft(original.STORE,saved);p=page();p.locator('.es-top-nav [data-view="practice"]').click()
  check('Resume displays real saved question position','Question 8 of 40' in p.locator('.es-draft-banner').inner_text())
  check('Saved session names its real exam','Renal' not in p.locator('.es-draft-banner h3').inner_text() and p.locator('.es-draft-banner h3').inner_text()==original.STORE.get_exam('pharm3').name)
  p.screenshot(path=str(SH/'saved-session.png'),animations='disabled')
  FAILURES['resume_exam']='Saved session could not be opened; it was not removed.'
  p.locator('[data-action="resume-exam"]').click();p.locator('.es-toast').wait_for()
  check('Resume failure leaves saved copy intact',draft_summary(original.STORE)['at']==8 and p.locator('[data-action="resume-exam"]').is_enabled())
  FAILURES.clear();p.locator('[data-action="discard-draft"]').click();p.locator('[data-action="close-modal"]').click()
  check('Cancel discard retains the saved exam',draft_summary(original.STORE) is not None)
  p.close();discard_draft(original.STORE)
  # Legacy, partial, all-correct, explicit scheduled/Pip outcomes and escaped labels.
  variants=[{**result(4,True)}, {**r,'items':[]}, {k:v for k,v in r.items() if k!='items'}, {**r,'pip_study':True,'items':[{**x,'scheduled':i==0} for i,x in enumerate(r['items'])]}]
  for i,x in enumerate(variants):
   p=page();show(p,x)
   check(f'Outcome variant {i} remains explicit and functional',p.locator('#suite-modal-title').inner_text()!='' and hit(p,'[data-action="close-modal"]'))
   if i==0:check('Partial result never reads as a complete mock','unfinished session' in p.locator('.es-result-diagnostics').inner_text())
   if i==2:check('Legacy item absence is not a fake success','older result' in p.locator('#suite-result-rows').inner_text())
   if i==3:check('Explicit native learning is disclosed in result','1 new card received' in p.locator('.suite-session-safety').inner_text())
   p.close()
  p=page(enabled=False);show(p,r);check('Passive-owner planner gets native-safe modal layout',all(layout(p).values()))
  check('No world background forced in original-owner mode',p.locator('html').get_attribute('data-atelier-world-enabled')=='false');p.close()
  b.close()
 check('No uncaught frontend exceptions',not ERRORS)
 (OUT/'results.json').write_text(json.dumps({'count':len(CHECKS),'passed':CHECKS,'errors':ERRORS,'native_qt_verified':False,'notes':'Real packaged web UI and original engine; original-card launches are bridge doubles. No native session geometry claims.'},indent=2))

if __name__=='__main__':run()

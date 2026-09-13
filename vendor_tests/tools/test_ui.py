"""Run production web UI against synthetic data; NOT a live Anki/Qt test.

Requires developer-only Playwright + Chromium. Nothing here ships in the add-on.
Run: python tools/test_ui.py
"""
from __future__ import annotations
from datetime import datetime, timedelta
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile
from uuid import uuid4
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from addon.core import CardInfo, DeckStats, PracticeSession, VERSION, plan_exam, sample_cards, suggest_decks, bounded_int, finite_weight
from addon.storage import Store
from addon.widget import countdown_html

OUT=ROOT/'docs'/'screenshots';OUT.mkdir(parents=True,exist_ok=True)
TMP=tempfile.TemporaryDirectory(prefix='exam-sprout-ui-')
STORE=Store(TMP.name)
DECKS=[{'id':11,'name':'Pharmacotherapy::Cardiology'},{'id':12,'name':'Pharmacotherapy::Renal & electrolytes'},{'id':13,'name':'Pharmacotherapy::Endocrinology'},{'id':14,'name':'Microbiology::Antimicrobials'},{'id':15,'name':'Microbiology::Organisms'},{'id':16,'name':'Clinical skills::Counseling'}]
COUNTS={11:280,12:190,13:160,14:210,15:160,16:50}
CARDS=[CardInfo(d['id']*100000+i,d['id']*100000+i,d['id'],i<COUNTS[d['id']]//6,i%7==0) for d in DECKS for i in range(COUNTS[d['id']])]
for eid,name,days,topics,scopes in [('pharm3','Pharmacotherapy · Exam 3',12,'Heart failure, arrhythmias, renal dosing, electrolytes, and diabetes.',[(11,2,45),(12,3,35),(13,4,20)]),('micro','Microbiology quiz',18,'Antimicrobials and organism identification.',[(14,3,1),(15,2,1)])]:
    due=(datetime.now()+timedelta(days=days)).replace(hour=9,minute=0,second=0,microsecond=0)
    STORE.save_exam({'id':eid,'name':name,'due':due.isoformat(timespec='minutes'),'topics':topics,'daily_minutes':90,'weekdays':[0,1,2,3,4,5],'scopes':[{'deck_id':did,'name':next(d['name'] for d in DECKS if d['id']==did),'confidence':confidence,'weight':weight} for did,confidence,weight in scopes]})
NIGHT=False
PENDING={}

def make_plan(e):
    stats={s.deck_id:DeckStats(s.deck_id,s.name,total=COUNTS.get(s.deck_id,0),new=COUNTS.get(s.deck_id,0)//6,due=COUNTS.get(s.deck_id,0)//7,attempts=90,again={11:27,12:12,13:4}.get(s.deck_id,12),seconds=2700) for s in e.scopes}
    return {'plan':plan_exam(e,stats),'warnings':[]}

def command(action,p):
    if action=='load':return {'state':STORE.state,'decks':DECKS,'version':VERSION,'night':NIGHT,'initial_exam':'pharm3','warning':'','read_only':False,'countdown_html':countdown_html(STORE,preview=True)}
    if action=='plan':return make_plan(STORE.get_exam(p['id']))
    if action=='dirty':return {}
    if action=='suggest':return {'ids':suggest_decks(p.get('topics',''),DECKS)}
    if action=='settings':STORE.save_settings(p);return {'state':STORE.state,'countdown_html':countdown_html(STORE,preview=True)}
    if action=='save_exam':
        if p.get('query')=='invalid:(':raise ValueError('Invalid Anki search filter (synthetic fixture).')
        e=STORE.save_exam(p);return {'state':STORE.state,'countdown_html':countdown_html(STORE,preview=True),'exam_id':e.id,**make_plan(e)}
    if action=='archive_exam':
        e=STORE.get_exam(p['id']);STORE.save_exam({**e.to_dict(),'archived':p['archived']});return {'state':STORE.state,'countdown_html':countdown_html(STORE,preview=True)}
    if action=='delete_exam':STORE.delete_exam(p['id']);return {'state':STORE.state,'countdown_html':countdown_html(STORE,preview=True)}
    if action=='prepare':
        e=STORE.get_exam(p['id']);size=bounded_int(p['size'],1,500,'Practice cards');minutes=bounded_int(p['minutes'],0,720,'Time limit')
        pool=[c for c in CARDS if c.owner in {s.deck_id for s in e.scopes} and (p.get('include_new',True) or not c.is_new)]
        weights={s.deck_id:(finite_weight(p.get('weights',{}).get(str(s.deck_id),s.weight)) if p['weighting']=='custom' else 1 if p['weighting']=='equal' else COUNTS[s.deck_id] if p['weighting']=='size' else s.weight) for s in e.scopes}
        result=sample_cards(pool,size,weights,p.get('one_per_note',True),p.get('ensure_coverage',True),random.Random(123))
        if not result.cards:raise ValueError('No eligible cards match these settings.')
        token=uuid4().hex;PENDING[token]=(e,result,p['kind'],minutes)
        return {'token':token,'requested':size,'actual':len(result.cards),'available':result.available,'kind':p['kind'],'minutes':minutes,'warnings':result.warnings,'counts':[{'name':next(s.name for s in e.scopes if s.deck_id==did),'count':count} for did,count in result.counts.items()]}
    if action=='start':raise ValueError('UI test host only: native card practice opens inside the installed Anki add-on.')
    if action=='browse':return {'preview_only':True}
    if action=='export':return {'saved':False}
    raise ValueError('Unknown preview action.')

def bridge(req):
    try:return {'id':str(req['id']),'data':command(req['action'],req.get('payload',{})),'error':None}
    except Exception as exc:return {'id':str(req['id']),'data':None,'error':str(exc)}

def page_html():
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exam Sprout — production UI / synthetic data</title><style>'+(ROOT/'addon/web/app.css').read_text()+(ROOT/'addon/web/countdown.css').read_text()+'</style></head><body><main id="es-app"></main><script>window.pycmd=function(message){window.fixtureCommand(JSON.parse(message.slice("exam-sprout:".length))).then(window.ExamSprout.receive);};</script><script>'+(ROOT/'addon/web/countdown.js').read_text()+';'+(ROOT/'addon/web/app.js').read_text()+'</script></body></html>'

CHECKS=[]
def check(name,condition=True):
    assert condition,name
    CHECKS.append(name)
    print('PASS',name,flush=True)

def overflow(page):return page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')

def run():
    global NIGHT
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=shutil.which("chromium") or pw.chromium.executable_path,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1100,'height':980},device_scale_factor=1)
        page.set_default_timeout(5000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.expose_function('fixtureCommand',bridge)
        page.set_content(page_html());page.locator('.es-focus-row').first.wait_for()
        check('Overview renders three priority decks',page.locator('.es-focus-row').count()==3)
        check('Desktop overview fits window',overflow(page))
        page.screenshot(path=str(OUT/'Exam Sprout - Planner.png'))
        page.locator('nav [data-action="nav"][data-view="practice"]').click()
        page.locator('[data-practice="size"]').fill('501');page.locator('[data-action="prepare"]').click()
        page.get_by_role('alert').wait_for();check('501-card session rejected',not page.locator('#es-modal').is_visible())
        page.locator('[data-practice="size"]').fill('100')
        page.locator('[data-practice="weighting"]').select_option('custom')
        for did,w in [(11,50),(12,30),(13,20)]:page.locator(f'[data-weight="{did}"]').fill(str(w))
        page.screenshot(path=str(OUT/'Exam Sprout - Practice settings.png'))
        page.locator('[data-action="prepare"]').click();page.locator('#es-modal[open]').wait_for()
        check('100-card allocation preview',page.locator('#es-modal h2').inner_text().startswith('100 cards'))
        check('Weighted allocation totals 100',sum(int(x) for x in page.locator('.es-allocation-row strong').all_inner_texts())==100)
        page.screenshot(path=str(OUT/'Exam Sprout - Exam allocation.png'))
        page.locator('[data-action="close-modal"]').click()
        for did in [11,12,13]:page.locator(f'[data-weight="{did}"]').fill('0')
        page.locator('[data-action="prepare"]').click();page.wait_for_timeout(150)
        check('All-zero weights do not create a session',not page.locator('#es-modal').is_visible())
        page.locator('[data-action="practice-kind"][data-value="practice"]').click()
        check('Practice mode selected','selected' in page.locator('[data-action="practice-kind"][data-value="practice"]').get_attribute('class'))
        page.locator('[data-action="nav"][data-view="settings"]').click()
        for theme in ['sage','lavender','peach','rose','sky','midnight','inherit']:
            page.locator(f'[data-action="theme"][data-value="{theme}"]').click()
            page.wait_for_function(f'document.querySelector("#es-app").dataset.theme === "{theme}"')
            check(f'{theme} theme applied',STORE.state['settings']['theme']==theme)
        page.screenshot(path=str(OUT/'Exam Sprout - Settings.png'))
        page.locator('[data-setting="show_countdown"]').uncheck();page.wait_for_timeout(150)
        check('Countdown can be hidden',STORE.state['settings']['show_countdown'] is False)
        page.locator('[data-setting="show_countdown"]').check();page.wait_for_timeout(100)
        page.locator('[data-action="new"]').click()
        page.locator('[data-action="next-step"]').click()
        page.get_by_role('alert').wait_for();check('Required exam title validation',page.locator('[data-field="name"]').is_visible())
        page.locator('[data-field="name"]').fill('Cardiology & renal quiz')
        page.locator('[data-field="topics"]').fill('Cardiology renal')
        page.locator('[data-action="next-step"]').click()
        page.locator('[data-action="suggest"]').click();page.wait_for_timeout(100)
        check('Deck name suggestions marked',page.locator('.es-hint').count()>=2)
        for did in [11,12]:page.locator(f'[data-special="choose-deck"][data-id="{did}"]').check()
        page.locator('[data-special="confidence"][data-id="11"]').select_option('1')
        page.locator('[data-special="emphasis"][data-id="11"]').fill('2')
        page.screenshot(path=str(OUT/'Exam Sprout - Deck setup.png'))
        page.locator('[data-action="next-step"]').click()
        page.locator('[data-action="study-mode"][data-value="cram"]').click()
        page.locator('[data-field="daily_minutes"]').fill('120')
        page.locator('[data-action="save"]').click();page.get_by_role('heading',name='Cardiology & renal quiz',exact=True).wait_for()
        created=next(e for e in STORE.exams() if e.name=='Cardiology & renal quiz')
        check('Three-step wizard saves exam',created.mode=='cram' and created.daily_minutes==120 and len(created.scopes)==2)
        check('Confidence and emphasis persisted',created.scopes[0].confidence==1 and created.scopes[0].weight==2)
        page.locator('[data-action="edit"]').click();page.locator('[data-field="name"]').fill('Do not save')
        page.locator('[data-action="cancel-form"]').click();page.locator('#es-modal[open]').wait_for();page.locator('[data-action="confirm-modal"]').click()
        page.get_by_role('heading',name='Cardiology & renal quiz',exact=True).wait_for();check('Discard edits preserves saved exam',STORE.get_exam(created.id).name=='Cardiology & renal quiz')
        page.locator('[data-action="archive"]').click();page.wait_for_timeout(150);check('Archive persisted',STORE.get_exam(created.id).archived)
        page.locator('[data-action="archive"]').click();page.wait_for_timeout(150);check('Unarchive persisted',not STORE.get_exam(created.id).archived)
        page.locator('[data-action="delete"]').click();page.locator('[data-action="confirm-modal"]').click();page.wait_for_timeout(200)
        check('Delete leaves other exams intact',len(STORE.exams())==2)
        page.locator('[data-action="select-exam"][data-id="pharm3"]').click();page.locator('.es-focus-row').first.wait_for()
        session=PracticeSession('pharm3',CARDS[:10]);session.submit()
        while session.phase!='finished':session.grade(1 if session.index%3 else .5)
        result=session.result();STORE.add_result(result)
        page.evaluate('(p)=>window.ExamSprout.event("result",p)',{'result':result,'state':STORE.state})
        page.locator('#es-modal[open]').wait_for();page.wait_for_timeout(350)
        check('Result remains open after asynchronous plan refresh',page.locator('#es-modal[open]').count()==1)
        page.screenshot(path=str(OUT/'Exam Sprout - Result.png'))
        page.locator('[data-action="close-modal"]').click();page.locator('.es-focus-row').first.wait_for()
        check('Refreshed plan appears after result is closed',page.locator('.es-focus-row').count()==3)
        # Reload the exact production UI in inherited dark mode.
        NIGHT=True;page.set_content(page_html());page.locator('.es-focus-row').first.wait_for()
        check('Dark mode activated',page.locator('#es-app').get_attribute('data-dark')=='true')
        page.screenshot(path=str(OUT/'Exam Sprout - Dark planner.png'))
        page.set_viewport_size({'width':600,'height':900})
        check('Narrow overview has no horizontal overflow',overflow(page))
        page.screenshot(path=str(OUT/'Exam Sprout - Narrow planner.png'))
        page.locator('[data-action="nav"][data-view="settings"]').click();check('Narrow settings fit',overflow(page))
        page.locator('[data-action="new"]').click();check('Narrow wizard fits',overflow(page))
        check('No uncaught JavaScript errors',not errors)
        # Countdown component uses the real component code in a labeled sample host.
        page.set_viewport_size({'width':850,'height':510})
        css=(ROOT/'addon/web/countdown.css').read_text();js=(ROOT/'addon/web/countdown.js').read_text()
        for night in [False,True]:
            bg,fg,link=('#20212b','#e8e9f2','#b7acdf') if night else ('#fcfcfd','#313341','#706285')
            html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><style>body{{margin:0;background:{bg};color:{fg};--link:{link};font:14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.shell{{max-width:700px;margin:0 auto;padding:30px 36px 36px}}.top{{display:flex;justify-content:center;gap:30px;font-size:13px;margin-bottom:54px}}.brand{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;opacity:.5;margin-bottom:25px;text-align:center}}.row{{display:flex;justify-content:space-between;padding:16px 12px;border-bottom:1px solid #8883;font-size:14px}}.row span{{font-size:12px;opacity:.65}}.caption{{text-align:center;font-size:11px;opacity:.55;margin-top:24px}}{css}</style></head><body><div class="shell"><div class="brand">Countdown component · example host</div><div class="top"><span>Decks</span><span>Add</span><span>Browse</span><span>Stats</span><span>Sync</span><span>Exams</span></div><div class="row">Pharmacotherapy<span>45 due</span></div><div class="row">Microbiology<span>22 due</span></div><div class="row" style="margin-bottom:26px">Clinical skills<span>8 due</span></div>{countdown_html(STORE)}<p class="caption">Production countdown code in a sample deck-screen layout · not a screenshot of Anki</p></div><script>window.pycmd=(m)=>window.__lastWidgetCommand=m;</script><script>{js}</script></body></html>'''
            page.set_content(html);page.wait_for_timeout(100)
            page.screenshot(path=str(OUT/('Exam Sprout - Dark countdown.png' if night else 'Exam Sprout - Countdown.png')))
            check(f'Countdown fits {"dark" if night else "light"} host',overflow(page))
            page.locator('#es-countdowns button').first.click()
            check(f'Countdown emits namespaced command ({night})',page.evaluate('window.__lastWidgetCommand').startswith('exam-sprout:open:'))
        browser.close()
    report={'suite':'Production web UI with synthetic fixture bridge','native_anki_tested':False,'checks_passed':len(CHECKS),'checks':CHECKS,'javascript_errors':errors}
    (ROOT/'docs/ui-results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    TMP.cleanup()

if __name__=='__main__':run()

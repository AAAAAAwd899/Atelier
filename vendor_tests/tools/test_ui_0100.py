"""Real packaged UI + live WebGL, synthetic Anki bridge + actual assessment engine."""
from pathlib import Path
import sys,json,random,time,shutil
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import test_ui_096 as u
import test_ui as f
from addon.core import Snapshot,DeckStats,plan_exam
from addon.exam_engine import sample_exam
from addon.exam_session import ExamSession
from addon.readiness import readiness
from addon.progress import PipProgress
from addon.drafts import save_draft,load_draft,discard_draft,draft_summary
from addon.session_tools import sampling_coverage
OUT=ROOT/'docs/readiness-0100';OUT.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[];CALLS=[]
base=u.command
progress=PipProgress(f.STORE);progress.record(list(range(1,246)))
e=f.STORE.get_exam('pharm3');f.STORE.save_exam({**e.to_dict(),'due':(datetime.now()+timedelta(days=3)).isoformat(timespec='minutes')})

def snapshot(e):
    cs=[c for c in f.CARDS if c.owner in {s.deck_id for s in e.scopes}]
    stats={s.deck_id:DeckStats(s.deck_id,s.name,total=sum(c.owner==s.deck_id for c in cs),new=sum(c.owner==s.deck_id and c.is_new for c in cs),due=12,attempts=50,again=5,seconds=1800) for s in e.scopes}
    now=time.time();events=[]
    for day in range(2,7):
        for c in cs:
            if not c.is_new:
                events.append({'card_id':c.id,'note_id':c.note_id,'owner':c.owner,'ts':now-day*86400,
                    'score':0 if (c.id+day)%20==0 else 1,'delayed':True,'source':'exam' if day in (2,4) else 'anki',
                    'confidence':3 if c.id%7==0 else 1,'sampling':'representative','session_id':f'mock{day}'})
    return Snapshot(f.DECKS,stats,cs,evidence={'events':events,'last_seen':{c.note_id:now-2*86400 for c in cs if not c.is_new}})

def command(action,p):
    CALLS.append((action,p))
    if action=='load':
        return {**base(action,p),'draft':draft_summary(f.STORE),'pip_growth':progress.signal()}
    if action=='plan':
        e=f.STORE.get_exam(p['id']);s=snapshot(e)
        return {'plan':{**plan_exam(e,s.stats),'growth':progress.signal(),'readiness':readiness(e,s)},'warnings':[],'draft':draft_summary(f.STORE)}
    if action=='prepare':
        e=f.STORE.get_exam(p['id']);s=snapshot(e)
        custom={t.deck_id:p.get('weights',{}).get(str(t.deck_id),t.weight) for t in e.scopes}
        sample,cards=sample_exam(e,s,p['size'],weighting=p['weighting'],custom=custom,strategy=p.get('strategy','representative'),
            include_new=p.get('include_new',True),one_per_note=p.get('one_per_note',True),ensure_coverage=p.get('ensure_coverage',True),cold_only=p.get('cold_only',False),rng=random.Random(42))
        token=f'test-{len(f.PENDING)}';f.PENDING[token]=(e,sample,p['kind'],p['minutes'])
        return {'token':token,'requested':p['size'],'actual':len(sample.cards),'available':sample.available,'kind':p['kind'],'minutes':p['minutes'],
            'strategy':p.get('strategy','representative'),'warnings':sample.warnings,'counts':[{'name':s.stats[k].name,'count':v} for k,v in sample.counts.items()],
            'coverage':sampling_coverage(e,s,cards,sample.counts)}
    if action in ('pip_study','resume_exam','export_result'):return {'started':True,'saved':True,'native_mock':True}
    if action=='discard_draft':discard_draft(f.STORE);return {}
    return base(action,p)
f.command=command

def check(label,condition=True):
    assert condition,label;CHECKS.append(label);print('PASS',label,flush=True)

def run():
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=b.new_page(viewport={'width':1440,'height':1020},device_scale_factor=1)
        page.set_default_timeout(15000);page.on('pageerror',lambda e:ERRORS.append(str(e)));page.route('**/*',u.route);page.expose_function('fixtureCommand',f.bridge)
        page.set_content(u.html());page.locator('.es-readiness-grade').wait_for();page.locator('.pip-card[data-pip-renderer="webgl2"]').wait_for()
        r=readiness(f.STORE.get_exam('pharm3'),snapshot(f.STORE.get_exam('pharm3')))
        check('Readiness displayed from actual heuristic engine',page.locator('.es-readiness-grade strong').inner_text()==r['grade'])
        check('Prominent no-guarantee warning',all(s in page.locator('.es-readiness-disclaimer').inner_text() for s in ('guarantee','actual exam grade')))
        check('Independent Pip effort meter',page.locator('.es-pip-progress').inner_text().find('245 effort points')>=0)
        check('No outdated mascot growth portraits',page.locator('.es-growth-steps img').count()==0)
        page.screenshot(path=str(OUT/'Exam_Sprout_Readiness.png'),full_page=True)
        grade=page.locator('.es-readiness-grade strong').inner_text();points=page.locator('.es-pip-progress').inner_text()
        page.locator('[data-pip-action="pet"]').click();page.locator('[data-pip-action="water"]').click()
        check('Playing changes neither readiness nor effort',page.locator('.es-readiness-grade strong').inner_text()==grade and page.locator('.es-pip-progress').inner_text()==points)
        page.locator('[data-action="readiness-method"]').click();page.locator('#es-modal[open]').wait_for()
        text=page.locator('#es-modal').inner_text()
        check('Method states not fitted or validated','no fitted or validated' in text)
        check('Grade legend includes F- A+ S',all(x in text for x in ('F-','A+','S')))
        check('Sensitivity not called grade confidence interval','NOT an exam-score confidence interval' in text)
        page.screenshot(path=str(OUT/'Exam_Sprout_Method.png'))
        page.locator('[data-action="close-modal"]').click()
        page.locator('[data-action="pip-study"]').first.click();page.locator('#es-modal[open]').wait_for()
        check('Pip Study explains native learning and learned rehearsal','currently NEW cards only' in page.locator('#es-modal').inner_text())
        page.locator('#es-pip-count').fill('501');page.locator('[data-action="begin-pip-study"]').click()
        check('Pip session bound enforced',not any(a=='pip_study' for a,p in CALLS))
        page.locator('#es-pip-count').fill('45');page.locator('#es-teach-new').uncheck();page.screenshot(path=str(OUT/'Exam_Sprout_Pip_Study.png'))
        page.locator('[data-action="begin-pip-study"]').click();page.wait_for_timeout(100)
        check('Rehearsal-only choice reaches bridge',CALLS[-1][0]=='pip_study' and CALLS[-1][1]['teach_new'] is False)
        page.locator('[data-action="pip-study"]').first.click();page.locator('#es-teach-new').check();page.locator('[data-action="begin-pip-study"]').click();page.wait_for_timeout(100)
        check('Explicit new-learning choice reaches bridge',CALLS[-1][1]['teach_new'] is True)
        page.locator('.es-top-nav [data-view="practice"]').click()
        check('500 cards and 720 minutes exposed',page.locator('[data-practice="size"]').get_attribute('max')=='500' and page.locator('[data-practice="minutes"]').get_attribute('max')=='720')
        for n in (25,50,100,200,500):
            page.locator(f'[data-action="question-preset"][data-size="{n}"]').click()
            check(f'{n}-question preset',page.locator('[data-practice="size"]').input_value()==str(n))
        page.locator('[data-practice="minutes"]').fill('180');page.locator('[data-practice="weighting"]').select_option('custom')
        for did,w in ((11,50),(12,30),(13,20)):page.locator(f'[data-weight="{did}"]').fill(str(w))
        page.screenshot(path=str(OUT/'Exam_Sprout_Exam_Builder.png'),full_page=True)
        page.locator('[data-action="prepare"]').click();page.locator('#es-modal[open]').wait_for()
        check('500-question weighted allocation',sum(map(int,page.locator('.es-allocation-row strong').all_inner_texts()))==500)
        check('Exam answer-lock described','hidden until you submit' in page.locator('#es-modal').inner_text())
        page.screenshot(path=str(OUT/'Exam_Sprout_Allocation.png'))
        page.locator('[data-action="confirm-modal"]').click();page.wait_for_timeout(100)
        check('Start uses sampled token',CALLS[-1][0]=='start' and CALLS[-1][1]['token'] in f.PENDING)
        page.locator('[data-practice="strategy"]').select_option('adaptive');page.locator('[data-practice="cold_only"]').check()
        page.locator('[data-action="prepare"]').click();page.locator('#es-modal[open]').wait_for()
        check('Targeted warning identifies selection bias','intentionally harder/biased' in page.locator('#es-modal').inner_text())
        check('Cold rule is not silently bypassed','cold-retrieval rule' in page.locator('#es-modal').inner_text())
        page.locator('[data-action="close-modal"]').click()
        sample=f.PENDING[next(reversed(f.PENDING))][1]
        s=ExamSession('pharm3',sample.cards[:5],kind='exam',minutes=90);s.enter();s.save_response('Example answer');s.set_confidence(3);s.flags.add(s.current.id);s.go(1)
        save_draft(f.STORE,s);page.evaluate('(d)=>ExamSprout.event("draft_saved",{draft:d})',draft_summary(f.STORE))
        check('Saved exam offers Resume with privacy notice',page.locator('[data-action="resume-exam"]').is_visible() and 'stored locally' in page.locator('.es-draft-banner').inner_text())
        page.locator('[data-action="resume-exam"]').click();page.wait_for_timeout(100);check('Resume reaches saved-session route',CALLS[-1][0]=='resume_exam')
        page.locator('[data-action="discard-draft"]').click();check('Discard requires confirmation',page.locator('#es-modal[open]').count()==1)
        page.locator('[data-action="confirm-modal"]').click();page.wait_for_timeout(100)
        check('Explicit discard removes draft',draft_summary(f.STORE) is None and page.locator('.es-draft-banner').count()==0)
        # Actual session engine produces result; no hidden generated score fixtures.
        s=ExamSession('pharm3',sample.cards[:5]);
        for i in range(5):
            s.enter();s.save_response(f'Answer {i}');s.set_confidence(3)
            if i<4:s.go(1)
        s.submit()
        while s.phase!='finished':s.set_error('concept' if s.index==0 else 'none');s.grade(0 if s.index==0 else 1)
        result=s.result();f.STORE.add_result(result)
        page.evaluate('(p)=>ExamSprout.event("result",p)',{'state':f.STORE.state,'result':result});page.locator('#es-modal[open]').wait_for();page.wait_for_timeout(250)
        check('Confident mistake appears in results','confident' in page.locator('#es-modal').inner_text())
        check('Review all and misses are separate',page.locator('[data-action="review-all"]').count()==1 and page.locator('[data-action="review-misses"]').count()==1)
        check('Result export present',page.locator('[data-action="export-result"]').count()==1)
        page.screenshot(path=str(OUT/'Exam_Sprout_Result.png'))
        page.locator('[data-action="export-result"]').click();page.wait_for_timeout(100);check('Export uses outcome-only endpoint',CALLS[-1][0]=='export_result')
        page.locator('[data-action="review-all"]').click();page.wait_for_timeout(100);check('Review all requests original cards',CALLS[-1][0]=='review_misses' and CALLS[-1][1]['filter']=='all')
        for width in (390,620,940,1440):
            page.set_viewport_size({'width':width,'height':1020})
            for view in ('overview','practice','settings'):
                page.locator(f'.es-top-nav [data-view="{view}"]').click();page.wait_for_timeout(80)
                check(f'{width}px {view}: no horizontal clipping',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            if width==390:
                page.locator('.es-top-nav [data-view="overview"]').click();page.screenshot(path=str(OUT/'Exam_Sprout_Narrow.png'),full_page=True)
        page.set_viewport_size({'width':1440,'height':1020});page.locator('.es-top-nav [data-view="settings"]').click()
        check('Written response retention still off by default',not page.locator('[data-setting="remember_answers"]').is_checked())
        check('Pip reviewer remains independently hideable',page.locator('[data-setting="reviewer_pip"]').count()==1)
        page.screenshot(path=str(OUT/'Exam_Sprout_Settings.png'),full_page=True)
        check('No uncaught JavaScript errors',not ERRORS)
        check('No external requests',not u.REMOTE)
        b.close()
    (OUT/'ui-results.json').write_text(json.dumps({'checks':len(CHECKS),'passed':CHECKS,'errors':ERRORS,'native_anki_tested':False,'bridge':'synthetic; actual assessment, storage and WebGL code exercised'},indent=2))
if __name__=='__main__':run()

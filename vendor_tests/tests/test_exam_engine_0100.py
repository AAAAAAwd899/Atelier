"""New assessment engine: real pure logic/SQLite/file tests, no native-Anki claims."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace,ModuleType
import time,json,random,sys
import pytest
from addon.core import Exam,Scope,CardInfo,DeckStats,Snapshot,MAX_QUESTIONS
from addon.readiness import readiness,letter,daily_first,GRADE_BANDS
from addon.exam_engine import sample_exam,item_priority,interleave
from addon.exam_session import ExamSession
from addon.storage import Store,validate_result
from addon.progress import PipProgress
from addon.drafts import save_draft,load_draft,discard_draft,draft_summary
from addon.evidence import collect_evidence,read_exam_snapshot
from addon.new_learning import introduce_new,fingerprint,available
from test_safety import CollectionFixture,exam

NOW=datetime(2026,9,11,12,tzinfo=timezone.utc)

def fixture(n=90,topics=3,new=False):
    e=Exam.parse({'id':'x','name':'Exam','due':'2026-09-14T12:00','scopes':[{'deck_id':k,'name':f'Topic {k}','weight':1} for k in range(1,topics+1)]})
    cs=[CardInfo(i,i,(i-1)%topics+1,new) for i in range(1,n+1)]
    st={s.deck_id:DeckStats(s.deck_id,s.name,sum(c.owner==s.deck_id for c in cs),sum(c.owner==s.deck_id and c.is_new for c in cs)) for s in e.scopes}
    return e,Snapshot([],st,cs,evidence={'events':[],'last_seen':{}})

def evidence(s,days=4,score=1,source='anki',cold=False):
    out=[]
    for day in range(1,days+1):
        for c in s.cards:
            out.append({'card_id':c.id,'note_id':c.note_id,'owner':c.owner,'ts':NOW.timestamp()-day*86400+c.id*.001,
                        'score':score,'source':source,'delayed':cold,'confidence':0,'session_id':f's{day}','sampling':'representative'})
    s.evidence['events']=out;s.evidence['last_seen']={c.note_id:NOW.timestamp()-86400 for c in s.cards}
    return s

@pytest.mark.parametrize('minimum,grade',GRADE_BANDS)
def test_grade_band_is_explicit(minimum,grade):assert letter(minimum)==grade

def test_no_evidence_is_unknown_not_f():
    e,s=fixture();r=readiness(e,s,NOW)
    assert r['score'] is None and r['grade']=='—' and 'guarantee' in r['disclaimer']

def test_confidence_alone_cannot_create_grade():
    e,s=fixture();other=Exam.parse({**e.to_dict(),'scopes':[{**x,'confidence':5} for x in e.to_dict()['scopes']]})
    assert readiness(other,s,NOW)['score'] is None
    evidence(s);assert readiness(e,s,NOW)['score']==readiness(other,s,NOW)['score']

def test_first_note_per_day_resists_repeats_and_sibling_farming():
    e,s=fixture(1,1);evidence(s,1,0)
    first=deepcopy(s.evidence['events'][0]);later=[{**first,'card_id':100+i,'ts':first['ts']+i+1,'score':1} for i in range(500)]
    assert daily_first([first]+later,NOW.timestamp())==[first]
    r=readiness(e,s,NOW);s.evidence['events']+=later
    assert readiness(e,s,NOW)['score']==r['score']

def test_unseen_sibling_does_not_count_as_checked_variant():
    e,s=fixture(1,1);evidence(s,3,1,cold=True)
    before=readiness(e,s,NOW)
    s.cards.append(CardInfo(2,1,1,True));s.stats[1].total+=1
    after=readiness(e,s,NOW)
    assert after['coverage']==50 and after['rows'][0]['known']==50 and after['score']<before['score']

def test_evidence_not_attributed_to_other_sibling_topic():
    e,s=fixture(2,2);s.cards[1]=CardInfo(2,1,2);evidence(s,1)
    s.evidence['events']=s.evidence['events'][:1]
    rows={r['deck_id']:r for r in readiness(e,s,NOW)['rows']}
    assert rows[2]['coverage']==0 and rows[2]['observed']==0

def test_small_sample_grade_capped():
    e,s=fixture(8,1);evidence(s,4,1,source='exam',cold=True)
    assert readiness(e,s,NOW)['score']<=79 and readiness(e,s,NOW)['evidence']=='Low'

def test_only_one_day_evidence_stays_low():
    e,s=fixture(120);evidence(s,1,1,source='exam',cold=True)
    assert readiness(e,s,NOW)['score']<=79

def test_native_review_only_cannot_receive_a_or_s():
    e,s=fixture(500);evidence(s,10,1,cold=True)
    assert readiness(e,s,NOW)['score']<=89 and readiness(e,s,NOW)['cold_mocks']==0

def test_strong_broad_repeated_cold_evidence_can_reach_s():
    e,s=fixture(500);evidence(s,10,1,source='exam',cold=True)
    r=readiness(e,s,NOW);assert r['grade']=='S' and r['evidence']=='High' and r['cold_mocks']==10

def test_narrow_mock_not_enough_for_a():
    e,s=fixture(300);evidence(s,4,1,cold=True)
    for ev in s.evidence['events']:
        if ev['owner']==1:ev['source']='exam'
    assert readiness(e,s,NOW)['cold_mocks']==0

def test_targeted_drill_not_a_cold_mock():
    e,s=fixture(300);evidence(s,4,1,source='exam',cold=True)
    for ev in s.evidence['events']:ev['sampling']='adaptive'
    r=readiness(e,s,NOW);assert r['cold_mocks']==0 and r['score']<=89

def test_missing_or_unmeasured_high_emphasis_topic_counts_against_grade():
    e,s=fixture(300);evidence(s,5,1,source='exam',cold=True)
    s.evidence['events']=[ev for ev in s.evidence['events'] if ev['owner']!=3]
    r=readiness(e,s,NOW);assert r['coverage']<70 and r['score']<=79

def test_deadline_farther_away_without_learning_does_not_increase_grade():
    e,s=fixture();evidence(s,4,1,source='exam',cold=True)
    later=Exam.parse({**e.to_dict(),'due':'2026-10-14T12:00'})
    assert readiness(later,s,NOW)['score']<readiness(e,s,NOW)['score']

def test_recent_failures_reduce_grade():
    e,s=fixture();evidence(s,4,1,source='exam',cold=True);before=readiness(e,s,NOW)['score']
    for ev in s.evidence['events']:
        if ev['ts']>NOW.timestamp()-2*86400:ev['score']=0
    assert readiness(e,s,NOW)['score']<before

def test_confident_mistakes_exposed_without_boosting_grade():
    e,s=fixture();evidence(s,4,0)
    baseline=readiness(e,s,NOW)['score']
    for ev in s.evidence['events']:ev['confidence']=3
    r=readiness(e,s,NOW);assert r['confident_misses']==360 and r['score']==baseline

def test_grade_output_finite_bounded_and_roundtrips():
    for seed in range(30):
        rng=random.Random(seed);e,s=fixture(rng.randint(1,200));evidence(s,rng.randint(1,10),rng.choice([0,.5,1]))
        r=readiness(e,s,NOW);json.dumps(r,allow_nan=False)
        assert 0<=r['score']<=100 and 0<=r['sensitivity'][0]<=r['sensitivity'][1]<=100

@pytest.mark.parametrize('n',[1,25,100,101,200,350,500])
@pytest.mark.parametrize('strategy',['representative','adaptive'])
def test_extended_question_counts_no_duplicates(n,strategy):
    e,s=fixture(700);out,_=sample_exam(e,s,n,strategy=strategy,rng=random.Random(1))
    assert len(out.cards)==n and len({c.id for c in out.cards})==n and len({c.note_id for c in out.cards})==n
    assert sum(out.counts.values())==n

@pytest.mark.parametrize('n',[0,501,True,float('inf'),'a'])
def test_question_safety_limits(n):
    e,s=fixture();
    with pytest.raises(ValueError):sample_exam(e,s,n)

def test_blueprint_weights_capacity_and_zero_weights():
    e,s=fixture(900);out,_=sample_exam(e,s,500,weighting='custom',custom={1:50,2:30,3:20},rng=random.Random(2))
    assert out.counts=={1:250,2:150,3:100}
    out,_=sample_exam(e,s,500,weighting='custom',custom={1:1,2:0,3:0})
    assert len(out.cards)==300 and all(c.owner==1 for c in out.cards)

def test_cold_excludes_new_and_recent_siblings():
    e,s=fixture(30,1);now=time.time()
    s.cards[0]=CardInfo(1,1,1,True);s.cards[1]=CardInfo(2,2,1)
    s.cards[2]=CardInfo(3,2,1);s.evidence['last_seen']={c.note_id:now-172800 for c in s.cards};s.evidence['last_seen'][2]=now-60
    out,_=sample_exam(e,s,30,cold_only=True)
    assert len(out.cards)==27 and not {1,2,3}&{c.id for c in out.cards} and out.warnings

def test_adaptive_biases_toward_recent_confident_mistakes():
    e,s=fixture(100,1);now=time.time()
    s.evidence['events']=[{'card_id':c.id,'note_id':c.note_id,'owner':1,'ts':now-120,'score':0 if c.id<=50 else 1,'confidence':3} for c in s.cards]
    s.evidence['last_seen']={c.note_id:now-120 for c in s.cards}
    count=0
    for seed in range(30):
        out,_=sample_exam(e,s,20,strategy='adaptive',rng=random.Random(seed));count+=sum(c.id<=50 for c in out.cards)
    assert count>480 # 600 questions, chance expectation 300; deterministic regression

def test_single_topic_or_interleaved_order_valid():
    for topics in (1,3):
        e,s=fixture(90,topics);out,_=sample_exam(e,s,90,rng=random.Random(5))
        assert len(out.cards)==90
        if topics==3:assert sum(a.owner!=b.owner for a,b in zip(out.cards,out.cards[1:]))>75

def test_adaptive_cross_topic_siblings_remain_unique_and_covered():
    e,s=fixture(6,3);s.cards=[CardInfo(i,(i+1)//2,(i-1)%3+1) for i in range(1,7)]
    for seed in range(15):
        out,_=sample_exam(e,s,3,strategy='adaptive',rng=random.Random(seed))
        assert len({c.note_id for c in out.cards})==3 and all(v==1 for v in out.counts.values())

def session(n=3,kind='exam',minutes=0,new=False):
    return ExamSession('x',[CardInfo(i,i,1,new) for i in range(1,n+1)],kind,minutes)

def test_500_answer_exam_persists_all_telemetry(tmp_path):
    s=session(500)
    for i in range(500):
        s.enter();s.save_response(f'answer {i}');s.set_confidence(3 if i%2 else 2)
        if i<499:s.go(1)
    s.submit()
    while s.phase!='finished':s.grade(.5 if s.index%7==0 else 1)
    r=validate_result(s.result());assert r['total']==500 and len(r['items'])==500
    assert r['items'][250]['attempted'] and r['items'][250]['seconds']>=0
    st=Store(tmp_path);e,_=fixture();st.save_exam(e.to_dict());st.add_result(r)
    assert len(Store(tmp_path).state['history'][0]['items'])==500 and 'answer 499' not in st.path.read_text()

def test_cannot_award_unanswered_exam_credit_after_reveal():
    s=session();s.submit()
    with pytest.raises(ValueError):s.grade(1)
    s.grade(0);assert s.index==1

def test_spoken_response_mark_and_confidence_lock():
    s=session();s.mark_attempted();s.set_confidence(1);s.submit();s.set_confidence(3);s.save_response('after reveal')
    assert s.confidence[1]==1 and 1 not in s.responses
    s.grade(1);assert s.grades[1]==1

def test_render_failure_never_graded():
    s=session(kind='practice');s.render_errors.add(1);s.reveal()
    with pytest.raises(ValueError):s.grade(0)
    s.skip();assert 1 not in s.grades

def test_error_type_records_after_reveal_only():
    s=session(kind='practice');s.set_error('concept');assert not s.errors
    s.reveal();s.set_error('concept');s.grade(.5);assert s.result()['items'][0]['error_type']=='concept'

def test_saved_exam_roundtrip_keeps_order_answers_flags_and_confidence(tmp_path):
    st=Store(tmp_path);s=session();s.enter();s.save_response('<private>');s.set_confidence(2);s.flags.add(2);s.go(1)
    save_draft(st,s);t=load_draft(st)
    assert [c.id for c in t.cards]==[1,2,3] and t.responses[1]=='<private>' and t.flags=={2} and t.index==1
    assert t.confidence[1]==2 and '<private>' in (st.folder/'active_exam.json').read_text()
    assert draft_summary(st)['questions']==3
    discard_draft(st,'other');assert load_draft(st) is not None
    discard_draft(st,s.id);assert load_draft(st) is None

@pytest.mark.parametrize('kind',['exam','practice'])
def test_resume_elapsed_timer_cannot_reset(kind):
    s=session(kind=kind,minutes=2);d=s.serialize();d['elapsed']=70
    r=ExamSession.restore(d);assert 48<=r.remaining_seconds()<=51

def test_timed_exam_keeps_counting_while_closed():
    s=session(minutes=1);d=s.serialize();past=datetime.now(timezone.utc)-timedelta(minutes=5)
    d['started_at']=past.isoformat();d['deadline']=past.timestamp()+60
    r=ExamSession.restore(d);assert r.phase=='grading' and r.timed_out and r.remaining_seconds() is None

def test_grading_session_restores_without_timed_resubmit():
    s=session(minutes=1);s.mark_attempted();s.submit();s.grade(1);d=s.serialize();t=ExamSession.restore(d)
    assert t.phase=='grading' and t.index==1 and t.grades=={1:1} and t.remaining_seconds() is None

@pytest.mark.parametrize('patch',[{'id':'../x'},{'index':999},{'minutes':721},{'revealed':'true'},{'responses':{'9':'secret'}},
 {'grades':{'1':1}},{'phase':'finished'},{'deadline':float('nan')},{'confidence':{'1':True}},{'sampling':'magic'}])
def test_corrupt_drafts_rejected(patch):
    d=session(minutes=1).serialize();d.update(patch)
    with pytest.raises((ValueError,KeyError)):ExamSession.restore(d)

def test_bad_progress_preserved(tmp_path):
    st=Store(tmp_path);path=st.folder/'pip_progress.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('broken')
    p=PipProgress(st);p.record([1]);assert path.read_text()=='broken' and p.signal()['warning']

def test_pip_effort_separate_from_exams_and_correctness(tmp_path):
    st=Store(tmp_path);p=PipProgress(st);p.record([1,1,2],NOW);assert p.total==2
    p.record([1,3],NOW);assert p.total==3
    p.record([1],NOW+timedelta(days=1));assert p.total==4
    e,s=fixture();st.save_exam(e.to_dict());st.delete_exam(e.id)
    assert PipProgress(st).total==4 and p.signal()['kind']=='effort'

def test_daily_effort_cap(tmp_path):
    p=PipProgress(Store(tmp_path));p.record(range(1,1000),NOW);assert p.total==500
    p.record([1200],NOW);assert p.total==500

def test_evidence_queries_use_actual_first_daily_answer_and_no_writes():
    col=CollectionFixture();col.conn.execute('ALTER TABLE revlog ADD COLUMN lastIvl INTEGER DEFAULT 3')
    before=col.fingerprint();snap=read_exam_snapshot(col,exam())
    assert col.fingerprint()==before and len(snap.evidence['events'])==1
    ev=snap.evidence['events'][0];assert ev['card_id']==2 and ev['score']==0 and ev['delayed']
    assert all(x.startswith('SELECT') for x in col.db.sql)

def test_native_and_practice_evidence_not_double_counted():
    col=CollectionFixture();col.conn.execute('ALTER TABLE revlog ADD COLUMN lastIvl INTEGER DEFAULT 3')
    s=session(1,kind='practice');s.cards=[CardInfo(2,2,2)];s.enter();s.reveal();s.scheduled.add(2);s.grade(1)
    r=s.result();r['exam_id']='exam';snap=read_exam_snapshot(col,exam(),[r])
    assert len(snap.evidence['events'])==1 and snap.evidence['events'][0]['source']=='anki'

def test_practice_results_remap_to_current_owner():
    col=CollectionFixture();col.conn.execute('ALTER TABLE revlog ADD COLUMN lastIvl INTEGER DEFAULT 3')
    s=session(1,kind='practice');s.cards=[CardInfo(2,2,99)];s.enter();s.reveal();s.grade(.5)
    r=s.result();r['exam_id']='exam';snap=read_exam_snapshot(col,exam(),[r])
    ev=[e for e in snap.evidence['events'] if e['source']=='practice'][0];assert ev['owner']==2

class FakeCollection:
    """Explicit scheduler double: proves boundary checks, NOT real Grade Now semantics."""
    def __init__(self):
        self.card=SimpleNamespace(id=1,nid=1,did=1,odid=0,type=0,queue=0,reps=0,mod=9)
        self.calls=[];self._backend=SimpleNamespace(grade_now=self.grade)
        self.decks=SimpleNamespace(all_names_and_ids=lambda **kw:[SimpleNamespace(id=1,name='Topic 1')])
    def get_card(self,cid):assert cid==1;return self.card
    def find_cards(self,q):return [1]
    def grade(self,**kw):self.calls.append(kw);self.card.type=1;self.card.queue=1;self.card.reps+=1;return {'changes':'native-double'}

@pytest.fixture
def native_enum(monkeypatch):
    a=ModuleType('anki');a.__path__=[];b=ModuleType('anki.scheduler');b.__path__=[];c=ModuleType('anki.scheduler.v3');c.CardAnswer=SimpleNamespace(AGAIN=1,HARD=2,GOOD=3,EASY=4)
    for k,v in [('anki',a),('anki.scheduler',b),('anki.scheduler.v3',c)]:monkeypatch.setitem(sys.modules,k,v)

@pytest.mark.parametrize('rating',[1,2,3,4])
def test_new_learning_records_one_native_rating_and_rejects_replay(native_enum,rating):
    col=FakeCollection();e,_=fixture(1,1);expected=fingerprint(col.card)
    introduce_new(col,card_id=1,expected=expected,exam=e,rating=rating,authorized=True)
    assert col.calls==[{'card_ids':[1],'rating':rating}]
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=expected,exam=e,rating=rating,authorized=True)
    assert len(col.calls)==1

@pytest.mark.parametrize('field,value',[('type',2),('queue',-1),('queue',-2),('queue',-3),('reps',1),('odid',5)])
def test_never_write_learned_suspended_buried_or_filtered(native_enum,field,value):
    col=FakeCollection();setattr(col.card,field,value);e,_=fixture(1,1)
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=fingerprint(col.card),exam=e,rating=3,authorized=True)
    assert not col.calls

@pytest.mark.parametrize('rating',[0,5,True,3.0,'3'])
def test_native_rating_validation(native_enum,rating):
    col=FakeCollection();e,_=fixture(1,1)
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=fingerprint(col.card),exam=e,rating=rating,authorized=True)
    assert not col.calls

def test_native_rating_requires_explicit_authorization(native_enum):
    col=FakeCollection();e,_=fixture(1,1)
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=fingerprint(col.card),exam=e,rating=3,authorized=False)
    assert not col.calls

def test_missing_api_and_stale_card_fail_closed(native_enum):
    col=FakeCollection();e,_=fixture(1,1);expected=fingerprint(col.card);col.card.mod+=1
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=expected,exam=e,rating=3,authorized=True)
    col._backend=object();assert not available(col)
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=fingerprint(col.card),exam=e,rating=3,authorized=True)
    assert not col.calls

def test_card_moved_outside_exam_or_filter_not_scheduled(native_enum):
    col=FakeCollection();e,_=fixture(1,1);col.card.did=20
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=fingerprint(col.card),exam=e,rating=3,authorized=True)
    col.card.did=1;e=Exam.parse({**e.to_dict(),'query':'tag:exam'});col.find_cards=lambda q:[]
    with pytest.raises(ValueError):introduce_new(col,card_id=1,expected=fingerprint(col.card),exam=e,rating=3,authorized=True)
    assert not col.calls

def test_waiting_alone_cannot_improve_projected_failed_recall():
    e,s=fixture(500);evidence(s,4,0,cold=True)
    early=Exam.parse({**e.to_dict(),'due':'2026-09-11T12:00'})
    later=Exam.parse({**e.to_dict(),'due':'2026-11-11T12:00'})
    assert readiness(later,s,NOW)['score']<=readiness(early,s,NOW)['score']

def test_other_exam_exposure_still_prevents_cold_repeat():
    col=CollectionFixture();col.conn.execute('ALTER TABLE revlog ADD COLUMN lastIvl INTEGER DEFAULT 3')
    s=session(1,kind='practice');s.cards=[CardInfo(1,1,1)];s.enter();s.reveal();s.grade(1)
    r=s.result();r['exam_id']='different_exam';snap=read_exam_snapshot(col,exam(),[r])
    assert snap.evidence['last_seen'][1]>time.time()-60
    assert any(e['card_id']==1 for e in snap.evidence['events'])

def test_large_evidence_limit_is_explained_and_capped():
    e,s=fixture(500);evidence(s,10,1,source='exam',cold=True);s.evidence['truncated']=True
    r=readiness(e,s,NOW);assert r['score']<=79 and any('safety limit' in x for x in r['limits'])

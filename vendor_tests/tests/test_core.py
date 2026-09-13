from datetime import datetime, timedelta
import math
import random
import pytest
from addon.core import *


def make_exam(**changes):
    data = {"id":"demo", "name":"Cardiology", "due":"2026-09-20T09:00", "scopes":[{"deck_id":1,"name":"Cardio","confidence":2,"weight":1}, {"deck_id":2,"name":"Renal","confidence":4,"weight":1}]}
    data.update(changes)
    return Exam.parse(data)

@pytest.mark.parametrize('value',[0,501,-1,1.5,'no',True,float('nan'),float('inf')])
def test_size_validation(value):
    with pytest.raises(ValueError):sample_cards([CardInfo(1,1,1)],value,{1:1})

@pytest.mark.parametrize('weight',[-1,float('nan'),float('inf'),'no',True,1001])
def test_weight_validation(weight):
    with pytest.raises(ValueError):sample_cards([CardInfo(1,1,1)],1,{1:weight})

@pytest.mark.parametrize('size',[1,2,3,7,10,25,50,99,100])
def test_sample_unique_and_capped(size):
    pool=[CardInfo(i,i//2,i%3+1) for i in range(1,301)]
    result=sample_cards(pool,size,{1:50,2:30,3:20},rng=random.Random(11))
    assert len(result.cards)==size
    assert len({c.id for c in result.cards})==size
    assert len({c.note_id for c in result.cards})==size
    assert sum(result.counts.values())==size
    if size>=3:assert all(result.counts[k]>0 for k in (1,2,3))

def test_weighted_allocation_exact_example():
    assert apportion(100,{1:50,2:30,3:20},{1:1000,2:1000,3:1000},True)=={1:50,2:30,3:20}

def test_short_pool_does_not_repeat():
    result=sample_cards([CardInfo(1,1,1),CardInfo(2,1,2),CardInfo(3,2,2)],100,{1:1,2:1},rng=random.Random(42))
    assert len(result.cards)==2
    assert result.warnings

def test_zero_means_excluded_even_when_other_exhausted():
    r=sample_cards([CardInfo(1,1,1)]+[CardInfo(i,i,2) for i in range(2,200)],100,{1:1,2:0})
    assert len(r.cards)==1 and r.counts[2]==0

def test_all_zero_is_an_error():
    with pytest.raises(ValueError):sample_cards([],5,{1:0})

def test_redistributes_when_group_small():
    assert apportion(100,{1:90,2:10},{1:2,2:200})=={1:2,2:98}

def test_note_siblings_can_be_allowed():
    pool=[CardInfo(1,1,1),CardInfo(2,1,1)]
    assert len(sample_cards(pool,2,{1:1},one_per_note=False).cards)==2

def test_overlap_maps_to_most_specific_and_uses_renamed_ids():
    scopes=[Scope(1,'Old name'),Scope(2,'Parent::Oldchild')]
    assert scope_owners(scopes,{1:'Root',2:'Root::Child',3:'Root::Child::Sub',4:'Root::Other',5:'Other'})=={1:1,2:2,3:2,4:1}

def test_missing_id_never_remapped_by_name():
    assert scope_owners([Scope(99,'Matching')],{1:'Matching'})=={}

def test_card_dedup_when_adapter_passes_duplicates():
    c=CardInfo(1,1,1)
    assert len(sample_cards([c,c,c],100,{1:1}).cards)==1

def test_cross_deck_siblings_do_not_erase_coverable_decks():
    cards=[CardInfo(1,1,1),CardInfo(2,1,2),CardInfo(3,2,1),CardInfo(4,2,2)]
    for seed in range(80):
        r=sample_cards(cards,2,{1:1,2:1},rng=random.Random(seed))
        assert r.counts=={1:1,2:1}

def test_matching_reassigns_to_cover_constrained_owner():
    cards=[CardInfo(1,1,1),CardInfo(2,1,2),CardInfo(3,2,1),CardInfo(4,2,3),CardInfo(5,3,1)]
    for seed in range(20):
        assert all(v==1 for v in sample_cards(cards,3,{1:1,2:1,3:1},rng=random.Random(seed)).counts.values())

def test_seed_reproducible_but_different_seed_randomized():
    cards=[CardInfo(i,i,i%3) for i in range(1,300)]
    def run(seed):return [c.id for c in sample_cards(cards,50,{0:1,1:1,2:1},rng=random.Random(seed)).cards]
    assert run(1)==run(1) and run(1)!=run(2)

def test_sampling_property_sweep():
    rng=random.Random(441)
    for _ in range(500):
        n=rng.randint(1,20)
        weights={i:rng.choice([0,.2,1,10,100]) for i in range(n)}
        caps={i:rng.randint(0,100) for i in range(n)}
        total=rng.randint(0,100)
        out=apportion(total,weights,caps,rng.choice([True,False]))
        assert sum(out.values())==min(total,sum(caps[k] for k in weights if weights[k]>0))
        assert all(0<=out[k]<=caps[k] and (weights[k]>0 or out[k]==0) for k in weights)

@pytest.mark.parametrize('changes',[
    {'name':''},{'due':'not a date'},{'daily_minutes':0},{'daily_minutes':481},
    {'weekdays':[]},{'weekdays':[7]},{'mode':'AI'},{'exam_format':'unknown'},
    {'scopes':[]},{'scopes':[None]},{'scopes':[{'deck_id':1,'weight':-1}]},
    {'scopes':[{'deck_id':1},{'deck_id':1}]},{'due':'2026-09-20T09:00+02:00'},
    {'id':'../../bad'},{'name':'a'*121},
])
def test_invalid_exams(changes):
    with pytest.raises(ValueError):make_exam(**changes)

def test_core_serializes_roundtrip():
    e=make_exam();assert Exam.parse(e.to_dict())==e

def test_lower_confidence_more_time_given_equal_stats():
    e=make_exam();stats={i:DeckStats(i,str(i),100,0,0) for i in (1,2)}
    p=plan_exam(e,stats,datetime(2026,9,11,12))
    rows={r['deck_id']:r for r in p['rows']}
    assert rows[1]['minutes']>rows[2]['minutes']
    assert p['focus_minutes']+p['break_minutes']==p['budget_minutes']==60

def test_emphasis_changes_priority():
    e=make_exam(scopes=[{'deck_id':1,'name':'A','confidence':3,'weight':1},{'deck_id':2,'name':'B','confidence':3,'weight':5}])
    p=plan_exam(e,{i:DeckStats(i,str(i),100,0,0) for i in (1,2)},datetime(2026,9,11))
    assert p['rows'][0]['deck_id']==2

def test_recent_misses_increase_priority():
    e=make_exam(scopes=[{'deck_id':i,'name':str(i),'confidence':3} for i in (1,2)])
    p=plan_exam(e,{1:DeckStats(1,'1',100,0,0,20,1),2:DeckStats(2,'2',100,0,0,20,15)},datetime(2026,9,11))
    assert p['rows'][0]['deck_id']==2

def test_auto_cram_boundary():
    e=make_exam(due='2026-09-14T12:00')
    st={1:DeckStats(1,'1',100),2:DeckStats(2,'2',100)}
    assert plan_exam(e,st,datetime(2026,9,11,12))['mode']=='cram'
    assert plan_exam(e,st,datetime(2026,9,11,11,59))['mode']=='steady'

def test_past_no_negative_time():
    p=plan_exam(make_exam(),{},datetime(2026,10,1))
    assert p['hours_left']==p['focus_minutes']==p['study_days_left']==0
    assert p['warnings']

def test_today_caps_at_actual_time_left():
    e=make_exam(due='2026-09-11T12:05')
    p=plan_exam(e,{1:DeckStats(1,'A',10)},datetime(2026,9,11,12))
    assert p['budget_minutes']==5

def test_rest_day_budget_is_labeled_next_day():
    e=make_exam(weekdays=[0,1,2,3])
    p=plan_exam(e,{1:DeckStats(1,'A',10)},datetime(2026,9,11,12))
    assert not p['today_is_study_day']
    assert p['next_study_day']=='2026-09-14'

def test_exam_day_not_promised_in_advance():
    e=make_exam(due='2026-09-14T09:00',weekdays=[0])
    assert study_days(e,datetime(2026,9,11))==[]

def test_suggestions_are_names_only():
    assert suggest_decks('Cardiology and renal exam',[{'id':1,'name':'Heart::Cardiology'},{'id':2,'name':'Law'},{'id':3,'name':'Renal'}])==[1,3]

def session(kind='exam',minutes=0):return PracticeSession('e',[CardInfo(i,i,1 if i<3 else 2) for i in range(1,4)],kind,minutes)

def test_exam_hides_answers_until_submit():
    s=session()
    with pytest.raises(ValueError):s.reveal()
    with pytest.raises(ValueError):s.grade(1)
    s.save_response('My answer');s.go(1);s.go(-1)
    assert s.responses[1]=='My answer'
    s.submit();assert s.phase=='grading' and s.revealed
    s.save_response('Cannot alter')
    assert s.responses[1]=='My answer'

def test_grading_summary_and_ungraded_denominator():
    s=session();s.submit();s.grade(1);s.grade(.5);s.skip()
    r=s.result()
    assert s.phase=='finished'
    assert r['percent']==50 and r['graded']==2 and r['ungraded']==1
    assert r['breakdown'][0]['missed_ids']==[2]
    assert 'responses' not in r

def test_practice_must_reveal_between_cards():
    s=session('practice')
    with pytest.raises(ValueError):s.grade(1)
    s.reveal();s.grade(1)
    assert not s.revealed
    with pytest.raises(ValueError):s.grade(1)

def test_timer_uses_elapsed_clock_and_stops_for_grading():
    s=session(minutes=1)
    assert s.remaining_seconds(s.start_clock+30)==30
    assert s.remaining_seconds(s.start_clock+70)==0
    s.submit(True)
    assert s.timed_out and s.remaining_seconds(s.start_clock+300) is None

def test_timeout_practice_finishes_without_grading_unknowns():
    s=session('practice',1);s.submit(True)
    assert s.phase=='finished'
    assert s.result()['graded']==0

def test_finished_state_is_guarded():
    s=session();s.submit();s.grade(1);s.grade(1);s.grade(1)
    with pytest.raises(ValueError):s.grade(1)
    with pytest.raises(ValueError):s.go(1)

@pytest.mark.parametrize('score',[-1,.3,2])
def test_invalid_self_marks_rejected(score):
    s=session();s.submit()
    with pytest.raises(ValueError):s.grade(score)

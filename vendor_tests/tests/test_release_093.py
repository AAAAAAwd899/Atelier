"""Focused 0.9.3 regression tests. Native objects remain test doubles."""
import sys
from datetime import datetime
from types import SimpleNamespace
import pytest
from addon.core import CardInfo, PracticeSession, plan_exam
from addon.collection_reader import read_snapshot
from test_safety import CollectionFixture, exam
from test_window_contract import integration


def test_selected_parent_covered_by_children_does_not_warn():
    c=CollectionFixture()
    c.conn.execute('DELETE FROM cards WHERE id = 1')
    e=exam()
    before=c.fingerprint()
    snap=read_snapshot(c,e)
    assert snap.stats[1].total==0 and snap.stats[1].covered_elsewhere
    assert {card.id for card in snap.cards}=={2,3}
    plan=plan_exam(e,snap.stats,datetime(2026,9,11))
    assert not any('“Pharmacy” has no eligible' in w for w in plan['warnings'])
    assert c.fingerprint()==before


def test_genuinely_empty_child_still_warns():
    c=CollectionFixture()
    c.conn.execute('DELETE FROM cards WHERE did=2 OR odid=2')
    e=exam()
    snap=read_snapshot(c,e)
    assert not snap.stats[2].covered_elsewhere
    plan=plan_exam(e,snap.stats,datetime(2026,9,11))
    assert any('Pharmacy::Cardio” has no eligible' in w for w in plan['warnings'])


def setup_browser(integration,monkeypatch,opener):
    monkeypatch.setattr(sys.modules['aqt'],'dialogs',SimpleNamespace(open=opener),raising=False)
    c=integration.c
    c.mw.col=SimpleNamespace(decks=SimpleNamespace(get=lambda did,default=False: {
        'name':'Pharmacy' if did==1 else 'Pharmacy::Cardio'}))
    c.store.save_exam(exam().to_dict())
    c.open()
    return c.dialog


def test_browser_uses_exported_dialog_manager(integration,monkeypatch):
    calls=[]
    d=setup_browser(integration,monkeypatch,lambda *a,**k:calls.append((a,k)))
    d._browse('7',{'id':'exam','deck_id':2})
    assert len(calls)==1 and calls[0][0][0]=='Browser'
    assert calls[0][1]['search']==('deck:"Pharmacy::Cardio" -is:suspended -is:buried',)
    assert d.closed


def test_browser_failure_keeps_planner_open(integration,monkeypatch):
    def fail(*args,**kwargs):raise RuntimeError('synthetic Browser error')
    d=setup_browser(integration,monkeypatch,fail)
    with pytest.raises(RuntimeError,match='synthetic Browser error'):
        d._browse('7',{'id':'exam','deck_id':2})
    assert not d.closed and d.web is not None and not d.forced


@pytest.mark.parametrize('start',[47.583770061,0.000000001,999999.123456789])
def test_timer_exact_second_float_boundaries(start):
    s=PracticeSession('exam',[CardInfo(1,1,1)],minutes=1)
    s.start_clock=start
    assert s.remaining_seconds(start+30)==30
    assert s.remaining_seconds(start+59)==1
    assert s.remaining_seconds(start+60)==0
    assert s.remaining_seconds(start+30.2)==30

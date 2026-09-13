"""Focused release regressions. Qt and Anki APIs below are explicit test doubles."""
from datetime import datetime
from types import SimpleNamespace, ModuleType
import sys,json,logging
import pytest
from addon.core import Exam, CardInfo, PracticeSession, sample_cards, DeckStats
from addon.session_tools import needs_focus_session,practice_weights,sampling_coverage,review_items,growth_signal
from addon.collection_reader import read_snapshot
from addon.storage import Store,validate_result
from addon.answers import clean_responses,save_answers,load_answers,clear_answers
from addon.diagnostics import LocalDiagnostics
from test_safety import CollectionFixture,exam
from test_window_contract import integration, Op


def result():
    s=PracticeSession('exam',[CardInfo(1,10,1),CardInfo(2,20,2),CardInfo(3,30,2)])
    s.save_response('original');s.submit();s.grade(0);s.grade(1);s.skip()
    return s.result()


def test_result_keeps_original_card_ids_without_plaintext():
    r=result();clean=validate_result(r)
    assert len(clean['items'])==3 and clean['items'][2]['grade'] is None
    assert 'original' not in json.dumps(clean)


def test_missed_and_unanswered_but_not_correct_are_reviewed():
    assert [x['card_id'] for x in review_items(result())]==[1,3]


def test_legacy_results_can_only_recover_missed_ids():
    r=result();r.pop('items');assert [x['card_id'] for x in review_items(r)]==[1]


def test_invalid_result_duplicate_items_rejected():
    r=result();r['items'][2]['card_id']=1
    with pytest.raises(ValueError):validate_result(r)


def test_invalid_result_grade_rejected():
    r=result();r['items'][0]['grade']=float('nan')
    with pytest.raises(ValueError):validate_result(r)


def test_answers_off_by_default_no_file(tmp_path):
    st=Store(tmp_path);save_answers(st,'a',{'1':'private'})
    assert not (st.folder/'practice_answers.json').exists() and load_answers(st)=={}


def test_optional_answers_are_separate_and_last_ten(tmp_path):
    st=Store(tmp_path);st.save_settings({**st.state['settings'],'remember_answers':True})
    for n in range(12):save_answers(st,str(n),{'1':f'private{n}'})
    data=load_answers(st);assert len(data)==10 and '0' not in data and data['11']['1']=='private11'
    assert 'private' not in st.path.read_text()
    clear_answers(st);assert not (st.folder/'practice_answers.json').exists()


def test_answers_text_is_bounded_and_only_card_ids():
    assert clean_responses({'1':'x'*12000,'bad':'y','-1':'z','2':9})=={'1':'x'*10000}


def test_parent_is_not_a_second_practice_quota():
    col=CollectionFixture();col.conn.execute('delete from cards where id=1')
    e=exam();snap=read_snapshot(col,e);weights=practice_weights(e,snap,snap.cards,'equal',{})
    assert weights=={2:1}
    sample=sample_cards(snap.cards,2,weights)
    assert len(sample.cards)==2 and not any('eligible' in x for x in sample.warnings)
    coverage=sampling_coverage(e,snap,snap.cards,sample.counts)
    assert coverage[0]['status']=='Covered through selected subdecks'
    assert coverage[0]['name']=='Pharmacy'


@pytest.mark.parametrize('mode',['equal','emphasis','custom','size'])
def test_sampling_weights_respect_nonempty_groups(mode):
    col=CollectionFixture();e=exam();snap=read_snapshot(col,e)
    weights=practice_weights(e,snap,snap.cards,mode,{1:2,2:1})
    assert set(weights)=={1,2} and all(x>0 for x in weights.values())


def test_study_requires_exact_scope_when_parent_and_child_selected():
    assert needs_focus_session(exam(),1,{1:'Pharmacy',2:'Pharmacy::Cardio'})
    assert not needs_focus_session(exam(),2,{1:'Pharmacy',2:'Pharmacy::Cardio'})
    assert needs_focus_session(exam('tag:exam'),2,{1:'Pharmacy',2:'Pharmacy::Cardio'})
    with pytest.raises(ValueError):needs_focus_session(exam(),3,{3:'Other'})


def test_growth_is_not_inflated_by_due_or_new_cards():
    e=Exam.parse({'name':'E','due':'2099-09-09T09:00','scopes':[{'deck_id':1,'name':'D','confidence':1}]})
    st=DeckStats(1,'D',total=100,new=100,due=100)
    g=growth_signal(e,{1:st});assert g['score']==0 and g['stage']==1
    st.new=0;st.attempts=100;st.again=0
    assert growth_signal(e,{1:st})['score']>g['score']


def test_diagnostics_current_session_does_not_pull_old_file(tmp_path):
    d=LocalDiagnostics();d.use_profile(tmp_path);d.path.parent.mkdir(parents=True)
    d.path.write_text('old error from old build')
    assert 'old error' not in d.report() and 'old error' in d.report(True)
    d.emit(logging.LogRecord('exam_sprout',logging.ERROR,'',0,'new event',(),None))
    assert 'new event' in d.report() and 'old error' not in d.report()


class NativeOp:
    queued=[]
    def __init__(self,*,parent,op):self.op=op
    def success(self,fn):self.ok=fn;return self
    def failure(self,fn):self.fail=fn;return self
    def run_in_background(self):self.queued.append(self)
    def complete(self,col):
        try:value=self.op(col)
        except Exception as e:self.fail(e)
        else:self.ok(value)


def setup_study(integration,monkeypatch):
    c=integration.c;col=CollectionFixture();selected=[];moves=[]
    col.decks.set_current=lambda did:selected.append(did)
    c.mw.col=col;c.mw.moveToState=lambda state:moves.append(state)
    c.store.save_exam(exam().to_dict());c.open();NativeOp.queued=[]
    monkeypatch.setattr(sys.modules['aqt.operations'],'CollectionOp',NativeOp,raising=False)
    return c,c.dialog,col,selected,moves


def test_start_here_really_launches_native_reviewer(integration,monkeypatch):
    c,d,col,selected,moves=setup_study(integration,monkeypatch)
    d._study('7',{'id':'exam','deck_id':2});Op.queued[-1].complete(col)
    assert not moves and len(NativeOp.queued)==1
    NativeOp.queued[-1].complete(col)
    assert selected==[2] and moves==['review'] and d.closed


def test_parent_start_here_routes_to_exact_focus_not_browser(integration,monkeypatch):
    c,d,col,selected,moves=setup_study(integration,monkeypatch);calls=[]
    monkeypatch.setattr(d,'_launch_focus',lambda *a:calls.append(a) or {'started':True})
    d._study('7',{'id':'exam','deck_id':1});Op.queued[-1].complete(col)
    assert len(calls)==1 and not moves and not NativeOp.queued


def test_profile_switch_cancels_queued_native_start(integration,monkeypatch):
    c,d,col,selected,moves=setup_study(integration,monkeypatch)
    d._study('7',{'id':'exam','deck_id':2});Op.queued[-1].complete(col)
    c.profile_close();NativeOp.queued[-1].complete(col)
    assert not moves and not selected


def test_empty_misses_are_inline_not_cid_zero_browser(integration,monkeypatch):
    c,d,col,selected,moves=setup_study(integration,monkeypatch)
    s=PracticeSession('exam',[CardInfo(1,1,1)]);s.submit();s.grade(1);r=s.result();c.store.add_result(r)
    sent=[];monkeypatch.setattr(d,'send',lambda *a,**k:sent.append((a,k)))
    d._review_misses('8',{'id':'exam','result_id':r['id']})
    assert sent[-1][0][1]['empty'] is True and not d.closed


def test_old_browser_misses_action_is_redirected(integration,monkeypatch):
    c,d,col,selected,moves=setup_study(integration,monkeypatch);calls=[]
    monkeypatch.setattr(d,'_review_misses',lambda *a:calls.append(a))
    d._browse('9',{'id':'exam','missed_result':'old'})
    assert calls==[('9',{'id':'exam','result_id':'old'})]


def load_runner_stub(monkeypatch,integration):
    import importlib.util
    from pathlib import Path
    qt=sys.modules['aqt.qt']
    for name in ['QSplitter','QProgressBar','QPlainTextEdit','QShortcut','QKeySequence','QComboBox']:
        monkeypatch.setattr(qt,name,object,raising=False)
    modules={
        'aqt.browser':{},
        'aqt.browser.previewer':{'Previewer':object},
        'aqt.sound':{'av_player':SimpleNamespace(stop_and_clear_queue=lambda:None)},
    }
    for name,attrs in modules.items():
        mod=ModuleType(name);mod.__dict__.update(attrs);monkeypatch.setitem(sys.modules,name,mod)
    monkeypatch.setattr(sys.modules['aqt.webview'],'AnkiWebViewKind',SimpleNamespace(PREVIEWER=1),raising=False)
    path=Path(__file__).resolve().parents[1]/'addon/runner.py'
    spec=importlib.util.spec_from_file_location('addon.runner_contract',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def make_runner(mod,ready=True):
    obj=mod.ExamRunner.__new__(mod.ExamRunner)
    obj.session=PracticeSession('exam',[CardInfo(1,1,1)],'practice');obj.session.save_response('original response')
    obj.finished_once=False;obj.forced=True;obj._open=True;obj._ui_ready=ready;obj.cancel_timer=lambda:None
    obj._web=None;obj._pip_web=None
    return obj


def test_native_close_retains_response_then_clears_memory(integration,monkeypatch):
    from test_window_contract import Event
    mod=load_runner_stub(monkeypatch,integration);obj=make_runner(mod);results=[];obj.callback=results.append;e=Event()
    obj.closeEvent(e)
    assert e.accepted and results[0]['_responses']=={1:'original response'} and obj.session.responses=={}


def test_native_cleanup_failure_cannot_trap_window(integration,monkeypatch):
    from test_window_contract import Event
    mod=load_runner_stub(monkeypatch,integration);obj=make_runner(mod);results=[];obj.callback=results.append;e=Event()
    def fail():raise RuntimeError('synthetic cleanup failure')
    obj._web=SimpleNamespace(cleanup=fail)
    obj.closeEvent(e)
    assert e.accepted and obj._web is None and len(results)==1


def test_failed_session_initialization_does_not_create_history(integration,monkeypatch):
    from test_window_contract import Event
    mod=load_runner_stub(monkeypatch,integration);obj=make_runner(mod,ready=False);results=[];obj.callback=results.append;e=Event()
    obj.closeEvent(e)
    assert e.accepted and not results

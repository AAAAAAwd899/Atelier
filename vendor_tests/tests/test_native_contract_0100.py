"""Explicit Anki/Qt doubles for new write-boundary and controller routing."""
from types import SimpleNamespace,ModuleType
from pathlib import Path
import sys,json,inspect
import pytest
from test_window_contract import integration,Op,Widget
from test_release_094 import load_runner_stub,setup_study
from test_exam_engine_0100 import FakeCollection,fixture,session,native_enum
from addon.core import Exam,CardInfo
from addon.new_learning import fingerprint
from addon.drafts import save_draft,load_draft

class WriteOp:
    queued=[]
    def __init__(self,*,parent,op):self.op=op
    def success(self,fn):self.ok=fn;return self
    def failure(self,fn):self.fail=fn;return self
    def run_in_background(self,**kw):self.queued.append(self)
    def complete(self,col):
        try:r=self.op(col)
        except Exception as ex:self.fail(ex)
        else:self.ok(r)

class Control:
    def __init__(self):self.enabled=True;self.text=''
    def setEnabled(self,v):self.enabled=v
    def setText(self,v):self.text=v

def make_native(integration,monkeypatch):
    mod=load_runner_stub(monkeypatch,integration)
    col=FakeCollection();c=integration.c;c.mw.col=col
    obj=mod.ExamRunner.__new__(mod.ExamRunner)
    obj.controller=c;obj.mw=c.mw;obj.epoch=c.epoch;obj._collection=col;obj.exam=fixture(1,1)[0]
    obj.session=session(2,kind='practice',new=True);obj.session.pip_study=True;obj.session.allow_new_learning=True
    obj.session.enter();obj.session.reveal()
    obj._learning_busy=False;obj._render_error=False;obj.finished_once=False;obj._learning_expected=fingerprint(col.card)
    obj.learning_buttons=[Control() for _ in range(4)]
    obj.save_close=Control();obj.skip_button=Control();obj.primary=Control();obj.explainer=Control()
    obj._show_current=lambda:None;obj._update_exam_controls=lambda:None
    WriteOp.queued=[];monkeypatch.setattr(sys.modules['aqt.operations'],'CollectionOp',WriteOp,raising=False)
    return obj,col

def test_write_button_double_click_queues_once(integration,monkeypatch,native_enum):
    r,col=make_native(integration,monkeypatch)
    r._schedule_rating(3);r._schedule_rating(3)
    assert len(WriteOp.queued)==1 and r._learning_busy and not r.skip_button.enabled
    WriteOp.queued[0].complete(col)
    assert len(col.calls)==1 and r.session.index==1 and r.session.scheduled=={1} and not r._learning_busy

def test_profile_change_before_write_does_not_touch_any_collection(integration,monkeypatch,native_enum):
    r,col=make_native(integration,monkeypatch);r._schedule_rating(3);r.controller.epoch+=1
    WriteOp.queued[0].complete(col)
    assert not col.calls and r.session.index==0

def test_background_write_rejects_another_collection(integration,monkeypatch,native_enum):
    r,col=make_native(integration,monkeypatch);r._schedule_rating(3);other=FakeCollection()
    WriteOp.queued[0].complete(other);assert not other.calls and not col.calls

def test_failed_write_never_advances_or_creates_success(integration,monkeypatch,native_enum):
    r,col=make_native(integration,monkeypatch);r._schedule_rating(3);col.card.mod+=1
    WriteOp.queued[0].complete(col)
    assert not col.calls and not r.session.scheduled and not r.session.grades and r.session.index==0
    assert 'changed' in r.explainer.text and r.skip_button.enabled

@pytest.mark.parametrize('attr,value',[('pip_study',False),('allow_new_learning',False),('kind','exam'),('revealed',False)])
def test_independent_exam_or_unconsented_session_cannot_write(integration,monkeypatch,native_enum,attr,value):
    r,col=make_native(integration,monkeypatch);setattr(r.session,attr,value)
    r._schedule_rating(3);assert not WriteOp.queued and not col.calls

def test_previously_failed_render_never_schedules(integration,monkeypatch,native_enum):
    r,col=make_native(integration,monkeypatch);r.session.render_errors.add(1)
    r._schedule_rating(3);assert not WriteOp.queued and not col.calls

def test_timer_cannot_submit_during_native_operation(integration,monkeypatch,native_enum):
    r,col=make_native(integration,monkeypatch);r._open=True;r._learning_busy=True
    r._tick();assert r.session.phase=='practice'

def test_native_effort_hook_is_failure_isolated(integration):
    c=integration.c;c.after_native_answer(None,object(),3)
    assert c.store is not None

def test_native_answer_invalidates_stale_exam_preview(integration):
    c=integration.c;c.open();c.dialog.pending_sample='sample';c.after_native_answer(None,SimpleNamespace(nid=123),3)
    assert c.dialog.pending_sample is None and c.pip_signal()['points']==1

class RunnerDouble:
    def __init__(self,controller,exam,cards,kind,minutes,finished):
        from addon.exam_session import ExamSession
        self.session=ExamSession(exam.id,cards,kind,minutes);self.callback=finished;self.opened=False
    def open(self):self.opened=True
    def force_close(self):self.opened=False

def test_pip_study_distinct_route_includes_adaptive_and_explicit_learning(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch)
    col.conn.execute('ALTER TABLE revlog ADD COLUMN lastIvl INTEGER DEFAULT 2')
    col._backend=SimpleNamespace(grade_now=lambda **kw:None)
    d.hide=lambda:None
    mod=ModuleType('addon.runner');mod.ExamRunner=RunnerDouble;monkeypatch.setitem(sys.modules,'addon.runner',mod)
    d._pip_study('1',{'id':'exam','size':2,'teach_new':True});Op.queued[-1].complete(col)
    assert c.runner.opened and c.runner.session.pip_study and c.runner.session.allow_new_learning
    assert c.runner.session.sampling=='adaptive'

def test_independent_mock_configuration_cannot_enable_new_learning(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch)
    col.conn.execute('ALTER TABLE revlog ADD COLUMN lastIvl INTEGER DEFAULT 2');d.hide=lambda:None
    mod=ModuleType('addon.runner');mod.ExamRunner=RunnerDouble;monkeypatch.setitem(sys.modules,'addon.runner',mod)
    d._prepare('1',{'id':'exam','size':2,'kind':'exam','teach_new':True,'strategy':'representative'})
    Op.queued[-1].complete(col);token=d.pending_sample[0];d._start('2',{'token':token})
    assert not c.runner.session.allow_new_learning and not c.runner.session.pip_study

def test_resume_uses_original_order_and_privately_saved_answers(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch);d.hide=lambda:None
    s=session();s.exam_id='exam';s.enter();s.save_response('Saved answer');s.go(1);save_draft(c.store,s)
    col.find_cards=lambda q:[1,2,3]
    mod=ModuleType('addon.runner');mod.ExamRunner=RunnerDouble;monkeypatch.setitem(sys.modules,'addon.runner',mod)
    d._resume_exam('3');Op.queued[-1].complete(col)
    assert c.runner.session.id==s.id and c.runner.session.responses[1]=='Saved answer' and c.runner.session.index==1

def test_deleted_card_cannot_silently_shrink_resumed_exam(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch);s=session();s.exam_id='exam';save_draft(c.store,s)
    col.find_cards=lambda q:[1,2]
    d._resume_exam('3');Op.queued[-1].complete(col)
    assert c.runner is None and load_draft(c.store).id==s.id

def test_learning_api_absent_fails_before_opening(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch)
    with pytest.raises(ValueError,match='unavailable'):d._pip_study('1',{'id':'exam','teach_new':True})
    assert c.runner is None

def test_delete_exam_removes_explicit_draft_and_keeps_pip_effort(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch);s=session();s.exam_id='exam';save_draft(c.store,s)
    c.record_effort([1,2]);d.bridge('exam-sprout:'+json.dumps({'id':'7','action':'delete_exam','payload':{'id':'exam'}}))
    assert load_draft(c.store) is None and c.pip_signal()['points']==2

def test_grade_now_call_exists_only_in_guarded_adapter():
    root=Path(__file__).resolve().parents[1]/'addon'
    files=[p.name for p in root.glob('*.py') if '._backend.grade_now(' in p.read_text()]
    assert files==['new_learning.py']

def test_installer_uses_cross_folder_singleton(integration,monkeypatch):
    mod=integration.module if hasattr(integration,'module') else None
    # The project source is verified independently of fake module naming.
    text=(Path(__file__).resolve().parents[1]/'addon/integration.py').read_text()
    assert 'getattr(aqt.mw, "_exam_sprout_controller", None)' in text
    assert 'aqt.mw._exam_sprout_controller = controller' in text

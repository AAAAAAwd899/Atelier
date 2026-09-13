"""Quiet-review policy and native control-tree contracts, with explicit Qt doubles.

These execute the shipped GUI builder, runner methods and ExamSession. They are
not native Qt layout/DPI or Windows scheduler tests.
"""
import inspect, json, sys, time
from types import SimpleNamespace as NS
import pytest
from addon.core import CardInfo, Exam
from addon.exam_session import ExamSession
from addon.review_ui import review_view, keyboard_actions
from test_window_contract import integration
from test_release_094 import load_runner_stub


def session(kind='practice', count=3):
    return ExamSession('exam',[CardInfo(i,i,10,is_new=True) for i in range(1,count+1)],kind,0)

@pytest.mark.parametrize('kind', ['practice','exam'])
@pytest.mark.parametrize('native', [False,True])
def test_front_view_has_one_honest_primary_action(kind,native):
    s=session(kind);v=review_view(s,native_new=native)
    assert v.grades=='none'
    if kind=='exam':assert v.primary=='Answered · next' and 'hidden' in v.mode
    elif native:assert 'updates Anki' in v.mode and v.primary=='Show answer'
    else:assert 'no rescheduling' in v.mode and v.primary=='Show answer'

@pytest.mark.parametrize('native,expected',[(False,'practice'),(True,'learning')])
def test_answered_practice_uses_distinct_marking_sets(native,expected):
    s=session();s.reveal();v=review_view(s,native_new=native)
    assert v.grades==expected
    keys=keyboard_actions(s,native_new=native)
    assert ' ' not in keys  # never invent a Good from another Space press
    assert ('4' in keys)==native
    assert keys['1']==('learn:1' if native else 'grade:0')

@pytest.mark.parametrize('native',[False,True])
def test_failed_card_cannot_have_grade_keys(native):
    s=session();s.reveal()
    assert keyboard_actions(s,native_new=native,render_error=True)=={'t':'tools'}
    assert review_view(s,native_new=native,render_error=True).grades=='none'

def test_unanswered_mock_cannot_get_positive_credit_by_key():
    s=session('exam');s.submit()
    assert keyboard_actions(s)=={'t':'tools','1':'grade:0'}
    s.attempted.add(1)
    assert keyboard_actions(s)['3']=='grade:1'

def test_mistake_keys_never_grade():
    s=session()
    assert set(keyboard_actions(s,mistake=True).values())=={'tools','primary','previous','skip'}
    assert review_view(s,mistake=True,answer_visible=True).primary=='Hide answer'

@pytest.mark.parametrize('phase',['answering','practice','grading','finished'])
def test_busy_session_has_no_keyboard_dispatch(phase):
    s=session();s.phase=phase
    assert keyboard_actions(s,busy=True)=={}

# Small strict widget stand-ins. Parent/visibility semantics exercise whether
# optional controls are really descendants of the click-open popup.
class Signal:
    def __init__(self):self.handlers=[]
    def connect(self,f):self.handlers.append(f)
    def emit(self,*a):
        for f in list(self.handlers):f(*a)
class Rect:
    def width(self):return 1366
    def height(self):return 768
    def left(self):return 0
    def right(self):return 1365
    def top(self):return 0
    def bottom(self):return 767
class Point:
    def __init__(self,x,y):self.xy=(x,y)
    def x(self):return self.xy[0]
    def y(self):return self.xy[1]
class W:
    focused=None
    def __init__(self,*args,**kwargs):
        self.parent=args[-1] if args and isinstance(args[-1],W) else None
        self.text=args[0] if args and isinstance(args[0],str) else ''
        self.children=[];self.hidden=False;self.enabled=True;self.props={};self.name=''
        self.clicked=Signal();self.activated=Signal();self.textChanged=Signal()
        self.blocked=False;self.width_value=1100;self.height_value=800;self.readonly=False
        if self.parent:self.parent.children.append(self)
    def setObjectName(self,v):self.name=v
    def setWindowTitle(self,v):self.title=v
    def setStyleSheet(self,v):self.sheet=v
    def setTextFormat(self,*a):pass
    def setWordWrap(self,*a):pass
    def setAlignment(self,*a):pass
    def setAccessibleName(self,v):self.accessible=v
    def setToolTip(self,v):self.tooltip=v
    def setText(self,v):self.text=v
    def setProperty(self,k,v):self.props[k]=v
    def setAutoDefault(self,v):self.auto_default=v
    def setFocusPolicy(self,v):self.focus_policy=v
    def setCheckable(self,v):self.checkable=v
    def setChecked(self,v):self.checked=v
    def setEnabled(self,v):self.enabled=v
    def setVisible(self,v):self.hidden=not v
    def hide(self):self.hidden=True
    def show(self):self.hidden=False
    def raise_(self):pass
    def setFocus(self):W.focused=self
    def isVisible(self):return not self.hidden and (self.parent is None or self.parent.isVisible())
    def setMinimumWidth(self,v):self.min_width=v
    def setMaximumWidth(self,v):self.max_width=v
    def setMinimumHeight(self,v):self.min_height=v
    def setMaximumHeight(self,v):self.max_height=v
    def setFixedWidth(self,v):self.width_value=v
    def setRange(self,*a):self.range=a
    def setTextVisible(self,v):self.textvisible=v
    def setValue(self,v):self.value=v
    def blockSignals(self,v):self.blocked=v
    def setPlainText(self,v):
        self.text=v
        if not self.blocked:self.textChanged.emit()
    def toPlainText(self):return self.text
    def setReadOnly(self,v):self.readonly=v
    def setPlaceholderText(self,v):self.placeholder=v
    def clear(self):self.items=[]
    def addItem(self,v):
        if not hasattr(self,'items'):self.items=[]
        self.items.append(v)
    def setCurrentIndex(self,v):self.index=v
    def setOrientation(self,v):self.orientation=v
    def setStretchFactor(self,*a):pass
    def setSizes(self,v):self.sizes=v
    def addWidget(self,w):
        if w.parent and w in w.parent.children:w.parent.children.remove(w)
        w.parent=self;self.children.append(w)
    def setWidgetResizable(self,*a):pass
    def setFrameShape(self,*a):pass
    def setWidget(self,w):self.addWidget(w)
    def width(self):return self.width_value
    def height(self):return self.height_value
    def resize(self,w,h):self.width_value=w;self.height_value=h
    def move(self,x,y):self.position=(x,y)
    def screen(self):return NS(availableGeometry=Rect)
    def mapToGlobal(self,p):return Point(10,720)
    def close(self):self.hide()
    def descendants(self):
        return [x for c in self.children for x in [c,*c.descendants()]]
class Dialog(W):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.hidden=True
    def hideEvent(self,e):pass
class Layout:
    def __init__(self,*args):self.items=[];self.parent=args[0] if args else None
    def setContentsMargins(self,*a):self.margins=a
    def setSpacing(self,v):self.spacing=v
    def addWidget(self,w,*a):self.items.append(w)
    def addStretch(self,*a):pass
    def addLayout(self,l):self.items.append(l)
class Web(W):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.scripts=[];self.zoom=1.0
    def eval(self,s):self.scripts.append(s)
    def setZoomFactor(self,v):self.zoom=v
    def zoomFactor(self):return self.zoom
    def cleanup(self):self.cleaned=True
    def evalWithCallback(self,code,cb):self.measurement_callback=cb
    def isAncestorOf(self,w):return w in self.descendants()

@pytest.fixture
def runner(integration,monkeypatch):
    m=load_runner_stub(monkeypatch,integration)
    qt=sys.modules['aqt.qt']
    for name in ['QWidget','QLabel','QPushButton','QProgressBar','QComboBox','QSplitter','QPlainTextEdit','QScrollArea']:
        monkeypatch.setattr(qt,name,W,raising=False)
    monkeypatch.setattr(qt,'QDialog',Dialog)
    for name,obj in {'QFrame':NS(Shape=NS(NoFrame=0)), 'QSizePolicy':object,'QPoint':Point,'QVBoxLayout':Layout,'QHBoxLayout':Layout}.items():
        monkeypatch.setattr(qt,name,obj,raising=False)
    qt.Qt=NS(TextFormat=NS(PlainText=0),AlignmentFlag=NS(AlignCenter=0),Orientation=NS(Horizontal=0,Vertical=1),WindowType=NS(Popup=1),FocusPolicy=NS(TabFocus=1))
    m.Qt=qt.Qt
    for name in ['QWidget','QLabel','QPushButton','QComboBox','QPlainTextEdit']:setattr(m,name,W)
    monkeypatch.setattr(sys.modules['aqt.webview'],'AnkiWebView',Web)
    monkeypatch.setattr(sys.modules['aqt'],'gui_hooks',NS(card_review_webview_did_init=lambda *a:None))
    # Production runner behavior, with stand-in base QWidget methods.
    class R(m.ExamRunner,W):pass
    r=R.__new__(R);W.__init__(r)
    c=integration.c;c.store.state['settings']['show_pip']=False;c.growth_cache={};c.suite=object()
    r.controller=c;r.mw=c.mw;r.epoch=c.epoch;r._collection=c.mw.col
    r.exam=NS(id='exam',name='Example exam')
    r.session=session();r._learning_busy=False;r.finished_once=False;r.forced=False
    r._open=True;r._ui_ready=True;r.item_prompts={};r._key_script=None
    r.render_card=lambda:None;r.card=lambda:NS(question=lambda:'Question')
    r._create_gui();r._show_current()
    return r,m

def visible_text(r):
    return [w.text for w in r.descendants() if w.isVisible() and getattr(w,'text','')]

def test_actual_builder_hides_all_extras_initially(runner):
    r,m=runner
    assert not r.tools_panel.isVisible() and not r.side.isVisible()
    assert r.primary.isVisible() and r.primary.text=='Show answer'
    for field in [r.save_close,r.attempt_button,r.confidence_control,r.error_control,r.flag,r.replay,r.fit_button,r.safety,r.explainer]:
        assert not field.isVisible()
    assert r.tools_button.isVisible() and r.mode_label.text=='Practice · no rescheduling'
    assert r.heading.text=='1 / 3' and not r.clock.isVisible()
    assert not r.progress_bar.isVisible()

def test_tools_open_only_after_click_and_close_without_leaving_card(runner):
    r,m=runner;cid=r.session.current.id
    r._toggle_tools()
    assert r.tools_panel.isVisible() and r.save_close.isVisible()
    assert r.save_close.text=='Save and close' and r.flag.text=='Bookmark question'
    assert r.tools_panel.position[0]>=0 and r.tools_panel.position[1]>=0
    r.reject()
    assert not r.tools_panel.isVisible() and r.session.current.id==cid and r._open

def test_plain_practice_reveal_then_selfmark_no_schedule(runner):
    r,m=runner;r._advance_primary()
    assert r.session.revealed and not r.primary.isVisible()
    assert [b.text for b in r.grade_buttons if b.isVisible()]==['Missed','Partial','Correct']
    assert not any(b.isVisible() for b in r.learning_buttons)
    r._allow_grade_at=0;r._grade(1)
    assert r.session.index==1 and r.session.grades=={1:1} and not r.session.scheduled

def test_new_learning_shows_only_real_anki_rating_labels(runner,monkeypatch):
    r,m=runner;r.session.pip_study=True;r.session.allow_new_learning=True
    monkeypatch.setattr(m,'fingerprint',lambda c:'expected')
    r._show_current();assert r.mode_label.text=='New card · updates Anki'
    r._advance_primary()
    assert [b.text for b in r.learning_buttons if b.isVisible()]==['Again','Hard','Good','Easy']
    assert not any(b.isVisible() for b in r.grade_buttons)
    assert not r.session.scheduled

def test_mock_answered_next_is_explicit_attempt_not_grade(runner):
    r,m=runner;r.session=session('exam');r._show_current()
    assert r.primary.text=='Answered · next' and r.skip_button.isVisible()
    assert not r.attempt_button.isVisible() # hidden with the entire Tools popup
    r._advance_primary()
    assert r.session.index==1 and r.session.attempted=={1} and not r.session.grades
    r._skip();assert r.session.index==2 and 2 not in r.session.attempted

@pytest.mark.parametrize('confirm',[False,True])
def test_last_question_is_not_marked_if_submission_cancelled(runner,monkeypatch,confirm):
    r,m=runner;r.session=session('exam',1);r._show_current()
    monkeypatch.setattr(m,'askUser',lambda *a,**k:confirm)
    r._advance_primary()
    assert (1 in r.session.attempted)==confirm
    assert r.session.phase==('grading' if confirm else 'answering')

def test_typing_panel_is_explicit_retained_and_closes_first_on_escape(runner):
    r,m=runner;r._toggle_tools();r._run_tool(r._toggle_side)
    assert not r.tools_panel.isVisible() and r.side.isVisible()
    r.response.setPlainText('An answer with spaces and 1 2 3')
    r.reject()
    assert not r.side.isVisible() and r.session.responses[1]=='An answer with spaces and 1 2 3'
    assert r._open and not r.session.grades

def test_small_window_moves_opt_in_answer_panel_below_card(runner):
    r,m=runner;r.width_value=640;r._layout_answer_panel()
    assert r.split.orientation==m.Qt.Orientation.Vertical and r.side.max_height==220
    r.width_value=1100;r._layout_answer_panel()
    assert r.split.orientation==m.Qt.Orientation.Horizontal and r.side.max_width==340
    assert not r.side.isVisible()

def test_unanswered_result_explanation_is_not_hidden_in_tools(runner):
    r,m=runner;r.session=session('exam');r.session.submit();r._show_current()
    assert r.notice.isVisible() and 'unanswered' in r.notice.text
    assert not r.grade_buttons[1].enabled and not r.grade_buttons[2].enabled

def test_stale_popup_command_does_not_apply_to_another_question(runner):
    r,m=runner;r._toggle_tools();old=r._tools_token
    r._advance_primary();assert r._key_token!=old
    r._run_tool(r._skip)
    assert r.session.index==0

@pytest.mark.parametrize('cause',['epoch','collection','busy','closed'])
def test_key_dispatch_is_noop_for_invalid_session(runner,cause):
    r,m=runner
    if cause=='epoch':r.epoch-=1
    if cause=='collection':r._collection=object()
    if cause=='busy':r._learning_busy=True
    if cause=='closed':r._open=False
    r._dispatch_review_key(' ')
    assert not r.session.revealed and not r.session.grades

def test_open_tools_cannot_receive_card_grade_keys(runner):
    r,m=runner;r._advance_primary();r._allow_grade_at=0;r._toggle_tools()
    r._dispatch_review_key('3')
    assert r.session.index==0 and not r.session.grades

def test_bridge_refuses_old_token_and_non_allowlisted_command(runner):
    r,m=runner;old=r._key_token
    r._on_bridge_cmd('atelier-review-key:'+json.dumps({'token':old,'key':' '}))
    assert r.session.revealed
    r._allow_grade_at=0
    r._on_bridge_cmd('atelier-review-key:'+json.dumps({'token':old,'key':'3'}))
    r._on_bridge_cmd('atelier-review-key:'+json.dumps({'token':r._key_token,'key':'eval'}))
    assert not r.session.grades

@pytest.mark.parametrize('message',['[]','null','"text"','{','{"key":3}','{"token":"","key":"3"}'])
def test_malformed_bridge_requests_are_ignored(runner,message):
    r,m=runner;r._on_bridge_cmd('atelier-review-key:'+message)
    assert not r.session.revealed

def test_refresh_does_not_move_masks_or_rebuild_native_card(runner):
    r,m=runner;calls=[];r.render_card=lambda:calls.append(1)
    r._refresh_quiet();r._toggle_tools();r._close_tools()
    assert not calls and r._web.zoomFactor()==1.0

def test_reset_zoom_changes_only_whole_document_zoom(runner):
    r,m=runner;r._web.setZoomFactor(.55);r._reset_zoom()
    assert r._web.zoomFactor()==1.0 and not r.session.grades

def test_caption_update_keeps_native_button_guard(runner):
    r,m=runner
    assert all(not b.auto_default for b in [r.primary,*r.grade_buttons,*r.learning_buttons])
    assert list(inspect.signature(m.ExamRunner.resizeEvent).parameters)==['self','event']
    assert 'event' not in m.ExamRunner.__dict__

def test_mistake_review_starts_closed_but_retains_original_answer(runner):
    r,m=runner
    class M(m.MistakeReview,W):pass
    v=M.__new__(M);W.__init__(v)
    for key in ['controller','mw','epoch','_collection','exam']:
        setattr(v,key,getattr(r,key))
    v.session=session();v._learning_busy=False;v.finished_once=False;v._open=True
    v._ui_ready=True;v.item_prompts={};v._key_script=None;v.forced=False
    v.items=[{'grade':0},{'grade':.5},{'grade':1}];v.saved_answers={'1':'My original response'}
    v.answer_visible=False;v.review_finished=lambda:None
    v.render_card=lambda:None
    v._create_gui();v._show_current()
    assert not v.side.isVisible() and not v.tools_panel.isVisible()
    assert v.response.text=='My original response' and v.response.readonly
    assert v.mode_label.text=='Mistake review · no changes'
    assert not any(x.isVisible() for x in v.learning_buttons+v.grade_buttons)
    before=v.session.serialize()
    v._toggle_side();assert v.side.isVisible()
    v._primary();assert v.primary.text=='Hide answer'
    assert v.session.serialize()['grades']==before['grades']
    assert not v.session.scheduled


def test_timed_mock_submission_closes_tools_and_preserves_prose(runner):
    r,m=runner;r.session=session('exam');r.session.minutes=1;r._show_current()
    r._toggle_side();r.response.setPlainText('My answer before timeout');r._toggle_tools()
    r.session.remaining_seconds=lambda: 0 if r.session.phase=='answering' else None
    r._tick()
    assert r.session.phase=='grading' and not r.tools_panel.isVisible()
    assert r.session.responses[1]=='My answer before timeout' and r.response.readonly


def test_bad_ui_callback_cannot_grade_a_stale_new_card(runner,monkeypatch):
    r,m=runner;r.session.pip_study=True;r.session.allow_new_learning=True
    monkeypatch.setattr(m,'fingerprint',lambda c:'expected')
    r._show_current();r._advance_primary()
    r._allow_grade_at=time.monotonic()+3
    r._schedule_rating(3)
    assert not r._learning_busy and not r.session.scheduled


def test_simplified_confidence_keeps_original_evidence_values(runner):
    r,m=runner;r._toggle_tools();r._confidence(3)
    assert r.session.confidence=={1:3} and not r.session.grades
    r._close_tools();r._confidence(1)
    assert r.session.confidence=={1:3} # stale hidden dropdown cannot change it

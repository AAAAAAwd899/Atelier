"""Window integration contract tests with strict Qt/Anki test doubles.

NOT native Anki/Qt tests. The stand-in delivers the inherited `event(QEvent)`
contract during construction, resize, show and close, which catches 0.9.1's
fatal accidental override (missed by the earlier browser-only tests).
"""
import ast
import importlib.util
import json
import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import pytest
from addon.storage import Store
from addon.diagnostics import LocalDiagnostics, LOG

ROOT = Path(__file__).resolve().parents[1]

class Signal:
    def __init__(self): self.functions=[]
    def connect(self, fn): self.functions.append(fn)
    def emit(self, *args):
        for fn in self.functions: fn(*args)

class Event:
    def __init__(self): self.accepted=None
    def accept(self): self.accepted=True
    def ignore(self): self.accepted=False

class Widget:
    def __init__(self, *args, **kwargs):
        self.events=0; self.visible=False; self.clicked=Signal(); self.triggered=Signal()
        self.text=args[0] if args and isinstance(args[0],str) else ''
        self.event(Event())
    def event(self, event): self.events += 1; return True
    def setAttribute(self,*a): self.event(Event())
    def setWindowTitle(self,*a): self.event(Event())
    def resize(self,*a): self.event(Event())
    def setMinimumSize(self,*a): self.event(Event())
    def setWindowModality(self,*a): self.event(Event())
    def show(self): self.event(Event()); self.visible=True
    def raise_(self): self.event(Event())
    def activateWindow(self): self.event(Event())
    def setWordWrap(self,*a): pass
    def setAutoDefault(self,*a): pass
    def setEnabled(self,value): self.enabled=value
    def setText(self,text): self.text=text
    def close(self):
        self.event(Event()); event=Event(); self.closeEvent(event)
        if event.accepted: self.visible=False
        return event.accepted

class Layout:
    def __init__(self,*args): self.widgets=[]
    def setContentsMargins(self,*args): pass
    def setSpacing(self,*args): pass
    def addWidget(self,widget,*args): self.widgets.append(widget)
    def addStretch(self,*args): pass
    def insertWidget(self,pos,widget,*args): self.widgets.insert(pos,widget)

class Timer:
    def __init__(self,*args): self.timeout=Signal(); self.running=False
    def setSingleShot(self,*args): pass
    def start(self,*args): self.running=True
    def stop(self): self.running=False

class Web(Widget):
    fail_load=False; fail_cleanup=False; fail_eval=False; load_callback=None
    def __init__(self,*args): super().__init__(*args); self.loadFinished=Signal(); self.scripts=[]; self.cleaned=False
    def set_bridge_command(self,handler,context): self.handler=handler
    def stdHtml(self,*args,**kwargs):
        if self.fail_load: raise RuntimeError('synthetic page load failure')
        self.content=(args,kwargs)
        if type(self).load_callback: type(self).load_callback()
    def eval(self,script):
        if self.fail_eval: raise RuntimeError('synthetic deleted webview')
        self.scripts.append(script)
    def cleanup(self):
        self.cleaned=True
        if self.fail_cleanup: raise RuntimeError('synthetic cleanup failure')

class Op:
    queued=[]
    def __init__(self,*,parent,op,success): self.parent=parent; self.op=op; self.success=success
    def failure(self,fn): self.failure_fn=fn; return self
    def run_in_background(self): type(self).queued.append(self)
    def complete(self,col):
        try: result=self.op(col)
        except Exception as e: self.failure_fn(e)
        else: self.success(result)

@pytest.fixture
def integration(monkeypatch,tmp_path):
    hooks=SimpleNamespace(**{name:[] for name in ('profile_did_open','profile_will_close','collection_will_temporarily_close','deck_browser_will_render_content','deck_browser_did_render','webview_will_set_content','webview_did_receive_js_message','top_toolbar_did_init_links')})
    class DeckBrowser:
        def __init__(self): self.web=Web(); self.refreshes=0
        def refresh(self): self.refreshes+=1
    notifications=[]; menu=[]; paints=[]
    mw=SimpleNamespace(col=object(),state='deckBrowser',pm=SimpleNamespace(profileFolder=lambda:str(tmp_path)),
        addonManager=SimpleNamespace(addonFromModule=lambda _: 'exam_sprout',setWebExports=lambda *a:None),
        form=SimpleNamespace(menuTools=SimpleNamespace(addAction=menu.append)),deckBrowser=DeckBrowser(),
        toolbar=SimpleNamespace(draw=lambda:paints.append('draw'),redraw=lambda:paints.append('redraw')))
    qt=ModuleType('aqt.qt')
    for name in ('QDialog','QWidget','QAction','QPushButton','QLabel'): setattr(qt,name,Widget)
    qt.QVBoxLayout=qt.QHBoxLayout=Layout; qt.QTimer=Timer; qt.QFileDialog=object
    qt.Qt=SimpleNamespace(WidgetAttribute=SimpleNamespace(WA_DeleteOnClose=1),WindowModality=SimpleNamespace(WindowModal=1))
    modules={'aqt':dict(mw=mw,gui_hooks=hooks),'aqt.qt':qt,'aqt.deckbrowser':dict(DeckBrowser=DeckBrowser),
             'aqt.operations':dict(QueryOp=Op),'aqt.webview':dict(AnkiWebView=Web),
             'aqt.utils':dict(askUser=lambda *a,**k:True,showWarning=lambda *a,**k:notifications.append(('modal',a)),tooltip=lambda *a,**k:notifications.append(('tooltip',a))),
             'aqt.theme':dict(theme_manager=SimpleNamespace(night_mode=True))}
    for name, values in modules.items():
        module=values if isinstance(values,ModuleType) else ModuleType(name)
        if isinstance(values,dict): module.__dict__.update(values)
        monkeypatch.setitem(sys.modules,name,module)
    spec=importlib.util.spec_from_file_location('addon.window_contract_integration',ROOT/'addon/integration.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.mw_fixture=mw; module.notifications=notifications; module.paints=paints
    Op.queued=[]; Web.fail_load=False; Web.fail_cleanup=False; Web.fail_eval=False; Web.load_callback=None
    controller=module.Controller(mw);controller.profile_open();module.c=controller
    yield module
    controller.profile_close()


def test_old_signature_reproduces_missing_payload_at_qt_event_contract():
    class Broken(Widget):
        def event(self,name,payload): pass
    with pytest.raises(TypeError,match='payload'): Broken()


def test_planner_does_not_override_qt_event_handler(integration):
    assert 'event' not in integration.PlannerDialog.__dict__
    assert integration.PlannerDialog.event is Widget.event
    integration.c.open(); d=integration.c.dialog
    assert d.events >= 6
    assert d.event(Event()) is True
    assert d.close() and d.closed and integration.c.dialog is None
    assert not integration.notifications


def test_open_repeat_resize_close_and_reopen(integration):
    for _ in range(10):
        integration.c.open(); d=integration.c.dialog
        for i in range(20):
            integration.c.open('example'); d.resize(900+i,700)
            assert integration.c.dialog is d
        assert d.close()
    assert not integration.notifications


def test_js_notifications_use_new_name_not_qt_event(integration):
    integration.c.open();d=integration.c.dialog
    d.emit_ui_event('select',{'id':'a'})
    assert 'ExamSprout.event("select"' in d.web.scripts[-1]
    assert d.event(Event()) is True


def test_reentrant_open_does_not_create_a_second_dialog(integration):
    Web.load_callback=integration.c.open
    integration.c.open(); d=integration.c.dialog
    assert d and d.visible and not integration.c._opening
    assert not integration.notifications


def test_constructor_failure_is_contained_and_guard_resets(integration,monkeypatch):
    def fail(*a): raise RuntimeError('synthetic constructor failure')
    monkeypatch.setattr(integration,'PlannerDialog',fail)
    integration.c.open()
    assert integration.c.dialog is None and not integration.c._opening
    assert all(n[0]!='modal' for n in integration.notifications)


def test_web_failure_keeps_native_controls_and_close(integration):
    Web.fail_load=True
    integration.c.open(); d=integration.c.dialog
    assert 'could not load' in d.status_label.text
    assert d.native_bar in d.layout_box.widgets and d.visible
    assert d.close()
    assert not integration.notifications


def test_failed_qt_load_signal_stops_timer_without_popup(integration):
    integration.c.open();d=integration.c.dialog
    d.web.loadFinished.emit(False)
    assert not d.open_timer.running
    assert 'could not load' in d.status_label.text
    assert not integration.notifications


def test_slow_load_uses_inline_status(integration):
    integration.c.open();d=integration.c.dialog
    d.open_timer.timeout.emit()
    assert 'Still waiting' in d.status_label.text
    assert d.close()


def test_cleanup_error_does_not_trap_close(integration):
    integration.c.open();d=integration.c.dialog;web=d.web
    Web.fail_cleanup=True
    assert d.close()
    assert d.closed and web.cleaned and integration.c.dialog is None and d.web is None
    assert not integration.notifications


def test_send_error_is_logged_not_raised(integration):
    integration.c.open();d=integration.c.dialog
    Web.fail_eval=True
    d.send('1',{})
    d.emit_ui_event('select',{})
    assert d.close()
    assert not integration.notifications


def test_query_is_parented_to_main_window_not_closed_dialog(integration):
    integration.c.open();d=integration.c.dialog
    d.query('1',lambda col:'done')
    op=Op.queued[-1]
    assert op.parent is integration.mw_fixture
    d.close(); op.complete(integration.mw_fixture.col)
    assert d.web is None and not integration.notifications


def test_old_profile_request_cannot_read_new_collection(integration):
    integration.c.open();d=integration.c.dialog; calls=[]
    d.query('1',lambda col:calls.append(col))
    integration.c.epoch += 1; integration.mw_fixture.col=object()
    Op.queued[-1].complete(integration.mw_fixture.col)
    assert not calls and not d.valid()


def test_success_response_updates_native_status(integration):
    integration.c.open();d=integration.c.dialog;d._load_rid='l'
    d.query('l',lambda col:[])
    Op.queued[-1].complete(integration.mw_fixture.col)
    assert not d.open_timer.running and 'card schedules' in d.status_label.text


def test_query_failures_do_not_spawn_progress_or_error_dialogs(integration):
    integration.c.open();d=integration.c.dialog
    def fail(col):raise ValueError('bad query')
    d.query('1',fail)
    Op.queued[-1].complete(integration.mw_fixture.col)
    assert 'bad query' in d.web.scripts[-1]
    assert not integration.notifications


def test_close_confirmation_reentrancy_is_guarded(integration,monkeypatch):
    integration.c.open();d=integration.c.dialog;d.dirty=True;calls=[]
    def ask(*a,**kw):
        calls.append(1);assert d.close() is False;return False
    monkeypatch.setattr(integration,'askUser',ask)
    assert d.close() is False
    assert calls==[1] and not d.closed
    d.forced=True;assert d.close()


def test_active_review_does_not_open_planner(integration):
    integration.mw_fixture.state='review'; integration.c.open()
    assert integration.c.dialog is None


def test_unknown_web_context_does_not_receive_assets(integration):
    for context in (None,object(),SimpleNamespace(name='reviewer'),SimpleNamespace(name='editor')):
        content=SimpleNamespace(css=[],js=[])
        integration.c.web_assets(content,context)
        assert not content.css and not content.js


def test_home_assets_idempotent(integration):
    content=SimpleNamespace(css=[],js=[])
    for _ in range(15):integration.c.web_assets(content,integration.mw_fixture.deckBrowser)
    assert len(content.css)==len(content.js)==1


def test_home_bridge_requires_current_home_context(integration):
    c=integration.c; current=integration.mw_fixture.deckBrowser
    assert c.web_message((False,None),'exam-sprout:open:a',object())==(False,None)
    assert c.web_message((True,'handled'),'exam-sprout:open:a',current)==(True,'handled')
    integration.mw_fixture.state='review'
    assert c.web_message((False,None),'exam-sprout:open:a',current)==(False,None)
    assert c.dialog is None


def test_redraw_triggers_atelier_toolbar_hook_path(integration):
    integration.c.refresh_home()
    assert integration.paints==['draw','redraw']


def test_refresh_failure_does_not_undo_saved_plan(integration,monkeypatch):
    def fail():raise RuntimeError('synthetic refresh failure')
    integration.mw_fixture.toolbar.draw=fail
    integration.c.refresh_home()
    assert not integration.notifications


def test_read_only_deck_reader_and_runner_unchanged():
    # The fix adds no new reviewer hooks, collection writes, or scheduler calls.
    source=(ROOT/'addon/integration.py').read_text()
    assert 'gui_hooks.reviewer_will_' not in source
    assert source.count('("reviewer_did_answer_card", controller.after_native_answer)') == 1
    assert '.with_progress(' not in source
    assert 'sys.excepthook' not in source
    tree=ast.parse(source)
    planner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PlannerDialog')
    assert 'event' not in [n.name for n in planner.body if isinstance(n,ast.FunctionDef)]


def test_log_isolation_no_stderr_or_root_logger(tmp_path,capsys):
    assert LOG.propagate is False
    logger=logging.Logger('local-test');sink=LocalDiagnostics();sink.use_profile(tmp_path)
    logger.addHandler(sink)
    try: raise RuntimeError('diagnostic sample')
    except RuntimeError: logger.exception('failure')
    assert 'diagnostic sample' in sink.report()
    assert not capsys.readouterr().err


def test_diagnostics_repeat_bounded_and_rotation(tmp_path):
    sink=LocalDiagnostics();sink.use_profile(tmp_path)
    for _ in range(500):sink.handle(logging.makeLogRecord({'msg':'same failure','levelno':40,'levelname':'ERROR'}))
    assert len(sink.records)==1
    for i in range(300):sink.handle(logging.makeLogRecord({'msg':f'{i}: '+('x'*1000),'levelno':40,'levelname':'ERROR'}))
    assert len(sink.records)==40
    assert sink.path.stat().st_size < 140000
    assert sink.path.with_suffix('.log.1').exists()


def test_diagnostics_file_failure_remains_in_memory(tmp_path,capsys):
    bad=tmp_path/'file';bad.write_text('not a folder')
    sink=LocalDiagnostics();sink.use_profile(bad)
    sink.handle(logging.makeLogRecord({'msg':'kept','levelno':40,'levelname':'ERROR'}))
    assert 'kept' in sink.report() and not capsys.readouterr().err


def test_upgraded_state_is_read_without_rewrite(integration):
    state=integration.c.store
    state.save_exam({'id':'original','name':'Original exam','due':'2099-09-20T09:00','scopes':[{'deck_id':1,'name':'Course'}]})
    original=state.path.read_bytes()
    integration.c.profile_open()
    assert integration.c.store.get_exam('original').name=='Original exam'
    assert integration.c.store.path.read_bytes()==original


def test_failed_window_cleanup_cannot_escape_open_guard(integration, monkeypatch):
    def bad_close(): raise RuntimeError('synthetic failed stale window cleanup')
    def fail(*a):
        integration.c.dialog=SimpleNamespace(force_close=bad_close)
        raise RuntimeError('synthetic failed window')
    monkeypatch.setattr(integration.c, '_open_planner', fail)
    integration.c.open()
    assert integration.c.dialog is None and not integration.c._opening
    assert all(n[0] != 'modal' for n in integration.notifications)

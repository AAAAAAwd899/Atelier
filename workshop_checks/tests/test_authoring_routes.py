"""Execute the suite's actual authoring install/routes with explicit Qt doubles."""
from __future__ import annotations
import importlib,sys,types
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from tests.fakes import install_stubs,FakeCollection

SRC=Path(__file__).resolve().parents[2]/'src'
class Signal:
    def __init__(self):self.handlers=[]
    def connect(self,fn):self.handlers.append(fn)
    def disconnect(self,fn):
        if fn not in self.handlers:raise TypeError('Not connected')
        self.handlers.remove(fn)
    def emit(self,*args):
        for fn in list(self.handlers):fn(*args)
class Action:
    def __init__(self,label='',*args):self.label=label;self.triggered=Signal();self.enabled=True
    def setShortcut(self,key):self.shortcut=key
    def setEnabled(self,v):self.enabled=v
class Menu:
    def __init__(self,*args):self.items=[];self._action=Action('menu')
    def addMenu(self,m):self.items.append(m.menuAction())
    def addAction(self,a,*args):
        if isinstance(a,str):a=Action(a)
        self.items.append(a);return a
    def actions(self):return self.items
    def menuAction(self):return self._action
    def removeAction(self,a):
        if a in self.items:self.items.remove(a)
    def setEnabled(self,v):pass
class Shortcut:
    def __init__(self,key,callback):self._key=key;self.activated=Signal();self.activated.connect(callback)
    def key(self):return NS(toString=lambda:self._key)
class Editor:
    def __init__(self,parent,kind='ioe',nid=7):
        self.parentWindow=parent;self.addMode=False;self.calls=[];self._links={'I/O':lambda e:self.calls.append(e)}
        fields=['Image','Question Mask','Answer Mask','Original Mask','ID (hidden)'] if kind=='ioe' else ['Front','Back']
        self.note=NS(id=nid,note_type=lambda:{'flds':[{'name':x} for x in fields]})
        self.current_notetype_is_image_occlusion=lambda:kind=='native'

@pytest.fixture
def env(tmp_path,monkeypatch):
    # New module identity for each fixture preserves actual boundary imports.
    for key in list(sys.modules):
        if key.startswith('suite_authoring_actual'):monkeypatch.delitem(sys.modules,key)
    pkg=types.ModuleType('suite_authoring_actual');pkg.__path__=[str(SRC)];monkeypatch.setitem(sys.modules,pkg.__name__,pkg)
    c=FakeCollection(tmp_path);events=[]
    mw=NS(col=c,state='deckBrowser',reviewer=NS(card=NS(nid=7)),pm=NS(profileFolder=lambda:str(tmp_path)),
          form=NS(menuTools=Menu()),toolbar=NS(),native=lambda name,kw:events.append((name,kw)),files=[],savepath='',
          addonManager=NS(addonFromModule=lambda n:'daedalus_atelier',setWebExports=lambda *a:events.append(('exports',a))))
    mw.onAddCard=lambda:events.append(('native',{}));mw.shortcuts=[Shortcut('A',mw.onAddCard),Shortcut('Ctrl+A',mw.onAddCard)]
    mw.findChildren=lambda cls:mw.shortcuts
    install_stubs(mw)
    qt=sys.modules['aqt.qt'];qt.QMenu=Menu;qt.QAction=Action;qt.QShortcut=Shortcut;qt.QKeySequence=lambda x:x
    callbacks=[];qt.QTimer.singleShot=lambda ms,fn:callbacks.append(fn)
    notices=[];sys.modules['aqt.utils'].tooltip=lambda text,**kw:notices.append(text)
    qt.Qt.WindowModality.WindowModal=1
    editcurrent=types.ModuleType('aqt.editcurrent');editcurrent.EditCurrent=type('EditCurrent',(),{})
    monkeypatch.setitem(sys.modules,'aqt.editcurrent',editcurrent)
    hooks=sys.modules['aqt.gui_hooks']
    for n in ['profile_did_open','profile_will_close','collection_will_temporarily_close','state_did_change','top_toolbar_did_init_links',
              'deck_browser_will_render_content','deck_browser_did_render','webview_will_set_content','webview_did_receive_js_message',
              'reviewer_will_show_context_menu','browser_menus_did_init','add_cards_did_add_note','editor_mask_editor_did_load_image','editor_did_load_note']:
        setattr(hooks,n,[])
    routes=importlib.import_module('suite_authoring_actual.authoring')
    life=importlib.import_module('suite_authoring_actual.lifecycle')
    owner=NS(menu=Menu());reg=life.Registration()
    yield NS(mw=mw,events=events,notices=notices,callbacks=callbacks,qt=qt,hooks=hooks,mod=routes,life=life,owner=owner,reg=reg,EditCurrent=editcurrent.EditCurrent)
    reg.rollback();c.close()

def installed(e):
    e.mod.install_authoring(e.owner,e.reg)
    return e.mw._atelier_authoring_routes

def test_real_embedded_controller_starts_with_correct_asset_root(env):
    r=installed(env);c=r.controller
    assert c.base=='/_addons/daedalus_atelier/workshop/web' and c.store.settings()['theme']=='atelier'
    assert env.mw.workshop_api_v1 is c.api and env.owner.workshop is c
    assert not any(x[0]=='exports' for x in env.events) # the suite's union export registration stays owned by suite
    assert r.editor_loaded in env.hooks.editor_did_load_note and len(env.owner.menu.items)==1

def test_real_install_rollback_removes_only_owned_registrations(env):
    foreign=lambda *a:None;env.hooks.editor_did_load_note.append(foreign)
    original=env.mw.onAddCard;r=installed(env);api=env.mw.workshop_api_v1
    env.reg.rollback()
    assert env.hooks.editor_did_load_note==[foreign] and not env.owner.menu.items
    assert env.mw.onAddCard is original and not hasattr(env.mw,'_daedalus_workshop_controller')
    assert not hasattr(env.mw,'workshop_api_v1')
    env.mw.shortcuts[0].activated.emit();assert env.events[-1][0]=='native'

def test_standalone_running_blocks_second_writer(env):
    old=NS(store='foreign');env.mw._daedalus_workshop_controller=old
    with pytest.raises(env.life.StartupBlocked):installed(env)
    assert env.mw._daedalus_workshop_controller is old and not env.owner.menu.items

def test_constructor_failure_cleans_half_menu_api(env,monkeypatch):
    integration=importlib.import_module('suite_authoring_actual.workshop.integration')
    class BadAction(Action):
        def setShortcut(self,key):raise RuntimeError('Qt destroyed')
    monkeypatch.setattr(integration,'QAction',BadAction)
    with pytest.raises(RuntimeError):installed(env)
    env.reg.rollback();assert not env.owner.menu.items and not hasattr(env.mw,'workshop_api_v1')

def test_add_and_toolbar_use_same_create_context(env):
    r=installed(env);calls=[];r.controller.open=lambda *a,**kw:calls.append((a,kw))
    env.mw.onAddCard();env.mw.shortcuts[0].activated.emit();r.message((False,None),'add',env.mw.toolbar)
    assert len(calls)==3 and all(x==(('studio',),{'allow_review':True}) for x in calls)

def test_foreign_shortcut_and_unknown_toolbar_not_intercepted(env):
    foreign=lambda:env.events.append(('foreign',{}));shortcut=Shortcut('A',foreign);env.mw.shortcuts.append(shortcut)
    r=installed(env);assert shortcut not in r._shortcuts
    assert r.message((False,None),'add',object())==(False,None)
    assert r.message((True,'owner'),'add',env.mw.toolbar)==(True,'owner')
    shortcut.activated.emit();assert env.events[-1][0]=='foreign'

def test_native_add_escape_does_not_recurse(env):
    r=installed(env);r.controller.open=lambda *a,**kw:pytest.fail('Studio must not open from native fallback')
    r.original_add();assert env.events[-1][0]=='AddCards'

def test_active_mock_blocks_creating_and_leaves_session(env):
    r=installed(env);runner=object();env.mw._exam_sprout_controller=NS(runner=runner)
    calls=[];r.controller.open=lambda *a,**kw:calls.append(a)
    r.create();assert not calls and 'practice session' in env.notices[-1] and env.mw._exam_sprout_controller.runner is runner

def test_reentrant_create_and_closed_profile_guard(env):
    r=installed(env);calls=[]
    def open(*a,**kw):calls.append(a);r.create()
    r.controller.open=open;r.create();assert len(calls)==1
    old=env.mw.col;env.mw.col=None;r.create();env.mw.col=old;assert len(calls)==1

def test_foreign_replacement_survives_dispose(env):
    r=installed(env);foreign=lambda:None;env.mw.onAddCard=foreign;r.dispose();assert env.mw.onAddCard is foreign

@pytest.mark.parametrize('kind', ['native','fields'])
def test_native_io_and_ordinary_note_not_reopened_or_converted(env,kind):
    r=installed(env);env.mw.state='review';e=Editor(env.EditCurrent(),kind);r.editor_loaded(e)
    assert not env.callbacks and not e.calls

def test_edit_current_auto_opens_ioe_once_with_original_editor(env):
    r=installed(env);env.mw.state='review';e=Editor(env.EditCurrent())
    r.editor_loaded(e);r.editor_loaded(e);assert len(env.callbacks)==1
    env.callbacks.pop()();assert e.calls==[e]
    r.editor_loaded(e);assert not env.callbacks

def test_browser_add_or_different_review_note_left_untouched(env):
    r=installed(env);env.mw.state='review'
    for e in (Editor(object()),Editor(env.EditCurrent(),nid=8)):
        r.editor_loaded(e)
    e=Editor(env.EditCurrent());e.addMode=True;r.editor_loaded(e)
    assert not env.callbacks

@pytest.mark.parametrize('change',['profile','note','dispose'])
def test_late_ioe_callback_is_stale_safe(env,change):
    r=installed(env);env.mw.state='review';e=Editor(env.EditCurrent());r.editor_loaded(e)
    if change=='profile':r.controller.epoch+=1
    elif change=='note':e.note=NS(id=8)
    else:r.dispose()
    env.callbacks.pop()();assert not e.calls

def test_missing_ioe_owner_leaves_field_editor(env):
    r=installed(env);env.mw.state='review';e=Editor(env.EditCurrent());e._links={};r.editor_loaded(e)
    assert 'Enable its owning add-on' in env.notices[-1] and not env.callbacks

def test_ioe_failure_does_not_raise_loop_or_convert(env):
    r=installed(env);env.mw.state='review';e=Editor(env.EditCurrent())
    def fail(_):raise RuntimeError('Unavailable owner')
    e._links={'I/O':fail};r.editor_loaded(e);env.callbacks.pop()()
    assert r.controller.errors and 'has not been converted' in env.notices[-1]

def test_native_modal_review_gate_real_controller_open(env,monkeypatch):
    r=installed(env);integration=importlib.import_module('suite_authoring_actual.workshop.integration');events=[]
    class Window:
        closed=False
        def __init__(self,*a):events.append('init')
        def setWindowModality(self,n):events.append(('modal',n))
        def show(self):events.append('show')
        def load(self):events.append('load')
    monkeypatch.setattr(integration,'Workspace',Window);env.mw.state='review'
    r.controller.open('studio');assert not events
    r.create();assert events==['init',('modal',1),'show','load']
    r.controller.window=None

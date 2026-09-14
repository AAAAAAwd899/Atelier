"""Unified startup, native dispatch, storage boundaries and artifact provenance.
Strict test doubles at the Qt boundary; not native Windows Anki execution.
"""
from fixtures import *
from types import SimpleNamespace as NS
import pytest, hashlib, re
from test_release import app, onigiri
from test_readiness import install_host
suite=importlib.import_module('atelier_testing.suite')
native=importlib.import_module('atelier_testing.native_tools')
life=importlib.import_module('atelier_testing.lifecycle')
Store=importlib.import_module('atelier_testing.sprout.storage').Store

@pytest.mark.parametrize('action',list(native.COMMANDS)+list(native.FORM_ACTIONS))
def test_native_tool_delegates_one_exact_original_action(action):
    calls=[];mw=NS(col=object(),form=NS())
    if action in native.COMMANDS:
        setattr(mw,native.COMMANDS[action][1][0],lambda:calls.append(action))
    else:
        setattr(mw.form,native.FORM_ACTIONS[action][0],NS(trigger=lambda:calls.append(action),isEnabled=lambda:True))
    assert native.capabilities(mw)[action]
    native.dispatch(mw,action)
    assert calls==[action]

@pytest.mark.parametrize('action',['sync','profiles','check_database'])
@pytest.mark.parametrize('obstacle',['runner','dirty'])
def test_destructive_lifecycle_route_preserves_unsaved_session(action,obstacle):
    c=NS(runner=object() if obstacle=='runner' else None,dialog=NS(dirty=obstacle=='dirty'))
    mw=NS(col=object(),_exam_sprout_controller=c)
    with pytest.raises(core.ValidationError,match='session|setup'):native.dispatch(mw,action)

@pytest.mark.parametrize('bad',[None,False,'eval','__import__','javascript:alert(1)',{},''])
def test_native_tool_rejects_non_allowlisted_actions(bad):
    with pytest.raises(core.ValidationError):native.dispatch(NS(col=object()),bad)

def test_unsupported_native_routes_do_not_claim_to_work():
    mw=NS(col=object(),form=NS())
    assert not any(native.capabilities(mw).values())
    with pytest.raises(core.ValidationError,match='original File or Tools'):native.dispatch(mw,'sync')

def test_disabled_native_action_is_respected():
    mw=NS(col=object(),form=NS(actionCheckMediaDatabase=NS(trigger=lambda:pytest.fail('disabled fired'),isEnabled=lambda:False)))
    with pytest.raises(core.ValidationError,match='disabled'):native.dispatch(mw,'check_media')

class ToolWindow:
    def __init__(self):self.sheet='/* foreign header */';self.props={};self.geometry=(0,0,1000,800)
    def styleSheet(self):return self.sheet
    def setStyleSheet(self,s):self.sheet=s
    def property(self,k):return self.props.get(k)
    def setProperty(self,k,v):self.props[k]=v

@pytest.mark.parametrize('theme',core.THEMES)
def test_native_surface_is_per_window_reversible_and_preserves_foreign_css(theme):
    cfg=core.settings({'visual_owner':'atelier','theme':theme});t=native.NativeSurfaces(NS(get_config=lambda:cfg));w=ToolWindow()
    t.opened(None,'Browser',w)
    assert review.PALETTES[theme]['panel'] in w.sheet and w.geometry==(0,0,1000,800)
    assert w.sheet.startswith('/* foreign header */')
    w.sheet+='\n/* another addon later */'
    cfg['visual_owner']='onigiri';t.refresh()
    assert native.BEGIN not in w.sheet and 'foreign header' in w.sheet and 'another addon later' in w.sheet
    assert w.property('atelier_surface') is None
    t.dispose()

def test_native_windows_fail_closed_for_unknown_windows():
    t=native.NativeSurfaces(NS(get_config=lambda:core.settings({'visual_owner':'atelier'})));w=ToolWindow()
    t.opened(None,'UnknownThirdPartyEditor',w);assert w.sheet=='/* foreign header */'

def make_plan(tmp_path,app):
    owner,mw,*_=app
    store=Store(tmp_path)
    e=store.save_exam({'id':'prepared-exam','name':'Prepared exam','due':'2026-12-12T09:00','scopes':[{'deck_id':2,'name':'School::Lecture A','weight':1,'confidence':3}]})
    c=NS(mw=mw,suite=owner,store=store,pip_signal=lambda:{'score':10,'kind':'effort'})
    mw._exam_sprout_controller=c
    return owner,mw,store,e

def test_bundle_reuses_exact_original_profile_store(tmp_path):
    store=Store(tmp_path)
    assert str(store.path).startswith(str(tmp_path/'exam_sprout'))
    store.save_exam({'id':'kept','name':'Kept name','due':'2026-12-12T09:00','scopes':[{'deck_id':2,'name':'Lecture','weight':1,'confidence':3}]})
    before=store.path.read_bytes();new=Store(tmp_path)
    assert new.get_exam('kept').name=='Kept name' and new.path.read_bytes()==before

def test_focus_plan_is_explicit_and_does_not_duplicate_or_write_engine(tmp_path,app):
    owner,mw,store,e=make_plan(tmp_path,app);before=store.path.read_bytes()
    first=suite.focus_exam(owner,e.id);second=suite.focus_exam(owner,e.id)
    assert first['study_id']==second['study_id'] and second['reused']
    assert len([x for x in owner.profile['studies'] if x['active']])==1
    assert store.path.read_bytes()==before

def test_filtered_plan_cannot_silently_broaden_to_scheduled_review(tmp_path,app):
    owner,mw,store,e=make_plan(tmp_path,app);store.save_exam({**e.to_dict(),'query':'tag:important'})
    with pytest.raises(core.ValidationError,match='filter'):suite.focus_exam(owner,e.id)
    assert not owner.profile['studies']

def test_archived_plan_cannot_be_pinned_without_reactivation(tmp_path,app):
    owner,mw,store,e=make_plan(tmp_path,app);store.save_exam({**e.to_dict(),'archived':True})
    with pytest.raises(core.ValidationError,match='Reactivate'):suite.focus_exam(owner,e.id)

def test_home_summary_reads_the_engine_not_copied_records(tmp_path,app):
    owner,mw,store,e=make_plan(tmp_path,app)
    assert suite.summary(mw)['plans'][0]['name']=='Prepared exam'
    store.save_exam({**e.to_dict(),'name':'Edited in original planner'})
    assert suite.summary(mw)['plans'][0]['name']=='Edited in original planner'

def test_no_separate_engine_is_required_when_bundled(app):
    owner,mw,*_=app;c=NS(mw=mw,suite=owner)
    mw._exam_sprout_controller=c
    link=importlib.import_module('atelier_testing.sprout_link')
    assert link.controller(mw) is c

# Source fidelity is data-driven: only four narrow adapters changed from the upload.
ORIGINAL=Path('/mnt/data/atelier_unified/sprout_original')
PY_PRESERVED=['answers.py','collection_reader.py','companion.py','companion_layout.py','core.py','diagnostics.py','drafts.py','evidence.py','exam_engine.py','exam_session.py','new_learning.py','progress.py','readiness.py','session_tools.py','storage.py','widget.py']
@pytest.mark.parametrize('filename',PY_PRESERVED)
def test_hardened_engine_module_is_unchanged(filename):
    # The source kit ships a hash manifest; original private absolute path is optional.
    expected=json.loads((ROOT/'vendor-baseline.json').read_text())['sha256'][filename]
    assert hashlib.sha256((SRC/'sprout'/filename).read_bytes()).hexdigest()==expected

def test_only_four_integration_files_changed():
    baseline=json.loads((ROOT/'vendor-baseline.json').read_text())['sha256']
    changed={n for n,h in baseline.items() if hashlib.sha256((SRC/'sprout'/n).read_bytes()).hexdigest()!=h}
    # 1.0.3 deliberately updates the suite presentation and themed Pip frame;
    # the engine modules remain covered by the exact hash assertions above.
    assert changed=={'__init__.py','integration.py','runner.py','web/app.js','web/pip.css'}
    assert all((SRC/'sprout'/n).is_file() for n in baseline)

def test_pip_animation_and_live_model_manifest_unchanged():
    baseline=json.loads((ROOT/'vendor-baseline.json').read_text())['sha256']
    for n,h in baseline.items():
        if n.startswith('web/pip') and n != 'web/pip.css':
            assert hashlib.sha256((SRC/'sprout'/n).read_bytes()).hexdigest()==h

def test_all_worlds_have_unique_original_scenery():
    worlds=json.loads((SRC/'web/worlds.json').read_text())
    assert len(worlds)==len(core.THEMES)>=12 and {w['id'] for w in worlds}==set(core.THEMES)
    assert len({hashlib.sha256((SRC/'web'/w['art']).read_bytes()).hexdigest() for w in worlds})==len(worlds)
    assert len({w['kind'] for w in worlds})==len(worlds) and len({w['radius'] for w in worlds})>=8

def merged_host(app,monkeypatch,tmp_path):
    """Real suite+engine initialization with explicit Qt widgets/Anki hooks doubles."""
    mod,hooks,filters,menus,mw=install_host(app,monkeypatch)
    # Load shared strict widget doubles without executing their fixtures.
    vendor=ROOT/'vendor_tests';sys.path.insert(0,str(vendor))
    spec=importlib.util.spec_from_file_location('vendor_window_contract',vendor/'tests/test_window_contract.py')
    doubles=importlib.util.module_from_spec(spec);spec.loader.exec_module(doubles)
    qt=sys.modules['aqt.qt']
    for name in ('QDialog','QWidget','QPushButton','QLabel','QAction','QAbstractButton','QObject','QMenu','QMovie','QPainter','QPixmap','QRect','QBuffer','QByteArray','QIODevice'):
        setattr(qt,name,doubles.Widget)
    qt.QVBoxLayout=qt.QHBoxLayout=doubles.Layout;qt.QTimer=doubles.Timer;qt.QFileDialog=object
    qt.Qt=NS(WidgetAttribute=NS(WA_DeleteOnClose=1),WindowModality=NS(WindowModal=1))
    qt.QApplication=NS(instance=lambda:None)
    for key in ('collection_will_temporarily_close','deck_browser_will_render_content','deck_browser_did_render','top_toolbar_did_init_links','reviewer_did_answer_card','dialog_manager_did_open_dialog','webview_did_inject_style_into_page'):
        setattr(hooks,key,[])
    util=sys.modules['aqt.utils'];util.askUser=lambda *a,**k:True;util.showWarning=lambda *a,**k:None;util.tooltip=lambda *a,**k:None
    web=types.ModuleType('aqt.webview');web.AnkiWebView=doubles.Web;monkeypatch.setitem(sys.modules,'aqt.webview',web)
    tm=types.ModuleType('aqt.theme');tm.theme_manager=NS(night_mode=True);monkeypatch.setitem(sys.modules,'aqt.theme',tm)
    mw.pm=NS(profileFolder=lambda:str(tmp_path));mw.toolbar=NS(draw=lambda:None,redraw=lambda:None)
    mw.deckBrowser=mod.DeckBrowser()
    for module in ('atelier_testing.sprout.integration','atelier_testing.sprout.companion'):
        monkeypatch.delitem(sys.modules,module,raising=False)
    monkeypatch.setattr(importlib.import_module('atelier_testing.authoring'),'install_authoring',lambda owner,registration:None)
    return mod,hooks,filters,menus,mw

def test_actual_combined_install_singleton_and_complete_rollback(app,monkeypatch,tmp_path):
    mod,hooks,filters,menus,mw=merged_host(app,monkeypatch,tmp_path)
    first=mod.install('daedalus_atelier');c=mw._exam_sprout_controller
    assert c is first.exam_engine and c.suite is first and c.store is not None and c.companion is not None
    assert c.asset_base=='/_addons/daedalus_atelier/sprout/web'
    assert len(hooks.reviewer_did_answer_card)==2  # effort observer + Pip layout observer
    before={k:len(v) for k,v in vars(hooks).items()}
    assert mod.install('daedalus_atelier') is first and before=={k:len(v) for k,v in vars(hooks).items()}
    first._registration.rollback()
    assert all(not v for v in vars(hooks).values()),{k:len(v) for k,v in vars(hooks).items()}
    assert not getattr(mw,'_exam_sprout_controller',None) and not menus and not filters

def test_combined_startup_failure_keeps_foreign_callbacks(app,monkeypatch,tmp_path):
    mod,hooks,filters,menus,mw=merged_host(app,monkeypatch,tmp_path)
    marker=lambda *a:None;hooks.reviewer_did_answer_card.append(marker)
    original=suite.install_engine
    def failed(owner,registration):original(owner,registration);raise RuntimeError('after engine construction')
    monkeypatch.setattr(suite,'install_engine',failed)
    with pytest.raises(RuntimeError,match='after engine'):mod.install('daedalus_atelier')
    assert hooks.reviewer_did_answer_card==[marker]
    assert all(not v for k,v in vars(hooks).items() if k!='reviewer_did_answer_card')
    assert not getattr(mw,'_exam_sprout_controller',None) and not filters and not menus

def test_standalone_engine_blocks_second_registration(app,monkeypatch,tmp_path):
    mod,hooks,filters,menus,mw=merged_host(app,monkeypatch,tmp_path)
    old=NS(mw=mw);mw._exam_sprout_controller=old
    with pytest.raises(life.StartupBlocked,match='Standalone'):mod.install('daedalus_atelier')
    assert mw._exam_sprout_controller is old and all(not v for v in vars(hooks).values())

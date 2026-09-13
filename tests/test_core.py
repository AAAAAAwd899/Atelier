import copy, json, types, sys, math
import pytest
from fixtures import core, guard, review, SRC

def study(i='a',ids=None,active=True,name='Exam 3'):
    return dict(id=i,deck_ids=ids or ['20'],name=name,date='2026-09-20',active=active)

def test_normalizer_no_loss():
    p=core.profile_settings(dict(studies=[study('a'),study('b')],selected_study='b',favorites=['3'],native_note_types=['12']))
    assert len(p['studies'])==2 and sum(s['active'] for s in p['studies'])==1
    assert p['studies'][1]['date']=='2026-09-20' and p['selected_study']=='all'
    assert p['favorites']==['3'] and p['native_note_types']==['12']

@pytest.mark.parametrize('ids', [['20'],['20','20']])
def test_duplicate_block(ids):
    p=core.upsert_study({},study())
    with pytest.raises(core.ValidationError,match='already an active exam'):core.upsert_study(p,study('b',ids,name='Renamed exam'))

@pytest.mark.parametrize('ids', [['20','21'],['21','20']])
def test_order_independent_duplicate(ids):
    p=core.upsert_study({},study(ids=['20','21']))
    with pytest.raises(core.ValidationError):core.upsert_study(p,study('b',ids))

def test_same_name_different_deck_allowed():
    p=core.upsert_study(core.upsert_study({},study()),study('b',['21']))
    assert sum(s['active'] for s in p['studies'])==2

def test_update_existing():
    p=core.upsert_study(core.upsert_study({},study()),study(name='New name'))
    assert len(p['studies'])==1 and p['studies'][0]['name']=='New name'

def test_quick_repeated_remove_restore():
    p=core.upsert_study({},study())
    for _ in range(20):p=core.quick_study(p,'20','Exam',True)
    assert len(p['studies'])==1
    p=core.quick_study(p,'20','Exam',False);assert not p['studies'][0]['active']
    p=core.quick_study(p,'20','Exam',True);assert p['studies'][0]['date']=='2026-09-20'

def test_reactivate_identical_saved():
    p=core.profile_settings(dict(studies=[study(),study('b',active=False)]))
    p=core.set_study_active(p,'b',True)
    assert [(s['id'],s['active']) for s in p['studies']]==[('a',False),('b',True)]

def test_mutators_do_not_mutate_input():
    p=core.profile_settings(dict(studies=[study()]));before=copy.deepcopy(p)
    core.quick_study(p,'20','X',False)
    assert p==before

@pytest.mark.parametrize('mode',['workspace','native'])
def test_migrated_settings(mode):
    assert core.settings(dict(mode=mode,surface_revision=1))['mode']==mode
    assert core.settings(dict(mode=mode))['mode']=='workspace'

def test_marker_persists(tmp_path):
    store=core.ProfileStore(tmp_path,'profile-path')
    p=core.profile_settings(dict(surfaces_version=1,studies=[study()]))
    store.write(p);assert store.read()==p

@pytest.mark.parametrize('theme',core.THEMES)
def test_prepaint_guard(theme):
    h=guard.home_guard(core.settings(dict(theme=theme)))
    assert 'data-atelier-home' in h and '7000' in h and review.PALETTES[theme]['bg'] in h
    assert 'document.body.innerHTML' not in h

# Mock only the boundary needed to verify asynchronous lifetime/height handling.
@pytest.fixture
def fit_env(monkeypatch):
    from importlib import import_module
    aqt=types.ModuleType('aqt');rv=types.ModuleType('aqt.reviewer')
    class Bottom:pass
    rv.ReviewerBottomBar=Bottom
    callbacks=[];jobs=[];sizes=[]
    web=types.SimpleNamespace(hidden=False,evalWithCallback=lambda js,cb:callbacks.append(cb),height=lambda:84,setFixedHeight=sizes.append,animation=types.SimpleNamespace(stop=lambda:None))
    mw=types.SimpleNamespace(state='review',reviewer=object(),bottomWeb=web,progress=types.SimpleNamespace(single_shot=lambda ms,f:jobs.append(f)))
    aqt.mw=mw;monkeypatch.setitem(sys.modules,'aqt',aqt);monkeypatch.setitem(sys.modules,'aqt.reviewer',rv)
    owner=types.SimpleNamespace(get_config=lambda:core.settings({"visual_owner":"atelier"}))
    obj=import_module('atelier_testing.review_theme').ReviewTheme(owner);obj.layout_token='abc'
    ctx=Bottom();ctx.reviewer=mw.reviewer
    return obj,mw,web,ctx,jobs,callbacks,sizes

def fire(e):
    obj,mw,web,ctx,jobs,cbs,sizes=e
    assert obj.receive_layout((False,None),'atelier:review-layout:abc',ctx)==(True,None)
    jobs.pop()();return cbs

@pytest.mark.parametrize('height',[36,84,106.1,160,600])
def test_safe_measurement(fit_env,height):
    cb=fire(fit_env)[0];cb(dict(token='abc',height=height))
    assert fit_env[-1]==([] if height==84 else [math.ceil(height)])

@pytest.mark.parametrize('data',[None,{},dict(token='wrong',height=120),dict(token='abc',height=True),dict(token='abc',height=0),dict(token='abc',height=99999),dict(token='abc',height=float('nan'))])
def test_invalid_and_destroyed_callbacks(fit_env,data):
    cb=fire(fit_env)[0];cb(data);assert fit_env[-1]==[]

@pytest.mark.parametrize('condition',['state','token','web','hidden'])
def test_stale_callback(fit_env,condition):
    cb=fire(fit_env)[0];obj,mw,web,ctx,*_=fit_env
    if condition=='state':mw.state='deckBrowser'
    if condition=='token':obj.layout_token='new-page'
    if condition=='web':mw.bottomWeb=object()
    if condition=='hidden':web.hidden=True
    cb(dict(token='abc',height=180));assert fit_env[-1]==[]

def test_coalesces(fit_env):
    obj,mw,web,ctx,jobs,*_=fit_env
    for _ in range(10):obj.receive_layout((False,None),'atelier:review-layout:abc',ctx)
    assert len(jobs)==1

def test_top_uses_native_toolbar_web():
    s=(SRC/'review_theme.py').read_text()
    assert 'getattr(mw, "toolbarWeb", None)' in s and 'getattr(mw, "topWeb", None)' not in s

@pytest.mark.parametrize('theme',core.THEMES)
@pytest.mark.parametrize('screen',['review','review-bottom','overview','overview-bottom'])
def test_web_content_injection_preserves_foreign_body(monkeypatch,theme,screen):
    from importlib import import_module
    rv=types.ModuleType('aqt.reviewer');ov=types.ModuleType('aqt.overview')
    rv.Reviewer=type('Reviewer',(),{});rv.ReviewerBottomBar=type('ReviewerBottomBar',(),{})
    ov.Overview=type('Overview',(),{});ov.OverviewBottomBar=type('OverviewBottomBar',(),{})
    monkeypatch.setitem(sys.modules,'aqt.reviewer',rv);monkeypatch.setitem(sys.modules,'aqt.overview',ov)
    owner=types.SimpleNamespace(get_config=lambda:core.settings({'theme':theme,'visual_owner':'atelier'}),package='daedalus_atelier')
    obj=import_module('atelier_testing.review_theme').ReviewTheme(owner)
    context={'review':rv.Reviewer,'review-bottom':rv.ReviewerBottomBar,'overview':ov.Overview,'overview-bottom':ov.OverviewBottomBar}[screen]()
    content=types.SimpleNamespace(head='<style id="other-addon">keep{color:red}</style>',body='<div id="qa"><canvas></canvas></div>',css=['native.css'],js=['native.js'])
    obj.add_content(content,context)
    assert content.body=='<div id="qa"><canvas></canvas></div>'
    assert content.css==['native.css'] and content.js[0]=='native.js'
    assert 'reviewer.js?v=' + core.VERSION in content.js[1] and 'atelier-review-css' in content.head
    assert review.PALETTES[theme]['bg'] in content.head and 'other-addon' in content.head


def test_state_change_invalidates_callback(fit_env):
    obj,mw,web,ctx,jobs,cbs,sizes=fit_env
    obj.before_state('deckBrowser','review')
    assert obj.layout_token=='' and obj.layout_pending is False

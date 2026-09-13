from types import SimpleNamespace as NS
from fixtures import core, guard, SRC
from test_release import own, app, onigiri
import pytest, importlib

def meta(package,name,enabled=True):
    return NS(dir_name=package,human_name=lambda:name,enabled=enabled,human_version='1.0')

def report(*entries):
    return own.detect_makeovers(NS(all_addon_meta=lambda:list(entries)))

def test_no_makeover_opens_without_question():
    r=report(meta('exam_sprout','Exam Sprout'),meta('io','Image Occlusion Enhanced'),meta('heat','Review Heatmap'))
    cfg=own.resolve_config(core.settings({}),r)
    assert cfg['visual_owner']=='atelier' and cfg['mode']=='workspace'
    assert not r['makeovers']

def test_onigiri_prompts_before_patcher_load():
    r=report(meta('12345','Onigiri'))
    cfg=own.resolve_config(core.settings({}),r)
    assert cfg['visual_owner']=='ask' and r['onigiri']

@pytest.mark.parametrize('name',['ReColor','Anki Redesign','Beautify Anki','Custom Background Image and Gear Icon','Anki Themes','SynapsePro','Advanced Review Bottom Bar'])
def test_potential_global_makeover_prompts(name):
    r=report(meta('1234',name))
    assert len(r['makeovers'])==1
    cfg=own.resolve_config(core.settings({'visual_owner':'atelier'}),r)
    assert cfg['visual_owner']=='ask'

def test_disabled_makeover_ignored():
    r=report(meta('recolor','ReColor',False),meta('onigiri','Onigiri',False))
    assert not r['onigiri'] and not r['makeovers']

def test_acknowledged_makeover_does_not_prompt_every_time():
    r=report(meta('1234','ReColor'))
    cfg=own.resolve_config(core.settings({'visual_owner':'atelier','acknowledged_makeovers':['1234']}),r)
    assert cfg['visual_owner']=='atelier'

def test_new_makeover_reprompts():
    r=report(meta('1234','ReColor'),meta('5678','Anki Redesign'))
    cfg=own.resolve_config(core.settings({'visual_owner':'atelier','acknowledged_makeovers':['1234']}),r)
    assert cfg['visual_owner']=='ask'

def test_original_external_always_passive():
    r=report(meta('1234','ReColor'))
    cfg=own.resolve_config(core.settings({'visual_owner':'external','mode':'native','surface_revision':1}),r)
    assert cfg['visual_owner']=='external' and cfg['mode']=='native'

def test_manual_external_available_with_no_detection():
    assert own.resolve_config(core.settings({'visual_owner':'external'}),report())['visual_owner']=='external'

def test_passive_owner_releases_presentation_wrappers(onigiri):
    gate,patch,cfg,calls=onigiri
    assert getattr(patch.generate_deck_browser_backgrounds,'_atelier_visual_gate',False)
    cfg['visual_owner']='onigiri';gate.install()
    assert not getattr(patch.generate_deck_browser_backgrounds,'_atelier_visual_gate',False)
    assert patch.generate_deck_browser_backgrounds()=='native-css'
    cfg['visual_owner']='atelier';gate.install()
    assert patch.generate_deck_browser_backgrounds()==''

@pytest.mark.parametrize('owner',['onigiri','external','ask'])
def test_no_shared_css_in_passive_or_pending_document(owner):
    h=guard.home_guard(core.settings({'visual_owner':owner}))
    assert '.sidebar-left' not in h and '#es-countdowns' not in h

def test_own_shared_css_retained():
    assert '.sidebar-left' in guard.home_guard(core.settings({'visual_owner':'atelier'}))

def test_compact_defaults_and_invalid_setting_guard():
    s=core.settings({})
    assert s['review_context']=='compact' and s['companion_shortcuts'] is False
    s=core.settings({'review_context':'bad','companion_shortcuts':'true'})
    assert s['review_context']=='compact' and s['companion_shortcuts'] is False
    assert core.settings({'review_context':'hidden'})['review_context']=='hidden'

def test_external_owner_save_and_acknowledgement(app):
    a,mw,actions,jobs,replies,configs=app
    a.ownership._report={'onigiri':True,'metadata_checked':True,'makeovers':[{'id':'23','name':'ReColor'}]}
    a.dispatch('test','r1','visual_owner',{'owner':'external'})
    assert configs['visual_owner']=='external' and configs['mode']=='native'
    assert configs['acknowledged_makeovers']==['23']
    assert not a.sprout_config()['match_sprout']
    jobs[-1]();assert actions==[('state','deckBrowser')]

def test_metadata_rescan_is_read_only(app):
    a,mw,actions,jobs,replies,configs=app
    before=dict(configs)
    mw.addonManager.all_addon_meta=lambda:[meta('23','ReColor')]
    a.dispatch('test','r1','rescan_makeovers',{})
    assert replies[-1]['result']['makeovers'][0]['name']=='ReColor'
    assert configs==before and not actions

def test_no_passive_sprout_recolor(app):
    a,mw,actions,jobs,replies,configs=app
    for owner in ['onigiri','external']:
        configs['visual_owner']=owner
        a.ownership.companion_palette={'bg':'#222222','text':'#eeeeee'}
        assert a.sprout_config()['match_sprout'] is False

def test_config_acknowledgements_not_mutable_default():
    a=core.settings({});a['acknowledged_makeovers'].append('a')
    assert core.settings({})['acknowledged_makeovers']==[]

@pytest.mark.parametrize('owner',['onigiri','external','ask'])
@pytest.mark.parametrize('screen',['Reviewer','ReviewerBottomBar','Overview','OverviewBottomBar'])
def test_passive_owner_injects_no_review_or_overview_assets(monkeypatch,owner,screen):
    import sys, types
    rv=types.ModuleType('aqt.reviewer'); ov=types.ModuleType('aqt.overview')
    for name in ['Reviewer','ReviewerBottomBar']:setattr(rv,name,type(name,(),{}))
    for name in ['Overview','OverviewBottomBar']:setattr(ov,name,type(name,(),{}))
    monkeypatch.setitem(sys.modules,'aqt.reviewer',rv)
    monkeypatch.setitem(sys.modules,'aqt.overview',ov)
    cls=getattr(rv,screen,None) or getattr(ov,screen)
    cfg=core.settings({'visual_owner':owner})
    theme=importlib.import_module('atelier_testing.review_theme').ReviewTheme(NS(get_config=lambda:cfg))
    content=NS(head='<style id="native">original</style>',body='<div>original page</div>',js=['native.js'],css=['native.css'])
    theme.add_content(content,cls())
    assert vars(content)==dict(head='<style id="native">original</style>',body='<div>original page</div>',js=['native.js'],css=['native.css'])

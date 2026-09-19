from release_copy import before_release_copy
"""Native home widgets: preferences, route safety and exact engine preservation."""
from pathlib import Path
from types import SimpleNamespace as NS
import copy, hashlib, importlib, json
import pytest
from fixtures import core, SRC, ROOT
from test_release import app, onigiri
nw = importlib.import_module('atelier_testing.native_widgets')
BASE=json.loads((ROOT/'native-widgets-baseline.json').read_text())

@pytest.mark.parametrize('raw',[None,False,{},[],{'items':'wrong'},'widget'])
def test_old_profiles_receive_fresh_defaults(raw):
    a=nw.widget_layout(raw); b=nw.widget_layout(raw)
    assert a==nw.DEFAULT_WIDGETS and a is not b
    a['items'][0]['home']=True
    assert b['items'][0]['home'] is False and nw.DEFAULT_WIDGETS['items'][0]['home'] is False

@pytest.mark.parametrize('wid',list(nw.BUILTIN_IDS)+['addon.example.notes','addon.study-tools'])
def test_id_roundtrip(wid):
    value={'items':[{'id':wid,'size':'normal','home':True}]}
    assert nw.widget_layout(value,strict=True)==value

@pytest.mark.parametrize('bad',[{},None,[],{'items':None},{'items':[{'id':'https://example.com','size':'wide','home':False}]},
 {'items':[{'id':'today','size':'giant','home':False}]},{'items':[{'id':'today','size':'normal','home':1}]},
 {'items':[{'id':'<script>','size':'wide','home':False}]},{'items':[{'id':123,'size':'wide','home':False}]},
 {'items':[{'id':'addon.a;body','size':'wide','home':False}]},{'items':[None]}])
def test_invalid_settings_refused_not_silently_saved(bad):
    with pytest.raises(core.ValidationError):nw.widget_layout(bad,strict=True)

def test_duplicate_and_limit_rejected():
    item={'id':'today','size':'wide','home':False}
    with pytest.raises(core.ValidationError):nw.widget_layout({'items':[item,item]},strict=True)
    with pytest.raises(core.ValidationError):nw.widget_layout({'items':[{'id':f'addon.test.{i}','size':'wide','home':False} for i in range(25)]},strict=True)
    assert len(nw.widget_layout({'items':[item,item]})['items'])==1

def test_empty_layout_is_deliberate_and_provider_absence_is_not_deletion():
    assert nw.widget_layout({'items':[]},strict=True)=={'items':[]}
    p=core.profile_settings({'native_widgets':{'items':[{'id':'addon.temporarily-missing','size':'normal','home':True}]}})
    assert p['native_widgets']['items'][0]['id']=='addon.temporarily-missing'

@pytest.mark.parametrize('text',['','Read lecture 2 first','<img src=x onerror=bad()>','🌲 café • \n日本語','x'*4000])
def test_plain_note_preserved_not_interpreted(text):
    assert nw.widget_note(text,strict=True)==text
    assert core.profile_settings({'native_widget_note':text})['native_widget_note']==text

@pytest.mark.parametrize('text',[None,3,'x'*4001,'abc\x00def',{}])
def test_note_limits(text):
    with pytest.raises(core.ValidationError):nw.widget_note(text,strict=True)
    assert nw.widget_note(text)==''

def test_profile_store_roundtrip_without_migrating_other_records(tmp_path):
    store=core.ProfileStore(tmp_path,'Anki Test profile')
    p=core.profile_settings({'favorites':['2'],'home_layout':{'enabled':False,'columns':3,'items':[]}})
    p['native_widgets']={'items':[{'id':'notes','size':'wide','home':True}]};p['native_widget_note']='A small reminder 🌲'
    store.write(p);read=store.read()
    assert read['native_widgets']==p['native_widgets'] and read['native_widget_note']==p['native_widget_note']
    assert read['favorites']==['2'] and read['home_layout']==p['home_layout']

@pytest.mark.parametrize('key,value',[('native_widgets',{'items':[{'id':'notes','size':'normal','home':True}]}),('native_widget_note','A new reminder')])
def test_existing_guarded_preference_route_saves_exact_value(app,key,value):
    a,mw,actions,_,replies,_=app;writes=[];a.store=NS(write=lambda p:writes.append(copy.deepcopy(p)))
    a.dispatch('test','req','preference',{'key':key,'value':value})
    assert a.profile[key]==value and writes[-1][key]==value and replies[-1]['result'][key]==value
    assert actions==[]  # no scheduler, decks or other app changes

@pytest.mark.parametrize('key,value',[('native_widgets',{'items':[{'id':'notes','size':'normal','home':True}]}),('native_widget_note','new')])
def test_failed_disk_write_keeps_previous_profile(app,key,value):
    a,_,actions,_,replies,_=app;before=copy.deepcopy(a.profile)
    def fail(_):raise OSError('fixture disk full')
    a.store=NS(write=fail)
    with pytest.raises(OSError):a.dispatch('test','req','preference',{'key':key,'value':value})
    assert a.profile==before and not replies and not actions

def test_validation_happens_before_store_write(app):
    a,_,_,_,_,_=app;calls=[];a.store=NS(write=lambda p:calls.append(p))
    with pytest.raises(core.ValidationError):a.dispatch('test','req','preference',{'key':'native_widgets','value':{'items':[{'id':'random','size':'wide','home':False}]}})
    assert not calls

def test_widget_page_survives_anki_home_redraw_ephemerally(app):
    a,_,actions,_,replies,_=app
    a.dispatch('test','req','ui',{'page':'widgets'})
    assert a._ui_state['page']=='widgets' and not actions

@pytest.mark.parametrize('prefix',['sprout/','workshop/'])
def test_every_hardened_embedded_file_byte_identical_to_shipped_rc4(prefix):
    names=[n for n in BASE if n.startswith(prefix) and n not in ('sprout/web/app.js','sprout/web/pip.css','sprout/web/pip.js','workshop/web/app.js','workshop/web/app.css')]
    assert len(names)>65
    for name in names:assert hashlib.sha256(before_release_copy(name)).hexdigest()==BASE[name],name

@pytest.mark.parametrize('name',['study_progress.py','focus_context.py','native_tools.py','quiet_navigation.py','ownership.py','lifecycle.py','web/reviewer.js','web/reviewer.css','web/session-shell.css','web/studio-shell.css'])
def test_native_operations_and_accepted_ui_not_rewritten(name):
    assert hashlib.sha256(before_release_copy(name)).hexdigest()==BASE[name]

def test_widget_assets_use_owned_home_hook_and_no_remote_dependency():
    integration=(SRC/'integration.py').read_text();css=(SRC/'web/native-widgets.css').read_text()
    for name in ['widget-registry.js','native-widgets.js']:assert name in integration
    assert 'native-widgets.css' in (SRC/'worlds.py').read_text()
    assert '#qa' not in css and '.modern-main-menu' not in css
    assert 'prefers-reduced-motion' in css and 'forced-colors' in css
    for name in ['widget-registry.js','native-widgets.js']:
        text=(SRC/'web'/name).read_text();assert 'https://' not in text and 'fetch(' not in text and 'eval(' not in text

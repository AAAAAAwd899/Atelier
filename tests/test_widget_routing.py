from release_copy import before_release_copy
"""Upgrade/menu/identity regression: original owners are not forced into Atelier.
Actual profile store is used for marker roundtrips; Qt/Anki dispatch is a double.
"""
import copy,hashlib,importlib,json
from types import SimpleNamespace as NS
import pytest
from fixtures import core,ROOT,SRC
from test_release import app,onigiri
nw=importlib.import_module('atelier_testing.native_widgets')
BASE=json.loads((ROOT/'widget-routing-baseline.json').read_text())

@pytest.mark.parametrize('owner',['atelier','onigiri','external','ask'])
@pytest.mark.parametrize('mode',['workspace','native'])
def test_one_time_upgrade_is_narrow_nonmutating_and_preserves_data(owner,mode):
 c=core.settings({'visual_owner':owner,'mode':mode,'surface_revision':1,'theme':'rose'})
 p=core.profile_settings({'surfaces_version':1,'favorites':['2'],'native_widget_note':'🌲 keep this', 'native_widgets':{'items':[{'id':'addon.example.custom','home':True,'size':'wide'}]}})
 before=copy.deepcopy((c,p))
 nc,np,recovered=nw.widget_route_upgrade(c,p)
 assert (c,p)==before
 assert recovered==(owner=='atelier' and mode=='native')
 assert nc['visual_owner']==owner and nc['theme']=='rose'
 assert nc['mode']==('workspace' if recovered else mode)
 assert {k:v for k,v in np.items() if k!='widget_route_version'}=={k:v for k,v in p.items() if k!='widget_route_version'}
 assert np['widget_route_version']==1
 assert nw.widget_route_upgrade(nc,np)==(nc,np,False)

@pytest.mark.parametrize('raw',[None,'1',True,-1,0,1,100])
def test_route_marker_normalization(raw):
 p=core.profile_settings({'widget_route_version':raw})
 assert p['widget_route_version']==(min(1,max(0,raw)) if type(raw) is int else 0)

def test_marker_roundtrips_real_profile_store(tmp_path):
 s=core.ProfileStore(tmp_path,'routing profile');p=core.profile_settings({'widget_route_version':1,'native_widget_note':'keep me'})
 s.write(p);assert s.read()==p

def test_completed_migration_does_not_prevent_later_explicit_provider_choice():
 c=core.settings({'visual_owner':'atelier','mode':'native','surface_revision':1});p=core.profile_settings({'widget_route_version':1})
 nc,np,found=nw.widget_route_upgrade(c,p)
 assert nc==c and np==p and not found

@pytest.mark.parametrize('owner',['atelier','onigiri','external'])
def test_menu_route_opens_built_in_page_without_switching_owner(app,owner):
 a,mw,actions,jobs,replies,configs=app
 a.ownership.report=lambda:{'onigiri':True,'makeovers':[],'metadata_checked':True}
 configs.update(visual_owner=owner,mode='native',surface_revision=1)
 before=copy.deepcopy(a.profile)
 a.open_widgets()
 assert a._ui_state=={'page':'widgets','location':'0','query':'','filter':'all'}
 assert configs['mode']=='workspace' and configs['visual_owner']==owner
 assert actions==[('state','deckBrowser')] and a.profile==before

def test_menu_without_profile_does_not_change_screen_or_preferences(app):
 a,mw,actions,jobs,replies,configs=app;mw.col=None;before=copy.deepcopy(configs)
 a.open_widgets();assert not actions and configs==before and a._ui_state=={}

@pytest.mark.parametrize('failure',['none','config','profile'])
def test_upgrade_via_real_ensure_store_preserves_data_and_retries_failures(app,monkeypatch,failure):
 a,mw,actions,_,_,configs=app
 mod=importlib.import_module('atelier_testing.integration')
 a.ownership.report=lambda:{'onigiri':True,'makeovers':[],'metadata_checked':True}
 configs.update(visual_owner='atelier',mode='native',surface_revision=1)
 original=core.profile_settings({'surfaces_version':1,'native_widget_note':'not lost','favorites':['2'],'native_widgets':{'items':[]}})
 stored=copy.deepcopy(original);writes=[]
 def storewrite(p):
  if failure=='profile':raise OSError('full')
  writes.append(copy.deepcopy(p))
 mock=NS(read=lambda:copy.deepcopy(stored),write=storewrite)
 monkeypatch.setattr(mod,'ProfileStore',lambda *_:mock)
 mw.pm=NS(profileFolder=lambda:'/test-profile')
 if failure=='config':
  def fail(*_):raise OSError('config is readonly')
  mw.addonManager.writeConfig=fail
 a.store=None
 type(a).ensure_store(a)
 assert a.profile['native_widgets']==original['native_widgets'] and a.profile['native_widget_note']=='not lost'
 if failure=='none':
  assert configs['mode']=='workspace' and a.profile['widget_route_version']==1 and a._ui_state['page']=='widgets'
 else:
  assert a.profile['widget_route_version']==0 and not writes
 # No collection/select/review/provider command.
 assert not actions

@pytest.mark.parametrize('prefix',['sprout/','workshop/'])
def test_all_embedded_engines_unchanged_from_actual_rc5(prefix):
 names=[n for n in BASE if n.startswith(prefix) and n not in ('sprout/web/app.js','sprout/web/pip.css','sprout/web/pip.js','workshop/web/app.js','workshop/web/app.css')];assert len(names)>65
 assert all(hashlib.sha256(before_release_copy(n)).hexdigest()==BASE[n] for n in names)

@pytest.mark.parametrize('name',['ownership.py','study_progress.py','figure_cache.py','quiet_navigation.py','native_tools.py','web/widget-registry.js','web/native-widgets.css','web/reviewer.js','web/reviewer.css'])
def test_existing_native_widgets_and_study_behaviors_unchanged(name):
 assert hashlib.sha256(before_release_copy(name)).hexdigest()==BASE[name]

def test_publication_identity_and_concrete_menu_route():
 assert json.loads((SRC/'manifest.json').read_text())['package']=='daedalus_atelier'
 text=(SRC/'integration.py').read_text()
 assert '("Open Atelier widgets", addon.open_widgets)' in text
 assert '"page": "widgets"' in text

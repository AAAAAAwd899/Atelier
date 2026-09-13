"""Current suite bridges, preservation and bounded quiet navigation.
Synthetic Anki/Qt contracts; not a native Windows sign-off.
"""
import ast,copy,hashlib,importlib,json,sys,types
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'src'
pkg=types.ModuleType('complete_contract');pkg.__path__=[str(SRC)];sys.modules[pkg.__name__]=pkg
studio=importlib.import_module('complete_contract.card_studio')
core=importlib.import_module('complete_contract.core')
# Protected incoming source engines are not reimplemented by integration.
BASE=json.loads((ROOT/'integration-baselines.json').read_text())


@pytest.mark.parametrize('name',[n for n in BASE['incoming'] if n.startswith('workshop/') and n not in ('workshop/integration.py','workshop/web/app.js')])
def test_incoming_card_engine_importers_mask_model_and_art_preserved(name):
 assert hashlib.sha256((SRC/name).read_bytes()).hexdigest()==BASE['incoming'][name]

@pytest.mark.parametrize('name',[n for n in BASE['rc6'] if n.startswith('sprout/') and n not in ('sprout/runner.py','sprout/web/app.js','sprout/integration.py')])
def test_latest_exam_engine_results_assets_preserved(name):
 assert hashlib.sha256((SRC/name).read_bytes()).hexdigest()==BASE['rc6'][name]

@pytest.mark.parametrize('name',['web/world-finishes.css','web/interaction-finish.css','web/review-finish.css','web/studio-shell.css','web/session-shell.css','web/model.js','session_model.py','lifecycle.py','ownership.py'])
def test_latest_graphics_session_and_home_contracts_survive(name):
 from upgrade_preservation import before_upgrade
 assert hashlib.sha256(before_upgrade(name)).hexdigest()==BASE['rc6'][name]

@pytest.mark.parametrize('theme',core.THEMES)
def test_studio_appearance_is_one_complete_world(theme):
 cfg=core.settings({'theme':theme,'visual_owner':'atelier'})
 owner=NS(get_config=lambda:cfg)
 a=studio.appearance(owner)
 assert a['enabled'] and a['theme']==theme and a['world']['id']==theme
 assert len(a['worlds'])==12 and a['palette']['text'] and a['palette']['scheme'] in ('light','dark')
 h=studio.head(owner)
 assert 'atelier-card-studio-shell' in h and 'http' not in h and '#qa' not in h

@pytest.mark.parametrize('mode',['external','onigiri','ask'])
def test_passive_owner_does_not_force_workshop_palette(mode):
 a=studio.appearance(NS(get_config=lambda:core.settings({'visual_owner':mode})))
 assert not a['enabled'] and a['palette']=={}

@pytest.fixture
def route_window(monkeypatch):
 cfg=core.settings({'visual_owner':'atelier','theme':'forest'});saved=[];opened=[]
 catalogue={'1':{'name':'Course'},'2':{'name':'Course::Lecture 2'}}
 col=NS(card_ids_of_note=lambda n:[n*10] if n in [3,4] else [],get_card=lambda c:NS(did=2,odid=0))
 mw=NS(col=col,state='deckBrowser',moveToState=lambda state:opened.append(('state',state)),_exam_sprout_controller=NS(runner=None))
 owner=NS(get_config=lambda:cfg,save_config=lambda p:(cfg.update(p),saved.append(p)),sprout_link=NS(open_target=lambda v,setup=None:opened.append((v,setup))))
 project={'id':'11111111111111111111111111111111','title':'A project <not markup>'}
 store=NS(get=lambda kind,i:project,list=lambda kind,i:[{'note_id':3},{'note_id':4},{'note_id':3},{'note_id':9}])
 w=NS(controller=NS(suite=owner),valid=lambda:True,dirty=False,busy=False,mw=mw,col=col,store=store,hide=lambda:opened.append(('hidden',)),close=lambda:opened.append(('closed',)))
 monkeypatch.setattr(studio,'fresh_catalog',lambda c:catalogue)
 return w,cfg,saved,opened

@pytest.mark.parametrize('patch',[{'theme':'rose'},{'motion':False},{'ambience':False}])
def test_world_settings_do_not_write_another_preference_store(route_window,patch):
 w,cfg,saved,_=route_window;a=studio.command(w,'suite_appearance',patch)
 assert saved==[patch] and a['theme']==cfg['theme']

@pytest.mark.parametrize('patch',[{}, {'theme':'x'}, {'theme':'rose','api_key':'no'}, {'motion':'false'}, {'visual_owner':'atelier'}])
def test_world_setting_bridge_rejects_unknown_or_invalid_patch(route_window,patch):
 w,_,saved,_=route_window
 with pytest.raises(core.ValidationError):studio.command(w,'suite_appearance',patch)
 assert saved==[]

@pytest.mark.parametrize('state',[{'busy':True},{'dirty':True}])
def test_handoff_refuses_unsaved_or_pending_source_operation(route_window,state):
 w,_,_,opened=route_window;w.__dict__.update(state)
 with pytest.raises(core.ValidationError):studio.project_to_plan(w,{'project_id':'11111111111111111111111111111111'})
 assert not opened

def test_project_handoff_uses_exact_existing_notes_without_copy_tag_or_clipboard(route_window):
 w,_,_,opened=route_window
 value=studio.project_to_plan(w,{'project_id':'11111111111111111111111111111111'})
 assert value['notes']==2 and value['query']=='nid:3,4'
 assert opened[0]==('state','deckBrowser')
 view,setup=opened[1];assert view=='new' and setup=={'name':'A project <not markup>','deck_ids':['2'],'query':'nid:3,4'}
 assert opened[-1]==('hidden',)

def test_no_existing_cards_does_not_open_or_save_plan(route_window):
 w,_,_,opened=route_window;w.col.card_ids_of_note=lambda n:[]
 with pytest.raises(core.ValidationError,match='Add or link'):studio.project_to_plan(w,{'project_id':'11111111111111111111111111111111'})
 assert not opened

def test_active_practice_blocks_cross_app_handoff(route_window):
 w,_,_,opened=route_window;w.mw._exam_sprout_controller.runner=object()
 with pytest.raises(core.ValidationError):studio.command(w,'suite_home',{})
 assert not opened

def test_unknown_native_command_cannot_escape_allowlist(route_window):
 w,_,_,opened=route_window
 with pytest.raises(core.ValidationError):studio.command(w,'suite_native',{'command':'arbitrary code'})
 assert not opened

@pytest.mark.parametrize('count',[1,24,25,100,500])
def test_quiet_tools_retains_bounded_current_question_map(monkeypatch,count):
 from qt_session_double import install,Widget,Layout
 install(monkeypatch)
 monkeypatch.setattr(Widget,'setProperty',lambda self,key,value:setattr(self,key,value),raising=False)
 nav=importlib.import_module('complete_contract.quiet_navigation')
 model=importlib.import_module('complete_contract.session_model')
 session=NS(cards=[NS(id=i+1) for i in range(count)],index=0,phase='answering',attempted={2},flags={3})
 calls=[];runner=NS(session=session,_jump_from_tools=lambda n:calls.append(n))
 ui=nav.QuestionNavigation(runner,Widget(),Layout())
 assert len(ui.buttons)==24 and len(ui.rows)<=24
 before=copy.deepcopy(session.__dict__)
 ui.next('flagged')
 if count>=3:assert calls==[2]
 ui.turn(1);assert ui.page<=max(0,(count-1)//24)
 if ui.rows:ui.choose(0);assert calls[-1]==ui.rows[0]['index']
 assert session.__dict__==before
 session.phase='grading';ui.refresh();assert ui.widget.hidden
 calls.clear();ui.choose(0);ui.next('unanswered');assert not calls

def test_quiet_input_and_original_native_edit_handlers_remain_incoming():
 assert (SRC/'sprout/web/review_keys.js').read_bytes()==(ROOT/'../inputs/authoring/sprout/web/review_keys.js').read_bytes() if (ROOT/'../inputs/authoring').exists() else hashlib.sha256((SRC/'sprout/web/review_keys.js').read_bytes()).hexdigest()==BASE['incoming']['sprout/web/review_keys.js']
 assert 'editor_loaded' in (SRC/'authoring.py').read_text() and "link(e)" in (SRC/'authoring.py').read_text()

@pytest.mark.parametrize('value,expect',[('balanced','balanced'),('original','original'),('broken','balanced'),(None,'balanced')])
def test_widget_mode_validated_and_original_default_identity(value,expect):
 assert core.settings({'widget_mode':value})['widget_mode']==expect


def test_no_duplicate_workshop_home_or_toolbar_in_suite_runtime():
 s=(SRC/'workshop/integration.py').read_text()
 for method in ('toolbar','home','home_ready','web_assets'):
  fn=next(n for c in ast.parse(s).body if isinstance(c,ast.ClassDef) and c.name=='Controller' for n in c.body if isinstance(n,ast.FunctionDef) and n.name==method)
  assert isinstance(fn.body[0],ast.If)
 assert 'authoring_open' in (SRC/'integration.py').read_text()
 assert 'suite_appearance' in (SRC/'card_studio.py').read_text()

@pytest.mark.parametrize('theme',core.THEMES)
def test_card_studio_native_chrome_is_owned_and_reversible(theme):
 class Window:
  def __init__(self):self.sheet='QLabel#foreign { font-size:15px; }';self.props={}
  def styleSheet(self):return self.sheet
  def setStyleSheet(self,x):self.sheet=x
  def setProperty(self,k,v):self.props[k]=v
 w=Window();original=w.sheet
 a=studio.appearance(NS(get_config=lambda:core.settings({'theme':theme,'visual_owner':'atelier'})))
 studio.native_chrome(w,a)
 assert original in w.sheet and a['palette']['bg'] in w.sheet and w.props['atelier_surface']
 studio.native_chrome(w,a)
 assert w.sheet.count('/* atelier-native-start */')==1
 studio.native_chrome(w,{'enabled':False})
 assert w.sheet==original and not w.props['atelier_surface']

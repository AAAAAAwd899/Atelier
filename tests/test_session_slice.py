import ast,copy,hashlib,importlib,json,subprocess,sys,types
from pathlib import Path
from types import SimpleNamespace
import pytest
R=Path(__file__).resolve().parents[1];SRC=R/'src'
pkg=types.ModuleType('session_contract');pkg.__path__=[str(SRC)];sys.modules.setdefault('session_contract',pkg)
model=importlib.import_module('session_contract.session_model')
core=importlib.import_module('session_contract.sprout.core')
Session=importlib.import_module('session_contract.sprout.exam_session').ExamSession

def session(n=30,kind='exam'):
 return Session('exam',[core.CardInfo(i+1,i+1,10+i%3) for i in range(n)],kind)

@pytest.mark.parametrize('count',[1,2,24,25,100,500])
@pytest.mark.parametrize('view',['all','flagged','unanswered'])
def test_map_is_bounded_and_never_changes_session(count,view):
 s=session(count);s.attempted=set(range(1,count+1,2));s.flags=set(range(2,count+1,3));before=copy.deepcopy(s.__dict__)
 q=model.question_page(s,view,2)
 assert len(q['rows'])<=24 and q['pages']>=1
 assert all(0<=x['index']<count for x in q['rows'])
 assert s.__dict__==before

@pytest.mark.parametrize('view',['flagged','unanswered'])
def test_next_matching_wraps_without_mark_or_reveal(view):
 s=session(8);s.flags={2,7};s.attempted={1,3,4,5,6,8};s.index=6
 assert model.next_question(s,view)==1
 assert not s.revealed and s.phase=='answering' and s.index==6
 s.flags={7};s.attempted={1,2,3,4,5,6,8}
 assert model.next_question(s,view) is None

@pytest.mark.parametrize('kind,phase,new,ro,title',[('exam','answering',False,False,'Mock exam'),('exam','grading',False,False,'Self-marking'),('practice','practice',False,False,'Focus practice'),('practice','practice',True,False,'New-card learning'),('practice','practice',True,True,'Original-card review')])
def test_explicit_mode_labels(kind,phase,new,ro,title):
 s=session(kind=kind);s.phase=phase
 p=model.presentation(s,read_only=ro,current_new=new)
 assert p['title']==title and p['native_rating']==(new and not ro)
 assert p['navigation']==(phase=='answering' and not ro)

@pytest.mark.parametrize('phase',['practice','grading','finished'])
def test_map_cannot_dispatch_a_jump_after_submission(phase):
 s=session();s.phase=phase
 assert model.next_question(s,'unanswered') is None

@pytest.mark.parametrize('view,page',[('bad',0),('all',True),('all',-1),('all',.5)])
def test_bad_map_requests_rejected(view,page):
 with pytest.raises(ValueError):model.question_page(session(),view,page)

PROTECTED=['core.py','exam_engine.py','exam_session.py','new_learning.py','storage.py','drafts.py','answers.py','evidence.py','readiness.py','progress.py','session_tools.py','companion.py','companion_layout.py','web/pip.js','web/pip-scene.js','web/app.css']
@pytest.mark.parametrize('file',PROTECTED)
def test_original_engine_and_card_integration_bytes_still_identical(file):
 before=json.loads((R/'session-slice-baseline.json').read_text())
 assert hashlib.sha256((SRC/'sprout'/file).read_bytes()).hexdigest()==before['sprout/'+file]

# Every incoming quiet-review handler stays identical. The one addition is a
# read-only navigation refresh at the end of _refresh_quiet (tested separately).
def methods(text):
 return {cl.name+'.'+f.name:f for cl in ast.parse(text).body if isinstance(cl,ast.ClassDef) for f in cl.body if isinstance(f,ast.FunctionDef)}
OLD=methods((R/'tests/data/incoming-quiet-runner.py').read_text());NEW=methods((SRC/'sprout/runner.py').read_text())
@pytest.mark.parametrize('name',[x for x in OLD if not x.endswith('._refresh_quiet')])
def test_every_incoming_quiet_handler_preserved_semantically(name):
 assert ast.dump(NEW[name],include_attributes=False)==ast.dump(OLD[name],include_attributes=False)

def test_gui_uses_the_single_incoming_quiet_builder():
 assert 'build_review_ui(self)' in (SRC/'sprout/runner.py').read_text()
 assert not (SRC/'session_ui.py').exists()
 assert 'suite_navigation_factory' in (SRC/'suite.py').read_text()

@pytest.mark.parametrize('theme', ['forest','rose','obsidian','glacier','bloom','linen','matcha','midnight','peach','tidal','ember','celestial'])
def test_result_model_asset_loaded_with_each_theme(theme):
 worlds=importlib.import_module('session_contract.worlds');cfg=importlib.import_module('session_contract.core').settings({'theme':theme,'visual_owner':'atelier'})
 head=worlds.planner_head(cfg,'daedalus_atelier')
 assert 'AtelierSessionModel' in head and 'Session/results · rc5' in head



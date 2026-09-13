"""UI-only release audit. Scheduler, sampling and persistence engines unchanged."""
from fixtures import *
import subprocess, re

def node(program):
 code='const m=require('+json.dumps(str(SRC/'web/model.js'))+');'+program
 r=subprocess.run(['node','-e',code],text=True,capture_output=True,check=True)
 return json.loads(r.stdout)

def test_natural_order_is_stable_and_non_mutating():
 out=node('''const x=[{id:'10',name:'Lecture 10',path:'Course::Lecture 10'}, {id:'2',name:'Lecture 2',path:'Course::Lecture 2'}, {id:'1',name:'Lecture 1',path:'Course::Lecture 1'}]; const before=JSON.stringify(x); console.log(JSON.stringify({ids:m.sortNodes(x).map(n=>n.id),same:before===JSON.stringify(x)}));''')
 assert out=={'ids':['1','2','10'],'same':True}

def test_due_order_has_learning_and_deterministic_ties():
 out=node('''const x=[{id:'10',name:'Lecture 10',review:0,learn:1},{id:'2',name:'Lecture 2',review:0,learn:1},{id:'1',name:'Lecture 1',review:2,learn:0}];console.log(JSON.stringify(m.sortNodes(x,{sort:'due'}).map(n=>n.id)));''')
 assert out==['1','2','10']

def test_recent_order_puts_unvisited_after_visited_then_natural():
 out=node('''console.log(JSON.stringify(m.sortNodes([{id:'10',name:'Lecture 10'},{id:'2',name:'Lecture 2'},{id:'1',name:'Lecture 1'},{id:'3',name:'Lecture 3'}],{sort:'recent',recent:['3','1']}).map(n=>n.id)));''')
 assert out==['3','1','2','10']

def test_empty_marked_folders_and_hierarchy_not_modified():
 out=node('''const x=[{id:'a',name:'AAA',parent:'course',children:[]},{id:'z',name:'ZZZ',parent:'course',children:[]},{id:'2',name:'Branch',parent:'course',children:['8']}];console.log(JSON.stringify({ids:m.sortNodes(x,{folderIds:['z']}).map(n=>n.id),parents:x.map(n=>n.parent)}));''')
 assert out=={'ids':['2','z','a'],'parents':['course']*3}

def test_duplicate_names_tie_by_path_and_id_without_precision_loss():
 out=node('''const x=[{id:'9223372036854775806',name:'Same',path:'Z::Same'},{id:'9223372036854775805',name:'Same',path:'A::Same'},{id:'9223372036854775804',name:'Same',path:'A::Same'}]; console.log(JSON.stringify(m.sortNodes(x).map(n=>n.id)));''')
 assert out==['9223372036854775804','9223372036854775805','9223372036854775806']

def test_accented_unicode_names_and_numeric_parent_paths():
 out=node('''console.log(JSON.stringify(m.sortNodes([{id:'1',name:'Éléments 10'},{id:'2',name:'Éléments 2'},{id:'3',name:'Éléments 1'}]).map(n=>n.id)));''')
 assert out==['3','2','1']

def test_production_strings_are_strict_utf8_without_common_mojibake():
 bad=[]
 for p in SRC.rglob('*'):
  if p.suffix not in ('.py','.js','.css','.json','.md','.txt','.svg'):continue
  txt=p.read_text(encoding='utf-8',errors='strict')
  if 'workshop/vendor/pypdf' in p.as_posix():continue  # preserved vendor character map, not interface text
  if re.search(r'\ufffd|Ã[\x80-\xbf]|Â[\xa0-\xbf]|â[€™œž“”]|ðŸ',txt):bad.append(str(p.relative_to(SRC)))
 assert not bad,bad

def test_world_catalog_is_complete_unique_and_has_valid_svg():
 import xml.etree.ElementTree as ET
 data=json.loads((SRC/'web/worlds.json').read_text())
 assert {x['id'] for x in data}==set(core.THEMES)
 assert len({x['title'] for x in data})==len(data)
 for w in data:
  root=ET.fromstring((SRC/'web'/w['art']).read_text(encoding='utf8'))
  assert root.tag.endswith('svg') and root.get('viewBox')
  assert not any(n.tag.endswith('script') for n in root.iter())

from test_release import app, onigiri
from types import SimpleNamespace as NS

def test_saved_world_is_delivered_to_same_home_page(app):
 owner,mw,*_=app;scripts=[];mw.web=NS(eval=scripts.append)
 owner.save_config({'theme':'forest'})
 assert len(scripts)==1 and 'applyAppearance' in scripts[0] and '"token":"test"' in scripts[0] and '"theme":"forest"' in scripts[0]
 assert 'reload' not in scripts[0] and 'innerHTML' not in scripts[0]

def test_saved_world_is_not_delivered_to_reviewer_as_home(app):
 owner,mw,*_=app;scripts=[];mw.web=NS(eval=scripts.append);mw.state='review'
 owner.save_config({'theme':'forest'});assert not scripts

def test_closed_home_during_theme_delivery_does_not_undo_saved_settings(app):
 owner,mw,_,_,_,cfg=app
 def closed(_):raise RuntimeError('QWebEngine object deleted')
 mw.web=NS(eval=closed)
 owner.save_config({'theme':'forest'});assert cfg['theme']=='forest'

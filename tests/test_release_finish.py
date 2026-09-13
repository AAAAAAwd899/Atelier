"""Release finish: real SQLite/read-only aggregates and cache/group contracts.
Native image decoding, export dialogs and Anki learning are explicit stand-ins.
"""
import ast,copy,importlib,json,sys,types,sqlite3,time,os,threading,hashlib
from pathlib import Path
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace as NS
import pytest
R=Path(__file__).resolve().parents[1];S=R/'src'
pkg=types.ModuleType('finish_test');pkg.__path__=[str(S)];sys.modules[pkg.__name__]=pkg
core=importlib.import_module('finish_test.core');fc=importlib.import_module('finish_test.focus_context');pr=importlib.import_module('finish_test.study_progress');cache=importlib.import_module('finish_test.figure_cache')
storage=importlib.import_module('finish_test.workshop.storage');docs=importlib.import_module('finish_test.workshop.documents')

@pytest.mark.parametrize('limit',[25,100,1000])
def test_cache_is_bounded_and_returns_independent_values(limit):
 c=cache.PreviewCache(limit,3)
 for n in range(12):c.get_or_create(n,lambda:{'n':n,'data':['x']})
 assert c.bytes<=limit and len(c._items)<=3
 data=c.get_or_create('a',lambda:{'value':[1]});data['value'].append(2)
 assert c.get_or_create('a',lambda:pytest.fail('miss'))=={'value':[1]}
 c.clear();assert c.bytes==0 and not c._items

def test_cache_does_not_store_failed_or_oversized_previews():
 c=cache.PreviewCache(100,2)
 for i in range(2):
  with pytest.raises(ValueError):c.get_or_create('fail',lambda:(_ for _ in ()).throw(ValueError('failed')))
 assert not c._items
 assert len(c.get_or_create('huge',lambda:'x'*101))==101 and not c._items
 assert c.get_or_create('fail',lambda:'okay')=='okay'

def test_same_page_requests_render_once_across_workers():
 c=cache.PreviewCache();calls=[]
 def create():calls.append(1);time.sleep(.01);return {'image':'one original render'}
 with ThreadPoolExecutor(8) as pool:out=list(pool.map(lambda _:c.get_or_create('page',create),range(20)))
 assert len(calls)==1 and len(out)==20 and c.hits==19

@pytest.fixture
def images(tmp_path):
 st=storage.Store(tmp_path);p=st.project({'title':'Cache fixture','cover':'botanical'})
 blob=st.save_blob(b'\x89PNG\r\n\x1a\n' + b'original-image-data'*400,'png')
 src=st.add_source(p['id'],'Illustrated lecture','pptx',[{'text':'Page one','assets':[{'blob':blob,'label':f'Figure {i}'} for i in range(40)]},{'text':'Page two'}])['source']
 return st,src,blob

def test_page_open_does_not_read_or_encode_embedded_figures(images,monkeypatch):
 st,source,blob=images;fp=cache.FigurePreviews(st);calls=[]
 original=docs.data_url
 monkeypatch.setattr(docs,'data_url',lambda p:(calls.append(p),original(p))[1])
 old=docs.render_page(st,source['version_id'],1,1600);assert len(calls)==40
 calls.clear();new=fp.page(source['version_id'],1,1600)
 assert not calls and new['text']==old['text'] and new['asset_count']==40
 assert all(x['preview_pending'] and not x['image'] for x in new['assets'])
 assert len(json.dumps(new))<len(json.dumps(old))*.03
 assert fp.page(source['version_id'],1,1600)==new and fp.cache.hits==1
 assert fp.image(blob)['image']==old['assets'][0]['image']
 assert st.blob_path(blob).read_bytes().endswith(b'original-image-data'*400)

def test_source_revision_page_size_and_blob_changes_invalidate_cache(images):
 st,s,b=images;f=cache.FigurePreviews(st);vid=s['version_id'];f.page(vid,1);f.page(vid,1);f.page(vid,2);f.page(vid,1,1200)
 assert f.cache.misses==3 and f.cache.hits==1
 v=st.get('version',vid);v['pages'][0]['text']='Revised current source';st.put('version',vid,{k:x for k,x in v.items() if k not in ('id','revision','updated')},v['revision'])
 assert f.page(vid,1)['text']=='Revised current source' and f.cache.misses==4

@pytest.mark.parametrize('page,width',[(0,1600),(3,1600),(True,1600),(1,10),(1,2201)])
def test_bad_page_or_size_stays_in_original_validation(images,page,width):
 st,s,b=images
 with pytest.raises(ValueError):cache.FigurePreviews(st).page(s['version_id'],page,width)

@pytest.mark.parametrize('path',['../other.png','http://example.org/image.png','x.png','',None])
def test_image_cache_does_not_bypass_source_path_validation(images,path):
 st,s,b=images
 with pytest.raises((ValueError,TypeError)):cache.FigurePreviews(st).image(path,360)

CAT={'1':{'name':'Current course','filtered':False},'2':{'name':'Current course::Lecture 2','filtered':False},'3':{'name':'Current course::Lecture 10','filtered':False},'4':{'name':'Old course','filtered':False},'5':{'name':'Filtered','filtered':True}}
def profile():return {'studies':[{'id':'active','name':'Course exam','deck_ids':['1'],'active':True,'date':''},{'id':'old','name':'Old course','deck_ids':['4'],'active':False}]}
def col_stub(cat=CAT):return NS(decks=NS(all_names_and_ids=lambda include_filtered=True:[NS(id=int(i),name=x['name']) for i,x in cat.items() if include_filtered or not x.get('filtered')]))

def test_group_projection_has_no_plan_writes_and_original_scope():
 o=NS(profile=profile());before=copy.deepcopy(o.profile);g=fc.groups(o,CAT);e=fc.group_exam(o,col_stub(),'active')
 assert len(g)==1 and g[0]['available'] and g[0]['deck_ids']==['1']
 assert e.id==fc.session_id('active') and [s.deck_id for s in e.scopes]==[1] and not e.query
 assert o.profile==before and fc.active_deck_ids(o.profile,CAT)=={'1','2','3'}

@pytest.mark.parametrize('decks',[['999'],['5'],[],[str(2**53)]])
def test_invalid_group_is_visible_but_unavailable(decks):
 p=profile();p['studies'][0]['deck_ids']=decks;o=NS(profile=p)
 assert not fc.groups(o,CAT)[0]['available']
 with pytest.raises(ValueError):fc.group_exam(o,col_stub(),'active')

def test_nested_roots_deduplicate_and_inactive_groups_cannot_start():
 p=profile();p['studies'][0]['deck_ids']=['2','1','2'];o=NS(profile=p)
 assert [x.deck_id for x in fc.group_exam(o,col_stub(),'active').scopes]==[1]
 p['studies'][0]['active']=False
 with pytest.raises(ValueError):fc.group_exam(o,col_stub(),'active')
 assert not fc.active_deck_ids(p,CAT)

def test_saved_group_uses_original_sample_decks_after_shortcut_is_removed():
 o=NS(profile={'studies':[]});e=fc.saved_group_exam(o,col_stub(),fc.session_id('removed'),[2,3,2])
 assert e.name=='Saved study group' and [s.deck_id for s in e.scopes]==[2,3]
 assert o.profile=={'studies':[]}

@pytest.mark.parametrize('id,ids',[('notgroup',[2]),(fc.session_id('x'),[]),(fc.session_id('x'),[0]),(fc.session_id('x'),[2**53])])
def test_saved_group_invalid_input_is_refused(id,ids):
 with pytest.raises(ValueError):fc.saved_group_exam(NS(profile={}),col_stub(),id,ids)

class DB:
 def __init__(self):self.cx=sqlite3.connect(':memory:');self.reads=0
 def all(self,q,*args):self.reads+=1;return self.cx.execute(q,args).fetchall()

@pytest.fixture
def history():
 db=DB();db.cx.executescript('CREATE TABLE cards(id INTEGER PRIMARY KEY,did INTEGER,odid INTEGER);CREATE TABLE revlog(id INTEGER PRIMARY KEY,cid INTEGER,ease INTEGER,type INTEGER,time INTEGER);')
 db.cx.executemany('INSERT INTO cards VALUES(?,?,?)',[(11,2,0),(12,3,0),(13,4,0),(14,5,2)])
 cut=int(datetime(2026,9,13,4).timestamp());today=cut-86400;ms=lambda s:int(s*1000)
 rows=[(ms(today+10),11,3,1,60000),(ms(today+20),11,1,1,30000),(ms(today-86400+10),12,3,0,30000),
       (ms(today+30),13,3,1,90000),(ms(today+40),14,2,3,30000),(ms(today+50),11,0,4,60000),
       (ms(today+60),11,3,4,60000),(ms(today+70),999,3,1,60000),(ms(cut-9*86400),11,3,1,60000)]
 db.cx.executemany('INSERT INTO revlog VALUES(?,?,?,?,?)',rows)
 c=col_stub();c.db=db;c.sched=NS(day_cutoff=cut)
 return c,ms(cut-3600)

def test_read_only_review_metrics_separate_events_cards_manual_and_orphans(history):
 c,now=history;before=c.db.cx.total_changes;r=pr.read_progress(c,profile(),'active',7,now)
 assert (r['reviews'],r['cards'],r['again'],r['minutes'],r['days_studied'])==(4,3,1,2.5,2)
 assert sum(x['reviews'] for x in r['daily'])==4 and sum(x['again'] for x in r['daily'])==1
 assert c.db.reads==3 and c.db.cx.total_changes==before
 assert {x['id'] for x in r['decks']}=={'2','3'}
 assert 'Deleted cards' in r['attribution']

@pytest.mark.parametrize('scope,days,answers',[('all',7,5),('active',30,5),('active',7,4)])
def test_scope_and_period_affect_exact_native_history(history,scope,days,answers):
 c,now=history;r=pr.read_progress(c,profile(),scope,days,now)
 assert r['reviews']==answers and len(r['daily'])==days

def test_empty_active_scope_does_not_fall_back_to_old_cards(history):
 c,now=history;r=pr.read_progress(c,{'studies':[]},'active',7,now)
 assert r['reviews']==0 and r['deck_count']==0 and c.db.reads==0

@pytest.mark.parametrize('scope,days',[('deleted',7),('old',7),('active',1),('all',True),('all','7')])
def test_invalid_scopes_and_periods_are_rejected(history,scope,days):
 c,now=history
 with pytest.raises(ValueError):pr.read_progress(c,profile(),scope,days,now)

@pytest.mark.parametrize('date,expected_hours',[(datetime(2026,3,9,4),23),(datetime(2026,11,2,4),25)])
def test_study_day_uses_civil_rollover_across_dst(date,expected_hours,monkeypatch):
 # Windows has no time.tzset(). Inject only the local clock boundary; exercise
 # the same real civil-day algorithm and both 23/25-hour assertions everywhere.
 from zoneinfo import ZoneInfo
 zone=ZoneInfo('America/Chicago')
 class ChicagoClock(datetime):
  @classmethod
  def fromtimestamp(cls,value,tz=None):return datetime.fromtimestamp(value,tz or zone)
 monkeypatch.setattr(pr,'datetime',ChicagoClock)
 date=date.replace(tzinfo=zone)
 col=col_stub();col.sched=NS(day_cutoff=int(date.timestamp()));r=pr.read_progress(col,{'studies':[]},'active',7,int(date.timestamp()*1000))
 assert any(round((x['end']-x['start'])/3600000)==expected_hours for x in r['daily'])

def methods(text):
 tree=ast.parse(text);out={}
 for n in tree.body:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):out[n.name]=ast.dump(n,include_attributes=False)
  elif isinstance(n,ast.ClassDef):
   for f in n.body:
    if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)):out[n.name+'.'+f.name]=ast.dump(f,include_attributes=False)
 return out

CHANGES={'sprout/integration.py':{'PlannerDialog.bridge','PlannerDialog._pip_study','PlannerDialog._resume_exam','PlannerDialog._review_misses'},'workshop/integration.py':{'Workspace.__init__','Workspace.base_state','Workspace.bridge'},'card_studio.py':{'command'}}
@pytest.mark.parametrize('file',list(CHANGES))
def test_all_unaffected_native_methods_remain_semantically_identical(file):
 old=methods((R/'tests/data/finish-rc3'/file).read_text());new=methods((S/file).read_text())
 differing={n for n,s in old.items() if new.get(n)!=s}
 assert differing<=CHANGES[file],differing-CHANGES[file]
 assert all(n in new for n in old)

def test_publishing_and_native_rating_algorithm_files_unchanged():
 baseline=json.loads((R/'usability-baseline.json').read_text())
 for f,h in baseline.items():
  if f.startswith('sprout/') and f not in ('sprout/integration.py','sprout/web/app.js') or f.startswith('workshop/') and f not in ('workshop/integration.py','workshop/web/app.js','workshop/INTEGRATION-NOTE.md'):
   assert hashlib.sha256((S/f).read_bytes()).hexdigest()==h,f

# Compile the actual changed handler, using strict host stand-ins and the original
# real draft/session serialization. No substitute implementation of the handler.
def planner_method(name,namespace):
 tree=ast.parse((S/'sprout/integration.py').read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PlannerDialog')
 method=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name))
 module=ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
 env={'__package__':'finish_test.sprout',**namespace};exec(compile(module,str(S/'sprout/integration.py'),'exec'),env)
 return env[name]

@pytest.fixture
def saved_group(tmp_path,monkeypatch):
 sc=importlib.import_module('finish_test.sprout.core');sd=importlib.import_module('finish_test.sprout.drafts')
 se=importlib.import_module('finish_test.sprout.exam_session');ss=importlib.import_module('finish_test.sprout.storage')
 st=ss.Store(tmp_path);session=se.ExamSession(fc.session_id('deleted'),[sc.CardInfo(11,21,2),sc.CardInfo(12,22,3)],'practice',25)
 session.pip_study=True;session.allow_new_learning=False;session.save_response('Keep my answer');session.flags.add(12);session.reveal();session.grade(1);sd.save_draft(st,session)
 col=col_stub();col.find_cards=lambda q:[11,12];owner=NS(profile={'studies':[]});ctrl=NS(runner=None,suite=owner,responses={});calls=[]
 class Runner:
  def __init__(self,controller,exam,cards,kind,minutes,finished):self.exam=exam;self.cards=cards;self.session=None;self.opened=False
  def open(self):self.opened=True
  def force_close(self):self.opened=False
 m=types.ModuleType('finish_test.sprout.runner');m.ExamRunner=Runner;monkeypatch.setitem(sys.modules,m.__name__,m)
 w=NS(controller=ctrl,mw=NS(col=col,state='deckBrowser'),store=st,hide=lambda:calls.append('hide'),_runner_finished=lambda:None)
 w.query=lambda rid,fn,done:done(fn(col))
 return w,sd,session,calls

def test_group_resume_real_saved_format_uses_owner_not_nonexistent_deck_id(saved_group):
 w,sd,s,calls=saved_group;before=(w.store.folder/'active_exam.json').read_bytes()
 f=planner_method('_resume_exam',{'load_draft':sd.load_draft});result=f(w,'1')
 r=w.controller.runner
 assert r.opened and r.session.id==s.id and r.session.index==1 and r.session.responses[11]=='Keep my answer'
 assert r.session.flags=={12} and r.session.deadline==s.deadline and not r.session.allow_new_learning
 assert [x.deck_id for x in r.exam.scopes]==[2,3] and r.exam.name=='Saved study group'
 assert (w.store.folder/'active_exam.json').read_bytes()==before and calls==['hide'] and not w.store.state['exams']

@pytest.mark.parametrize('reason',['deleted_card','window_open_failure','another_session','review_active'])
def test_failed_group_resume_does_not_delete_saved_work(saved_group,reason,monkeypatch):
 w,sd,s,calls=saved_group;before=(w.store.folder/'active_exam.json').read_bytes()
 if reason=='deleted_card':w.mw.col.find_cards=lambda q:[11]
 if reason=='window_open_failure':
  monkeypatch.setattr(sys.modules['finish_test.sprout.runner'].ExamRunner,'open',lambda self:(_ for _ in ()).throw(RuntimeError('Qt closed')))
 if reason=='another_session':w.controller.runner=object()
 if reason=='review_active':w.mw.state='review'
 with pytest.raises((ValueError,RuntimeError)):planner_method('_resume_exam',{'load_draft':sd.load_draft})(w,'2')
 assert (w.store.folder/'active_exam.json').read_bytes()==before and not calls
 if reason!='another_session':assert w.controller.runner is None

@pytest.mark.parametrize('change',['removed','different_scope','session_started','same_scope'])
def test_group_sampling_revalidates_scope_and_session_after_background_read(monkeypatch,change):
 sc=importlib.import_module('finish_test.sprout.core');calls=[];owner=NS(profile=profile());col=col_stub();ctrl=NS(runner=None,suite=owner)
 class Runner:
  def __init__(self,controller,exam,cards,kind,minutes,finished):self.exam=exam;self.cards=cards
  def open(self):calls.append('open')
  def force_close(self):calls.append('close')
 m=types.ModuleType('finish_test.sprout.runner');m.ExamRunner=Runner;monkeypatch.setitem(sys.modules,m.__name__,m)
 queued=[];w=NS(controller=ctrl,mw=NS(col=col,state='deckBrowser'),store=NS(state={'history':[]}),hide=lambda:calls.append('hide'),_runner_finished=lambda:None,
  _session_options=lambda cards,snap,mode:{},_configure_runner=lambda runner,opt:calls.append(opt),query=lambda rid,fn,done:queued.append((fn,done)))
 env={'native_learning_available':lambda c:True,'bounded_int':sc.bounded_int,'MAX_QUESTIONS':500,'deepcopy':copy.deepcopy,
 'read_exam_snapshot':lambda c,e,h:NS(exam=e),'sample_exam':lambda e,s,n,**kw:(NS(cards=[sc.CardInfo(11,21,2)]),{})}
 planner_method('_pip_study',env)(w,'x',{'group_id':'active','teach_new':False,'size':20})
 if change=='removed':owner.profile['studies'][0]['active']=False
 if change=='different_scope':owner.profile['studies'][0]['deck_ids']=['3']
 if change=='session_started':ctrl.runner=object()
 fn,done=queued[0]
 if change=='same_scope':
  assert done(fn(col))['started'];assert calls[0]['pip_study'] and not calls[0]['teach_new'] and calls[-1]=='hide'
 else:
  with pytest.raises(ValueError):done(fn(col))
  assert not calls

@pytest.mark.parametrize('did,valid',[(2,True),('2',True),('999',False),('2 OR 1=1',False),(True,False)])
def test_export_handoff_opens_original_options_only_for_existing_deck(monkeypatch,did,valid):
 calls=[];m=types.ModuleType('aqt.import_export.exporting');m.ExportDialog=lambda mw,**kw:(calls.append(kw),NS())[1]
 monkeypatch.setitem(sys.modules,m.__name__,m);mw=NS(col=col_stub())
 if valid:pr.export_deck(mw,did);assert calls==[{'did':2}]
 else:
  with pytest.raises(ValueError):pr.export_deck(mw,did)
  assert not calls

@pytest.mark.parametrize('animated,expected',[(False,True),(True,False)])
def test_thumbnail_decoder_uses_scaled_qimage_not_pixmap_and_original_action_is_exact(images,monkeypatch,animated,expected):
 st,s,blob=images;calls=[]
 class Size:
  def __init__(self,w,h):self.w=w;self.h=h
  def width(self):return self.w
  def height(self):return self.h
 class Reader:
  def __init__(self,path):calls.append(path);self.dim=Size(4000,2000)
  def size(self):return self.dim
  def supportsAnimation(self):return animated
  def setScaledSize(self,sz):self.dim=sz;calls.append((sz.w,sz.h))
  def read(self):
   size=self.dim
   def save(buf,fmt):buf.data.extend(b'thumbnail');return True
   return NS(isNull=lambda:False,width=size.width,height=size.height,save=save)
 class Buffer:
  def __init__(self,data):self.data=data
  def open(self,*args):pass
  def close(self):pass
 gui=types.ModuleType('PyQt6.QtGui');gui.QImageReader=Reader
 qt=types.ModuleType('PyQt6.QtCore');qt.QSize=Size;qt.QByteArray=bytearray;qt.QBuffer=Buffer;qt.QIODevice=NS(OpenModeFlag=NS(WriteOnly=2))
 monkeypatch.setitem(sys.modules,'PyQt6.QtGui',gui);monkeypatch.setitem(sys.modules,'PyQt6.QtCore',qt)
 fp=cache.FigurePreviews(st);thumb=fp.image(blob,360);assert thumb['preview']==expected
 if expected:assert (360,180) in calls and thumb['width']==360
 original=fp.image(blob);assert not original['preview'] and original['image']==docs.data_url(st.blob_path(blob))

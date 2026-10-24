"""Actual Anki backend move/Undo, isolated disposable collection, never owner data."""
from pathlib import Path
import sys,types,importlib,json,time,traceback,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
from anki.collection import Collection
from anki import buildinfo
pkg=types.ModuleType('atelier_move_qa');pkg.__path__=[str(ROOT/'src')];sys.modules[pkg.__name__]=pkg
core=importlib.import_module(pkg.__name__+'.core')
OUT=ROOT/'output/native-move-108';OUT.mkdir(parents=True,exist_ok=True)
db=OUT/('qa-'+str(time.time_ns())+'.anki2')
report={'category':'actual Anki backend; synthetic collection; no GUI or hardware claim','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'checks':{},'errors':[],'owner_profile_accessed':False}
col=Collection(str(db))
try:
    source=col.decks.id('Course A::Exam');child=col.decks.id('Course A::Exam::Lecture');target=col.decks.id('Course B');other=col.decks.id('Other')
    model=col.models.by_name('Basic')
    for did in [source,child,other]:
        note=col.new_note(model);note['Front']='Synthetic question '+str(did);note['Back']='Synthetic answer';col.add_note(note,did)
    media=Path(col.media.dir())/'preserved.txt';media.write_text('Synthetic preserved media')
    def cards():return col.db.all('select id,nid,did,ord,type,queue,due,ivl,factor,reps,lapses,left,odue,odid,flags,data from cards order by id')
    before=cards();history=col.db.all('select * from revlog');notes=col.db.all('select * from notes order by id')
    check=report['checks'];catalog=core.fresh_catalog(col)
    def rejected(did,parent,expected):
        try:core.validate_move(core.fresh_catalog(col),str(did),str(parent),expected)
        except core.ValidationError:return True
        return False
    check['self_and_descendant_rejected']=rejected(source,source,'Course A::Exam') and rejected(source,child,'Course A::Exam')
    check['stale_source_rejected']=rejected(source,target,'Old name')
    collision=col.decks.id('Course B::Exam')
    check['name_collision_rejected']=rejected(source,target,'Course A::Exam')
    col.decks.rename(col.decks.get(collision),'Course B::Existing')
    s,t=core.validate_move(core.fresh_catalog(col),str(source),str(target),'Course A::Exam')
    col.decks.reparent(deck_ids=[int(s)],new_parent=int(t))
    check['branch_paths_moved']=col.decks.get(source)['name']=='Course B::Exam' and col.decks.get(child)['name']=='Course B::Exam::Lecture'
    check['card_ids_and_scheduling_unchanged']=cards()==before
    check['note_contents_and_review_history_unchanged']=col.db.all('select * from notes order by id')==notes and col.db.all('select * from revlog')==history
    check['media_unchanged']=media.read_text()=='Synthetic preserved media'
    check['study_scope_ids_still_resolve']=all(str(did) in core.fresh_catalog(col) for did in [source,child,other])
    col.undo()
    check['native_undo_restores_branch']=col.decks.get(source)['name']=='Course A::Exam' and col.decks.get(child)['name']=='Course A::Exam::Lecture' and cards()==before
    s,t=core.validate_move(core.fresh_catalog(col),str(source),'0','Course A::Exam');col.decks.reparent(deck_ids=[int(s)],new_parent=int(t))
    check['move_to_top_level_keeps_contents']=col.decks.get(source)['name']=='Exam' and col.decks.get(child)['name']=='Exam::Lecture' and cards()==before
    col.undo();check['top_level_undo_restores_original']=col.decks.get(source)['name']=='Course A::Exam' and cards()==before
    check['database_integrity']=col.db.scalar('pragma integrity_check')=='ok'
except Exception:report['errors'].append(traceback.format_exc())
finally:
    col.close();report['closed_collection_sha256']=hashlib.sha256(db.read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if report['errors'] or not all(report['checks'].values()):raise SystemExit(1)

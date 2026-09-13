"""Real Anki backend transaction/order probe in a new disposable synthetic collection."""
from pathlib import Path
import sys,types,importlib,json,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
from anki.collection import Collection
from anki import buildinfo
pkg=types.ModuleType('atelier_folder_qa');pkg.__path__=[str(ROOT/'src')];sys.modules[pkg.__name__]=pkg
folder=importlib.import_module(pkg.__name__+'.folder_study')
OUT=ROOT/'output/native-folder';OUT.mkdir(parents=True,exist_ok=True)
report={'category':'actual Anki backend; isolated synthetic collection; no GUI or hardware claim','anki':buildinfo.version,'build':buildinfo.buildhash,'runtime_sha256':runtime_digest(),'checks':{},'errors':[],'owner_profile_accessed':False}
col=Collection(str(OUT/('qa-'+str(time.time_ns())+'.anki2')))
try:
    parent=col.decks.id('Folder QA::Exam');lectures=[col.decks.id(f'Folder QA::Exam::Lecture {n}') for n in range(1,4)];unrelated=col.decks.id('Unrelated QA')
    model=col.models.by_name('Basic')
    for did in lectures+[unrelated]:
        for n in range(9):
            note=col.new_note(model);note['Front']=f'Synthetic recall {did} / {n}';note['Back']='Synthetic answer';col.add_note(note,did)
    ids=[parent,*lectures,unrelated]
    before_ids={did:col.decks.get(did)['conf'] for did in ids}
    before=col.decks.get_deck_configs_for_update(parent)
    original={row.config.id:row.config.SerializeToString() for row in before.all_config}
    globals_before={name:getattr(before,name,None) for name in folder.GLOBAL_FIELDS}
    try:folder.select_folder(col,str(parent),'Folder QA::Exam','shuffle')
    except folder.ValidationError as e:
        report['supported']=False;report['supported_fallback']=str(e)
        report['checks']['unsupported_host_leaves_presets_unchanged']={did:col.decks.get(did)['conf'] for did in ids}==before_ids
    else:
        report['supported']=True
        after=col.decks.get_deck_configs_for_update(parent)
        checks=report['checks'];checks['parent_isolated']=col.decks.get(parent)['conf']!=before_ids[parent]
        checks['lectures_and_unrelated_keep_presets']=all(col.decks.get(did)['conf']==before_ids[did] for did in lectures+[unrelated])
        checks['all_original_preset_bytes_preserved']=all(any(row.config.id==cid and row.config.SerializeToString()==data for row in after.all_config) for cid,data in original.items())
        checks['global_flags_preserved']={name:getattr(after,name,None) for name in folder.GLOBAL_FIELDS}==globals_before
        col.undo();restored=col.decks.get_deck_configs_for_update(parent)
        checks['native_undo_restores_parent_and_preset_set']=all(col.decks.get(did)['conf']==before_ids[did] for did in ids) and {row.config.id:row.config.SerializeToString() for row in restored.all_config}==original
        folder.select_folder(col,str(parent),'Folder QA::Exam','shuffle');count=len(col.decks.get_deck_configs_for_update(parent).all_config)
        folder.select_folder(col,str(parent),'Folder QA::Exam','shuffle');checks['repeat_does_not_clone_again']=len(col.decks.get_deck_configs_for_update(parent).all_config)==count
        queued=col._backend.get_queued_cards(fetch_limit=50,intraday_learning_only=False)
        order=[int(row.card.deck_id) for row in queued.cards];report['native_queue_deck_ids']=order
        report['lecture_ids']=lectures;checks['native_queue_keeps_scope']=bool(order) and set(order)<=set(lectures)
        checks['native_queue_contains_multiple_lectures']=len(set(order))>1
except Exception:report['errors'].append(traceback.format_exc())
finally:col.close();(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

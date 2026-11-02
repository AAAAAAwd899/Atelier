"""Actual installed Anki backend, disposable collection, no desktop windows."""
from pathlib import Path
import sys, types, importlib, json, time, traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
from anki.collection import Collection
from anki import buildinfo
pkg=types.ModuleType('atelier_order_qa');pkg.__path__=[str(ROOT/'src')];sys.modules[pkg.__name__]=pkg
core=importlib.import_module(pkg.__name__+'.core')
OUT=ROOT/'output/native-folder-order-111';OUT.mkdir(parents=True,exist_ok=True)
db=OUT/('qa-'+str(time.time_ns())+'.anki2')
report={'category':'actual Anki backend; synthetic collection; no GUI claim','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'checks':{},'errors':[],'owner_profile_accessed':False}
col=Collection(str(db))
try:
    a=col.decks.id('Biology');b=col.decks.id('Chemistry');x=col.decks.id('Biology::Cells');y=col.decks.id('Biology::Plants')
    for did in [x,y,b]:
        note=col.new_note(col.models.by_name('Basic'));note['Front']='Synthetic question';note['Back']='Synthetic answer';col.add_note(note,did)
    def snapshot():return {t:col.db.all('select * from '+t+' order by id') for t in ['cards','notes','revlog','decks']}
    before=snapshot();catalog=core.folder_order_catalog(col)
    root=[str(b),str(a)];report['deck_tree_root_ids']=[str(n.deck_id) for n in col.decks.deck_tree().children];report['snapshot_root_ids']=[n['id'] for n in core.collection_snapshot(col)['nodes'] if n['parent']=='0'];p,order=core.validate_folder_order(catalog,'0',root)
    nested,lectures=core.validate_folder_order(catalog,str(a),[str(y),str(x)])
    store=core.ProfileStore(OUT/'preferences',str(db.parent/'Synthetic'))
    data=store.read();data['folder_order']={p:order,nested:lectures};store.write(data)
    check=report['checks'];check['visible_tree_matches_snapshot']=set(catalog)=={n['id'] for n in core.collection_snapshot(col)['nodes']};check['root_order_roundtrip']=store.read()['folder_order']['0']==root
    check['nested_order_roundtrip']=store.read()['folder_order'][str(a)]==[str(y),str(x)]
    check['cards_notes_decks_and_review_history_unchanged']=snapshot()==before
    old=store.read();del old['folder_order']['0'];store.write(old)
    check['reset_parent_preserves_other_order']=store.read()['folder_order']=={str(a):[str(y),str(x)]}
    col.decks.id('Biology::New lecture')
    try:core.validate_folder_order(core.folder_order_catalog(col),str(a),lectures)
    except core.ValidationError:check['stale_membership_rejected']=True
    else:check['stale_membership_rejected']=False
    note=col.new_note(col.models.by_name('Basic'));note['Front']='Default card';note['Back']='Synthetic';col.add_note(note,1)
    check['nonempty_default_is_included']='1' in core.folder_order_catalog(col)
    check['database_integrity']=col.db.scalar('pragma integrity_check')=='ok'
except Exception:report['errors'].append(traceback.format_exc())
finally:
    col.close();(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if report['errors'] or not all(report['checks'].values()) or len(report['checks'])!=8:raise SystemExit(1)

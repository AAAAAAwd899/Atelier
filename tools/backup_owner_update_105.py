"""Local, private pre-update backup. Requires Anki to be closed; no collection writes."""
from pathlib import Path
import datetime,hashlib,json,sqlite3,zipfile
BASE=Path.home()/'AppData/Roaming/Anki2'
OUT=Path(__file__).resolve().parents[1]/'output/anki-update-105/private-backup'
OUT.mkdir(parents=True,exist_ok=True)
assert not any(p.stat().st_size for p in BASE.glob('*/collection.anki2-wal')), 'Close Anki before making the backup'
files=[p for p in BASE.glob('prefs21.db*') if p.is_file()]
collections=[]
for p in BASE.glob('*/collection.anki2'):
    db=sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True)
    # quick_check checks structure, not the application-specific index ordering.
    db.create_collation('unicase',lambda a,b:(a.casefold()>b.casefold())-(a.casefold()<b.casefold()))
    assert db.execute('pragma quick_check').fetchone()[0]=='ok',p.parent.name
    collections.append({'profile':p.parent.name,'notes':db.execute('select count(*) from notes').fetchone()[0],'cards':db.execute('select count(*) from cards').fetchone()[0]})
    db.close();files.append(p)
    for folder in ['exam_sprout','workshop']:
        files.extend(q for q in (p.parent/folder).rglob('*') if q.is_file())
addon=BASE/'addons21/daedalus_atelier'
files.extend(p for p in addon.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
files.extend(p for p in (BASE/'addons21').glob('*/meta.json') if p not in files)
manifest={str(p.relative_to(BASE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
dest=OUT/'before-anki-26.09-atelier-1.0.5.zip'
assert not dest.exists(), 'Keep the original pre-update backup'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p in files:z.write(p,str(p.relative_to(BASE)))
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest.items())
receipt={'created':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':manifest,'collections':collections,'zip_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'media':'Not copied: updater does not modify collection.media. Existing media stays in place.','private':True}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'verified_files':len(files),'bytes':dest.stat().st_size,'collection_quick_check':'ok','backup':str(dest)}))

"""Actual installed Anki export/import and native answer activity in disposable data."""
from pathlib import Path
import sys,types,importlib,json,time,traceback,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
from anki.collection import Collection,ImportAnkiPackageRequest
from anki import buildinfo
import anki.lang
anki.lang.set_lang('en_US')
pkg=types.ModuleType('atelier_sharing_qa');pkg.__path__=[str(ROOT/'src')];sys.modules[pkg.__name__]=pkg
sharing=importlib.import_module(pkg.__name__+'.folder_sharing');journey=importlib.import_module(pkg.__name__+'.companion_journey')
OUT=ROOT/'output/native-sharing-116';OUT.mkdir(parents=True,exist_ok=True)
stage=OUT/'stage';stage.mkdir(exist_ok=True)
assert not list(stage.iterdir()),'Reclaim the prior diagnosed stage before another run.'
report={'category':'Actual installed Anki backend; synthetic collection and native answer events; no live hosting claim','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'checks':{},'errors':[],'owner_profile_accessed':False}
col=Collection(str(stage/'source.anki2'));recipient=None

def check(name,ok):
 report['checks'][name]=bool(ok)
 assert ok,name

def snapshot(c):return {t:c.db.all('select * from '+t+' order by id') for t in ['cards','notes','revlog','decks']}
try:
 a=col.decks.id('Cardiology');x=col.decks.id('Cardiology::Lecture 1');b=col.decks.id('Pharmacotherapy');y=col.decks.id('Pharmacotherapy::Lecture 2');other=col.decks.id('Private course')
 media=Path(col.media.dir());(media/'shared.png').write_bytes((ROOT/'src/sprout/web/pip/companion-green-1.0.3.png').read_bytes())
 (media/'_unrelated-private.png').write_bytes(b'PRIVATE STATIC FILE')
 (media/'unrelated-private.png').write_bytes(b'PRIVATE FILE')
 for i in range(12):
  n=col.new_note(col.models.by_name('Basic'));n['Front']=f'Question {i} <img src="shared.png">';n['Back']='Answer';col.add_note(n,x if i<6 else y)
 n=col.new_note(col.models.by_name('Basic'));n['Front']='Private material';n['Back']='Do not share';col.add_note(n,other)
 roots=[str(a),str(x),str(b)];scope=sharing.inspect_scope(col,roots)
 check('Two parent courses include lectures, and overlap counts once',scope['card_count']==12 and scope['deck_count']==4)
 before=snapshot(col);path=stage/'shared.apkg';meta=sharing.export_scope(col,roots,path)
 check('Native export preserves source cards, notes, decks and history',snapshot(col)==before)
 check('Native APKG is bounded and SHA-checked',0<meta['bytes']<=41943040 and len(meta['sha256'])==64)
 recipient=Collection(str(stage/'recipient.anki2'))
 recipient.import_anki_package(ImportAnkiPackageRequest(package_path=str(path)))
 check('Native import contains only the selected twelve cards',recipient.card_count()==12 and not recipient.find_notes('Private material'))
 check('Parent and lecture names survive native export/import',all(recipient.decks.by_name(n) for n in ['Cardiology','Cardiology::Lecture 1','Pharmacotherapy','Pharmacotherapy::Lecture 2']))
 check('Unselected and unreferenced media do not leave the attached courses',not (Path(recipient.media.dir())/'_unrelated-private.png').exists() and not (Path(recipient.media.dir())/'unrelated-private.png').exists())
 check('Referenced image bytes survive native export/import',(Path(recipient.media.dir())/'shared.png').read_bytes()==(media/'shared.png').read_bytes())
 check('Export does not give recipient the publisher review history',recipient.db.scalar('select count(*) from revlog')==0)
 old_ids=set(recipient.find_notes(''))
 time.sleep(1.1)  # Native note modification timestamps have one-second precision.
 note=col.get_note(col.find_notes('deck:"Cardiology::Lecture 1"')[0]);note['Back']='Updated explanation';col.update_note(note)
 changed=sharing.inspect_scope(col,roots);check('Editing card content changes the folder publication digest',changed['digest']!=scope['digest'])
 sharing.export_scope(col,roots,path);recipient.import_anki_package(ImportAnkiPackageRequest(package_path=str(path)))
 check('Importing a later version retains note identity instead of duplicating',set(recipient.find_notes(''))==old_ids and recipient.card_count()==12)
 check('Updated card explanation reaches recipient through native import',len(recipient.find_notes('back:"Updated explanation"'))==1)
 before_answer=sharing.inspect_scope(col,roots)['digest'];col.decks.select(a)
 for i in range(10):
  if i==6:col.decks.select(b)
  cards=col.sched.get_queued_cards(fetch_limit=1)
  if not cards or not cards.cards:raise RuntimeError('Native scheduler did not supply a card')
  card=col.get_card(cards.cards[0].card.id)
  card.start_timer()
  col.sched.answer_card(col.sched.build_answer(card=card,states=cards.cards[0].states,rating=3))
 status=journey.status(col,{})
 check('Real native answer events unlock the first keepsake',status['reviews']==10 and status['days_studied']==1 and status['rewards'][0]['eligible'])
 check('Normal review alone does not republish folder content',sharing.inspect_scope(col,roots)['digest']==before_answer)
 saved=journey.claim(col,{},'journal')
 check('Claim stores a permanent local earned timestamp','journal' in saved['earned'])
 try:journey.claim(col,{},'greenhouse')
 except ValueError:check('Unmet seven-day keepsake cannot be forged by a client command',True)
 else:check('Unmet seven-day keepsake cannot be forged by a client command',False)
 check('Source and recipient collection integrity',col.db.scalar('pragma integrity_check')=='ok' and recipient.db.scalar('pragma integrity_check')=='ok')
 report['export']={k:v for k,v in meta.items() if k!='card_ids'}
except Exception:report['errors'].append(traceback.format_exc())
finally:
 col.close()
 if recipient:recipient.close()
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'anki':report['anki'],'checks':len(report['checks']),'errors':report['errors']},indent=2))
 # Only successful disposable payloads are reclaimed; receipts remain.
 if not report['errors']:
  assert stage.resolve().is_relative_to(OUT.resolve());shutil.rmtree(stage)
if report['errors'] or not all(report['checks'].values()):raise SystemExit(1)

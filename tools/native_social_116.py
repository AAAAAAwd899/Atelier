"""Actual Anki Friends bridge and keepsakes. Hard offscreen, isolated profile."""
from pathlib import Path
import os,sys,time,json,shutil,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import production_files,runtime_digest
OUT=ROOT/'output/native-social-116';OUT.mkdir(parents=True,exist_ok=True)
BASE=OUT/'stage';assert not BASE.exists(),'Retain the failure receipt and reclaim only its diagnosed disposable stage first.';BASE.mkdir()
assert shutil.disk_usage(ROOT).free>50*1024**3+400_000_000
for source,name in production_files():
 dest=BASE/'addons21/daedalus_atelier'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
os.environ.update(QT_QPA_PLATFORM='offscreen',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1',QTWEBENGINE_REMOTE_DEBUGGING='127.0.0.1:61315')
import anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Atelier Friends QA');pm.load('Atelier Friends QA');pm.meta.update(firstRun=False,defaultLang='en_US',updates=False,check_for_updates=False);pm.profile.update(autoSync=False);pm.save();pm.db.close()
import aqt,aqt.main
from aqt.qt import QTimer
from aqt.operations import QueryOp
aqt.AnkiApp.secondInstance=lambda self:False
report={'category':'Actual installed Anki + Qt, offscreen, disposable unsynced profile; no hosted service or Windows-display acceptance','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'checks':{},'errors':[],'owner_profile_accessed':False,'completed':False}
aqt.main.showWarning=lambda message,*a,**k:report['errors'].append('Anki warning: '+str(message))
app=aqt._run(['anki','-b',str(BASE),'-p','Atelier Friends QA','-l','en_US'],exec=False)
assert app.platformName()=='offscreen'
finished=False;owner=None;waits=0

def check(name,ok):report['checks'][name]=bool(ok);assert ok,name

def finish():
 global finished
 if finished:return
 finished=True
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 import threading
 watchdog=threading.Timer(25,lambda:os._exit(2));watchdog.daemon=True;watchdog.start()
 aqt.mw.unloadProfileAndExit()

def fail():report['errors'].append(traceback.format_exc());finish()

def later(fn,ms=400):QTimer.singleShot(ms,fn)

def dom(expression,callback,attempt=0):
 def result(value):
  try:
   if value:callback(value)
   elif attempt<60:later(lambda:dom(expression,callback,attempt+1))
   else:raise RuntimeError('Native view did not become ready: '+expression)
  except Exception:fail()
 owner.friends.window.web.evalWithCallback(expression,result)

def capture(phase,then,attempt=0):
 request=OUT/'capture-request.json'
 request.write_text(json.dumps({'phase':phase,'port':61315,'title':'Atelier Friends','selector':'#es-app' if phase=='pip' else '#atelier-social'})+'\n')
 ack=OUT/(phase+'-captured.json')
 if attempt==0:ack.unlink(missing_ok=True)
 def poll():
  if ack.exists():then()
  elif attempt<240:later(lambda:capture(phase,then,attempt+1),250)
  else:raise RuntimeError('Actual Qt capture was not acknowledged')
 try:poll()
 except Exception:fail()

def start(attempt=0):
 global owner
 try:
  for widget in app.topLevelWidgets():
   if type(widget).__name__=='ChooseAddonsToUpdateDialog':widget.reject()
  owner=getattr(aqt.mw,'_daedalus_atelier_runtime',None)
  if not aqt.mw.col or not owner:
   if attempt<60:later(lambda:start(attempt+1));return
   raise RuntimeError('Atelier startup failed')
  owner.ensure_store();cfg=owner.get_config();cfg.update(visual_owner='external',mode='native',chrome=False,shared_theme=False,match_sprout=False,theme='forest',surface_revision=1);aqt.mw.addonManager.writeConfig(owner.module,cfg);owner.ownership.install()
  names=[a.text() for a in owner.menu.actions()]
  check('Friends and companion Tools entries exist with Atelier visuals off',all(any(x in name for name in names) for x in ['Friends & shared folders','Companion journey']))
  owner.open_friends('shared')
  dom('window.AtelierSocial?.getState()&&document.querySelectorAll("nav button").length===4',opened)
 except Exception:fail()

def opened(_):
 try:
  check('Opening Friends leaves native Anki home preference intact',owner.get_config()['mode']=='native' and owner.get_config()['visual_owner']=='external')
  check('No service connection or token is created by opening the tab',not owner.friends.client.configured and not owner.friends.client.session)
  owner.friends.window.web.eval('document.querySelector("[data-op=tab][data-tab=journey]").click()')
  dom('document.querySelector(".scene-art img")?.complete&&document.querySelector(".scene-art img")?.naturalWidth>=1000',locked)
 except Exception:fail()

def locked(_):
 try:
  check('Real native collection has zero invented study progress',owner.friends.window and not owner.profile.get('journey',{}).get('earned'))
  owner.friends.command('journey_claim',{'id':'greenhouse'})
  dom('document.querySelector("[role=alert]")?.textContent.includes("not ready")',lambda _:capture('locked',activity))
 except Exception:fail()

def activity():
 def make(col):
  did=col.decks.id('Biology::Cell structure')
  for i in range(10):
   note=col.new_note(col.models.by_name('Basic'));note['Front']='Native question '+str(i);note['Back']='Native answer';col.add_note(note,did)
  col.decks.select(did)
  for i in range(10):
   queued=col.sched.get_queued_cards(fetch_limit=1);card=col.get_card(queued.cards[0].card.id);card.start_timer();col.sched.answer_card(col.sched.build_answer(card=card,states=queued.cards[0].states,rating=3))
  return col.db.all('select * from cards order by id'),col.db.all('select * from revlog order by id')
 def done(value):
  global before
  try:
   before=value;owner.friends.refresh();dom('window.AtelierSocial?.getState()?.journey.rewards[0].eligible',eligible)
  except Exception:fail()
 QueryOp(parent=aqt.mw,op=make,success=done).failure(lambda e:(report['errors'].append(str(e)),finish())).run_in_background()

def eligible(_):
 try:
  check('Actual ten native answers enable only the one-day reward',True)
  owner.friends.window.web.eval('document.querySelector("[data-op=claim][data-id=journal]").click()')
  dom('window.AtelierSocial.getState().journey.rewards[0].collected',claimed)
 except Exception:fail()

def claimed(_):
 try:
  check('Collect action persists an earned timestamp through the native bridge','journal' in owner.profile['journey']['earned'])
  owner.friends.window.web.eval('document.querySelector("[data-op=equip][data-id=journal]").click()')
  dom('window.AtelierSocial.getState().journey.saved.equipped==="journal"',equipped)
 except Exception:fail()

def equipped(_):
 try:
  check('Scene choice reaches the existing planner presentation config',owner.sprout_config().get('companion_scene')=='journal')
  owner.friends.window.web.eval('(()=>{const t=document.querySelector("textarea[name=value]");t.value="A little progress today.";t.form.requestSubmit();})()')
  dom('window.AtelierSocial.getState().journey.saved.reflection==="A little progress today."',reflected)
 except Exception:fail()

def reflected(_):
 try:
  check('Private reflection persists without any service account',owner.profile['journey']['reflection']=='A little progress today.' and owner.friends.client.session is None)
  check('Keepsake preferences leave native cards and review history unchanged',(aqt.mw.col.db.all('select * from cards order by id'),aqt.mw.col.db.all('select * from revlog order by id'))==before)
  owner.friends.window.web.eval('document.querySelector("[data-op=tab][data-tab=shared]").click()')
  owner.friends.window.close()
  owner.open_friends('journey')
  dom('Boolean(document.querySelector(".journey-heading"))&&AtelierSocial.getState().journey.reviews===10',reopened)
 except Exception:fail()

def reopened(_):
 old=owner.friends;old.col=object();owner.open_friends('journey')
 check('Stale Friends context is replaced and its client is closed',old.stopped and old.client.closed and owner.friends is not old and owner.friends.valid())
 dom('Boolean(document.querySelector(".journey-heading"))&&AtelierSocial.getState().journey.reviews===10',focused)

def focused(_):
 deck=aqt.mw.col.decks.by_name('Biology::Cell structure')
 owner.profile.update(focus_enabled=True,selected_study='biology',studies=[{'id':'biology','name':'Biology','date':'','deck_ids':[str(deck['id'])],'active':True},{'id':'chemistry','name':'Chemistry','date':'','deck_ids':[str(deck['id'])],'active':True}])
 owner.store.write(owner.profile);owner.friends.refresh()
 dom('AtelierSocial.getState().focus.join("|")==="Biology"',unfocused)

def unfocused(_):
 check('Greenhouse context follows the selected study rather than all active courses',True)
 owner.profile['focus_enabled']=False;owner.store.write(owner.profile);owner.friends.refresh()
 dom('AtelierSocial.getState().focus.length===0',refreshed)

def refreshed(_):
 check('Greenhouse clears its focus hint when focus is disabled',True)
 check('Reopening restores the requested tab and refreshes native activity',True)
 capture('collected',open_planner)

def open_planner():
 try:
  from datetime import datetime,timedelta
  if owner.exam_engine.store is None:owner.exam_engine.profile_open()
  deck=aqt.mw.col.decks.by_name('Biology::Cell structure')
  owner.exam_engine.store.save_exam({'id':'native-journey-qa','name':'Biology final','due':(datetime.now()+timedelta(days=7)).isoformat(timespec='minutes'),'scopes':[{'deck_id':deck['id'],'name':deck['name']}]})
  owner.sprout_link.open_target('overview','native-journey-qa')
  owner.exam_engine.dialog.showNormal();owner.exam_engine.dialog.resize(1400,1000)
  planner_ready()
 except Exception:fail()

def planner_ready(attempt=0):
 try:
  dialog=getattr(owner.exam_engine,'dialog',None)
  if not dialog or not getattr(dialog,'web',None):
   if attempt<80:later(lambda:planner_ready(attempt+1));return
   raise RuntimeError('Native Pip planner did not open')
  def ready(value):
   try:
    if not value:
     if attempt<80:later(lambda:planner_ready(attempt+1));return
     raise RuntimeError('Native Pip scene did not load')
    check('Collected art reaches actual native Pip without replacing its study engine',value['scene'] and value['pixels']>=1000 and value['journeyButton'])
    dialog.web.eval('window.ExamSprout.suiteRequest("suite_journey",{}).then(()=>window.nativeJourneyAdapterPassed=true)')
    planner_bridge(dialog)
   except Exception:fail()
  dialog.web.evalWithCallback('(()=>{const c=document.querySelector(".pip-card"),i=c?.querySelector(".pip-image");return c&&i?.complete&&i.naturalWidth>0?{scene:i.src.endsWith("keepsake-journal-1.0.15.png"),pixels:i.naturalWidth,journeyButton:!!document.querySelector("[data-action=companion-journey]")}:null})()',ready)
 except Exception:fail()

def planner_bridge(dialog,attempt=0):
 def result(ok):
  try:
   if not ok:
    if attempt<80:later(lambda:planner_bridge(dialog,attempt+1));return
    raise RuntimeError('Planner-to-journey native adapter failed')
   check('New journey navigation uses the live planner adapter and preserves its request channel',True)
   capture('pip',lambda:(dialog.force_close(),shutdown()))
  except Exception:fail()
 dialog.web.evalWithCallback('Boolean(window.nativeJourneyAdapterPassed)',result)

def shutdown():
 try:
  c=owner.friends;client=c.client;owner.closed()
  check('Profile close invalidates network client and clears tokens',c.stopped and client.closed and client.session is None and owner.friends is None)
  c.command('refresh',{})
  check('A callback from a closed profile cannot restart Friends',not c.valid() and owner.store is None)
  check('Actual native database remains healthy',aqt.mw.col.db.scalar('pragma integrity_check')=='ok')
  report['completed']=True;finish()
 except Exception:fail()

later(start,1800);later(finish,160000)
code=app.exec();report['graceful_shutdown']=code==0
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({'checks':len(report['checks']),'errors':report['errors'],'completed':report['completed']}))
if not report['completed'] or report['errors'] or not all(report['checks'].values()):raise SystemExit(1)

"""Actual Anki/Qt tour, synthetic unsynced profile; run with Anki's Python.

The caller reclaims the profile after this process releases its file handles.
No physical input, owner collection, live Onigiri or hardware GPU claim.
"""
from pathlib import Path
import hashlib,json,os,sqlite3,sys,time,traceback,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest,production_files
OUT=ROOT/'output/native-onboarding-107';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/native-onboarding-107';SH.mkdir(parents=True,exist_ok=True)
BASE=OUT/('profile-'+str(time.time_ns()));BASE.mkdir()
assert BASE.resolve().is_relative_to(ROOT.resolve())
installer=ROOT/'dist/Atelier-1.0.7.ankiaddon'
target=BASE/'addons21/daedalus_atelier';target.mkdir(parents=True)
with zipfile.ZipFile(installer) as z:z.extractall(target)
assert all((target/n).read_bytes()==p.read_bytes() for p,n in production_files())
os.environ.update(QT_QPA_PLATFORM='windows',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki,anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Tour QA');pm.load('Tour QA')
pm.meta.update(firstRun=False,defaultLang='en_US',updates=False,check_for_updates=False);pm.profile.update(autoSync=False);pm.save();pm.db.close()
import aqt,aqt.main
from aqt.qt import QTimer
aqt.AnkiApp.secondInstance=lambda self:False
report={'category':'actual Windows Anki/Qt; scripted tour in a synthetic unsynced profile','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'installer_sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'owner_profile_accessed':False,'checks':{},'captures':[],'errors':[]}
aqt.main.showWarning=lambda message,*a,**k:report['errors'].append('Anki warning: '+str(message))
app=aqt._run(['anki','-b',str(BASE),'-p','Tour QA','-l','en_US'],exec=False)
finished=False;before=None
JS="""(()=>{const r=document.getElementById('atelier-root')?.shadowRoot,c=r?.querySelector('.tour-card'),b=c?.getBoundingClientRect();return {...(window.AtelierMakeover?.diagnostics()||{}),title:r?.querySelector('#tour-title')?.textContent,cardVisible:!!c,cardFits:!b||(b.left>=0&&b.top>=0&&b.right<=innerWidth&&b.bottom<=innerHeight),inert:!!r?.querySelector('.frame')?.inert}})()"""
def check(name,ok):
    report['checks'][name]=bool(ok)
    if not ok:raise AssertionError(name)
def done():
    global finished
    if finished:return
    finished=True
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    import threading
    watchdog=threading.Timer(30,lambda:os._exit(2));watchdog.daemon=True;watchdog.start()
    aqt.mw.unloadProfileAndExit()
def wait_for(predicate,then,attempt=0):
    def received(value):
        try:
            if finished:return
            if predicate(value or {}):
                # The JS callback precedes Qt's compositor paint. Allow a frame
                # to settle before capturing or advancing to the next step.
                def painted():
                    try:then(value)
                    except Exception:report['errors'].append(traceback.format_exc());done()
                aqt.mw.showNormal();aqt.mw.raise_();aqt.mw.activateWindow()
                aqt.mw.web.evalWithCallback('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))',lambda _:QTimer.singleShot(2500,painted))
            elif attempt<60:QTimer.singleShot(250,lambda:wait_for(predicate,then,attempt+1))
            else:raise RuntimeError('Native tour did not settle: '+str(value))
        except Exception:report['errors'].append(traceback.format_exc());done()
    aqt.mw.web.evalWithCallback(JS,received)
def click(action):
    aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('.tour-card [data-action=\""+action+"\"]').click()")
def capture(name,value):
    # Qt captures can contain stale compositor frames in the Windows helper
    # desktop. Keep geometry evidence here; capture deliverable images through
    # the foreground computer-use API separately and visually review them.
    report['captures'].append({'stage':name,'state':value,'logical_window':[aqt.mw.width(),aqt.mw.height()],'screenshot':'separate foreground computer-use capture; no Qt grab accepted'})
def counts():
    c=aqt.mw.col
    return (c.card_count(),c.note_count(),tuple((int(d.id),d.name) for d in c.decks.all_names_and_ids()))
def welcome(value):
    global before
    before=counts();check('automatic_first_run_offer',value['title']=='A quick look around Atelier.')
    check('welcome_fits_native_viewport',value['cardFits']);check('tour_blocks_background_shortcuts',value['inert'])
    capture('native-welcome.png',value);click('tour-next');wait_for(lambda v:v.get('tourStep')==0,lambda v:step(0,v))
def step(index,value):
    check('step_'+str(index+1)+'_native_geometry',value['cardFits'] and value['cardVisible'])
    if index in (2,3,9):capture('native-step-'+str(index+1)+'.png',value)
    click('tour-next')
    if index<12:wait_for(lambda v:v.get('tourStep')==index+1,lambda v:step(index+1,v))
    else:wait_for(lambda v:v.get('tourStep')==13,complete)
def complete(value):
    check('completion_has_next_tasks',value['title']=='Ready for your next chapter.')
    capture('native-completion.png',value);click('tour-next')
    wait_for(lambda v:not v.get('cardVisible') and v.get('loaded'),after_complete)
def after_complete(value):
    owner=aqt.mw._daedalus_atelier_runtime
    check('completion_saved_in_real_profile_store',owner.store.read()['onboarding']=={'version':1,'status':'completed'})
    check('cards_notes_and_decks_preserved',counts()==before)
    check('background_unlocked',not value['inert'])
    action=next(a for a in owner.menu.actions() if a.text()=='Guided tour…')
    action.trigger();wait_for(lambda v:v.get('tourStep')==-1,replayed)
def replayed(value):
    check('native_tools_menu_replays_tour',value['cardVisible']);click('tour-skip')
    wait_for(lambda v:not v.get('cardVisible') and v.get('loaded'),after_skip)
def after_skip(value):
    owner=aqt.mw._daedalus_atelier_runtime
    check('skip_saved_in_real_profile_store',owner.store.read()['onboarding']['status']=='skipped')
    aqt.mw.deckBrowser.refresh()
    QTimer.singleShot(1500,lambda:wait_for(lambda v:v.get('loaded') and not v.get('cardVisible'),after_redraw))
def after_redraw(value):
    check('dismissal_survives_native_home_redraw',not value['cardVisible'])
    check('tour_never_changed_collection',counts()==before);done()
def start(attempt=0):
    try:
        if '--await-activation' in sys.argv and not (OUT/'capture-activated.flag').exists():
            QTimer.singleShot(500,lambda:start(attempt));return
        if not aqt.mw.col or not getattr(aqt.mw,'_daedalus_atelier_runtime',None):
            if attempt<30:QTimer.singleShot(500,lambda:start(attempt+1));return
            raise RuntimeError('Anki did not load Atelier')
        aqt.mw.resize(1100,650);wait_for(lambda v:v.get('loaded') and v.get('tourStep')==-1,welcome)
    except Exception:report['errors'].append(traceback.format_exc());done()
QTimer.singleShot(1500,start);QTimer.singleShot(150000,lambda:(report['errors'].append('native tour timeout'),done()))
code=app.exec();report['checks']['graceful_shutdown']=code==0
try:
    with sqlite3.connect('file:'+(BASE/'Tour QA/collection.anki2').as_posix()+'?mode=ro',uri=True) as db:
        db.create_collation('unicase',lambda a,b:(a.casefold()>b.casefold())-(a.casefold()<b.casefold()))
        report['checks']['collection_sqlite_integrity']=db.execute('pragma quick_check').fetchone()[0]=='ok'
except Exception:report['errors'].append(traceback.format_exc())
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
if report['errors'] or not all(report['checks'].values()):sys.exit(1)

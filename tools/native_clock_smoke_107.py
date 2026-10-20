"""Actual Anki/Qt tour, synthetic unsynced profile; run with Anki's Python.

The caller reclaims the profile after this process releases its file handles.
No physical input, owner collection, live Onigiri or hardware GPU claim.
"""
from pathlib import Path
import hashlib,json,os,sqlite3,sys,time,traceback,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest,production_files
OUT=ROOT/'output/native-clock-107';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/native-clock-107';SH.mkdir(parents=True,exist_ok=True)
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
report={'category':'actual Windows Anki/Qt study clock and task guide; synthetic unsynced profile','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'installer_sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'owner_profile_accessed':False,'checks':{},'captures':[],'errors':[]}
aqt.main.showWarning=lambda message,*a,**k:report['errors'].append('Anki warning: '+str(message))
app=aqt._run(['anki','-b',str(BASE),'-p','Tour QA','-l','en_US'],exec=False)
finished=False;before=None

def check(name,value):
    report['checks'][name]=bool(value)
    if not value:raise AssertionError(name)
def done():
    global finished
    if finished:return
    finished=True
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    aqt.mw.unloadProfileAndExit()
def start(attempt=0):
    global before,w,tick_now
    try:
        mw=aqt.mw;a=getattr(mw,'_daedalus_atelier_runtime',None)
        if not mw.col or not a:
            if attempt<50:QTimer.singleShot(500,lambda:start(attempt+1));return
            raise RuntimeError('Atelier startup did not settle')
        before=(mw.col.note_count(),mw.col.card_count())
        a.open_clock();w=a.study_clock;tick_now=[100.0];w.clock.now=lambda:tick_now[0]
        check('native_menu_has_clock_and_help',all(any(label in x.text() for x in a.menu.actions()) for label in ['Study clock','Getting started']))
        check('clock_default_countdown',w.clock.mode=='countdown' and w.digits.text()=='25:00')
        w.length.setValue(1);w.toggle.click();tick_now[0]+=12;w.tick()
        check('native_countdown_updates',w.digits.text()=='00:48' and w.toggle.text()=='Pause')
        w.close();check('closing_window_keeps_timing',not w.isVisible() and w.clock.running)
        tick_now[0]+=3;a.open_clock();w.tick();check('reopen_keeps_same_clock',a.study_clock is w and w.digits.text()=='00:45')
        w.toggle.click();tick_now[0]+=600;w.tick();check('pause_excludes_breaks',w.digits.text()=='00:45')
        w.toggle.click();tick_now[0]+=45;w.tick();check('countdown_finishes_without_grading',w.clock.complete and not w.clock.running and 'Time' in w.status.text())
        w.reset.click();w.modes['stopwatch'].click();w.toggle.click();tick_now[0]+=83;w.tick();check('native_stopwatch_works',w.digits.text()=='01:23')
        w.toggle.click();a.open_help();check('task_guide_opens',a._help_window is not None and a._help_window.isVisible())
        a._help_window.close()
        themes=list(a.get_config() for _ in [])
        from importlib import import_module
        global palettes,original_get,world_ids
        from aqt.qt import QApplication
        original_get=a.get_config
        palettes=import_module(a.module+'.review_model').PALETTES
        world_ids=list(palettes)
        QTimer.singleShot(300,lambda:theme(0))
    except Exception:report['errors'].append(traceback.format_exc());done()
def theme(index):
    try:
        a=aqt.mw._daedalus_atelier_runtime
        if index==len(world_ids):
            a.get_config=original_get
            w.clock.start();w.tick();w.close()
            check('clock_did_not_change_collection',(aqt.mw.col.note_count(),aqt.mw.col.card_count())==before)
            report['clock_file']=str(w.store.path.relative_to(BASE));done();return
        key=world_ids[index];cfg=original_get();cfg.update(theme=key,visual_owner='atelier');a.get_config=lambda:cfg
        w.refresh();w.show();w.repaint();app.processEvents()
        check(key+'_scenic_raster_and_theme',not w.scene.pixmap().isNull() and w.scene.isVisible() and palettes[key]['accent'] in w.styleSheet())
        check(key+'_controls_fit_scroll_surface',w.digits.width()>100 and w.toggle.width()>50)
        if key in ['forest','obsidian','rose','linen','castle']:
            path=SH/(key+'-study-clock.png');w.grab().save(str(path));report['captures'].append(str(path.relative_to(ROOT)))
        if index==0:
            cfg['visual_owner']='external';w.refresh();check('original_theme_retains_native_widgets',not w.styleSheet() and not w.scene.isVisible());cfg['visual_owner']='atelier'
        QTimer.singleShot(150,lambda:theme(index+1))
    except Exception:report['errors'].append(traceback.format_exc());done()
QTimer.singleShot(2000,start)
QTimer.singleShot(150000,lambda:(report['errors'].append('Native clock timeout'),done()))
code=app.exec();report['checks']['graceful_shutdown']=code==0
try:
    saved=json.loads((BASE/report['clock_file']).read_text());report['checks']['shutdown_saved_elapsed_without_running_anchor']=saved['mode']=='stopwatch' and saved['elapsed']>=83 and 'anchor' not in saved and 'running' not in saved
except Exception:report['errors'].append(traceback.format_exc())
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'anki':report['anki'],'checks':len(report['checks']),'failed':[k for k,v in report['checks'].items() if not v],'errors':report['errors']},indent=2))
if report['errors'] or not all(report['checks'].values()):sys.exit(1)

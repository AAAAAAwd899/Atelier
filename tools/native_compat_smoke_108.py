"""Actual Anki/Qt tour, synthetic unsynced profile; run with Anki's Python.

The caller reclaims the profile after this process releases its file handles.
No physical input, owner collection, live Onigiri or hardware GPU claim.
"""
from pathlib import Path
import hashlib,json,os,sqlite3,sys,time,traceback,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest,production_files
OUT=ROOT/'output/native-compat-108';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/native-compat-108';SH.mkdir(parents=True,exist_ok=True)
BASE=OUT/('profile-'+str(time.time_ns()));BASE.mkdir()
assert BASE.resolve().is_relative_to(ROOT.resolve())
installer=ROOT/'dist/Atelier-1.0.8.ankiaddon'
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
report={'category':'actual Windows Anki/Qt original QAction compatibility; synthetic menu providers, not installed third-party add-ons','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'installer_sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'owner_profile_accessed':False,'checks':{},'captures':[],'errors':[]}
aqt.main.showWarning=lambda message,*a,**k:report['errors'].append('Anki warning: '+str(message))
app=aqt._run(['anki','-b',str(BASE),'-p','Tour QA','-l','en_US'],exec=False)
finished=False;before=None;tested_owner=None

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
    try:
        mw=aqt.mw;a=getattr(mw,'_daedalus_atelier_runtime',None)
        if a is None or not mw.col:
            if attempt<30:QTimer.singleShot(500,lambda:start(attempt+1));return
            raise RuntimeError('Runtime not ready')
        global before,menu,command,calls,disabled,parent_action,late,tested_owner,closed_window
        from aqt.qt import QAction,QMenu
        tested_owner=a;calls=[];before=(mw.col.note_count(),mw.col.card_count())
        menu=QMenu('Study companion QA',mw);mw.menuBar().addMenu(menu)
        command=QAction('Show companion',mw);command.setCheckable(True);command.setShortcut('Ctrl+Alt+9');command.triggered.connect(lambda checked:calls.append(checked));menu.addAction(command)
        disabled=QAction('Unavailable command',mw);disabled.setEnabled(False);menu.addAction(disabled)
        nested=menu.addMenu('Suspended tools');parent_action=nested.menuAction();parent_action.setEnabled(False);nested.addAction('Nested command')
        a.open_addon_tools();w=a._addon_tools_window;closed_window=w;w.search.setText('companion');app.processEvents()
        check('real_qaction_discovered',any(x['action'] is command for x in w.rows))
        check('foreign_shortcut_unchanged',command.shortcut().toString()=='Ctrl+Alt+9')
        check('no_action_triggered_by_discovery',calls==[])
        check('original_menus_not_reparented',menu.parent() is mw and menu.menuAction() in mw.menuBar().actions())
        check('window_fits_native_screen',w.width()<=w.screen().availableGeometry().width() and w.height()<=w.screen().availableGeometry().height())
        item=next(w.tree.topLevelItem(i) for i in range(w.tree.topLevelItemCount()) if w.tree.topLevelItem(i).text(0)=='Show companion')
        w.tree.setCurrentItem(item);w.selection();check('available_original_action_enabled',w.open_button.isEnabled())
        shot=SH/'addon-tools.png';w.grab().save(str(shot));report['captures'].append(str(shot.relative_to(ROOT)))
        w.open_selected();QTimer.singleShot(150,after_trigger)
    except Exception:report['errors'].append(traceback.format_exc());done()

def after_trigger():
    try:
        mw=aqt.mw;a=mw._daedalus_atelier_runtime
        check('original_slot_called_exactly_once',calls==[True]);check('native_checkable_action_toggled',command.isChecked())
        check('launcher_closed_after_trigger',getattr(a,'_addon_tools_window',None) is None)
        import PyQt6.sip as sip
        check('closed_dialog_deleted',sip.isdeleted(closed_window))
        a.open_addon_tools();w=a._addon_tools_window
        from aqt.qt import Qt,QAction
        w.search.setText('unavailable');w.tree.setCurrentItem(w.tree.topLevelItem(0));w.selection();check('disabled_action_stays_disabled',not w.open_button.isEnabled())
        w.search.setText('nested command');w.tree.setCurrentItem(w.tree.topLevelItem(0));w.selection();check('disabled_submenu_respected',not w.open_button.isEnabled())
        parent_action.setEnabled(True);w.selection();check('live_parent_enabled_state_respected',w.open_button.isEnabled())
        late=QAction('Late registered command',mw);menu.addAction(late);w.reload();check('refresh_finds_late_action',any(x['action'] is late for x in w.rows))
        w.search.setText('not a matching command');check('empty_search_is_clear',w.tree.topLevelItemCount()==0 and not w.open_button.isEnabled())
        w.search.clear();check('own_launcher_not_recursively_listed',not any(x['title']=='Add-on tools…' and x['path'].startswith('Tools') for x in w.rows))
        check('collection_unchanged',(mw.col.note_count(),mw.col.card_count())==before)
        done()
    except Exception:report['errors'].append(traceback.format_exc());done()
QTimer.singleShot(2000,start)
QTimer.singleShot(90000,lambda:(report['errors'].append('Native compatibility timeout'),done()))
code=app.exec();report['checks']['graceful_shutdown']=code==0
report['checks']['profile_close_disposed_launcher']=getattr(tested_owner,'_addon_tools_window',None) is None
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'anki':report['anki'],'checks':len(report['checks']),'failed':[k for k,v in report['checks'].items() if not v],'errors':report['errors']},indent=2))
if report['errors'] or not all(report['checks'].values()):sys.exit(1)

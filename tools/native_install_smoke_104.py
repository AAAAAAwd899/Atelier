"""Actual Anki AddonManager update in a fresh disposable application profile."""
from pathlib import Path
import hashlib,json,os,sqlite3,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest,production_files,write_archive
OUT=ROOT/'output/native-install-104';OUT.mkdir(parents=True,exist_ok=True)
BASE=OUT/('profile-'+str(time.time_ns()));BASE.mkdir();assert BASE.resolve().is_relative_to(ROOT.resolve())
baseline=ROOT/'output/baseline-runtime/src';manifest=json.loads((ROOT/'baseline-1.0.2.json').read_text())
assert all(hashlib.sha256((baseline/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
basezip=OUT/'qa-baseline.ankiaddon';write_archive(basezip,[(baseline/n,n) for n in manifest])
installer=ROOT/'dist/Atelier-1.0.4.ankiaddon'
os.environ.update(QT_QPA_PLATFORM='windows',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki,anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Install QA');pm.load('Install QA');pm.meta.update(firstRun=False,defaultLang='en_US',updates=False);pm.profile.update(autoSync=False);pm.save();pm.db.close()
import aqt
from aqt.qt import QTimer
from aqt.addons import InstallOk
import aqt.main
aqt.AnkiApp.secondInstance=lambda self:False
report={'category':'actual Anki AddonManager installer API; synthetic application profile; GUI file picker not automated','runtime_sha256':runtime_digest(),'installer_sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'anki':buildinfo.version,'checks':{},'errors':[],'owner_profile_accessed':False}
def record_warning(message,*args,**kwargs):
 report['errors'].append('Anki warning during synthetic install/shutdown: '+str(message))
 # A modal warning would stall unattended QA; record it without showing a dialog.
aqt.main.showWarning=record_warning
app=aqt._run(['anki','-b',str(BASE),'-p','Install QA','-l','en_US'],exec=False);attempts=0;finished=False
def done():
 global finished
 if finished:return
 finished=True;(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
 import threading
 # Let Anki run its own collection integrity check, backup, and profile cleanup.
 # Closing mw.col directly first makes that normal check inspect a closed DB and
 # falsely display Anki's collection-corrupt warning during shutdown.
 watchdog=threading.Timer(30,lambda:os._exit(2));watchdog.daemon=True;watchdog.start()
 aqt.mw.unloadProfileAndExit()
def run():
 global attempts
 attempts+=1
 try:
  mw=aqt.mw
  if not mw.col:
   if attempts>30:raise RuntimeError('QA application failed to load')
   QTimer.singleShot(1000,run);return
  manager=mw.addonManager;target=Path(manager.addonsFolder('daedalus_atelier'))
  assert target.resolve().is_relative_to(BASE.resolve())
  first=manager.install(str(basezip));assert isinstance(first,InstallOk)
  report['checks']['baseline_install_accepted']=True
  files=[target/'user_files/qa-preservation-marker.txt',Path(mw.pm.profileFolder())/'exam_sprout/qa-preservation-marker.txt',Path(mw.pm.profileFolder())/'workshop/qa-preservation-marker.txt']
  for file in files:file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'SYNTHETIC SAVED WORK\n')
  preferences={'visual_owner':'atelier','theme':'forest','qa_marker':'keep preferences'}
  meta=manager.addonMeta('daedalus_atelier');meta['config']=preferences;manager.writeAddonMeta('daedalus_atelier',meta)
  result=manager.install(str(installer));report['checks']['cumulative_update_accepted']=isinstance(result,InstallOk)
  report['checks']['installed_runtime_bytes_equal']=all((target/n).read_bytes()==p.read_bytes() for p,n in production_files())
  report['checks']['preferences_preserved']=manager.addonMeta('daedalus_atelier')['config']==preferences
  report['checks']['user_files_preserved']=files[0].read_bytes()==b'SYNTHETIC SAVED WORK\n'
  report['checks']['profile_saved_files_preserved']=all(file.read_bytes()==b'SYNTHETIC SAVED WORK\n' for file in files[1:])
  report['checks']['private_identity_retained']=manager.addon_meta('daedalus_atelier').ankiweb_id() is None and manager.addon_meta('daedalus_atelier').human_version=='1.0.4'
  report['checks']['no_conflicting_installs']=isinstance(result,InstallOk) and not result.conflicts
  report['native_installer_compatible_flag']=result.compatible if isinstance(result,InstallOk) else False
  done()
 except Exception:report['errors'].append(traceback.format_exc());done()
QTimer.singleShot(1200,run);QTimer.singleShot(150000,lambda:(report['errors'].append('native installer timeout'),done()))
exit_code=app.exec()
report['checks']['graceful_native_shutdown']=exit_code==0
collection=BASE/'Install QA'/'collection.anki2'
try:
 with sqlite3.connect('file:'+collection.as_posix()+'?mode=ro',uri=True) as db:
  db.create_collation('unicase',lambda a,b:(a.casefold()>b.casefold())-(a.casefold()<b.casefold()))
  report['checks']['collection_sqlite_integrity']=db.execute('pragma quick_check').fetchone()[0]=='ok'
except Exception:report['errors'].append('Post-shutdown collection check failed: '+traceback.format_exc())
if not report['checks'].get('graceful_native_shutdown'):report['errors'].append('Anki returned a nonzero exit code')
report['scratch_cleanup_pending']=not(report['errors'] or not all(report['checks'].values()))
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
if report['errors'] or not all(report['checks'].values()):sys.exit(1)

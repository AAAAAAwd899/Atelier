"""Explicit owner-authorized local update through Anki's AddonManager.

Run with run_installed_anki_qa.py and --apply-owner-update only after closing Anki,
creating the private backup, and passing current release verification. Opens a
disposable application profile, never the owner's collection. Nothing is uploaded.
"""
from pathlib import Path
import hashlib,json,os,sys,time,traceback
assert '--apply-owner-update' in sys.argv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import production_files,runtime_digest
OWNER=Path.home()/'AppData/Roaming/Anki2'
OUT=ROOT/'output/anki-update-105';BACKUP=OUT/'private-backup'
backup=json.loads((BACKUP/'receipt.json').read_text())
assert hashlib.sha256((BACKUP/'before-anki-26.09-atelier-1.0.5.zip').read_bytes()).hexdigest()==backup['zip_sha256']
assert not any(p.stat().st_size for p in OWNER.glob('*/collection.anki2-wal'))
proof=json.loads((ROOT/'verification/verified.json').read_text())
assert proof['runtime_sha256']==runtime_digest() and proof['python_failed']==proof['browser_errors']==0
target=OWNER/'addons21/daedalus_atelier';assert target.is_dir()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=[p for p in (target/'user_files').rglob('*') if p.is_file() and p.name!='README.txt']
for profile in OWNER.iterdir():
    if profile.is_dir() and profile.name!='addons21':
        for name in ['exam_sprout','workshop']:
            protected.extend(p for p in (profile/name).rglob('*') if p.is_file())
protected.extend(OWNER.glob('*/collection.anki2'))
before={p:digest(p) for p in protected}
meta=json.loads((target/'meta.json').read_text());config=meta.get('config')
other_meta={p:digest(p) for p in (OWNER/'addons21').glob('*/meta.json') if p.parent!=target}
BASE=OUT/('owner-install-scratch-'+str(time.time_ns()));BASE.mkdir()
os.environ.update(QT_QPA_PLATFORM='windows',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Update');pm.load('Update')
pm.meta.update(firstRun=False,defaultLang='en_US',check_for_updates=False);pm.profile['autoSync']=False;pm.save();pm.db.close()
import aqt
from aqt.qt import QTimer
from aqt.addons import AddonManager,InstallOk
aqt.AnkiApp.secondInstance=lambda self:False
app=aqt._run(['anki','-b',str(BASE),'-p','Update','-l','en_US'],exec=False)
report={'anki':buildinfo.version,'atelier':'1.0.5','runtime_sha256':runtime_digest(),'installer_sha256':digest(ROOT/'dist/Atelier-1.0.5.ankiaddon'),'owner_collection_opened':False,'checks':{},'errors':[]}
def update():
    original=aqt.mw.pm.addonFolder
    try:
        aqt.mw.pm.addonFolder=lambda:str(OWNER/'addons21')
        manager=AddonManager(aqt.mw)
        assert Path(manager.addonsFolder('daedalus_atelier')).resolve()==target.resolve()
        result=manager.install(str(ROOT/'dist/Atelier-1.0.5.ankiaddon'))
        assert isinstance(result,InstallOk) and result.compatible and not result.conflicts,result
        report['checks']['native_installer_accepted']=True
        report['checks']['all_runtime_bytes_equal']=all((target/n).read_bytes()==p.read_bytes() for p,n in production_files())
        report['checks']['configuration_preserved']=json.loads((target/'meta.json').read_text()).get('config')==config
        report['checks']['saved_work_and_collections_unchanged']=all(p.exists() and digest(p)==h for p,h in before.items())
        report['checks']['other_addon_metadata_unchanged']=all(p.exists() and digest(p)==h for p,h in other_meta.items())
        report['protected_file_count']=len(before)
    except Exception:report['errors'].append(traceback.format_exc())
    finally:
        aqt.mw.pm.addonFolder=original
        aqt.mw.unloadProfileAndExit()
QTimer.singleShot(1500,update)
code=app.exec();report['checks']['graceful_shutdown']=code==0
(OUT/'owner-update.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if report['errors'] or not all(report['checks'].values()):sys.exit(1)

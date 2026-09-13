"""Actual installed Anki/Qt, isolated generated profile, offscreen rendering.

Never opens, copies, syncs or changes the owner's profile. Run with Anki's Python.
The single-instance IPC is disabled to prevent forwarding into another Anki.
"""
from pathlib import Path
import os,sys,shutil,json,traceback
ROOT=Path(__file__).resolve().parents[1]
DESKTOP='--desktop' in sys.argv
if '--scale-100' in sys.argv:os.environ['QT_SCALE_FACTOR']='0.666666667'
OUT=ROOT/('output/native-desktop-100-25.09.5' if '--scale-100' in sys.argv else 'output/native-desktop-25.09.5' if DESKTOP else 'output/native-25.09.5');OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'native-test-profile';BASE.mkdir(exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='windows' if DESKTOP else 'offscreen',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki,anki.lang
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Atelier QA');pm.load('Atelier QA')
pm.meta.update(firstRun=False,defaultLang='en_US',updates=False,uiScale=2/3 if '--scale-100' in sys.argv else 1);pm.profile.update(autoSync=False);pm.save();pm.db.close()
target=BASE/'addons21/daedalus_atelier'
shutil.copytree(ROOT/'src',target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
cfg=json.loads((target/'config.json').read_text(encoding='utf8'));cfg.update(visual_owner='atelier',mode='workspace',theme='midnight',motion=False)
(target/'meta.json').write_text(json.dumps({'config':cfg}),encoding='utf8')
import aqt
from aqt.qt import QTimer
aqt.AnkiApp.secondInstance=lambda self:False
report={'category':f'actual Anki 25.09.5 / native Qt {"desktop" if DESKTOP else "offscreen"} on Windows; synthetic profile','version':anki.version,'owner_profile_accessed':False,'hardware_tested':False,'captures':[],'errors':[]}
app=aqt._run(['anki','-b',str(BASE),'-p','Atelier QA','-l','en_US'],exec=False)
attempts=0;finished=False
def done():
    global finished
    if finished:return
    finished=True
    (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    if aqt.mw.col:aqt.mw.col.close()
    app.quit();os._exit(0)
def capture(theme,destination,retries=0):
    mw=aqt.mw;name=f'{theme}-{destination}.png'
    def record(value):
        if (not value or not value.get('loaded')) and retries<15:
            QTimer.singleShot(700,lambda:capture(theme,destination,retries+1));return
        def painted():
            shot=mw.grab();shot.save(str(OUT/name))
            report['captures'].append({'path':name,'diagnostics':value,'logical_window':[mw.width(),mw.height()],'pixel_size':[shot.width(),shot.height()],'device_pixel_ratio':shot.devicePixelRatio()})
            if not value or not value.get('loaded'):report['errors'].append(f'{theme}/{destination} did not finish loading')
            next_capture()
        QTimer.singleShot(1200,painted)
    mw.web.evalWithCallback('window.AtelierMakeover ? AtelierMakeover.diagnostics() : {missing:true}',record)
queue=[(theme,page) for theme in ['midnight','rose','forest'] for page in ['desk','widgets']]
def next_capture():
    if not queue:done();return
    theme,page=queue.pop(0);owner=aqt.mw._daedalus_atelier_runtime
    owner.save_config({'theme':theme});owner._ui_state={'page':page,'location':'0','query':'','filter':'all'}
    owner.open_widgets() if page=='widgets' else owner.open()
    QTimer.singleShot(1800,lambda:capture(theme,page))
def start():
    global attempts
    attempts+=1
    try:
        mw=aqt.mw
        if not mw.col or not getattr(mw,'_daedalus_atelier_runtime',None):
            if attempts>30:raise RuntimeError('Native startup/profile unavailable after 30 seconds')
            QTimer.singleShot(1000,start);return
        mw.resize(1440,900)
        if mw.col.card_count()==0:
            for i in range(1,4):
                did=mw.col.decks.id(f'Atelier QA::Exam::Lecture {i}')
                n=mw.col.new_note(mw.col.models.by_name('Basic'));n['Front']=f'QA lecture {i}: recall this concept';n['Back']='Synthetic local acceptance card.';mw.col.add_note(n,did)
        next_capture()
    except Exception:
        report['errors'].append(traceback.format_exc());done()
QTimer.singleShot(1500,start)
QTimer.singleShot(150000,lambda:(report['errors'].append('Native test timeout'),done()))
app.exec()
print(json.dumps(report,indent=2))

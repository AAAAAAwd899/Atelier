"""Actual Anki/Qt tour, synthetic unsynced profile; run with Anki's Python.

The caller reclaims the profile after this process releases its file handles.
No physical input, owner collection, live Onigiri or hardware GPU claim.
"""
from pathlib import Path
import hashlib,json,os,sqlite3,sys,time,traceback,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest,production_files
WITH_ONIGIRI='--with-onigiri' in sys.argv
OUT=ROOT/('output/listing-native-117-onigiri' if WITH_ONIGIRI else 'output/listing-native-117');OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/listing-native-117';SH.mkdir(parents=True,exist_ok=True)
previous=json.loads((OUT/'cdp.json').read_text()) if '--reuse' in sys.argv else None
(OUT/'stop.flag').unlink(missing_ok=True)
BASE=sorted(OUT.glob('profile-*'))[-1] if previous else OUT/('profile-'+str(time.time_ns()))
BASE.mkdir(exist_ok=True)
assert BASE.resolve().is_relative_to(ROOT.resolve())
installer=ROOT/'dist/Atelier-1.0.17.ankiaddon'
target=BASE/'addons21/daedalus_atelier';target.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(installer) as z:z.extractall(target)
assert all((target/n).read_bytes()==p.read_bytes() for p,n in production_files())
if WITH_ONIGIRI:
    onigiri=Path.home()/'AppData/Roaming/Anki2/addons21/1011095603'
    assert onigiri.is_dir()
    # Private QA copy only. Never copy owner preferences, stores or credentials,
    # and never add third-party code/assets to Atelier's production package.
    staged=BASE/'addons21/1011095603'
    def excluded(folder,names):
        return {n for n in names if n in {'user_files','__pycache__','.git','meta.json','config.json'} or n.startswith('.env') or Path(n).suffix in {'.db','.anki2','.sqlite','.sqlite3'}}
    shutil.copytree(onigiri,staged,ignore=excluded,dirs_exist_ok=True)

os.environ.update(QT_QPA_PLATFORM='offscreen',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import socket
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
os.environ['QTWEBENGINE_REMOTE_DEBUGGING']='127.0.0.1:'+str(port)
os.environ['QT_SCALE_FACTOR']='1'
(OUT/'cdp.json').write_text(json.dumps({'port':port,'ready':False}))
import anki,anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Tour QA');pm.load('Tour QA')
pm.meta.update(firstRun=False,defaultLang='en_US',updates=False,check_for_updates=False);pm.profile.update(autoSync=False);pm.save();pm.db.close()
import aqt,aqt.main
from aqt.qt import QTimer
aqt.AnkiApp.secondInstance=lambda self:False
report={'category':'Actual Anki 26.09.3 Qt offscreen webviews; example collection; outer chrome excluded, no physical display claim','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'installer_sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'owner_profile_accessed':False,'checks':{},'captures':[],'errors':[]}
aqt.main.showWarning=lambda message,*a,**k:report['errors'].append('Anki warning: '+str(message))
app=aqt._run(['anki','-b',str(BASE),'-p','Tour QA','-l','en_US'],exec=False)

assert app.platformName()=='offscreen'
finished=False

def finish():
    global finished
    if finished:return
    finished=True
    if aqt.mw.col:report['checks']['database_integrity']=aqt.mw.col.db.scalar('pragma integrity_check')=='ok'
    (OUT/'host-report.json').write_text(json.dumps(report,indent=2)+'\n')
    aqt.mw.unloadProfileAndExit()
def start(attempt=0):
    try:
        mw=aqt.mw;a=getattr(mw,'_daedalus_atelier_runtime',None)
        if not mw.col or not a:
            if attempt<60:QTimer.singleShot(500,lambda:start(attempt+1));return
            raise RuntimeError('Native listing host failed to start')
        from aqt import update as anki_update
        mw._qa_update_calls=[]
        class ControlledUpdate:
            def with_progress(self):return self
            def run_in_background(self):mw._qa_update_calls.append('native-check')
        anki_update.get_latest_release_op=lambda **kwargs:ControlledUpdate()
        if previous:
            import importlib
            foreign_config=importlib.import_module('1011095603.core.config');ng=foreign_config.get_config();ng.setdefault('restaurant_level',{}).update(enabled=True,notifications_enabled=False);ng.setdefault('onigiriWidgetLayout',{}).setdefault('grid',{})['restaurant_level']={'pos':4,'row':2,'col':2};foreign_config.write_config(ng)
            rewards=importlib.import_module('1011095603.gamification.nook_level').manager;rewards.set_enabled(True)
            mw.resize(1440,900);mw.deckBrowser.refresh()
            def inspect_toolbar():
                report['toolbar_diagnostic']={'state':mw.state,'config':{k:a.get_config().get(k) for k in ['visual_owner','mode','native_toolbar']},'fullscreen_type':type(getattr(mw,'fullscreen',None)).__name__,'fullscreen_value':str(getattr(mw,'fullscreen',None)),'before_hidden':mw.toolbarWeb.isHidden(),'height':mw.toolbarWeb.height()}
                report['checks']['native_toolbar_restored']=not report['toolbar_diagnostic']['before_hidden']
                (OUT/'toolbar-diagnostic.json').write_text(json.dumps(report['toolbar_diagnostic'],indent=2))
            QTimer.singleShot(500,inspect_toolbar)
            (OUT/'cdp.json').write_text(json.dumps(dict(previous,port=port,ready=True)))
            QTimer.singleShot(500,poll);return
        c=mw.col;basic=c.models.by_name('Basic')
        examples=[('Biology 101::Week 1 · Cells',[('What controls entry into and exit from a cell?','The plasma membrane.'),('Where is most genetic material stored in a eukaryotic cell?','The nucleus.'),('Which organelle makes most ATP during aerobic respiration?','Mitochondria.')]),('Biology 101::Week 2 · Photosynthesis',[('What gas do plants take in for photosynthesis?','Carbon dioxide.'),('What organelle carries out photosynthesis?','The chloroplast.')]),('Chemistry 101::Week 1 · Atoms',[('What does the atomic number represent?','The number of protons.'),('What charge does an electron have?','Negative.')]),('Geography::Landscapes',[('What is a drainage basin?','The area of land drained by a river and its tributaries.')])]
        for name,notes in examples:
            did=c.decks.id(name)
            for front,back in notes:
                n=c.new_note(basic);n['Front']=front;n['Back']=back;c.add_note(n,did)
        parent=c.decks.id('Biology 101');chem=c.decks.id('Chemistry 101')
        a.ensure_store()
        profile=dict(a.profile,onboarding={'version':1,'status':'offered'},focus_enabled=True,selected_study='biology',studies=[{'id':'biology','name':'Biology 101','date':'2026-11-06','deck_ids':[str(parent)],'active':True}],favorites=[str(parent)],last_studied=str(c.decks.id('Biology 101::Week 1 · Cells')))
        a.store.write(profile);a.profile=a.store.read()
        import importlib
        rewards=importlib.import_module('1011095603.gamification.nook_level').manager
        foreign_config=importlib.import_module('1011095603.core.config');ng=foreign_config.get_config();ng.setdefault('restaurant_level',{}).update(enabled=True,notifications_enabled=False);foreign_config.write_config(ng);rewards.set_enabled(True)
        cfg=a.get_config();cfg.update(visual_owner='atelier',mode='workspace',theme='forest',motion=False,surface_revision=1);mw.addonManager.writeConfig(a.module,cfg)
        controller=mw._atelier_authoring_routes.controller
        if controller.store is None:controller.profile_open()
        st=controller.store;project=st.project({'title':'Landscapes · Field notes','description':'Example source project for the Atelier listing.','cover':'botanical'})
        data=(target/'web/world-art/forest-1.0.3.png').read_bytes();blob=st.save_blob(data,'png')
        source=st.add_source(project['id'],'A mountain lake','image',[{'text':'Look at the landscape. Use Mask figure to make an image-occlusion card, or draft a question beside this source.','assets':[{'blob':blob,'label':'Mountain lake · illustrative example'}]},{'text':'Field notes: keep one question focused on one thing you want to recall.'}])['source']
        report['move_source']=str(c.decks.id('Biology 101::Week 1 · Cells'));report['move_target']=str(chem);report['cards_before_move']=c.db.all('select id,nid,did,type,queue,due,ivl,factor,reps,lapses from cards order by id')
        report['onigiri_loaded']=bool(a.ownership.report(refresh=True).get('onigiri_loaded'));report['example_data']=True;report['source_project']=project['id'];report['source_id']=source['id'];report['collection_counts']={'notes':c.note_count(),'cards':c.card_count()}
        mw.resize(1440,900);mw.toolbarWeb.hide();mw.deckBrowser.refresh()
        report['native_toolbar_forced_hidden_in_qa']=True
        QTimer.singleShot(250,lambda:report['checks'].update(native_toolbar_restored=not mw.toolbarWeb.isHidden()))
        (OUT/'cdp.json').write_text(json.dumps({'port':port,'ready':True,'project':project['id'],'source':source['id'],'move_source':report['move_source'],'move_target':report['move_target']}))
        QTimer.singleShot(500,poll)
    except Exception:report['errors'].append(traceback.format_exc());finish()
def poll():
    try:
        routes=getattr(aqt.mw,'_atelier_authoring_routes',None)
        window=getattr(getattr(routes,'controller',None),'window',None)
        if window and window.isVisible() and not window.property('publishSized'):
            window.resize(1360,960);window.setProperty('publishSized',True)
        if (OUT/'verify-move.flag').exists() and not report['checks']:
            c=aqt.mw.col;did=int(report['move_source']);checks=report['checks']
            checks['ui_confirmation_reaches_native_reparent']=c.decks.get(did)['name']=='Chemistry 101::Week 1 · Cells'
            checks['card_ids_and_schedule_preserved']=c.db.all('select id,nid,did,type,queue,due,ivl,factor,reps,lapses from cards order by id')==report['cards_before_move']
            c.undo();checks['native_undo_restores_ui_move']=c.decks.get(did)['name']=='Biology 101::Week 1 · Cells'
            checks['database_integrity']=c.db.scalar('pragma integrity_check')=='ok'
            report.pop('cards_before_move',None);aqt.mw.deckBrowser.refresh()
            (OUT/'move-verified.json').write_text(json.dumps({'checks':checks,'runtime_sha256':runtime_digest()},indent=2))
        if (OUT/'verify-icons.flag').exists() and not report.get('icons_checked'):
            report['icons_checked']=True;a=aqt.mw._daedalus_atelier_runtime;a.ensure_store();stored=a.store.read()
            report['checks']['icon_metadata_persisted']=stored['folder_icons'].get(report['move_target'])=='pills'
            report['checks']['icons_do_not_change_cards']=aqt.mw.col.db.all('select id,nid,did,type,queue,due,ivl,factor,reps,lapses from cards order by id')==report.get('cards_before_move')
            report.pop('cards_before_move',None)
            (OUT/'icons-verified.json').write_text(json.dumps({'checks':report['checks'],'onigiri_loaded':report.get('onigiri_loaded',False)},indent=2))
        if (OUT/'verify-updates.flag').exists() and not report.get('updates_checked'):
            report['updates_checked']=True
            report['checks']['actual_anki_update_action_reached']=bool(getattr(aqt.mw,'_qa_update_calls',[]))
            (OUT/'updates-verified.json').write_text(json.dumps({'checks':report['checks'],'runtime_sha256':runtime_digest(),'category':'real update QAction and native Anki handler with controlled release-query boundary; no network/download/install'},indent=2))
        if (OUT/'stop.flag').exists():finish();return
        QTimer.singleShot(500,poll)
    except Exception:report['errors'].append(traceback.format_exc());finish()
QTimer.singleShot(3000,start);QTimer.singleShot(300000,finish)
code=app.exec();report['graceful_shutdown']=code==0
(OUT/'host-report.json').write_text(json.dumps(report,indent=2)+'\n')

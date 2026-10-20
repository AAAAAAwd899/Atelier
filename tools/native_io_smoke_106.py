"""Real native IO question/answer, view transform, grade and Undo in synthetic data.
Run with the installed Anki Python, never the user's profile.
"""
from pathlib import Path
import os,sys,json,shutil,traceback,hashlib,time
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/native-io-106-profile'/('run-'+str(time.time_ns()));BASE.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='windows',QT_SCALE_FACTOR='0.666666667',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki,anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
ANKI_VERSION=''.join(c for c in buildinfo.version if c.isalnum() or c in '.-_')
OUT=ROOT/('output/native-io-106-'+ANKI_VERSION);OUT.mkdir(parents=True,exist_ok=True)
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Atelier IO QA');pm.load('Atelier IO QA')
pm.meta.update(firstRun=False,defaultLang='en_US',updates=False,check_for_updates=False,uiScale=2/3);pm.profile.update(autoSync=False);pm.save();pm.db.close()
sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest, production_files
fingerprint=runtime_digest(Path(os.environ.get('ATELIER_NATIVE_SRC',ROOT/'src')))
target=BASE/'addons21/daedalus_atelier'
shutil.copytree(Path(os.environ.get('ATELIER_NATIVE_SRC',ROOT/'src')),target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
assert all((target/n).read_bytes()==p.read_bytes() for p,n in production_files()), 'Native copy differs from release payload'
cfg=json.loads((target/'config.json').read_text(encoding='utf8'));cfg.update(visual_owner='atelier',mode='workspace',theme='midnight',motion=False)
(target/'meta.json').write_text(json.dumps({'config':cfg}),encoding='utf8')
import aqt
from aqt.qt import QTimer,QImage,QPainter,QColor,QFont
aqt.AnkiApp.secondInstance=lambda self:False
app=aqt._run(['anki','-b',str(BASE),'-p','Atelier IO QA','-l','en_US'],exec=False)
report={'runtime_sha256':fingerprint,'payload_bytes_equal':True,'input_method':'scripted native API and JavaScript calls; no physical input device', 'category':'actual Anki native IO renderer and collection; synthetic Windows profile','anki':buildinfo.version,'captures':[],'checks':{},'errors':[],'owner_profile_accessed':False}
attempts=0;card_id=0;before=None;original_note=None;media_file=None;finished=False
def done():
    global finished
    if finished:return
    finished=True
    (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    import threading
    watchdog=threading.Timer(30,lambda:os._exit(2));watchdog.daemon=True;watchdog.start()
    aqt.mw.unloadProfileAndExit()

def fail():report['errors'].append(traceback.format_exc());done()
def shot(stage,then,retries=0):
    def result(value):
        if (not value or not value.get('stage') or value['stage']['height']<1) and retries<20:
            QTimer.singleShot(500,lambda:shot(stage,then,retries+1));return
        report['captures'].append({'stage':stage,'dom':value})
        if stage in ('question','answer'):
            i=value.get('image');c=value.get('canvas');s=value.get('stage')
            report['checks'][stage+'_registered']=bool(i and c and all(abs(i[k]-c[k])<2 for k in ('x','y','width','height')))
            report['checks'][stage+'_fits']=bool(s and s['bottom']<=value['viewport'][1]+2 and value.get('fit'))
        (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        def painted():
            aqt.mw.grab().save(str(OUT/(stage+'.png')))
            QTimer.singleShot(600,then)
        QTimer.singleShot(600,painted)
    aqt.mw.web.evalWithCallback('''(()=>{let s=document.querySelector('#image-occlusion-container'),i=s?.querySelector('img'),c=s?.querySelector('canvas');let r=e=>{if(!e)return null;let b=e.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height,bottom:b.bottom}};let ink=null;try{ink=Array.from(c.getContext('2d').getImageData(Math.floor(c.width*.3),Math.floor(c.height*.28),1,1).data)}catch(e){ink=String(e)};return {viewport:[innerWidth,innerHeight],stage:r(s),image:r(i),canvas:r(c),canvasInk:ink,imageVisibility:i&&getComputedStyle(i).visibility,canvasVisibility:c&&getComputedStyle(c).visibility,canvasOpacity:c&&getComputedStyle(c).opacity,stageVisibility:s&&getComputedStyle(s).visibility,stageHTML:s?.outerHTML,fit:!!document.querySelector('#atelier-image-fit'),info:window.__atelierReviewCard,diagnostics:window.AtelierReview?.diagnostics()}})()''',result)
def answer():
    try:
        aqt.mw.reviewer._showAnswer();QTimer.singleShot(1800,lambda:shot('answer',actual_size))
    except Exception:fail()
def actual_size():
    aqt.mw.web.eval("document.getElementById('atelier-image-fit')?.click()")
    QTimer.singleShot(500,lambda:shot('actual-size',grade))
def grade():
    try:
        col=aqt.mw.col
        report['checks']['renderer_did_not_change_note_fields']=col.get_note(col.get_card(card_id).nid).fields==original_note
        report['checks']['original_image_bytes_unchanged']=hashlib.sha256(media_file.read_bytes()).hexdigest()==report['media_sha256']
        aqt.mw.reviewer._answerCard(3)
        QTimer.singleShot(1500,undo)
    except Exception:fail()
def undo():
    try:
        col=aqt.mw.col
        report['checks']['native_grade_added_revlog']=col.db.scalar('select count(*) from revlog where cid=?',card_id)==before['revlogs']+1
        col.undo()
        c=col.get_card(card_id)
        report['checks']['native_undo_restored_schedule']={k:getattr(c,k) for k in ['type','queue','due','ivl','reps','lapses']}==before['card']
        report['checks']['native_undo_restored_revlog']=col.db.scalar('select count(*) from revlog where cid=?',card_id)==before['revlogs']
        done()
    except Exception:fail()
def start():
    global attempts,card_id,before,original_note,media_file
    attempts+=1
    try:
        if attempts==1:
            # Let Anki's initial deck-browser document finish before switching
            # to review; switching during its first load races native scripts.
            QTimer.singleShot(5000,start);return
        mw=aqt.mw;col=mw.col
        if not col or not getattr(mw,'_daedalus_atelier_runtime',None):
            if attempts>30:raise RuntimeError('Native startup timeout')
            QTimer.singleShot(1000,start);return
        mw.resize(1440,900)
        col._backend.add_image_occlusion_notetype();col.models._clear_cache()
        model=next(m for m in col.models.all() if m.get('originalStockKind')==6)
        img=QImage(800,1200,QImage.Format.Format_RGB32);img.fill(QColor('#f4f0e7'));p=QPainter(img)
        p.setPen(QColor('#142d46'));p.setFont(QFont('Segoe UI',26));p.drawText(60,90,'Synthetic native image-occlusion test')
        p.fillRect(200,300,180,100,QColor('#91bbd6'));p.drawText(220,360,'Landmark')
        p.drawLine(0,600,800,600);p.drawLine(400,0,400,1200);p.drawText(60,1150,'Original image: 800 × 1200');p.end()
        image_path=OUT/'source-landmarks.png';img.save(str(image_path))
        name=col.media.add_file(str(image_path));media_file=Path(col.media.dir())/name
        report['media_sha256']=hashlib.sha256(media_file.read_bytes()).hexdigest()
        n=col.new_note(model);n['Occlusion']='{{c1::image-occlusion:rect:left=0.25:top=0.25:width=0.225:height=0.0833333:oi=1}}'
        n['Image']='<img src="'+name+'">';n['Header']='Native IO · whole-stage fit';n['Back Extra']='The original image and native mask remain separate.'
        did=col.decks.id('Atelier IO QA::'+str(time.time_ns())+'::Tall page landmarks');col.add_note(n,did);card_id=n.cards()[0].id;original_note=list(n.fields)
        c=col.get_card(card_id);before={'card':{k:getattr(c,k) for k in ['type','queue','due','ivl','reps','lapses']},'revlogs':col.db.scalar('select count(*) from revlog where cid=?',card_id)}
        col.decks.select(did);mw.moveToState('review')
        QTimer.singleShot(5000,lambda:shot('question',answer))
    except Exception:fail()
QTimer.singleShot(1500,start)
QTimer.singleShot(90000,lambda:(report['errors'].append('native IO test timeout'),done()))
code=app.exec()
report['checks']['graceful_shutdown']=code==0
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'anki':report['anki'],'checks':report['checks'],'errors':report['errors']},indent=2))
if report['errors'] or not all(report['checks'].values()):sys.exit(1)

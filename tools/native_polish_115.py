"""Actual installed Anki + Onigiri, disposable defaults, Qt offscreen only.
Third-party code and assets stay in the disposable QA tree, never src/dist.
"""
from pathlib import Path
import os,sys,json,time,shutil,hashlib,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import production_files,runtime_digest
ALONE='--onigiri-only' in sys.argv
OUT=ROOT/('output/onigiri-alone-115' if ALONE else 'output/onigiri-coexistence-115');OUT.mkdir(parents=True,exist_ok=True)
BASE=OUT/('profile-'+str(time.time_ns()));BASE.mkdir()
foreign=Path.home()/'AppData/Roaming/Anki2/addons21/1011095603'
assert shutil.disk_usage(ROOT).free>50*1024**3+450_000_000
target=BASE/'addons21/daedalus_atelier';target.mkdir(parents=True)
for src,name in ([] if ALONE else production_files()):
    dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
excluded={'user_files','__pycache__','.git','__MACOSX','tests','meta.json','config.json','onigiri_layout.json'}
def ignore(folder,names):return {n for n in names if n in excluded or n.startswith('.env') or Path(n).suffix in {'.db','.anki2','.sqlite','.sqlite3','.pyc'}}
shutil.copytree(foreign,BASE/'addons21/1011095603',ignore=ignore)
(BASE/'addons21/1011095603/config.json').write_text('{}',encoding='utf8')
os.environ.update(QT_QPA_PLATFORM='offscreen',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki.lang
from anki import buildinfo
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Companion QA');pm.load('Companion QA')
pm.meta.update(firstRun=False,defaultLang='en_US',updates=False,check_for_updates=False);pm.profile.update(autoSync=False);pm.save();pm.db.close()
import aqt,aqt.main
from aqt.qt import QTimer
aqt.AnkiApp.secondInstance=lambda self:False
report={'category':'actual installed Anki and installed Onigiri source with disposable default settings; Qt offscreen, not Windows-display acceptance','anki':buildinfo.version,'runtime_sha256':runtime_digest(),'owner_profile_accessed':False,'owner_addons_modified':False,'checks':{},'errors':[],'captures':[],'completed':False,'atelier_enabled':not ALONE,'visual_capture':'Offscreen Qt grab can show a stale composited frame; diagnostic only, not accepted visual evidence.'}
aqt.main.showWarning=lambda message,*a,**k:report['errors'].append('Anki warning: '+str(message))
app=aqt._run(['anki','-b',str(BASE),'-p','Companion QA','-l','en_US'],exec=False)
assert app.platformName()=='offscreen';report['platform']=app.platformName()
done=False
def check(name,value):
    report['checks'][name]=bool(value)
    if not value:raise AssertionError(name)
def finish():
    global done
    if done:return
    done=True
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    import threading
    watchdog=threading.Timer(25,lambda:os._exit(2));watchdog.daemon=True;watchdog.start()
    aqt.mw.unloadProfileAndExit()
def fail():report['errors'].append(traceback.format_exc());finish()
def later(fn,ms=1800):QTimer.singleShot(ms,fn)
def start(attempt=0):
    try:
        global owner,cid,before,notes,history,reward_manager
        mw=aqt.mw
        for widget in app.topLevelWidgets():
            if type(widget).__name__=='ChooseAddonsToUpdateDialog':widget.reject()
        owner=getattr(mw,'_daedalus_atelier_runtime',None)
        if not mw.col or (not ALONE and not owner):
            if attempt<60:later(lambda:start(attempt+1),500);return
            raise RuntimeError('Atelier did not start')
        check('onigiri_loaded',any(name.endswith('.rendering.patcher') for name in sys.modules))
        from aqt import gui_hooks
        report['onigiri_answer_hooks_before']=[getattr(fn,'__module__','')+'.'+getattr(fn,'__name__','') for fn in gui_hooks.reviewer_did_answer_card._hooks if getattr(fn,'__module__','').startswith('1011095603')]
        if owner:report['owner_detection']=owner.ownership.report(refresh=True)
        import importlib
        reward_manager=importlib.import_module('1011095603.gamification.nook_level').manager
        foreign_config=importlib.import_module('1011095603.core.config');ng=foreign_config.get_config();ng.setdefault('restaurant_level',{}).update(enabled=True,notifications_enabled=False);foreign_config.write_config(ng);reward_manager.set_enabled(True)
        report['test_settings']='Disposable defaults with Nook Level rewards enabled and notifications off'
        report['xp_before']=reward_manager.get_progress().total_xp
        if owner:
            cfg=owner.get_config();cfg.update(visual_owner='atelier',mode='workspace',theme='obsidian',review_style='adaptive',motion=False,acknowledged_makeovers=[x['id'] for x in owner.ownership.report()['makeovers']]);mw.addonManager.writeConfig(owner.module,cfg);owner.ownership.install()
        c=mw.col;did=c.decks.id('Example course::Lecture');n=c.new_note(c.models.by_name('Basic'));n['Front']='Synthetic companion question';n['Back']='Synthetic answer';c.add_note(n,did)
        cid=c.find_cards('deck:"Example course::Lecture"')[0]
        before=c.db.all('select * from cards order by id');notes=c.db.all('select * from notes order by id');history=c.db.all('select * from revlog')
        c.decks.select(did);mw.web.eval("document.querySelector('#onigiri-welcome-overlay .btn-continue')?.click()");mw.resize(1280,900)
        if owner:
            mw.toolbarWeb.hide();mw.moveToState('deckBrowser');mw.deckBrowser.refresh();later(home_bar)
        else:mw.onOverview();later(overview)
    except Exception:fail()
def home_bar(attempt=0):
    def result(v):
        try:
            if not v or not v.get('loaded'):
                if attempt<30:later(lambda:home_bar(attempt+1),500);return
                raise RuntimeError('Atelier home action bar did not finish loading')
            if v.get('tour') and attempt<30:
                aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('[data-action=tour-skip]').click()");later(lambda:home_bar(attempt+1),700);return
            report['home_action_bar']=v
            check('stock_toolbar_hidden_for_compatibility_test',not aqt.mw.toolbarWeb.isVisible())
            for command,visible in v['commands'].items():check('home_action_visible_and_hit_testable_'+command,visible)
            aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('.decks-top').click()")
            later(home_navigated,600)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("""(()=>{const s=document.getElementById('atelier-root')?.shadowRoot;const loaded=!!window.AtelierMakeover?.diagnostics().loaded;if(!s||!loaded)return null;const commands={};for(const k of ['decks-top','add-cards-top','browse-top','stats-top','sync-top','addon-tools-top']){const b=s.querySelector('.anki-commandbar .'+k),r=b?.getBoundingClientRect();const hit=r&&s.elementFromPoint(r.x+r.width/2,r.y+r.height/2);commands[k]=!!b&&!!r&&r.width>0&&r.height>0&&r.y>=0&&r.bottom<=innerHeight&&b.contains(hit)}return {loaded,tour:!!s.querySelector('[data-action=tour-skip]'),commands,viewport:[innerWidth,innerHeight]}})()""",result)

def home_navigated():
    def result(v):
        try:
            check('topbar_decks_opens_library',v=='library')
            aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('.folder-explorer-launch').click()")
            later(full_library,800)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("window.AtelierMakeover?.diagnostics().page",result)

def full_library():
    def result(v):
        try:
            check('full_library_button_opens_native_main_tree',v.get('tree'))
            check('local_authored_atlas_loaded_in_native_anki',v.get('art')=='ready')
            report['native_library_sidebar_rows']=v['sidebar']
            aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('[data-action=expand-folders]').click()")
            later(opened_branch,400)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("(()=>{const h=document.getElementById('atelier-root'),s=h.shadowRoot;return {tree:!!s.querySelector('.folder-outline'),art:h.dataset.folderArt,sidebar:s.querySelectorAll('.tree-row').length}})()",result)

def opened_branch():
    def result(v):
        try:
            check('native_whole_branch_exposes_lecture',v.get('lecture'))
            check('native_main_expansion_keeps_sidebar_compact',v['sidebar']==report['native_library_sidebar_rows'])
            aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('.outline-row [data-action=organize]').click()")
            later(icon_choice,400)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("(()=>{const s=document.getElementById('atelier-root').shadowRoot;return {lecture:[...s.querySelectorAll('.outline-row .outline-open strong')].some(e=>e.textContent==='Lecture'),sidebar:s.querySelectorAll('.tree-row').length}})()",result)

def icon_choice():
    def result(v):
        try:
            check('native_picker_has_24_symbols_and_automatic',v==25)
            aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('[data-action=folder-icon][data-icon=music]').click()")
            later(icon_saved,600)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("document.getElementById('atelier-root').shadowRoot.querySelectorAll('[data-action=folder-icon]').length",result)

def icon_saved():
    def result(v):
        try:
            check('new_symbol_saves_through_real_native_bridge',v.get('symbol')=='music' and v.get('pressed')=='true')
            aqt.mw.web.eval("document.getElementById('atelier-root').shadowRoot.querySelector('.dialog-header [data-action=close-dialog]').click()")
            aqt.mw.onOverview();later(overview)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("(()=>{const s=document.getElementById('atelier-root').shadowRoot;return {symbol:s.querySelector('.personalization-art [data-folder-symbol]')?.dataset.folderSymbol,pressed:s.querySelector('[data-action=folder-icon][data-icon=music]')?.getAttribute('aria-pressed')}})()",result)

def overview(attempt=0):
    def result(v):
        try:
            if (not isinstance(v,dict) or not v.get('studyRect')) and attempt<30:
                later(lambda:overview(attempt+1),500);return
            if not isinstance(v,dict):raise RuntimeError('Overview did not finish loading')
            if v.get('welcome') and attempt<30:
                aqt.mw.web.eval("document.querySelector('#onigiri-welcome-overlay .btn-continue')?.click()");later(lambda:overview(attempt+1),700);return
            report['overview']=v
            aqt.mw.grab().save(str(OUT/'overview.png'))
            if not ALONE:check('native_overview_is_atelier_scoped',v.get('screen')=='overview')
            check('onigiri_profile_and_progress_retained',v['profile'] and v['progress'])
            check('study_control_visible_and_hit_testable',v['studyHit'])
            check('overview_has_no_horizontal_overflow',v['fits'])
            check('original_overview_actions_retained',all(v['actions']))
            check('rendering_did_not_mutate_cards_or_notes',aqt.mw.col.db.all('select * from cards order by id')==before and aqt.mw.col.db.all('select * from notes order by id')==notes)
            aqt.mw.grab().save(str(OUT/'overview.png'));report['captures'].append('overview.png')
            aqt.mw.web.eval("document.getElementById('study').click()");later(question)
        except Exception:fail()
    aqt.mw.web.evalWithCallback('''(()=>{if(!document.documentElement||!document.getElementById('study'))return null;const s=document.getElementById('study'),r=s?.getBoundingClientRect(),hit=r&&document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {welcome:!!document.querySelector('#onigiri-welcome-overlay'),viewport:[innerWidth,innerHeight],studyRect:r?{x:r.x,y:r.y,w:r.width,h:r.height}:null,hit:hit?.outerHTML?.slice(0,700),controls:[...document.querySelectorAll('button,a')].map(e=>({text:e.textContent.trim(),id:e.id,onclick:e.getAttribute('onclick'),href:e.getAttribute('href')})),screen:document.documentElement.dataset.atelierScreen,profile:!!document.querySelector('.profile-bar'),progress:!!document.querySelector('.onigiri-deck-progress'),studyHit:!!s&&s.contains(hit),fits:document.scrollingElement.scrollWidth<=innerWidth+1,actions:['opts','studymore','description'].map(x=>!!document.querySelector('[onclick*="'+x+'"]')),fonts:[...document.querySelectorAll('.stats-row,.profile-name')].map(x=>({text:x.textContent.trim(),font:getComputedStyle(x).fontFamily,size:getComputedStyle(x).fontSize}))}})()''',result)
def question():
    try:
        check('study_click_reaches_native_reviewer',aqt.mw.state=='review' and aqt.mw.reviewer.card.id==cid)
        aqt.mw.web.evalWithCallback("({text:document.getElementById('qa')?.textContent,headers:document.querySelectorAll('#atelier-review-header').length})",question_result)
    except Exception:fail()
def question_result(v):
    try:
        check('question_and_single_context_header_preserved','Synthetic companion question' in v['text'] and v['headers']<=1)
        footer_click('ans','show_answer_button',answer)
    except Exception:fail()
def footer_click(command,key,next_step):
    def result(v):
        try:
            report[key]=v
            check(key+'_visible_and_hit_testable',isinstance(v,dict) and v.get('hit') and v.get('clicked'))
            later(next_step)
        except Exception:fail()
    code=r"""(()=>{const command=COMMAND;const candidates=[...document.querySelectorAll('button,a,[role=button]')];const b=candidates.find(e=>{const h=e.getAttribute('onclick')||'';return h.includes(command)&&/pycmd/.test(h)})||document.querySelector(command==='ans'?'#ansbut':'[data-ease="3"]');const r=b?.getBoundingClientRect();const hit=!!r&&r.width>0&&r.height>0&&r.y>=0&&r.bottom<=innerHeight+1&&b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));const out={hit,clicked:false,command,viewport:[innerWidth,innerHeight],buttons:candidates.map(e=>({id:e.id,text:e.textContent.trim().slice(0,80),onclick:e.getAttribute('onclick')}))};if(hit&&!b.disabled){b.click();out.clicked=true}return out})()""".replace('COMMAND',json.dumps(command))
    aqt.mw.bottomWeb.evalWithCallback(code,result)

def answer():
    def result(v):
        try:
            check('native_answer_visible','Synthetic answer' in v)
            aqt.mw.grab().save(str(OUT/'answer.png'));report['captures'].append('answer.png')
            footer_click('ease3','good_rating_button',undo)
        except Exception:fail()
    aqt.mw.web.evalWithCallback("document.getElementById('qa')?.textContent||''",result)
def undo():
    try:
        c=aqt.mw.col
        report['undo_status_after_grade']=str(c.undo_status())
        check('grading_adds_one_native_review',len(c.db.all('select * from revlog'))==len(history)+1)
        report['xp_after_answer']=reward_manager.get_progress().total_xp
        check('onigiri_xp_increases_after_native_answer',report['xp_after_answer']>report['xp_before'])
        from aqt import gui_hooks
        def undone(changes):
            gui_hooks.state_did_undo.remove(undone);later(verify_undo,500)
        gui_hooks.state_did_undo.append(undone)
        aqt.mw.onUndo();return
    except Exception:fail()
def verify_undo():
    try:
        c=aqt.mw.col
        report['undo_diagnostic']={'cards_before':before,'cards_after':c.db.all('select * from cards order by id'),'revlog_before':history,'revlog_after':c.db.all('select * from revlog'),'undo_status':str(c.undo_status())}
        check('native_undo_restores_cards_and_history',c.db.all('select * from cards order by id')==before and c.db.all('select * from revlog')==history)
        report['xp_after_undo']=reward_manager.get_progress().total_xp
        check('onigiri_xp_undo_matches_native_undo',report['xp_after_undo']==report['xp_before'])
        from aqt import gui_hooks
        report['onigiri_answer_hooks_after']=[getattr(fn,'__module__','')+'.'+getattr(fn,'__name__','') for fn in gui_hooks.reviewer_did_answer_card._hooks if getattr(fn,'__module__','').startswith('1011095603')]
        check('reward_hooks_still_installed',bool(report['onigiri_answer_hooks_before']) and report['onigiri_answer_hooks_before']==report['onigiri_answer_hooks_after'])
        if owner:
            cfg=owner.get_config();cfg['visual_owner']='onigiri';aqt.mw.addonManager.writeConfig(owner.module,cfg);owner.ownership.install()
            check('switching_owner_releases_presentation_gates',not owner.ownership._wrapped)
        check('database_integrity',c.db.scalar('pragma integrity_check')=='ok')
        report['completed']=True;finish()
    except Exception:fail()
later(start,3000);later(finish,180000)
code=app.exec();report['graceful_shutdown']=code==0
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
if not report['completed'] or report['errors'] or not all(report['checks'].values()):raise SystemExit(1)

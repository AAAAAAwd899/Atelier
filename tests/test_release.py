import sys, types, importlib, json
from types import SimpleNamespace as NS
import pytest
from fixtures import core, review, SRC
own = importlib.import_module('atelier_testing.ownership')

@pytest.mark.parametrize('value',['ask','atelier','onigiri'])
def test_owner_is_persisted(value):
    assert core.settings({'visual_owner':value})['visual_owner']==value

def test_invalid_owner_defaults_to_ask():
    assert core.settings({'visual_owner':'bad'})['visual_owner']=='ask'

@pytest.fixture
def onigiri(monkeypatch):
    calls=[]
    patch=types.ModuleType('test_onigiri.patcher')
    for name in own.CSS_FUNCTIONS + own.VOID_FUNCTIONS:
        setattr(patch,name,lambda *a,_name=name,**kw: calls.append(_name) or ('native-css' if _name in own.CSS_FUNCTIONS else None))
    parent=types.ModuleType('test_onigiri');parent.patcher=patch;parent.onigiri_renderer=object()
    monkeypatch.setitem(sys.modules,'test_onigiri',parent);monkeypatch.setitem(sys.modules,'test_onigiri.patcher',patch)
    cfg={'visual_owner':'atelier','review_style':'adaptive'}
    owner=NS(get_config=lambda:cfg,current_state=lambda:'deckBrowser')
    gate=own.Ownership(owner);gate.install()
    yield gate,patch,cfg,calls
    gate.dispose()

@pytest.mark.parametrize('name',own.CSS_FUNCTIONS + own.VOID_FUNCTIONS)
def test_adapter_gates_only_in_atelier(onigiri,name):
    gate,patch,cfg,calls=onigiri
    result=getattr(patch,name)()
    assert not calls
    assert result==('' if name in own.CSS_FUNCTIONS else None)
    cfg['visual_owner']='onigiri'
    getattr(patch,name)()
    assert calls==[name]

def test_wrapper_idempotent_restore(onigiri):
    gate,patch,cfg,calls=onigiri
    fn=patch.generate_reviewer_background_css
    gate.install();assert patch.generate_reviewer_background_css is fn
    gate.dispose();assert patch.generate_reviewer_background_css()=='native-css'
    assert not getattr(patch.generate_reviewer_background_css,'_atelier_visual_gate',False)

def test_review_recovery_returns_native_presentation(onigiri):
    gate,patch,cfg,calls=onigiri
    gate.owner.current_state=lambda:'review';cfg['review_style']='off'
    assert patch.generate_reviewer_background_css()=='native-css'

def test_palette_rejects_css_injection():
    with pytest.raises(ValueError):own.validate_palette({'bg':'red;}</style>'})
    pal=own.validate_palette({'bg':'#111111','panel':'#222222','text':'#eeeeee','accent':'#abcdef','junk':'url(x)','scheme':'dark'})
    assert 'junk' not in pal

@pytest.fixture
def app(monkeypatch,onigiri):
    class QObject: pass
    class QWidget: pass
    qt=types.ModuleType('aqt.qt')
    for n,v in dict(QAction=object,QApplication=object,QEvent=object,QObject=QObject,Qt=object,QWidget=QWidget).items():setattr(qt,n,v)
    class DeckBrowser: pass
    db=types.ModuleType('aqt.deckbrowser');db.DeckBrowser=DeckBrowser;db.DeckBrowserBottomBar=type('DeckBrowserBottomBar',(),{})
    data={1:'School',2:'School::Lecture A',3:'School::Lecture B'};actions=[];jobs=[];configs=core.settings({'visual_owner':'ask','surface_revision':1})
    class Decks:
        def get(self,id,default=False):return {'name':data[id],'id':id} if id in data else None
        def all_names_and_ids(self,**kw):return [NS(id=i,name=n) for i,n in data.items()]
        def set_current(self,id):actions.append(('select',id));return NS(changes=NS())
    col=NS(decks=Decks(),startTimebox=lambda:actions.append(('timebox',)))
    class Op:
        def __init__(self,parent=None,op=None,success=None,*a):self.op=op;self.ok=success;self.err=None
        def success(self,f):self.ok=f;return self
        def failure(self,f):self.err=f;return self
        def run_in_background(self):
            try:r=self.op(col)
            except Exception as e:
                if self.err:self.err(e)
                else:raise
            else:
                if self.ok:self.ok(r)
    ops=types.ModuleType('aqt.operations');ops.CollectionOp=ops.QueryOp=Op
    utils=types.ModuleType('aqt.utils');utils.showInfo=lambda *a:None
    def writeConfig(module,c):configs.clear();configs.update(c)
    mw=NS(col=col,state='deckBrowser',addonManager=NS(addonFromModule=lambda m:'daedalus_atelier',getConfig=lambda m:dict(configs),writeConfig=writeConfig),progress=NS(single_shot=lambda ms,fn,*a:jobs.append(fn)),onOverview=lambda:actions.append(('overview',)),moveToState=lambda s:actions.append(('state',s)))
    aqt=types.ModuleType('aqt');aqt.mw=mw;aqt.gui_hooks=NS()
    for name,value in [('aqt',aqt),('aqt.qt',qt),('aqt.deckbrowser',db),('aqt.operations',ops),('aqt.utils',utils)]:monkeypatch.setitem(sys.modules,name,value)
    monkeypatch.delitem(sys.modules,'atelier_testing.integration',raising=False)
    mod=importlib.import_module('atelier_testing.integration');a=mod.Atelier('daedalus_atelier')
    a.ensure_store=lambda:None;a.store=NS(write=lambda p:None);a.nonce='test';a.profile=core.profile_settings({})
    replies=[];a.reply=lambda n,r,**kw:replies.append(kw)
    return a,mw,actions,jobs,replies,configs

def test_quick_study_individual_native_dispatch(app):
    a,mw,actions,_,replies,_=app
    a.dispatch('test','r1','study_now',{'id':'2'})
    assert actions==[('select',2),('timebox',),('state','review')]
    assert a.profile['last_studied']=='2' and replies[-1]['result'] is True

def test_quick_study_parent_cannot_start(app):
    a,mw,actions,_,replies,_=app
    a.dispatch('test','r1','study_now',{'id':'1'})
    assert not actions and 'individual lecture' in replies[-1]['error']

@pytest.mark.parametrize('value,mode',[('atelier','workspace'),('onigiri','native')])
def test_owner_save_then_reload(app,value,mode):
    a,mw,actions,jobs,replies,configs=app
    a.dispatch('test','r1','visual_owner',{'owner':value})
    assert configs['visual_owner']==value and configs['mode']==mode
    assert replies[-1]['result']['visual_owner']==value
    assert not actions
    jobs[-1]();assert actions==[('state','deckBrowser')]

def test_owner_no_smuggling_in_settings(app):
    a,*_=app
    with pytest.raises(core.ValidationError):a.dispatch('test','r1','settings',{'visual_owner':'onigiri'})

def test_sprout_shortcut_calls_existing_practice_tab(monkeypatch):
    link=importlib.import_module('atelier_testing.sprout_link');jobs=[];scripts=[]
    mw=NS(col=object(),state='deckBrowser',progress=NS(single_shot=lambda ms,fn:jobs.append(fn)))
    web=NS(evalWithCallback=lambda s,cb:(scripts.append(s),cb(True)))
    c=NS(mw=mw,open=lambda:None,runner=None,dialog=NS(web=web,closed=False))
    monkeypatch.setitem(sys.modules,'exam_sprout.integration',NS(CONTROLLER=c))
    s=link.SproutLink(NS(get_config=lambda:core.settings({})),mw)
    assert s.open_practice();jobs.pop()()
    assert len(scripts)==1 and 'b.click()' in scripts[0] and 'data-view="practice"' in scripts[0]
    assert 'S.view' not in scripts[0] and 'innerHTML' not in scripts[0]

def test_manifest_and_not_preview_installer_source():
    m=json.loads((SRC/'manifest.json').read_text());assert m['package']=='daedalus_atelier' and m['human_version']==core.VERSION
    text=(SRC/'integration.py').read_text()
    assert '"preview": False' in text and 'ownership.js?v={VERSION}' in text
    assert 'reading_template' in (SRC/'review_theme.py').read_text()

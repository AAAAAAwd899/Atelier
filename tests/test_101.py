"""Regression/preservation tests for 1.0.1. Explicit native doubles, not hardware."""
import importlib, json,sys,types,hashlib,copy
from types import SimpleNamespace as NS
import pytest
from fixtures import SRC,ROOT,core,review
model=importlib.import_module('atelier_testing.remote_model')
remotes=importlib.import_module('atelier_testing.remotes')

@pytest.mark.parametrize('key',[32,48,57,65,90,0x01000004,0x01000005,0x01000013,0x01000016,0x01000030,0x01000047])
def test_key_allowlist(key):
 assert model.valid_key(key) and model.key_name(key)!='Not assigned'
@pytest.mark.parametrize('key',[True,False,None,0,-1,9,27,31,1000000000,'65',65.0,0x01000000])
def test_bad_key_rejected(key):assert not model.valid_key(key)
@pytest.mark.parametrize('value',[None,[],{'enabled':1},{'enabled':True},{'bindings':[]},{'bindings':{'delete':65}},{'bindings':{'good':65,'again':65}},{'enabled':True,'bindings':{'good':False}}])
def test_bad_settings(value):
 with pytest.raises(ValueError):model.validate_settings(value)
 assert model.settings(value)=={'enabled':False,'bindings':{}}
def test_passive_default_and_roundtrip():
 assert not core.settings({})['remote']['enabled']
 cfg={'enabled':True,'bindings':{'reveal':32,'good':74,'again':75}}
 assert core.settings({'remote':cfg})['remote']==cfg
 assert core.settings({'remote':{'enabled':True,'bindings':{'good':1}}})['remote']['enabled'] is False

def test_bounce_hold_across_cards():
 clock=[1.];gate=model.PressGate(lambda:clock[0])
 assert gate.press(74)
 clock[0]+=1
 assert not gate.press(74) and not gate.press(74,True)
 gate.release(74,True);assert not gate.press(74)
 gate.release(74);assert gate.press(74)
 gate.release(74);clock[0]+=.1;assert not gate.press(75)
 gate.reset();assert not gate.press(74)
 clock[0]+=.3;gate.release(74);assert gate.press(74)

BASE={'id':1,'css':'.card {font-family: arial;font-size:20px;text-align:center;color:black;background-color:white}', 'tmpls':[{'qfmt':'{{Front}}','afmt':'{{FrontSide}}<hr id=answer>{{Back}}'}]}
@pytest.mark.parametrize('html',[
 '<div id="io-container"><img id="io-original"><img id="io-qmask"></div>',
 '<div id="io_container"><img id="io_amask"></div>',
 '<div style="position: absolute;top:0"><img></div>',
 '<div style="transform:scale(.7)"><img></div>',
 '<div style="height:100vh">{{Front}}</div>',
 '{{cloze:Occlusion}}', '<canvas></canvas>', '<svg></svg>',
 '<div style="overflow:hidden">{{Front}}</div>',
])
def test_static_css_does_not_make_mask_template_eligible(html):
 m=copy.deepcopy(BASE);m['tmpls'][0]['qfmt']=html
 assert not review.reading_template(m)
def test_plain_text_still_eligible():assert review.reading_template(BASE)
@pytest.mark.parametrize('m',[{},None,{'tmpls':[]},{'tmpls':['bad']}])
def test_invalid_template_fails_closed(m):assert not review.reading_template(m)

def native(monkeypatch):
 callbacks=[];commands=[]
 web=NS(evalWithCallback=lambda js,fn:callbacks.append(fn),eval=lambda js:commands.append(('scroll',js)))
 card=NS(id=1)
 reviewer=NS(card=card,state='question',web=web,_getTypedAnswer=lambda:commands.append('reveal'),
  _answerCard=lambda n:commands.append(('grade',n)),_answerButtonList=lambda:[(1,'Again'),(2,'Hard'),(3,'Good'),(4,'Easy')],replayAudio=lambda:commands.append('replay'))
 mw=NS(col=object(),state='review',web=web,reviewer=reviewer)
 monkeypatch.setitem(sys.modules,'aqt',NS(mw=mw))
 cfg={'remote':{'enabled':True,'bindings':{'reveal':32,'good':74}},'theme':'forest','visual_owner':'atelier'}
 owner=NS(get_config=lambda:cfg,save_config=lambda x:cfg.update(x),package='daedalus_atelier')
 c=remotes.RemoteControls(owner);c.token='t';c.input_allowed=True;c.active=lambda *a:True;c.focused_web=lambda:web;c.footer_focus=lambda:False
 return c,mw,reviewer,callbacks,commands,cfg

@pytest.mark.parametrize('action,stage,want',[('reveal','question',['reveal']),('reveal','answer',[]),('good','question',[]),('good','answer',[('grade',3)]),('again','answer',[('grade',1)]),('hard','answer',[('grade',2)]),('easy','answer',[('grade',4)]),('replay','question',['replay'])])
def test_native_dispatch_is_explicit_and_stage_bound(monkeypatch,action,stage,want):
 c,mw,r,cb,commands,cfg=native(monkeypatch);r.state=stage;c.request(action);assert len(cb)==1
 cb[0]({'token':'t','ready':True});assert commands==want

@pytest.mark.parametrize('change',['editing','inactive','disabled','token','card','stage','collection','reviewer'])
def test_late_remote_reply_cannot_act_on_another_context(monkeypatch,change):
 c,mw,r,cb,commands,cfg=native(monkeypatch);r.state='answer';c.request('good')
 reply={'token':'t','ready':True}
 if change=='editing':reply['ready']=False
 if change=='inactive':c.active=lambda *a:False
 if change=='disabled':cfg['remote']['enabled']=False
 if change=='token':c.token='changed'
 if change=='card':r.card=NS(id=2)
 if change=='stage':r.state='question'
 if change=='collection':mw.col=object()
 if change=='reviewer':mw.reviewer=NS()
 cb[0](reply);assert not commands

@pytest.mark.parametrize('action',['hard','easy'])
def test_unavailable_native_rating_not_substituted(monkeypatch,action):
 c,mw,r,cb,commands,cfg=native(monkeypatch);r.state='answer';r._answerButtonList=lambda:[(1,'Again'),(3,'Good')]
 c.request(action);cb[0]({'token':'t','ready':True});assert not commands

def test_pending_and_missing_permission_refuse(monkeypatch):
 c,mw,r,cb,commands,cfg=native(monkeypatch);c.input_allowed=False;c.request('reveal');assert not cb
 c.input_allowed=True;c.request('reveal');c.request('reveal');assert len(cb)==1
 cb[0](None);assert not commands and not c.pending

def test_guards_reset_on_leave(monkeypatch):
 c,mw,r,cb,commands,cfg=native(monkeypatch);c.state_changed('deckBrowser','review');assert not c.token and not c.input_allowed

def test_engine_and_every_non_allowlisted_byte_preserved():
 baseline=json.loads((ROOT/'baseline-1.0.0.json').read_text())
 allowed={'core.py','config.json','config.schema.json','manifest.json','integration.py','review_model.py','review_theme.py','web/reviewer.js','web/reviewer.css','web/atelier.js','USER-GUIDE.md','RELEASE-NOTES.md','config.md','SUPPORT.md'}
 changed=[]
 for rel,sha in baseline.items():
  assert (SRC/rel).is_file()
  if hashlib.sha256((SRC/rel).read_bytes()).hexdigest()!=sha:changed.append(rel)
 assert set(changed)<=allowed,changed
 assert not any(rel.startswith(('sprout/','workshop/')) for rel in changed)

@pytest.mark.parametrize('repeat',[False,True])
def test_keypress_consumed_once_no_duplicate_native_shortcut(monkeypatch,repeat):
 from enum import IntFlag
 c,mw,r,cb,commands,cfg=native(monkeypatch)
 class Mods(IntFlag):ControlModifier=1;MetaModifier=2;AltModifier=4;ShiftModifier=8
 types_=NS(ShortcutOverride=1,KeyPress=2,KeyRelease=3)
 monkeypatch.setitem(sys.modules,'aqt.qt',NS(QEvent=NS(Type=types_),Qt=NS(KeyboardModifier=Mods)))
 e=NS(key=lambda:74,modifiers=lambda:0,isAutoRepeat=lambda:repeat,accept=lambda:None)
 assert c.key_event(mw.web,e,types_.ShortcutOverride)
 assert c.key_event(mw.web,e,types_.KeyPress)
 assert len(cb)==(0 if repeat else 1)
 assert c.key_event(mw.web,e,types_.KeyPress)
 assert len(cb)==(0 if repeat else 1)

@pytest.mark.parametrize('mode',['editing','disabled','modifier','wrong-window','unmapped'])
def test_do_not_capture_ordinary_inputs(monkeypatch,mode):
 from enum import IntFlag
 c,mw,r,cb,commands,cfg=native(monkeypatch)
 class Mods(IntFlag):ControlModifier=1;MetaModifier=2;AltModifier=4;ShiftModifier=8
 T=NS(ShortcutOverride=1,KeyPress=2,KeyRelease=3)
 monkeypatch.setitem(sys.modules,'aqt.qt',NS(QEvent=NS(Type=T),Qt=NS(KeyboardModifier=Mods)))
 if mode=='editing':c.input_allowed=False
 if mode=='disabled':cfg['remote']['enabled']=False
 if mode=='wrong-window':c.active=lambda *a:False
 e=NS(key=lambda:65 if mode=='unmapped' else 74,modifiers=lambda:1 if mode=='modifier' else 0,isAutoRepeat=lambda:False,accept=lambda:None)
 assert not c.key_event(mw.web,e,T.ShortcutOverride) and not c.key_event(mw.web,e,T.KeyPress)
 assert not cb

def test_changed_focus_during_callback_does_not_grade(monkeypatch):
 c,mw,r,cb,commands,cfg=native(monkeypatch);r.state='answer';c.request('good');c.focused_web=lambda:object()
 cb[0]({'token':'t','ready':True});assert not commands

def test_native_footer_focus_can_use_remote(monkeypatch):
 c,mw,r,cb,commands,cfg=native(monkeypatch);c.input_allowed=False;c.footer_focus=lambda:True;c.request('reveal')
 cb[0]({'token':'t','ready':True});assert commands==['reveal']

def test_paint_hook_ignores_preview_and_mask_notes(monkeypatch):
 mod=importlib.import_module('atelier_testing.review_theme')
 cfg={'visual_owner':'atelier','review_style':'adaptive'}
 t=mod.ReviewTheme(NS(get_config=lambda:cfg));t.card_info=lambda *a:{'eligible':True,'protected':False,'id':'1','stage':'question'}
 assert t.prepare_card('<p>q</p>',None,'previewQuestion')=='<p>q</p>'
 value=t.prepare_card('<p>q</p>',None,'reviewQuestion')
 assert value.startswith('<p>q</p>') and 'onUpdateHook' in value and 'onShownHook' in value
 t.card_info=lambda *a:{'eligible':False,'protected':True}
 assert t.prepare_card('<div id="io-qmask">mask</div>',None,'reviewQuestion')=='<div id="io-qmask">mask</div>'
 cfg['visual_owner']='onigiri'
 assert t.prepare_card('<p>q</p>',None,'reviewQuestion')=='<p>q</p>'


def test_native_remote_dialog_contract(monkeypatch):
 """Construct actual UI against strict doubles; never label this native rendering."""
 from qt_session_double import Widget,Layout,Signal
 from enum import IntFlag
 class W(Widget):
  def __init__(self,*a):super().__init__(*a);self.finished=Signal();self.toggled=Signal();self.accepted=False
  def setWindowTitle(self,v):self.title=v
  def setAttribute(self,*v):self.attribute=v
  def resize(self,*v):self.dims=v
  def setMinimumSize(self,*v):self.mins=v
  def isActiveWindow(self):return True
  def isAncestorOf(self,x):return True
  def accept(self):self.accepted=True;self.finished.emit(1)
  def reject(self):self.finished.emit(0)
  def setWidgetResizable(self,x):pass
  def setFrameShape(self,x):pass
  def setWidget(self,x):self.widget=x
  def setChecked(self,x):self.checked=x;self.toggled.emit(x)
  Shape=NS(NoFrame=0)
 class L(Layout):
  def setHorizontalSpacing(self,v):pass
  def setVerticalSpacing(self,v):pass
 filters=[]
 class Mods(IntFlag):ControlModifier=1;MetaModifier=2;AltModifier=4;ShiftModifier=8
 T=NS(ShortcutOverride=1,KeyPress=2,KeyRelease=3)
 qt=NS(**{n:W for n in ('QDialog','QLabel','QPushButton','QCheckBox','QScrollArea','QWidget')},**{n:L for n in ('QVBoxLayout','QHBoxLayout','QGridLayout')},Qt=NS(Key=NS(Key_Escape=27),KeyboardModifier=Mods,WidgetAttribute=NS(WA_DeleteOnClose=1)),QEvent=NS(Type=T),QApplication=NS(instance=lambda:NS(installEventFilter=filters.append,removeEventFilter=filters.remove)))
 monkeypatch.setitem(sys.modules,'aqt.qt',qt)
 saved=[];controller=NS(config=lambda:{'enabled':False,'bindings':{}},owner=NS(get_config=lambda:{'theme':'forest','visual_owner':'atelier'}),save=lambda x:saved.append(x),window=None)
 ui=importlib.import_module('atelier_testing.remote_ui');d=ui.create_dialog(controller,W())
 assert d in filters and d.mins==(520,420)
 d.start_test();d.eventFilter(d,NS(type=lambda:2,isAutoRepeat=lambda:False,key=lambda:74,modifiers=lambda:0))
 assert 'Received: J' in d.status.text and not saved
 d.learn('good');d.eventFilter(d,NS(type=lambda:2,isAutoRepeat=lambda:False,key=lambda:74,modifiers=lambda:0))
 assert d.binding['good']==74 and not saved
 d.learn('again');d.eventFilter(d,NS(type=lambda:2,isAutoRepeat=lambda:False,key=lambda:74,modifiers=lambda:0))
 assert 'Clear that assignment' in d.status.text and 'again' not in d.binding
 d.enabled.setChecked(True);d.save();assert saved==[{'enabled':True,'bindings':{'good':74}}] and not filters and d.accepted

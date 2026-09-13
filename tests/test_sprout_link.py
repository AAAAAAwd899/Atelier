from fixtures import *
from types import SimpleNamespace as NS
import pytest
link=importlib.import_module('atelier_testing.sprout_link')

@pytest.fixture
def setup(monkeypatch):
 mw=NS(col=object(),state='deckBrowser')
 config=core.settings({})
 owner=NS(get_config=lambda:config,package="test_package")
 calls=[]
 c=NS(mw=mw,dialog=None,runner=None,open=lambda:calls.append('open'))
 monkeypatch.setitem(sys.modules,'exam_sprout.integration',NS(CONTROLLER=c))
 a=link.SproutLink(owner,mw)
 return a,c,mw,config,calls

class Bar:
 def __init__(self):self.sheet='original header stylesheet'
 def styleSheet(self):return self.sheet
 def setStyleSheet(self,v):self.sheet=v
class Web:
 def __init__(self):self.scripts=[]
 def eval(self,s):self.scripts.append(s)
class PlannerDialog:
 def __init__(self):self.web=Web();self.native_bar=Bar();self.closed=False


def test_optional_dependency_absent(monkeypatch):
 monkeypatch.delitem(sys.modules,'exam_sprout.integration',raising=False)
 assert link.controller(object()) is None

def test_controller_identity_and_open_guard(setup):
 a,c,mw,cfg,calls=setup
 assert a.available();assert a.open();assert calls==['open']
 mw.state='review';assert not a.open();assert calls==['open']
 mw.state='deckBrowser';mw.col=None;assert not a.open()
 c.mw=object();assert not a.available()

@pytest.mark.parametrize('kind',['planner','runner','foreign','same_name','none'])
def test_injection_context_allowlist(setup,kind):
 a,c,mw,cfg,_=setup;c.dialog=PlannerDialog()
 ctx={'planner':c.dialog,'runner':NS(),'foreign':object(),'same_name':PlannerDialog(),'none':None}[kind]
 content=NS(head='native head',body='<canvas>original</canvas>',css=['original.css'],js=['original.js'])
 a.add_content(content,ctx)
 assert ('atelier-sprout-tokens' in content.head)==(kind=='planner')
 assert content.body=='<canvas>original</canvas>' and content.css==['original.css'] and content.js==['original.js']

@pytest.mark.parametrize('theme',core.THEMES)
def test_theme_refresh_preserves_dialog_and_settings(setup,theme):
 a,c,mw,cfg,_=setup;c.dialog=PlannerDialog();d=c.dialog
 content=NS(head='');a.add_content(content,d)
 cfg['theme']=theme;a.refresh()
 assert c.dialog is d and len(d.web.scripts)==2
 assert review.PALETTES[theme]['bg'] in d.web.scripts[-1]
 assert 'innerHTML' not in d.web.scripts[-1]
 assert review.PALETTES[theme]['side'] in d.native_bar.sheet
 assert not hasattr(c,'store') # the adapter never creates or accesses it

def test_restore_original_header_and_competing_styles(setup):
 a,c,mw,cfg,_=setup;c.dialog=PlannerDialog();d=c.dialog
 a.add_content(NS(head=''),d);assert d.native_bar.sheet!='original header stylesheet'
 cfg['match_sprout']=False;a.refresh();assert d.native_bar.sheet=='original header stylesheet'
 cfg['match_sprout']=True;a.refresh()
 d.native_bar.sheet='another extension changed this'
 cfg['match_sprout']=False;a.refresh();assert d.native_bar.sheet=='another extension changed this'

def test_closed_dialog_ignored(setup):
 a,c,mw,cfg,_=setup;c.dialog=PlannerDialog();c.dialog.closed=True
 a.refresh();assert c.dialog.web.scripts==[]

def test_presentation_defaults_and_boolean_sanitizing():
 cfg=core.settings({});assert cfg['shared_theme'] is True and cfg['match_sprout'] is True
 assert core.settings({'shared_theme':False,'match_sprout':False})['match_sprout'] is False
 assert core.settings({'match_sprout':'yes'})['match_sprout'] is True

def test_prepaint_palette_includes_complete_shared_chrome():
 html=guard.home_guard(core.settings({'theme':'obsidian','mode':'native','visual_owner':'atelier'}))
 assert 'atelier-shared-style' in html and 'atelierShared' in html
 assert review.PALETTES['obsidian']['bg'] in html
 assert '#es-countdowns' in html and '.sidebar-left' in html

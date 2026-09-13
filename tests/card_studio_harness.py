"""Actual merged workspace+Store+painter; the host/Qt and cross-window display are explicit doubles."""
from pathlib import Path
from types import SimpleNamespace,ModuleType
import sys,importlib,json
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/'src'
sys.path.insert(0,str(ROOT/'workshop_checks/tools'))
from ui_harness import Host,HTML
pkg=ModuleType('atelier_card_qa');pkg.__path__=[str(SRC)];sys.modules.setdefault('atelier_card_qa',pkg)

class UnifiedHost(Host):
 def __init__(self,theme='forest',owner='atelier',sample=True):
  super().__init__(sample=sample)
  # Different package name permits the production relative suite imports.
  mod=importlib.import_module('atelier_card_qa.workshop.integration')
  old=self.workspace; w=mod.Workspace.__new__(mod.Workspace);w.__dict__.update(old.__dict__)
  self.workspace=w;c=w.controller;c.window=w
  self._daedalus_workshop_controller=c
  self.settings={'theme':theme,'visual_owner':owner,'mode':'workspace','motion':False,'ambience':True}
  self.theme_updates=[];self.plan_requests=[];self.appearance_module=importlib.import_module('atelier_card_qa.card_studio')
  self.owner=SimpleNamespace(get_config=lambda:dict(self.settings),save_config=self.save_theme,
    nonce='',workshop=c,sprout_link=SimpleNamespace(open_target=self.open_plan))
  c.suite=self.owner;c.preferred_deck=None;c.refresh_home=lambda:None
  from atelier_card_qa.figure_cache import FigurePreviews
  w.figure_previews=FigurePreviews(w.store)
  self.owner.profile={'studies':[{'id':'qa-group','name':'Active class','deck_ids':['1'],'active':True}]}
  self.owner.ensure_store=lambda:None
  w.suite_palette=self.appearance_module.appearance(self.owner)['palette'];w.hide=lambda:self.native('HideStudio',{})
  w.close=lambda:self.native('CloseStudio',{})
  self.onBrowse=lambda:self.native('Browse',{});self.on_sync_button_clicked=lambda:self.native('Sync',{})
  self.moveToState=lambda state:self.native('State',{'state':state})
  self.col.get_card=lambda cid:SimpleNamespace(did=self.col.db.scalar('SELECT did FROM cards WHERE id=?',int(cid)),odid=0)
  self._exam_sprout_controller=SimpleNamespace(runner=None,dialog=None)
 def save_theme(self,patch):
  self.settings.update(patch);self.theme_updates.append(patch);return dict(self.settings)
 def open_plan(self,target,**payload):
  self.plan_requests.append({'target':target,**payload})
 def html(self):
  text=HTML
  for f in ('app.css','mask-editor.css'):text=text.replace('<link rel="stylesheet" href="/web/'+f+'">','<style>'+(SRC/'workshop/web'/f).read_text()+'</style>')
  for f in ('icons.js','art.js','mask-editor.js','app.js'):text=text.replace('<script src="/web/'+f+'"></script>','<script>'+(SRC/'workshop/web'/f).read_text()+'</script>')
  return text.replace('</head>',self.appearance_module.head(self.owner)+'</head>')

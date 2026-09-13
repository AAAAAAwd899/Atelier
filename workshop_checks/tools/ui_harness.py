"""Actual production bridge + real local Store; only Anki/Qt are explicit doubles.
Sample records belong exclusively to this test harness and never ship in the add-on.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import json,sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from addon.storage import Store
from addon import collection,core
from addon.network import Provider
from tests.fakes import FakeCollection,install_stubs

class Host:
    def __init__(self,directory=None,sample=True):
        self.sample=sample;self.directory=Path(directory or tempfile.mkdtemp(prefix='workshop-ui-'));self.store=Store(self.directory)
        self.col=FakeCollection(self.directory);self.native_events=[];self.clipboard='';self.files=[];self.savepath='';self.requests=[];self.errors=[]
        self.state='deckBrowser';self.app=SimpleNamespace(clipboard=lambda:SimpleNamespace(setText=lambda x:setattr(self,'clipboard',x)))
        self.pm=SimpleNamespace(profileFolder=lambda:str(self.directory));self.onSync=lambda:self.native('Sync',{});self.onCheckMedia=lambda:self.native('CheckMedia',{})
        install_stubs(self)
        from addon.integration import Workspace
        self.workspace=Workspace.__new__(Workspace);w=self.workspace
        controller=SimpleNamespace(mw=self,store=self.store,epoch=1,base='/web',package=core.PACKAGE,last_undo=None,provider=Provider(),native_context={},window=w,previews=[])
        controller.record=lambda action,e:self.errors.append({'action':action,'error':str(e)})
        controller.refresh_home=lambda:None;controller.api=SimpleNamespace(announce=lambda *a:None);controller.diagnostics=lambda:None
        controller.open=lambda *a:None
        self._exam_sprout_controller=SimpleNamespace(open=lambda:self.native('Exam Sprout',{}))
        w.controller=controller;w.mw=self;w.store=self.store;w.epoch=1;w.col=self.col;w.night=True;w.initial_view='library';w.initial_note=None
        w.figure_previews=None;w.closed=False;w.forced=False;w.busy=False;w.dirty=False;w.tokens={};w.jobs=0;w.web=None;w.status=SimpleNamespace(setText=lambda x:None)
        w.integration_snapshot={'sprout':True,'atelier':True,'hypertts':False,'contanki':False,'anki_hub':False,'anki_collab':False,'native_occlusion':True,'enabled_addons':[],'protocol':1}
        w.send=self.receive;w.emit=lambda *a:None;w.close=lambda:None
        self.responses={}
        if sample:self.seed()
    def native(self,name,kwargs):self.native_events.append({'name':name,'kwargs':kwargs});return SimpleNamespace()
    def receive(self,rid,data=None,error=None):
        if data and isinstance(data,dict) and 'catalog' in data:data['preview']=self.sample
        self.responses[rid]={'id':rid,'data':data,'error':error}
    def dispatch(self,message):
        obj=json.loads(message.split(':',1)[1]);self.requests.append({'action':obj['action'],'payload':obj['payload']})
        self.workspace.bridge(message)
        return self.responses.pop(str(obj['id']),{'id':str(obj['id']),'data':None,'error':'No response was produced by the integration double.'})
    def seed(self):
        titles=['Memory & Meaning','The Night Atlas','Worlds in Motion','Structures & Space','Tides & Currents','The Written Word']
        descriptions=['Better questions, lasting understanding. A source-aware approach to deliberate recall.',
                      'A field notebook for patient observation and the questions a night sky invites.',
                      'Places, patterns, and the relationships that make a map meaningful.',
                      'A visual collection of forms, proportions, and the ideas behind them.',
                      'A small atlas of connections, from first observations to careful explanations.',
                      'Language, close reading, and the precise question behind a sentence.']
        passage='SOURCE-AWARE AUTHORING\n\nOne idea, clearly asked.\n\nA useful question identifies what should be recalled without revealing its answer. Preserve the conditions that make the answer meaningful. A short question is not automatically a good question.\n\nKeep the original within reach.\n\nRecord the source title, edition, and supporting passage. A citation tells you where a claim came from; it does not certify that the claim is correct. Check the original before approving a draft.\n\nRepair, rather than repeat blindly.\n\nWhen two ideas keep getting confused, name the difference explicitly. A comparison card can test that distinction. Keep the original notes unless you deliberately decide otherwise.\n\nPreparation is not mastery.\n\nCreating a card prepares an opportunity to retrieve an idea. Learning still takes place through thoughtful practice. A finished project means its cards are prepared, not that the subject has been mastered.'
        for i,(title,desc,cover) in enumerate(zip(titles,descriptions,core.COVERS)):
            p=self.store.project({'title':title,'description':desc,'cover':cover});s=self.store.add_source(p['id'],'A guide to source-aware authoring' if i==0 else title+' · field notes','text',[{'text':passage}])['source']
            if i<5:
                n=self.col.seed('What does a source citation establish?' if i==0 else f'What is the purpose of the {title} project?', 'Where the claim originated; not a certification of correctness.' if i==0 else desc)
                self.store.link_note(n.id,p['id'],s['id'],s['version_id'],1,'A citation tells you where a claim came from; it does not certify that the claim is correct.')
            if i in (0,1,3):
                self.store.save_draft({'project_id':p['id'],'source_id':s['id'],'version_id':s['version_id'],'page':1,'kind':'question','front':'When is a comparison card useful?' if i==0 else 'What should a source-linked draft preserve?', 'back':'When it tests the specific distinction between ideas that are repeatedly confused.' if i==0 else 'The original passage, its title, edition, and the conditions of the claim.', 'context':'Focus on the defining difference rather than memorizing two disconnected definitions.','quote':'A comparison card can test that distinction.','deck_id':2,'tags':['Workshop::Sources']})
            if i==0:
                self.store.flag(n.id,'Check the source wording before simplifying this answer.',p['id'])
                self.primary_project=p['id'];self.primary_source=s['id']
        # A second distinct concept makes comparison and bulk edits meaningful.
        self.col.seed('What should happen when one question tests unrelated ideas?','Consider splitting it into separate learning targets.')
        self.col.seed('What does finishing a draft prove?','Only that the material has been prepared; it does not demonstrate recall.')
        self.store.event('cards_committed',{'notes':2});self.store.event('repair_resolved',{'notes':1})

HTML='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/web/app.css"><link rel="stylesheet" href="/web/mask-editor.css"></head><body><main id="workshop" aria-label="Workshop"></main><script>window.pycmd=async function(message){const response=await window.nativeBridge(message);window.Workshop.receive(response);};</script><script src="/web/icons.js"></script><script src="/web/art.js"></script><script src="/web/mask-editor.js"></script><script src="/web/app.js"></script></body></html>'''

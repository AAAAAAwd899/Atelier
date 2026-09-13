"""Additive, profile-bound Anki integration. Native controls remain available on page failure."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from dataclasses import dataclass
import json
import logging
import platform
import re
import time
from typing import Callable, Any

import aqt
from aqt import gui_hooks
from aqt.qt import (QAction, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                    QFileDialog, QInputDialog, QLineEdit, QMenu, Qt, QTimer, QUrl,
                    QDesktopServices, QApplication, QKeySequence, QBuffer, QByteArray, QIODevice)
from aqt.operations import QueryOp, CollectionOp
from aqt.webview import AnkiWebView
from aqt.deckbrowser import DeckBrowser
from aqt.utils import askUser, tooltip, restoreGeom, saveGeom
from aqt.theme import theme_manager
from .core import (VERSION, PACKAGE, ValidationError, ConflictError, identifier, integer,
                   uid, now, text, plain, safe_json, escaped_field, workload, keywords, rank_matches, fingerprint)
from .storage import Store
from . import collection as cards
from . import documents
from .network import Provider, allowed_source_url, endpoint

LOG=logging.getLogger('daedalus_workshop')
ROOT=Path(__file__).resolve().parent
PREFIX='workshop:'

class WorkshopAPI:
    """Versioned, opt-in extension contract. Does not expose a writable data store."""
    version=1
    def __init__(self,controller):self.controller=controller;self.listeners=[]
    def open(self,view='library',note_id=None):self.controller.open(view,note_id=note_id)
    def flag(self,note_id,reason='Review this card'):
        self.controller.flag_note(int(note_id),reason)
    def subscribe(self,callback):
        if not callable(callback):raise TypeError('A listener must be callable.')
        self.listeners.append(callback)
        return lambda:self.listeners.remove(callback) if callback in self.listeners else None
    def announce(self,name,payload):
        for callback in tuple(self.listeners):
            try:callback({'version':1,'event':name,'data':deepcopy(payload)})
            except Exception:LOG.exception('A Workshop integration listener failed')

class Controller:
    def __init__(self,mw,suite=None):
        self.suite=suite
        self.mw=mw;self.store=None;self.window=None;self.epoch=0;self.opening=False
        self.provider=Provider();self.last_undo=None;self.native_context={};self.errors=[];self.host_palette={}
        self.package=mw.addonManager.addonFromModule(__name__)
        self.base=f'/_addons/{self.package}/'+('workshop/web' if suite else 'web')
        if suite is None:mw.addonManager.setWebExports(__name__,r'web/.*\.(css|js|svg|png|webp)$')
        self.api=WorkshopAPI(self);mw.workshop_api_v1=self.api
        self.menu_parent=getattr(suite,'menu',None) or mw.form.menuTools
        self.menu=QMenu('Card Studio' if suite else 'Workshop',mw);self.menu_parent.addMenu(self.menu)
        for label,fn in [('Sources & projects',lambda:self.open('library')),('Create cards',lambda:self.open('studio',allow_review=True)),
                         ('Find cards & sources',lambda:self.open('find')),('Improve cards',lambda:self.open('improve')),
                         ('Mark current card: needs attention',self.flag_current),('Show current card source',self.show_current_source),
                         ('Diagnostics',self.diagnostics)]:
            action=QAction(label,mw);action.triggered.connect(lambda _=False,f=fn:f());self.menu.addAction(action)
        self.open_action=self.menu.actions()[0]
        self.open_action.setShortcut(QKeySequence('Ctrl+Alt+W'))
        self.menu.actions()[4].setShortcut(QKeySequence('Ctrl+Alt+R'))
        self.menu.actions()[4].setEnabled(False);self.menu.actions()[5].setEnabled(False)

    def profile_open(self,*_):
        self.epoch+=1;self.provider.clear();self.last_undo=None;self.native_context={};self.preferred_deck=None
        try:self.store=Store(self.mw.pm.profileFolder(),initial_theme='atelier' if getattr(self,'suite',None) else None)
        except Exception as exc:self.store=None;self.record('open_workspace',exc)
        self.menu.setEnabled(True)
    def profile_close(self,*_):
        self.epoch+=1;self.provider.clear();self.last_undo=None;self.native_context={};self.preferred_deck=None
        for preview in tuple(getattr(self,'previews',[])):
            try:preview.close()
            except Exception:pass
        if self.window:self.window.force_close()
        self.window=None;self.store=None
    def collection_close(self,*_):
        self.profile_close()
    def state_change(self,state,old):
        active=state=='review' and bool(getattr(self.mw.reviewer,'card',None))
        for i in (4,5):self.menu.actions()[i].setEnabled(active)
    def record(self,action,exc):
        # Session diagnostics only, without source contents or credentials.
        row=f'{now()} · {action} · {type(exc).__name__}: {str(exc)[:300]}'
        self.errors.append(row);self.errors=self.errors[-30:]
        LOG.warning('Workshop action %s failed (%s)',action,type(exc).__name__)
    def diagnostics(self):
        info=f'Workshop {VERSION}\n{platform.system()} · Python {platform.python_version()}\nProfile-local data: '+('available' if self.store else 'unavailable')
        info+='\nNative Windows acceptance is not implied by automated tests.\n\n'+'\n'.join(self.errors or ['No errors recorded in this session.'])
        dialog=QDialog(self.window or self.mw);dialog.setWindowTitle('Workshop diagnostics');layout=QVBoxLayout(dialog)
        from aqt.qt import QPlainTextEdit
        output=QPlainTextEdit(dialog);output.setPlainText(info);output.setReadOnly(True);layout.addWidget(output)
        buttons=QHBoxLayout();copy=QPushButton('Copy details');copy.clicked.connect(lambda:self.mw.app.clipboard().setText(info));buttons.addWidget(copy)
        close=QPushButton('Close');close.clicked.connect(dialog.accept);buttons.addWidget(close);layout.addLayout(buttons);dialog.resize(640,400);dialog.exec()
    def open(self,view='library',note_id=None,allow_review=False):
        if self.opening:return
        if not self.mw.col:return
        engine=getattr(self.mw,'_exam_sprout_controller',None)
        if getattr(engine,'runner',None) is not None:
            tooltip('Save and close or finish your practice session before opening Card Studio. Your answers stay open.',parent=self.mw);return
        if self.mw.state=='review' and not allow_review:
            tooltip('Finish this card or return to Decks before opening the workspace. “Needs attention” can be marked without leaving review.',parent=self.mw);return
        self.opening=True
        try:
            if self.store is None:self.profile_open()
            if self.store is None:self.diagnostics();return
            if self.window and not self.window.closed:
                if self.window.busy:
                    self.window.raise_();self.window.activateWindow();return
                if allow_review and self.mw.state=='review':
                    self.window.hide();self.window.setWindowModality(Qt.WindowModality.WindowModal)
                self.window.emit('navigate',{'view':view,'note_id':note_id,'deck_id':getattr(self,'preferred_deck',None)});self.window.show();self.window.raise_();self.window.activateWindow();return
            self.window=Workspace(self,view,note_id)
            if allow_review and self.mw.state=='review':self.window.setWindowModality(Qt.WindowModality.WindowModal)
            self.window.show();self.window.load()
        except Exception as exc:
            self.record('open',exc)
            if self.window:self.window.force_close()
            self.window=None;tooltip('Card Studio could not open. Tools → Atelier → Card Studio → Diagnostics has the details.' if getattr(self,'suite',None) else 'Workshop could not open. Tools → Workshop → Diagnostics has the details.',parent=self.mw)
        finally:self.opening=False
    def flag_note(self,nid,reason='Review this card'):
        if not self.mw.col or self.store is None:return
        col=self.mw.col;store=self.store;epoch=self.epoch
        def task(c):
            if c is not col or self.epoch!=epoch or self.store is not store:raise ValidationError('The active profile changed.')
            c.get_note(integer(nid,1,2**53-1,'Note ID'))
            links=[l for l in store.list('link') if l['note_id']==nid]
            return store.flag(nid,reason,links[0]['project_id'] if links else '')
        QueryOp(parent=self.mw,op=task,success=lambda _:tooltip('Saved to Workshop’s repair queue. Keep studying.',parent=self.mw) if self.epoch==epoch else None).failure(lambda e:self.record('mark_for_repair',e)).run_in_background()
    def flag_current(self):
        c=getattr(self.mw.reviewer,'card',None)
        if self.mw.state=='review' and c:self.flag_note(int(c.nid))
    def show_current_source(self):
        c=getattr(self.mw.reviewer,'card',None)
        if not c or not self.store:return
        matches=[l for l in self.store.list('link') if l['note_id']==int(c.nid) and l.get('source_id')]
        if not matches:tooltip('This card has no Workshop source link.',parent=self.mw);return
        # A native, read-only source dialog is deliberate; no reviewer overlay injection.
        link=matches[0];source=self.store.get('source',link['source_id']);version=self.store.get('version',link['version_id'])
        dialog=QDialog(self.mw);dialog.setWindowTitle('Source · '+source['title']);layout=QVBoxLayout(dialog)
        from aqt.qt import QPlainTextEdit
        content=QPlainTextEdit(dialog);content.setReadOnly(True);content.setPlainText(f'{source["title"]} · page {link["page"]} · version {version["ordinal"]}\n\n'+(link.get('quote') or version['pages'][link['page']-1]['text']));layout.addWidget(content)
        close=QPushButton('Return to review');close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.resize(690,470);dialog.exec()
    def reviewer_menu(self,reviewer,menu):
        if reviewer is not self.mw.reviewer:return
        menu.addSeparator();menu.addAction('Atelier · Needs attention',self.flag_current);menu.addAction('Atelier · Show source',self.show_current_source)
    def toolbar(self,links,toolbar):
        if self.suite is not None:return  # native Add is the single creation route
        if not self.store or self.store.settings()['show_toolbar']:
            links.append(toolbar.create_link('workshop_open','Card Studio' if getattr(self,'suite',None) else 'Workshop',lambda:self.open(),tip='Living Library, source-aware card creation, and card repair',id='workshop-nav'))
    def home(self,deckbrowser,content):
        if self.suite is not None:return  # suite owns the one authoring projection
        if self.store and self.store.settings()['show_home']:
            content.stats=self.home_html()+content.stats
    def home_html(self):
        if not self.store or not self.store.settings()['show_home']:return ''
        count=sum(d.get('status')!='committed' for d in self.store.list('draft'))
        return '<section id="ws-home"><button type="button" data-ws-open="true"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 5c3-1 6-1 9 1 3-2 6-2 9-1v14c-3-1-6-1-9 1-3-2-6-2-9-1Z M12 6v14" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg><span><strong>Card Studio</strong><small>'+ (f'{count} drafts to shape' if count else 'Your living library')+'</small></span><span aria-hidden="true">↗</span></button></section>'
    def web_assets(self,content,context):
        if self.suite is not None:return
        if isinstance(context,DeckBrowser):
            for target,f in ((content.css,'home.css'),(content.js,'home.js')):
                asset=self.base+'/'+f
                if asset not in target:target.append(asset)
    def home_ready(self,deckbrowser):
        if self.suite is not None:return
        if deckbrowser is not self.mw.deckBrowser or self.mw.state!='deckBrowser':return
        html=safe_json(self.home_html())
        deckbrowser.web.eval(f'window.WorkshopHome && window.WorkshopHome.mount({html});')
    def web_message(self,handled,message,context):
        if handled[0]:return handled
        if isinstance(context,DeckBrowser) and context is self.mw.deckBrowser and self.mw.state=='deckBrowser' and message=='workshop:open':
            self.open();return (True,None)
        return handled
    def refresh_home(self):
        if self.suite is not None:
            from ..card_studio import refresh_home
            refresh_home(self.suite)
            return
        if self.mw.col and self.mw.state=='deckBrowser':
            try:self.mw.deckBrowser.refresh();self.mw.toolbar.draw()
            except Exception as e:self.record('refresh_home',e)
    def browser_menu(self,browser):
        menu=getattr(browser.form,'menuEdit',None)
        if menu:
            action=QAction('Atelier · Improve selected notes',browser)
            def selected():
                fn=getattr(browser,'selected_notes',None) or getattr(browser,'selectedNotes',None)
                ids=list(fn()) if callable(fn) else []
                if not ids:tooltip('Select a note first.',parent=browser);return
                self.open('improve',int(ids[0]))
            action.triggered.connect(selected);menu.addAction(action)
    def native_added(self,note):
        if not self.store:return
        tags=list(note.tags)
        ctx=next((self.native_context.get(t) for t in tags if t in self.native_context),None)
        if not ctx or ctx['epoch']!=self.epoch:return
        try:
            self.store.link_note(int(note.id),ctx['project_id'],ctx['source_id'],ctx['version_id'],ctx['page'],ctx.get('quote',''),snapshot=fingerprint(note.fields,note.tags))
            self.native_context.pop(ctx['tag'],None)
            self.api.announce('notes_added',{'note_ids':[int(note.id)],'project_id':ctx['project_id']})
            if self.window:self.window.emit('refresh',{})
        except Exception as e:self.record('native_source_link',e)
    def mask_loaded(self,editor,path):
        if not self.native_context:return
        ctx=next((v for v in self.native_context.values() if v.get('image_path')==str(path) and v['epoch']==self.epoch),None)
        if ctx and editor.note:
            tag=ctx['tag']
            if tag not in editor.note.tags:editor.note.tags.append(tag)
            editor.web.eval('setTags('+safe_json(editor.note.tags)+');')

class Workspace(QDialog):
    def __init__(self,controller,view,note_id):
        super().__init__(controller.mw)
        self.controller=controller;self.mw=controller.mw;self.store=controller.store;self.epoch=controller.epoch;self.col=self.mw.col
        self.night=bool(theme_manager.night_mode)
        self.integration_snapshot=self.integrations()
        self.suite_palette={}
        if getattr(controller,'suite',None):
            from ..review_model import PALETTES
            cfg=controller.suite.get_config()
            self.suite_palette=deepcopy(PALETTES.get(cfg['theme'],{})) if cfg.get('visual_owner')=='atelier' else {}
        self.closed=False;self.forced=False;self.busy=False;self.dirty=False;self.initial_view=view;self.initial_note=note_id
        self.tokens={};self.web=None;self.jobs=0
        self.setWindowTitle('Atelier · Card Studio' if getattr(controller,'suite',None) else 'Workshop · Living Library');self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setWindowModality(Qt.WindowModality.NonModal);self.setMinimumSize(680,480)
        screen=self.mw.screen().availableGeometry();self.resize(min(1360,int(screen.width()*.94)),min(900,int(screen.height()*.91)))
        try:restoreGeom(self,'workshop_workspace')
        except Exception:pass
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0);self.layout_box=layout
        native=QHBoxLayout();native.setContentsMargins(12,5,12,5)
        self.status=QLabel('Opening your library…',self);self.status.setTextFormat(Qt.TextFormat.PlainText);native.addWidget(self.status,1)
        for label,fn in [('Diagnostics',controller.diagnostics),('Close',self.close)]:
            b=QPushButton(label,self);b.setAutoDefault(False);b.clicked.connect(lambda _=False,f=fn:f());native.addWidget(b)
        layout.addLayout(native)
    def valid(self):
        return not self.closed and self.col is self.mw.col and self.col is not None and self.controller.epoch==self.epoch and self.controller.store is self.store
    def load(self):
        if getattr(self.controller,'suite',None) is not None:
            from ..card_studio import native_chrome
            native_chrome(self,self.suite_appearance())
        self.web=AnkiWebView(self);self.layout_box.insertWidget(0,self.web,1);self.web.set_bridge_command(self.bridge,self)
        self.web.loadFinished.connect(lambda ok:self.status.setText('The page could not load. Native Close and Diagnostics remain available.') if not ok and self.valid() else None)
        self.web.stdHtml('<main id="workshop" aria-label="Workshop"><div class="boot-loader">Opening your library…</div></main>',css=[self.controller.base+'/app.css',self.controller.base+'/mask-editor.css'],js=[self.controller.base+'/mask-editor.js',self.controller.base+'/icons.js',self.controller.base+'/art.js',self.controller.base+'/app.js'],head=self.suite_head(),context=self)
    def suite_head(self):
        if getattr(self.controller,'suite',None) is None:return ""
        from ..card_studio import head
        return head(self.controller.suite)

    def send(self,rid,data=None,error=None):
        if self.valid() and self.web:
            self.web.eval('window.Workshop && window.Workshop.receive('+safe_json({'id':rid,'data':data,'error':error})+');')
    def emit(self,event,data):
        if self.valid() and self.web:self.web.eval('window.Workshop && window.Workshop.event('+safe_json(event)+','+safe_json(data)+');')
    def task(self,rid,fn:Callable,finish=lambda x:x,write=False,use_col=True):
        if write and self.busy:raise ValidationError('Wait for the current collection change to finish.')
        epoch=self.epoch;col=self.col;store=self.store
        if write:self.busy=True
        self.jobs+=1
        def guarded(c):
            if not self.valid() or (use_col and c is not col):raise ValidationError('The profile or collection changed. This operation was cancelled.')
            return fn(c)
        def done(result):
            self.jobs=max(0,self.jobs-1)
            if write:self.busy=False
            if not self.valid():return
            try:
                out=finish(result.data if write else result)
                if write:
                    self.controller.last_undo=None if isinstance(result.data,dict) and result.data.get('undone') else self.col.undo_status().last_step
                    self.controller.api.announce('collection_changed',result.data)
                self.send(rid,out)
            except Exception as e:self.controller.record('finish_request',e);self.send(rid,error=str(e))
        def fail(exc):
            self.jobs=max(0,self.jobs-1)
            if write:self.busy=False
            if self.valid():self.controller.record('collection_write' if write else 'read',exc);self.send(rid,error=str(exc))
        if write:CollectionOp(parent=self.mw,op=guarded).success(done).failure(fail).run_in_background(initiator=self)
        else:
            op=QueryOp(parent=self.mw,op=guarded,success=done).failure(fail)
            if not use_col:op.without_collection()
            op.run_in_background()
    def grant(self,kind,data):
        self.tokens={k:v for k,v in self.tokens.items() if time.monotonic()-v[2]<900}
        if len(self.tokens)>30:self.tokens.clear()
        token=uid();self.tokens[token]=(kind,deepcopy(data),time.monotonic());return token
    def consume(self,token,kind):
        value=self.tokens.pop(str(token),None)
        if not value or value[0]!=kind or time.monotonic()-value[2]>900:raise ValidationError('This approval preview expired. Open a new preview before applying changes.')
        return value[1]
    def base_state(self,col):
        state=self.store.summary();cat=cards.catalog(col)
        palette=deepcopy(getattr(self,'suite_palette',{}));current=0
        try:current=int(col.decks.selected())
        except (AttributeError,TypeError,ValueError):pass
        return {'state':state,'catalog':cat,'version':VERSION,'initial_view':self.initial_view,'initial_note':self.initial_note,
                'night':bool(getattr(self,'night',False)),'integrations':deepcopy(self.integration_snapshot), 'preview':False,'key_set':bool(self.controller.provider.key),'asset_base':self.controller.base, 'integrated':bool(getattr(self.controller,'suite',None)), 'suite_palette':palette, 'current_deck':getattr(self.controller,'preferred_deck',None) or current, 'suite_appearance':self.suite_appearance()}
    def suite_appearance(self):
        if getattr(self.controller,'suite',None) is None:return None
        from ..card_studio import appearance
        return appearance(self.controller.suite)
    def integrations(self):
        sprout=getattr(self.mw,'_exam_sprout_controller',None)
        try:
            enabled=[{'id':str(i),'name':str(self.mw.addonManager.addonName(i))} for i in self.mw.addonManager.allAddons() if not self.mw.addonManager.isDisabled(i)]
        except Exception:enabled=[]
        names=' '.join(i['name'] for i in enabled).lower()
        return {'sprout':bool(sprout and hasattr(sprout,'open')),'atelier':'atelier' in names,
                'hypertts':'hypertts' in names,'contanki':'contanki' in names,'anki_hub':'ankihub' in names,'anki_collab':'ankicollab' in names,
                'native_occlusion':True,'enabled_addons':enabled,'protocol':1}
    def bridge(self,message):
        if not self.valid() or not isinstance(message,str) or not message.startswith(PREFIX):return
        rid=''
        try:
            if len(message)>1_200_000:raise ValidationError('This request is too large.')
            obj=json.loads(message[len(PREFIX):]);rid=str(obj.get('id',''))[:80];action=obj.get('action');p=obj.get('payload',{})
            if not isinstance(p,dict):raise ValidationError('Invalid request payload.')
            if isinstance(action,str) and action.startswith('suite_') and getattr(self.controller,'suite',None) is not None:
                from ..card_studio import command
                return self.send(rid,command(self,action,p))
            if action=='load':
                self.status.setText('Local library · explicit, undo-aware collection changes')
                return self.task(rid,self.base_state)
            if action=='state':return self.task(rid,lambda _:self.store.summary(),use_col=False)
            if action=='close_studio':
                if self.busy or self.dirty:raise ValidationError('Save your changes before returning to the study desk.')
                self.send(rid,{'closed':True});self.close();return
            if action=='dirty':self.dirty=p.get('value') is True;return self.send(rid,{})
            if action=='project':
                result=self.store.project(p);self.controller.refresh_home();return self.send(rid,result)
            if action=='source_text':
                result=self.store.add_source(identifier(p['project_id']),text(p.get('title',''),200,'Source title',True),'text',[{'text':text(p.get('text',''),6_000_000,'Source text',True)}],locator=allowed_source_url(p.get('url','')),source_id=p.get('source_id',''))
                return self.send(rid,result)
            if action=='import_file':return self.import_files(rid,p)
            if action=='clipboard_image':return self.clipboard_image(rid,p)
            if action=='pdf_layout':return self.pdf_layout(rid,p)
            if action=='mask_source':
                version_id=identifier(p['version_id']);page=integer(p.get('page',1),1,2000,'Page')
                def mask_source(_):
                    view=documents.render_page(self.store,version_id,page,2000)
                    if not view.get('image'):raise ValidationError('Choose an embedded figure or attach a PDF layout to mask this slide visually.')
                    from base64 import b64decode
                    name=view.get('blob') or self.store.save_blob(b64decode(view['image'].split(',',1)[1]),'png')
                    return {'blob':name,'image':view['image']}
                return self.task(rid,mask_source,use_col=False)
            if action=='source':
                source=self.store.get('source',identifier(p['id']));versions=[{'id':v['id'],'ordinal':v['ordinal'],'created':v['created']} for v in self.store.list('version',source['project_id']) if v['source_id']==source['id']]
                version=self.store.get('version',p.get('version_id') or source['version_id'])
                if version['source_id']!=source['id']:raise ValidationError('This version belongs to another source.')
                return self.send(rid,{'source':source,'version':version,'versions':sorted(versions,key=lambda x:-x['ordinal'])})
            if action=='page':return self.task(rid,lambda _:documents.render_page(self.store,identifier(p['version_id']),p.get('page',1),p.get('width',1400)),use_col=False)
            if action=='crop':return self.task(rid,lambda _:documents.crop_page(self.store,identifier(p['version_id']),p['page'],p['rect']),use_col=False)
            if action=='image':
                path=self.store.blob_path(p['blob']);return self.send(rid,{'image':documents.data_url(path)})
            if action=='open_original':
                v=self.store.get('version',identifier(p['version_id']));path=self.store.blob_path(v['blob']);QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)));return self.send(rid,{})
            if action=='source_diff':return self.task(rid,lambda _:documents.compare_source(self.store,identifier(p['source_id'])),use_col=False)
            if action=='queue_source_changes':
                diff=documents.compare_source(self.store,identifier(p['source_id']))
                for link in diff['affected']:self.store.flag(link['note_id'],'Source changed: '+diff['source']['title'],link['project_id'],'source',{'source_id':p['source_id']})
                return self.send(rid,{'queued':len(diff['affected'])})
            if action=='save_draft':
                out=self.store.save_draft(p);self.dirty=False;self.controller.refresh_home();return self.send(rid,out)
            if action=='delete_draft':
                d=self.store.get('draft',identifier(p['id']))
                if d.get('status')=='committed':raise ValidationError('This draft was already added to Anki. Use the Browser to manage its note.')
                self.store.remove('draft',d['id'],p.get('revision'));return self.send(rid,{})
            if action=='search':return self.task(rid,lambda col:cards.search_notes(col,p.get('query',''),self.store.settings(),p.get('mode','words'),p.get('deck_id',0),p.get('limit',60),p.get('offset',0)))
            if action=='source_search':
                q=text(p.get('query',''),2000,'Search query')
                def source_search(_):
                    rows=[]
                    for v in self.store.list('version'):
                        for page in v['pages']:
                            rows.append({'id':v['id']+':'+str(page['page']),'version_id':v['id'],'source_id':v['source_id'],'page':page['page'],'text':page['text']+'\n\n'+page.get('notes',''),'project_id':v['project_id']})
                    return {'results':rank_matches(q,rows,30)}
                return self.task(rid,source_search,use_col=False)
            if action=='note':return self.task(rid,lambda col:cards.note_data(col,p['note_id'],self.store.settings()))
            if action=='scan':
                def finish(result):
                    self.store.index_notes(result.pop('indexed'),clear=p.get('cursor',0)==0);return result
                return self.task(rid,lambda col:cards.scan_notes(col,self.store.settings(),p.get('cursor',0),p.get('size',250)),finish)
            if action=='flag':
                def mark(col):
                    col.get_note(integer(p['note_id'],1,2**53-1,'Note ID'))
                    return self.store.flag(p['note_id'],p.get('reason','Review this card'),p.get('project_id',''))
                return self.task(rid,mark)
            if action=='resolve':return self.send(rid,self.store.resolve(identifier(p['id']),p['status']))
            if action=='link':
                def link(col):
                    n=col.get_note(integer(p['note_id'],1,2**53-1,'Note ID'))
                    return self.store.link_note(int(n.id),identifier(p['project_id']),p.get('source_id',''),p.get('version_id',''),p.get('page',1),text(p.get('quote',''),20000,'Source passage'),snapshot=fingerprint(n.fields,n.tags))
                return self.task(rid,link)
            if action=='preflight':
                return self.task(rid,lambda col:cards.preflight(col,self.store,p['draft_ids']),lambda data:{**data,'token':self.grant('commit',data)})
            if action=='commit':
                if p.get('approved') is not True:raise ValidationError('Approve the full batch preview before adding cards.')
                data=self.consume(p.get('token'),'commit');dup=p.get('allow_duplicates',[])
                if not isinstance(dup,list):raise ValidationError('Invalid duplicate approval.')
                return self.task(rid,lambda col:cards.commit(col,self.store,data,set(dup),self.valid),write=True)
            if action=='edit_preview':
                return self.task(rid,lambda col:cards.edit_preview(col,self.store,p['note_id'],p['fields'],p['fingerprint']),lambda data:{**data,'token':self.grant('edit',data)})
            if action=='edit_apply':
                data=self.consume(p.get('token'),'edit')
                if p.get('approved')is not True:raise ValidationError('Confirm the before/after preview first.')
                return self.task(rid,lambda col:cards.apply_edit(col,self.store,data,self.valid),write=True)
            if action=='batch_preview':return self.task(rid,lambda col:cards.batch_preview(col,self.store,p),lambda data:{**data,'token':self.grant('batch',data)})
            if action=='batch_apply':
                data=self.consume(p.get('token'),'batch')
                if p.get('approved')is not True:raise ValidationError('Approve the bulk preview first.')
                return self.task(rid,lambda col:cards.apply_batch(col,self.store,data,self.valid),write=True)
            if action=='undo':return self.undo(rid)
            if action=='native':return self.native(rid,p)
            if action=='occlude':return self.occlude(rid,p)
            if action=='media':return self.task(rid,lambda col:cards.media_catalog(col,p.get('query',''),p.get('limit',120),p.get('offset',0)))
            if action=='media_references':return self.task(rid,lambda col:cards.media_references(col,p['name']))
            if action=='media_preview':
                def preview(col):
                    name=text(p['name'],250,'Media filename',True);root=Path(col.media.dir()).resolve();path=(root/name).resolve()
                    if path.parent!=root or not path.is_file():raise ValidationError('This media file is unavailable.')
                    return {'image':documents.data_url(path)}
                return self.task(rid,preview)
            if action=='source_confirm':
                link=self.store.get('link',identifier(p['link_id']));source=self.store.get('source',link['source_id']);v=self.store.get('version',source['version_id'])
                page=integer(p.get('page',link['page']),1,len(v['pages']),'Source page')
                if p.get('approved')is not True:raise ValidationError('Confirm you checked this note against the revised source.')
                link.update(version_id=v['id'],page=page,quote=text(p.get('quote',''),20000,'Revised source passage'),checked_at=now())
                return self.send(rid,self.store.put('link',link['id'],link,link['revision']))
            if action=='media_import':return self.import_media(rid)
            if action=='media_reuse':
                def reuse(col):
                    name=text(p['name'],250,'Media filename',True);path=(Path(col.media.dir())/name).resolve()
                    if path.parent!=Path(col.media.dir()).resolve():raise ValidationError('Invalid media path.')
                    if path.stat().st_size>20*1024*1024:raise ValidationError('Use a media file smaller than 20 MB.')
                    blob=self.store.save_blob(path.read_bytes(),path.suffix[1:]);return {'blob':blob,'image':documents.data_url(self.store.blob_path(blob))}
                return self.task(rid,reuse)
            if action=='settings':
                if p.get('ai_endpoint'):endpoint(p['ai_endpoint'])
                return self.send(rid,self.store.set_settings(p))
            if action=='set_key':
                key,ok=QInputDialog.getText(self,'Optional provider key','API key (kept in memory until this profile closes):',QLineEdit.EchoMode.Password)
                if ok:self.controller.provider.set_key(key)
                return self.send(rid,{'set':bool(self.controller.provider.key)})
            if action=='clear_key':self.controller.provider.clear();return self.send(rid,{})
            if action=='ai_drafts':
                settings=self.store.settings();source=text(p.get('passage',''),16000,'Selected passage',True)
                return self.task(rid,lambda _:self.controller.provider.drafts(settings,source,p.get('count',5),p.get('kind','question'),p.get('approved')is True),use_col=False)
            if action=='semantic':
                candidates=p.get('candidates',[])
                return self.task(rid,lambda _:self.controller.provider.rerank(self.store.settings(),p.get('query',''),candidates,p.get('approved')is True),use_col=False)
            if action=='pair':
                ids=p.get('note_ids',[])
                if not isinstance(ids,list) or not 2<=len(set(ids))<=3:raise ValidationError('Select two or three notes to compare.')
                def pair(col):
                    notes=[cards.note_data(col,integer(n,1,2**53-1,'Note ID'),self.store.settings()) for n in ids]
                    record=self.store.put('pair',uid(),{'project_id':p.get('project_id',''),'note_ids':ids,'label':text(p.get('label','Ideas to distinguish'),120,'Comparison title'),'created':now()})
                    return {'pair':record,'notes':notes}
                return self.task(rid,pair)
            if action=='workload':return self.send(rid,workload(p.get('cards',0),p.get('daily',15),p.get('seconds',30)))
            if action=='export':return self.export(rid,p)
            if action=='import_library':return self.import_library(rid)
            if action=='sprout':return self.sprout(rid,p)
            if action=='clipboard':
                value=text(p.get('text',''),100000,'Clipboard text');self.mw.app.clipboard().setText(value);return self.send(rid,{})
            if action=='open_url':
                url=allowed_source_url(p.get('url',''))
                if url:QDesktopServices.openUrl(QUrl(url))
                return self.send(rid,{})
            if action=='diagnostics':self.controller.diagnostics();return self.send(rid,{})
            raise ValidationError('Unsupported Workshop action.')
        except Exception as e:
            self.controller.record(str(locals().get('action','request')),e);self.send(rid,error=str(e))
        return None
    def import_files(self,rid,p):
        project=identifier(p['project_id']);self.store.get('project',project)
        paths,_=QFileDialog.getOpenFileNames(self,'Bring a source into Workshop','',
            'Sources (*.pdf *.png *.jpg *.jpeg *.webp *.txt *.md *.html *.docx *.pptx *.odt *.odp *.csv *.tsv *.json)')
        if not paths:return self.send(rid,{'cancelled':True})
        if len(paths)>20:raise ValidationError('Import no more than 20 files at a time.')
        if p.get('source_id') and len(paths)!=1:raise ValidationError('Choose one file when updating a source.')
        def read(_):
            results=[];errors=[]
            for path in paths:
                try:results.append(documents.capture_file(self.store,project,path,p.get('source_id',''),self.valid))
                except Exception as e:errors.append({'file':Path(path).name,'error':str(e)})
            return {'sources':results,'errors':errors}
        self.task(rid,read,use_col=False)
    def pdf_layout(self,rid,p):
        version_id=identifier(p['version_id']);self.store.get('version',version_id)
        path,_=QFileDialog.getOpenFileName(self,'Attach the matching PDF export','', 'PDF layout (*.pdf)')
        if not path:return self.send(rid,{'cancelled':True})
        return self.task(rid,lambda _:documents.attach_pdf_layout(self.store,version_id,path,self.valid),use_col=False)
    def clipboard_image(self,rid,p):
        project=identifier(p['project_id']);self.store.get('project',project)
        image=self.mw.app.clipboard().image()
        if image.isNull():raise ValidationError('Copy an image or screenshot first, then choose Paste image.')
        if image.width()*image.height()>24_000_000:raise ValidationError('Copy a smaller image (up to 24 million pixels).')
        raw=QByteArray();buffer=QBuffer(raw)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        try:
            if not image.save(buffer,'PNG'):raise ValidationError('The clipboard image could not be encoded.')
        finally:buffer.close()
        data=bytes(raw)
        if len(data)>20*1024*1024:raise ValidationError('The clipboard image is larger than 20 MB.')
        def save(_):
            blob=self.store.save_blob(data,'png')
            return self.store.add_source(project,'Clipboard image · '+now().replace('T',' ')[:16],'png',[{'text':'','image':blob}],blob)
        return self.task(rid,save,use_col=False)
    def import_media(self,rid):
        path,_=QFileDialog.getOpenFileName(self,'Attach media to a draft','', 'Images and audio (*.png *.jpg *.jpeg *.webp *.mp3 *.wav *.ogg)')
        if not path:return self.send(rid,{'cancelled':True})
        def read(_):
            p=Path(path)
            if p.stat().st_size>20*1024*1024:raise ValidationError('Use a media file smaller than 20 MB.')
            data=p.read_bytes()
            if p.suffix.lower() in ('.png','.jpg','.jpeg','.webp'):documents.validate_image_header(data)
            blob=self.store.save_blob(data,p.suffix[1:]);return {'blob':blob,'image':documents.data_url(self.store.blob_path(blob))}
        self.task(rid,read,use_col=False)
    def export(self,rid,p):
        kind=p.get('kind','library')
        if kind=='library':
            path,_=QFileDialog.getSaveFileName(self,'Export your local Workshop library','Workshop Library.wslibrary','Workshop library (*.wslibrary)')
            if not path:return self.send(rid,{'cancelled':True})
            return self.task(rid,lambda _:documents.export_workspace(self.store,Path(path)),use_col=False)
        if kind=='drafts':
            path,_=QFileDialog.getSaveFileName(self,'Export draft text','Workshop Drafts.tsv','Tab-separated text (*.tsv)')
            if not path:return self.send(rid,{'cancelled':True})
            def write(_):
                import csv
                rows=self.store.list('draft',p.get('project_id',''))
                with open(path,'w',encoding='utf-8',newline='') as f:
                    out=csv.writer(f,delimiter='\t');out.writerow(['Question','Answer','Context','Source passage','Tags','Status'])
                    for d in rows:out.writerow([d['front'],d['back'],d['context'],d['quote'],' '.join(d['tags']),d['status']])
                return {'exported':len(rows)}
            return self.task(rid,write,use_col=False)
        raise ValidationError('Choose a supported export format.')
    def import_library(self,rid):
        path,_=QFileDialog.getOpenFileName(self,'Import a Workshop library','','Workshop library (*.wslibrary)')
        if not path:return self.send(rid,{'cancelled':True})
        if not askUser('Import this as additional projects? Existing projects and Anki cards will not be overwritten. Imported drafts return to unapproved status; note links from another collection are not adopted.',parent=self):return self.send(rid,{'cancelled':True})
        self.task(rid,lambda _:documents.import_workspace(self.store,Path(path)),use_col=False)
    def undo(self,rid):
        step=self.controller.last_undo
        if step is None:raise ValidationError('There is no current Workshop collection operation to undo. Use Anki’s Edit → Undo for its other operations.')
        def apply(col):
            if col.undo_status().last_step!=step:raise ValidationError('Anki has performed another operation since Workshop’s change. Use Anki’s native undo history instead.')
            result=col.undo();recovered=0
            # Source records stay inspectable; undone drafts become editable again.
            for d in self.store.list('draft'):
                if d.get('status')=='committed' and d.get('note_id') and not col.find_notes('nid:'+str(d['note_id'])):
                    nid=d.pop('note_id',None);d['status']='draft';self.store.put('draft',d['id'],d,d['revision']);recovered+=1
                    for link in self.store.list('link'):
                        if link['note_id']==nid:self.store.remove('link',link['id'],link['revision'])
            return cards.OperationResult(result.changes,{'undone':True,'restored_drafts':recovered})
        def finish(result):self.controller.last_undo=None;return result
        self.task(rid,apply,finish,write=True)
    def native(self,rid,p):
        action=p.get('action');nid=p.get('note_id')
        if self.busy:raise ValidationError('Wait for the current collection change to finish.')
        if action in ('browse','edit'):
            query='nid:'+str(integer(nid,1,2**53-1,'Note ID')) if nid else text(p.get('query',''),2000,'Anki search')
            browser=aqt.dialogs.open('Browser',self.mw,search=(query,))
            self.send(rid,{'opened':'Browser'});return
        if action=='preview':
            nid=integer(nid,1,2**53-1,'Note ID');ids=list(self.col.card_ids_of_note(nid))
            if not ids:raise ValidationError('This note has no cards to preview.')
            from .preview import CardPreview
            preview=CardPreview(self.controller,ids)
            if not hasattr(self.controller,'previews'):self.controller.previews=[]
            self.controller.previews.append(preview);preview.open();self.send(rid,{'opened':'Preview'});return
        if action in ('add','tts'):
            editor=aqt.dialogs.open('AddCards',self.mw)
            if action=='tts':self.send(rid,{'opened':'Native editor','message':'Use HyperTTS’s own toolbar button here. Workshop does not call its private API.'})
            else:self.send(rid,{'opened':'Native editor'})
            return
        if action in ('sync','check_media') and getattr(self.controller,'suite',None) is not None:
            from ..card_studio import command
            return self.send(rid,command(self,'suite_native',{'command':action}))
        if action=='sync':
            if not askUser('Open Anki’s normal synchronization now? Workshop’s local source library is not synchronized by AnkiWeb.',parent=self):return self.send(rid,{'cancelled':True})
            self.send(rid,{});self.close();self.mw.onSync();return
        if action=='check_media':
            self.send(rid,{});self.close();self.mw.onCheckMedia();return
        raise ValidationError('Unsupported native action.')
    def occlude(self,rid,p):
        project=identifier(p['project_id']);self.store.get('project',project)
        path=self.store.blob_path(p['blob'])
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValidationError('Choose an image for native occlusion.')
        dialog=aqt.dialogs.open('AddCards',self.mw)
        editor=getattr(dialog,'editor',None)
        if editor is None or not hasattr(editor,'setup_mask_editor'):raise ValidationError('This Anki editor does not expose the supported native mask handoff. The crop is saved; open it with native Image Occlusion from Add.')
        if hasattr(editor,'fieldsAreBlank') and not editor.fieldsAreBlank():raise ValidationError('The native Add window has unfinished work. Finish or clear it first; Workshop did not overwrite it.')
        ctx={'project_id':project,'source_id':p.get('source_id',''),'version_id':p.get('version_id',''),'page':p.get('page',1),'quote':p.get('quote',''),'epoch':self.epoch,'image_path':str(path),'tag':'wsctx_'+uid()}
        self.controller.native_context.clear()
        self.controller.native_context[ctx['tag']]=ctx
        if hasattr(dialog,'set_deck'):dialog.set_deck(integer(p.get('deck_id',1),1,2**53-1,'Deck ID'))
        try:
            # Do not assume the native Add dialog already has an IO note type.
            from .masks import native_model
            model=native_model(self.col,create=False)
            if model is None:
                raise ValidationError('Create/select Anki’s native Image Occlusion note type in Add first, or publish directly with Mask Studio. The current native draft has not been changed.')
            editor.set_note(self.col.new_note(model))
            if hasattr(editor,'setup_mask_editor_for_new_note'):
                editor.setup_mask_editor_for_new_note(str(path),notetype_id=0)
            else:
                editor.setup_mask_editor(str(path))
        except Exception:
            self.controller.native_context.pop(ctx['tag'],None)
            raise
        # Only the known new native-note buffer receives the provenance tag; no existing note is edited.
        if editor.note:
            if ctx['tag'] not in editor.note.tags:editor.note.tags.append(ctx['tag'])
            editor.web.eval('setTags('+safe_json(editor.note.tags)+');')
        self.send(rid,{'opened':'Native image occlusion','message':'Draw masks and approve with Anki’s Add button. Workshop records the source when the tagged note is added.'})
    def sprout(self,rid,p):
        if getattr(self.controller,'suite',None) is not None:
            from ..card_studio import project_to_plan
            return self.send(rid,project_to_plan(self,p))
        project=self.store.get('project',identifier(p['project_id']))
        ids=sorted({l['note_id'] for l in self.store.list('link',project['id'])})
        ids=[i for i in ids if self.col.find_notes('nid:'+str(i))]
        if not ids:raise ValidationError('Add or link cards to this project before preparing an exam scope.')
        query='nid:'+','.join(map(str,ids))
        if len(query)>2000:raise ValidationError('This project exceeds Sprout’s 2,000-character search field. Choose a smaller group in Anki’s Browser, or build the covering deck/tag scope manually. Existing linked notes are not silently tagged by Workshop.')
        controller=getattr(self.mw,'_exam_sprout_controller',None)
        if not controller or not hasattr(controller,'open'):raise ValidationError('Exam Sprout is not enabled. Your cards and project remain usable in Workshop.')
        self.mw.app.clipboard().setText(query)
        controller.open()
        self.send(rid,{'notes':len(ids),'query':query,'message':'Exact note filter copied. In Exam Sprout, choose the covering decks and paste it into Edit exam → Your routine → Advanced search. No exam settings were changed automatically.'})
    def force_close(self):self.forced=True;self.close()
    def reject(self):self.close()
    def closeEvent(self,event):
        if self.closed:event.accept();return
        if not self.forced:
            if self.busy:tooltip('Wait for the collection change to finish before closing Workshop.',parent=self);event.ignore();return
            if self.dirty and not askUser('Leave without saving the current draft edits? Your last saved draft remains available.',parent=self):event.ignore();return
        self.closed=True;self.tokens.clear()
        try:saveGeom(self,'workshop_workspace')
        except Exception:pass
        if self.controller.window is self:self.controller.window=None
        web,self.web=self.web,None
        if web:
            try:web.cleanup()
            except Exception:pass
        event.accept()


def install(suite=None,registration=None):
    if aqt.mw is None:return
    if getattr(aqt.mw,'_daedalus_workshop_controller',None):return
    # Register rollback before construction: even a native QAction failure must
    # not leave an orphan menu/API when the containing suite rolls back startup.
    controller=Controller.__new__(Controller)
    def construction_cleanup():
        api=getattr(controller,'api',None)
        if api is not None and getattr(aqt.mw,'workshop_api_v1',None) is api:delattr(aqt.mw,'workshop_api_v1')
        try:controller.menu_parent.removeAction(controller.menu.menuAction())
        except Exception:pass
    if registration:registration.cleanup(construction_cleanup)
    try:controller.__init__(aqt.mw,suite=suite)
    except Exception:
        construction_cleanup();raise
    aqt.mw._daedalus_workshop_controller=controller
    def cleanup():
        controller.profile_close()
        if getattr(aqt.mw,'_daedalus_workshop_controller',None) is controller:delattr(aqt.mw,'_daedalus_workshop_controller')
        if getattr(aqt.mw,'workshop_api_v1',None) is controller.api:delattr(aqt.mw,'workshop_api_v1')
        try:controller.menu_parent.removeAction(controller.menu.menuAction())
        except Exception:pass
    if registration:registration.cleanup(cleanup)
    hooks=[('profile_did_open',controller.profile_open),('profile_will_close',controller.profile_close),
           ('collection_will_temporarily_close',controller.collection_close),('state_did_change',controller.state_change),
           ('top_toolbar_did_init_links',controller.toolbar),('deck_browser_will_render_content',controller.home),
           ('deck_browser_did_render',controller.home_ready),('webview_will_set_content',controller.web_assets),
           ('webview_did_receive_js_message',controller.web_message),('reviewer_will_show_context_menu',controller.reviewer_menu),
           ('browser_menus_did_init',controller.browser_menu),('add_cards_did_add_note',controller.native_added),
           ('editor_mask_editor_did_load_image',controller.mask_loaded)]
    for name,callback in hooks:
        hook=getattr(gui_hooks,name,None)
        if hook is not None:
            if registration:registration.hook(hook,callback)
            else:hook.append(callback)
    if aqt.mw.col:controller.profile_open()
    return controller

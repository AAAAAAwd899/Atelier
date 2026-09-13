"""Explicit Anki/Qt contract doubles, never a native Anki certification."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace, ModuleType
from copy import deepcopy
import json,re,sqlite3,sys,time,shutil

@dataclass
class AddNoteRequest:
    note:object
    deck_id:int

class OpChanges:
    def __init__(self):self.note=True;self.card=True;self.notetype=False;self.browser_table=True;self.study_queues=True

class DB:
    def __init__(self):
        self.conn=sqlite3.connect(':memory:',check_same_thread=False)
        self.conn.executescript('CREATE TABLE notes(id INTEGER PRIMARY KEY,mod INTEGER,sfld TEXT);CREATE TABLE cards(id INTEGER PRIMARY KEY,nid INTEGER,did INTEGER,queue INTEGER,type INTEGER,due INTEGER,ivl INTEGER,reps INTEGER,lapses INTEGER);CREATE TABLE revlog(id INTEGER PRIMARY KEY,cid INTEGER,ease INTEGER);')
    def all(self,q,*args):return self.conn.execute(q,args).fetchall()
    def list(self,q,*args):return [r[0] for r in self.all(q,*args)]
    def first(self,q,*args):return self.conn.execute(q,args).fetchone()
    def scalar(self,q,*args):
        r=self.first(q,*args);return r[0] if r else None
    def snapshot(self):return {t:self.all('SELECT * FROM '+t+' ORDER BY id') for t in ('notes','cards','revlog')}

class Models:
    def __init__(self,col):self.col=col;self.items={};self.counter=100
    def new(self,name):return {'id':0,'name':name,'type':0,'flds':[],'tmpls':[],'css':''}
    def new_field(self,name):return {'name':name,'ord':0}
    def add_field(self,m,f):f['ord']=len(m['flds']);m['flds'].append(f)
    def new_template(self,name):return {'name':name,'qfmt':'{{Front}}','afmt':'{{Back}}'}
    def add_template(self,m,t):m['tmpls'].append(t)
    def add(self,m):
        self.col.checkpoint();self.counter+=1;m['id']=self.counter;self.items[m['id']]=deepcopy(m)
    def get(self,id):return deepcopy(self.items.get(int(id)))
    def by_name(self,name):return next((deepcopy(v) for v in self.items.values() if v['name']==name),None)
    def all_names_and_ids(self):return [SimpleNamespace(id=k,name=m['name']) for k,m in self.items.items()]

class Note:
    def __init__(self,col,model):self.col=col;self.mid=model['id'];self.id=0;self.fields=['']*len(model['flds']);self.tags=[];self.mod=1
    def keys(self):return [f['name'] for f in self.col.models.items[self.mid]['flds']]
    def __getitem__(self,k):return self.fields[self.keys().index(k)]
    def __setitem__(self,k,v):self.fields[self.keys().index(k)]=v
    def note_type(self):return self.col.models.get(self.mid)
    def copy(self):
        n=Note(self.col,self.note_type());n.id=self.id;n.fields=self.fields[:];n.tags=self.tags[:];n.mod=self.mod;return n

class Media:
    def __init__(self,path):self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True)
    def dir(self):return str(self.path)
    def add_file(self,p):
        p=Path(p);dest=self.path/p.name
        if dest.resolve()!=p.resolve():shutil.copyfile(p,dest)
        return dest.name
    def files_in_str(self,mid,value):
        return [next(x for x in m if x) for m in re.findall(r'<img[^>]+src=["\']([^"\']+)|\[sound:([^\]]+)\]',value)]

class FakeCollection:
    def __init__(self,profile):
        self.db=DB();self.models=Models(self);self.notes={};self.counter=1700000000000;self.cardcounter=1800000000000
        self.media=Media(Path(profile)/'collection.media');self.writes=[];self.steps=[];self.seq=0
        self.decks=SimpleNamespace(all_names_and_ids=lambda include_filtered=False:[SimpleNamespace(id=1,name='Default'),SimpleNamespace(id=2,name='Workshop studies'),SimpleNamespace(id=3,name='Workshop studies::Foundations')],get=lambda did,default=False:{1:{'id':1,'name':'Default','dyn':0},2:{'id':2,'name':'Workshop studies','dyn':0},3:{'id':3,'name':'Workshop studies::Foundations','dyn':0}}.get(int(did)))
    def new_note(self,m):return Note(self,m)
    def get_note(self,n):
        if int(n) not in self.notes:raise ValueError('Note no longer exists')
        return self.notes[int(n)].copy()
    def note_count(self):return len(self.notes)
    def card_ids_of_note(self,n):return self.db.list('SELECT id FROM cards WHERE nid=?',int(n))
    def find_notes(self,q):
        q=q.strip()
        if q.startswith('nid:'):return [int(n) for n in q[4:].split(',') if n.isdigit() and int(n) in self.notes]
        if q.startswith('tag:'):return [k for k,n in self.notes.items() if q[4:] in n.tags]
        if q.startswith('cid:'):return list(set(self.db.list('SELECT nid FROM cards WHERE id IN ('+','.join('?'*len(q[4:].split(',')))+')',*map(int,q[4:].split(',')))))
        terms=re.findall(r'"((?:\\.|[^"\\])*)"',q)
        terms=[t.replace('\\"','"').replace('\\\\','\\').lower() for t in terms]
        if not terms and q:terms=[q.lower()]
        return [nid for nid,n in self.notes.items() if not terms or any(t in ' '.join(n.fields).lower() for t in terms)]
    def snapshot(self):return {'notes':{k:(n.mid,n.fields[:],n.tags[:],n.mod) for k,n in self.notes.items()},'models':deepcopy(self.models.items),'db':self.db.snapshot()}
    def checkpoint(self):
        self.seq+=1;self.steps.append((self.seq,self.snapshot()));return self.seq
    def add_custom_undo_entry(self,label):return self.checkpoint()
    def merge_undo_entries(self,seq):
        first=next((x for x in self.steps if x[0]==seq),None)
        if first:self.steps=[x for x in self.steps if x[0]<seq]+[first]
        return OpChanges()
    def add_notes(self,reqs):
        self.checkpoint();self.writes.append(('add_notes',len(reqs)))
        for r in reqs:
            self.counter+=1;n=r.note;n.id=self.counter;self.notes[n.id]=n.copy();self.db.conn.execute('INSERT INTO notes VALUES(?,?,?)',(n.id,n.mod,n.fields[0]));m=n.note_type()
            from addon.core import clozes
            count=len(clozes(n.fields[0])) if m['type']==1 else len(m['tmpls'])
            for i in range(count):self.cardcounter+=1;self.db.conn.execute('INSERT INTO cards VALUES(?,?,?,?,?,?,?,?,?)',(self.cardcounter,n.id,r.deck_id,0,0,0,0,0,0))
        return OpChanges()
    def update_note(self,n):return self.update_notes([n])
    def update_notes(self,notes):
        self.checkpoint();self.writes.append(('update_notes',len(notes)))
        for n in notes:n.mod+=1;self.notes[n.id]=n.copy();self.db.conn.execute('UPDATE notes SET mod=?,sfld=? WHERE id=?',(n.mod,n.fields[0],n.id))
        return OpChanges()
    def undo_status(self):return SimpleNamespace(last_step=self.steps[-1][0] if self.steps else 0)
    def undo(self):
        if not self.steps:raise ValueError('Nothing to undo')
        _,snap=self.steps.pop();self.models.items=snap['models'];self.notes={}
        for k,(mid,fields,tags,mod) in snap['notes'].items():n=Note(self,self.models.items[mid]);n.id=k;n.fields=fields;n.tags=tags;n.mod=mod;self.notes[k]=n
        for table,rows in snap['db'].items():
            self.db.conn.execute('DELETE FROM '+table)
            for row in rows:self.db.conn.execute('INSERT INTO '+table+' VALUES('+','.join('?'*len(row))+')',row)
        return SimpleNamespace(changes=OpChanges())
    def seed(self,front,back,model=None,tags=None,deck=2):
        if model is None:
            from addon.collection import ensure_model
            model=ensure_model(self,'question')
        n=self.new_note(model);n.fields[0]=front;n.fields[1]=back;n.tags=tags or [];self.add_notes([AddNoteRequest(n,deck)]);return n
    def close(self):self.db.conn.close()

class Signal:
    def connect(self,fn):self.fn=fn
class Dummy:
    def __init__(self,*a,**kw):self.triggered=Signal();self.clicked=Signal();self.loadFinished=Signal()
    def __getattr__(self,name):return lambda *a,**kw:None
class QWidget(Dummy):pass
class QDialog(QWidget):pass
class Action(Dummy):pass
class Operation:
    mw=None
    def __init__(self,parent,op,success=None):self.op=op;self.done=success;self.fail=None;self.off=False
    def success(self,f):self.done=f;return self
    def failure(self,f):self.fail=f;return self
    def without_collection(self):self.off=True;return self
    def run_in_background(self,**kw):
        try:r=self.op(None if self.off else self.mw.col)
        except Exception as e:
            if self.fail:self.fail(e)
            else:raise
        else:
            if self.done:self.done(r)

def install_stubs(mw):
    aqt=ModuleType('aqt');aqt.__path__=[];aqt.mw=mw;aqt.dialogs=SimpleNamespace(open=lambda name,*a,**kw:mw.native(name,kw));sys.modules['aqt']=aqt
    hooks=ModuleType('aqt.gui_hooks');aqt.gui_hooks=hooks;sys.modules['aqt.gui_hooks']=hooks
    names='QAction QDialog QVBoxLayout QHBoxLayout QPushButton QLabel QFileDialog QInputDialog QLineEdit QMenu Qt QTimer QUrl QDesktopServices QApplication QKeySequence QBuffer QByteArray QIODevice QPlainTextEdit QWidget'
    qt=ModuleType('aqt.qt')
    for n in names.split():setattr(qt,n, QDialog if n=='QDialog' else type(n,(Dummy,),{}))
    qt.Qt=SimpleNamespace(WidgetAttribute=SimpleNamespace(WA_DeleteOnClose=1),WindowModality=SimpleNamespace(NonModal=0),TextFormat=SimpleNamespace(PlainText=0))
    qt.QLineEdit.EchoMode=SimpleNamespace(Password=2);qt.QFileDialog.getOpenFileNames=lambda *a:(list(mw.files),'')
    qt.QFileDialog.getOpenFileName=lambda *a:(mw.files[0] if mw.files else '','');qt.QFileDialog.getSaveFileName=lambda *a:(mw.savepath,'')
    qt.QInputDialog.getText=lambda *a:('test-key',True);qt.QDesktopServices.openUrl=lambda url:mw.native('external',{'url':url})
    qt.QUrl.fromLocalFile=lambda p:p;sys.modules['aqt.qt']=qt
    ops=ModuleType('aqt.operations');Operation.mw=mw;ops.QueryOp=Operation;ops.CollectionOp=Operation;sys.modules['aqt.operations']=ops
    web=ModuleType('aqt.webview');web.AnkiWebView=Dummy;sys.modules['aqt.webview']=web
    browser=ModuleType('aqt.deckbrowser');browser.DeckBrowser=type('DeckBrowser',(Dummy,),{});sys.modules['aqt.deckbrowser']=browser
    util=ModuleType('aqt.utils');util.askUser=lambda *a,**k:True;util.tooltip=lambda *a,**k:None;util.restoreGeom=lambda *a:None;util.saveGeom=lambda *a:None;sys.modules['aqt.utils']=util
    theme=ModuleType('aqt.theme');theme.theme_manager=SimpleNamespace(night_mode=True);sys.modules['aqt.theme']=theme
    anki=ModuleType('anki');anki.__path__=[];sys.modules['anki']=anki
    ac=ModuleType('anki.collection');ac.AddNoteRequest=AddNoteRequest;ac.OpChanges=OpChanges;sys.modules['anki.collection']=ac
    return aqt

"""Profile-local, transactional storage; never opens Anki's collection SQLite file."""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
from typing import Any
from .core import (SCHEMA, THEMES, COVERS, MAX_SOURCE_BYTES, MAX_TEXT, ConflictError,
                   ValidationError, identifier, integer, now, uid, text, safe_json, validate_draft)

DEFAULT_SETTINGS={'theme':'night','living_library':True,'motion':True,'show_home':True,
                  'show_toolbar':True,'new_per_day':15,
                  'seconds_per_card':30,'protected_fields':[],'protected_tags':['AnkiHub','AnkiCollab'],
                  'ai_enabled':False,'ai_endpoint':'','ai_model':'','embedding_model':'',
                  'remote_consent':False}
ENTITY_KINDS=frozenset(('project','source','version','draft','link','repair','pair','milestone','settings'))

class Store:
    def __init__(self, profile: str | Path, initial_theme=None):
        self.root=Path(profile).resolve()/'workshop'
        self.root.mkdir(parents=True,exist_ok=True)
        self.blobs=self.root/'sources';self.blobs.mkdir(exist_ok=True)
        self.db_path=self.root/'workshop.sqlite3'
        self.lock=threading.RLock()
        with self.connection() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version>SCHEMA:raise ValidationError('This workspace was saved by a newer Workshop version. Update Workshop; your library has not been reset.')
            db.executescript('''
            CREATE TABLE IF NOT EXISTS entities(kind TEXT NOT NULL,id TEXT PRIMARY KEY,project TEXT NOT NULL DEFAULT '',revision INTEGER NOT NULL,updated TEXT NOT NULL,body TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS entities_kind ON entities(kind, project);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,action TEXT NOT NULL,details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS note_index(nid INTEGER PRIMARY KEY,modified INTEGER,text TEXT NOT NULL,front TEXT NOT NULL,model TEXT NOT NULL,fields TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            ''')
            db.execute(f'PRAGMA user_version={SCHEMA}')
        if not self.get('settings','global',required=False):
            self.put('settings','global',{**DEFAULT_SETTINGS,**({'theme':initial_theme} if initial_theme in THEMES else {})})

    @contextmanager
    def connection(self):
        with self.lock:
            db=sqlite3.connect(str(self.db_path),timeout=10)
            db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA busy_timeout=10000')
            try:
                with db:yield db
            finally:db.close()

    def _decode(self,row):
        if not row:return None
        item=json.loads(row[3]);item.update(id=row[0],revision=row[1],updated=row[2]);return item

    def get(self, kind: str, item_id: str, *, required: bool=True):
        with self.connection() as db:
            row=db.execute('SELECT id,revision,updated,body FROM entities WHERE kind=? AND id=?',(kind,item_id)).fetchone()
        if not row and required:raise ValidationError('This item is no longer in your workspace. Refresh and try again.')
        return self._decode(row)

    def list(self,kind:str,project:str='', *, limit:int=10000) -> list[dict]:
        with self.connection() as db:
            sql='SELECT id,revision,updated,body FROM entities WHERE kind=?';params:list[Any]=[kind]
            if project:sql+=' AND project=?';params.append(project)
            sql+=' ORDER BY updated DESC,id LIMIT ?';params.append(limit)
            rows=db.execute(sql,params).fetchall()
        return [self._decode(r) for r in rows]

    def put(self,kind:str,item_id:str,data:dict,expected:int|None=None) -> dict:
        if kind not in ENTITY_KINDS:raise ValidationError('Unsupported workspace item.')
        if not(kind=='settings' and item_id=='global'):identifier(item_id)
        payload=deepcopy(data)
        for k in ('id','revision','updated'):payload.pop(k,None)
        encoded=safe_json(payload)
        if len(encoded)>20_000_000:raise ValidationError('This item is too large for the workspace.')
        with self.connection() as db:
            prev=db.execute('SELECT revision FROM entities WHERE id=? AND kind=?',(item_id,kind)).fetchone()
            rev=prev[0] if prev else 0
            if expected is not None and rev!=expected:raise ConflictError('This item changed in another window. Reload it before applying changes.')
            stamp=now()
            db.execute('INSERT INTO entities(kind,id,project,revision,updated,body) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET project=excluded.project,revision=excluded.revision,updated=excluded.updated,body=excluded.body',
                       (kind,item_id,payload.get('project_id',''),rev+1,stamp,encoded))
        return {**payload,'id':item_id,'revision':rev+1,'updated':stamp}

    def remove(self,kind:str,item_id:str,expected:int|None=None):
        with self.connection() as db:
            row=db.execute('SELECT revision FROM entities WHERE kind=? AND id=?',(kind,item_id)).fetchone()
            if expected is not None and (not row or row[0]!=expected):raise ConflictError('This item changed. Refresh before removing it.')
            db.execute('DELETE FROM entities WHERE kind=? AND id=?',(kind,item_id))
        self.event('removed',{'kind':kind,'id':item_id})

    def event(self,action:str,details:dict):
        # No raw documents, prompts, or provider keys in diagnostic/event records.
        with self.connection() as db:
            db.execute('INSERT INTO events(at,action,details) VALUES(?,?,?)',(now(),action,safe_json(details)))
            db.execute('DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 1000)')

    def events(self,limit=50):
        with self.connection() as db:
            rows=db.execute('SELECT id,at,action,details FROM events ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
        return [{'id':r[0],'at':r[1],'action':r[2],'details':json.loads(r[3])} for r in rows]

    def settings(self):
        value=self.get('settings','global')
        return {**DEFAULT_SETTINGS,**{k:value[k] for k in DEFAULT_SETTINGS if k in value}}

    def set_settings(self,patch):
        s=self.settings()
        for k,v in patch.items():
            if k not in s:continue
            if isinstance(DEFAULT_SETTINGS[k],bool):
                if type(v)is not bool:raise ValidationError(f'{k} must be enabled or disabled.')
            elif k in ('new_per_day','seconds_per_card'):
                v=integer(v,1 if k=='new_per_day' else 5,500 if k=='new_per_day' else 300,k)
            elif k in ('protected_fields','protected_tags'):
                if not isinstance(v,list) or len(v)>100 or any(not isinstance(x,str) or len(x)>100 for x in v):raise ValidationError('Invalid protection list.')
                v=list(dict.fromkeys(x.strip() for x in v if x.strip()))
            else:v=text(v,2000,k)
            s[k]=v
        if s['theme'] not in THEMES:raise ValidationError('Choose an available appearance.')
        self.put('settings','global',s);return s

    def project(self,data):
        title=text(data.get('title',''),120,'Project title',True)
        cover=data.get('cover','botanical')
        if cover not in COVERS:raise ValidationError('Choose an available binding.')
        old=self.get('project',data['id']) if data.get('id') else {}
        payload={**old,'title':title,'description':text(data.get('description',''),1200,'Project description'),
                 'cover':cover,'archived':bool(data.get('archived',False)),
                 'created':old.get('created') or now()}
        item=self.put('project',old.get('id') or uid(),payload,data.get('revision'))
        self.event('project_saved',{'project_id':item['id']});return item

    def save_blob(self,content:bytes,suffix:str)->str:
        if not isinstance(content,bytes) or not content or len(content)>MAX_SOURCE_BYTES:raise ValidationError('Choose a nonempty file under 60 MB.')
        suffix=suffix.lower().lstrip('.')
        if suffix not in ('pdf','png','jpg','jpeg','webp','mp3','wav','ogg','txt','md','docx','pptx','html','json','odt','odp','csv','tsv'):raise ValidationError('Unsupported source file.')
        name=hashlib.sha256(content).hexdigest()+'.'+suffix
        dest=self.blobs/name
        if not dest.exists():
            fd,tmp=tempfile.mkstemp(prefix='.write-',dir=str(self.blobs))
            try:
                with os.fdopen(fd,'wb') as out:out.write(content);out.flush();os.fsync(out.fileno())
                os.replace(tmp,dest)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        return name

    def blob_path(self,name:str)->Path:
        if not isinstance(name,str) or not re.fullmatch(r'[a-f0-9]{64}\.[a-z0-9]{2,5}',name):raise ValidationError('Invalid source reference.')
        path=(self.blobs/name).resolve()
        if path.parent!=self.blobs.resolve() or not path.is_file():raise ValidationError('The local source file is missing. Restore your workspace backup or reimport it.')
        return path

    def add_source(self,project_id:str,title:str,kind:str,pages:list[dict],blob:str='',locator:str='',source_id:str='',metadata:dict|None=None):
        self.get('project',identifier(project_id))
        title=text(title,200,'Source title',True)
        if not isinstance(pages,list) or not 1<=len(pages)<=2000:raise ValidationError('Use a source with 1–2,000 pages or sections.')
        total=0;clean=[]
        for i,p in enumerate(pages):
            value=text(p.get('text',''),500_000,'Page text');total+=len(value)
            if total>MAX_TEXT:raise ValidationError('This source has too much extracted text. Import it in smaller parts.')
            clean.append({'page':i+1,'text':value,'image':p.get('image',''),'label':str(p.get('label',i+1))[:80]})
            if clean[-1]['image']:self.blob_path(clean[-1]['image'])
            clean[-1]['notes']=text(p.get('notes',''),500_000,'Speaker notes')
            total+=len(clean[-1]['notes'])
            if total>MAX_TEXT:raise ValidationError('The source and its notes are too large.')
            assets=p.get('assets',[])
            if not isinstance(assets,list) or len(assets)>100:raise ValidationError('Use at most 100 embedded figures per page.')
            clean[-1]['assets']=[]
            for asset in assets:
                name=asset.get('blob','')
                if not isinstance(name,str) or not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|jpeg|webp)',name):raise ValidationError('Invalid embedded raster image.')
                self.blob_path(name)
                clean[-1]['assets'].append({'blob':name,'label':text(asset.get('label','Figure'),160,'Figure label')})
            clean[-1]['hidden_slide']=bool(p.get('hidden_slide',False))
        if blob:self.blob_path(blob)
        old=self.get('source',source_id) if source_id else None
        if old and old['project_id']!=project_id:raise ValidationError('That source belongs to another project.')
        digest=hashlib.sha256(safe_json(clean).encode()).hexdigest()
        if old:
            last=self.get('version',old['version_id'])
            if digest==last['digest'] and blob==last.get('blob',''):return {'source':old,'unchanged':True}
        sid=source_id or uid();vid=uid()
        ordinal=self.get('version',old['version_id'])['ordinal']+1 if old else 1
        version={'project_id':project_id,'source_id':sid,'ordinal':ordinal,'pages':clean,'digest':digest,'blob':blob,'created':now(),'metadata':metadata or {}}
        source={'project_id':project_id,'title':title,'kind':kind,'version_id':vid,'locator':text(locator,2000,'Source location'),'created':old.get('created',now()) if old else now(),'page_count':len(clean)}
        # Entity transaction is atomic across the version and source pointer.
        with self.connection() as db:
            for k,i,payload,rev in [('version',vid,version,1),('source',sid,source,(old['revision']+1) if old else 1)]:
                db.execute('INSERT OR REPLACE INTO entities VALUES(?,?,?,?,?,?)',(k,i,project_id,rev,now(),safe_json(payload)))
        self.event('source_updated' if old else 'source_added',{'project_id':project_id,'source_id':sid,'version':ordinal})
        return {'source':self.get('source',sid),'previous_version':old['version_id'] if old else '', 'unchanged':False}

    def save_draft(self,data:dict):
        d=validate_draft(data)
        self.get('project',d['project_id'])
        if d['source_id']:
            source=self.get('source',d['source_id']);version=self.get('version',d['version_id'])
            if source['project_id']!=d['project_id'] or version['source_id']!=source['id']:raise ValidationError('The source does not belong to this project.')
            if d['page']>len(version['pages']):raise ValidationError('That source page is unavailable.')
        old=self.get('draft',data['id']) if data.get('id') else {}
        if old.get('status')=='committed':raise ValidationError('This draft is already in Anki. Use Improve to change its note.')
        d['status']='draft';d['created']=old.get('created') or now()
        if old.get('front')!=d['front'] or old.get('back')!=d['back']:
            if d['origin']=='ai':d['verified']=False if not data.get('review_confirm') else d['verified']
        return self.put('draft',old.get('id') or uid(),d,data.get('revision'))

    def link_note(self,nid:int,project_id:str,source_id:str='',version_id:str='',page:int=1,quote:str='',draft_id:str='',snapshot:str=''):
        self.get('project',project_id)
        if source_id:
            source=self.get('source',source_id);v=self.get('version',version_id)
            if source['project_id']!=project_id or v['source_id']!=source_id:raise ValidationError('Invalid source link.')
            integer(page,1,len(v['pages']),'Source page')
        links=self.list('link',project_id)
        existing=next((x for x in links if x['note_id']==nid and x.get('source_id')==source_id and x.get('version_id')==version_id and x.get('page')==page),None)
        out=self.put('link',existing['id'] if existing else uid(),{'project_id':project_id,'note_id':nid,'source_id':source_id,'version_id':version_id,'page':page,'quote':quote[:20000],'draft_id':draft_id,'fingerprint':snapshot,'created':now()})
        if draft_id:
            d=self.get('draft',draft_id);d.update(status='committed',note_id=nid)
            self.put('draft',draft_id,d,d['revision'])
        return out

    def flag(self,nid:int,reason:str='Review this card',project_id:str='',origin:str='manual',extra:dict|None=None):
        nid=integer(nid,1,2**53-1,'Note ID')
        if project_id:self.get('project',project_id)
        prior=next((r for r in self.list('repair') if r['note_id']==nid and r['status']=='open' and r.get('reason')==reason),None)
        if prior:return prior
        return self.put('repair',uid(),{'project_id':project_id,'note_id':nid,'reason':text(reason,500,'Repair reason',True),'status':'open','origin':origin,'created':now(),'extra':extra or {}})

    def resolve(self,rid:str,status:str):
        r=self.get('repair',rid)
        if status not in ('resolved','dismissed','open'):raise ValidationError('Choose an available repair status.')
        r['status']=status;r['resolved_at']=now() if status!='open' else ''
        out=self.put('repair',rid,r,r['revision']);self.event('repair_'+status,{'repair_id':rid,'note_id':r['note_id']});return out

    def summary(self):
        projects=self.list('project');sources=self.list('source');drafts=self.list('draft');links=self.list('link');repairs=self.list('repair')
        for p in projects:
            pid=p['id'];ps=[s for s in sources if s['project_id']==pid]
            p['sources']=len(ps);p['pages']=sum(s['page_count'] for s in ps)
            p['drafts']=sum(d['project_id']==pid and d.get('status')!='committed' for d in drafts)
            p['notes']=len({l['note_id'] for l in links if l['project_id']==pid})
            p['repairs']=sum(r.get('project_id')==pid and r['status']=='open' for r in repairs)
            p['stage']='prepared' if p['notes'] and not p['drafts'] else 'shaping' if p['drafts'] or p['notes'] else 'collected' if p['sources'] else 'new'
        return {'projects':projects,'sources':sources,'drafts':drafts,'links':links,'repairs':repairs,'settings':self.settings(),'events':self.events(20),'pairs':self.list('pair')}

    def index_notes(self,rows:list[dict],clear=False):
        with self.connection() as db:
            if clear:db.execute('DELETE FROM note_index')
            db.executemany('INSERT OR REPLACE INTO note_index VALUES(?,?,?,?,?,?)',[(r['id'],r.get('modified',0),r['text'],r.get('front',''),r.get('model',''),safe_json(r.get('fields',{}))) for r in rows])
            db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('index_updated',now()))

    def indexed(self,terms:list[str],limit=1000):
        with self.connection() as db:
            if terms:
                sql='SELECT nid,modified,text,front,model,fields FROM note_index WHERE '+' OR '.join('text LIKE ? ESCAPE "\\"' for _ in terms)
                args=['%'+t.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%' for t in terms]
            else:sql='SELECT nid,modified,text,front,model,fields FROM note_index';args=[]
            sql+=' LIMIT ?';args.append(limit)
            rows=db.execute(sql,args).fetchall()
        return [{'id':r[0],'modified':r[1],'text':r[2],'front':r[3],'model':r[4],'fields':json.loads(r[5])} for r in rows]

    def backup(self,dest:Path):
        with self.lock:
            source=sqlite3.connect(str(self.db_path));target=sqlite3.connect(str(dest))
            try:source.backup(target)
            finally:target.close();source.close()

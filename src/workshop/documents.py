"""Bounded local document capture, original-page rendering, and portable archives."""
from __future__ import annotations
from base64 import b64encode
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import hashlib
import json
import mimetypes
import re
import zipfile
from xml.etree import ElementTree as ET
from .core import MAX_SOURCE_BYTES, MAX_TEXT, ValidationError, integer, plain, text, uid, now, diff_pages


def _zip_entries(data:bytes):
    z=zipfile.ZipFile(BytesIO(data))
    entries=z.infolist()
    names=[x.filename for x in entries]
    if len(names)!=len(set(names)):
        z.close();raise ValidationError('This document contains duplicate archive paths.')
    if len(entries)>8000 or sum(i.file_size for i in entries)>160*1024*1024:
        z.close();raise ValidationError('This compressed document expands beyond the import limit.')
    if any(i.flag_bits&1 for i in entries):z.close();raise ValidationError('Unlock this document before importing it.')
    return z

def _xml(raw:bytes):
    if len(raw)>15_000_000 or b'<!DOCTYPE' in raw.replace(b'\x00',b'').upper() or b'<!ENTITY' in raw.replace(b'\x00',b'').upper():raise ValidationError('Unsupported XML content in this document.')
    return ET.fromstring(raw)

def capture_file(store,project_id:str,path:str,source_id:str='',alive=lambda:True):
    p=Path(path)
    if not p.is_file() or p.stat().st_size>MAX_SOURCE_BYTES:raise ValidationError('Choose a file under 60 MB.')
    data=p.read_bytes()
    if not data:raise ValidationError('This file is empty.')
    suffix=p.suffix.lower().lstrip('.')
    title=p.stem.replace('_',' ').strip()
    metadata={'filename':p.name,'bytes':len(data),'imported':now()}
    pages=[]
    if suffix=='pdf':
        if not data.lstrip().startswith(b'%PDF'):raise ValidationError('This file does not contain a PDF document.')
        from .vendor.pypdf import PdfReader
        reader=PdfReader(BytesIO(data),strict=False)
        if reader.is_encrypted and not reader.decrypt(''):raise ValidationError('Remove the PDF password before importing. Your original file is unchanged.')
        if not 1<=len(reader.pages)<=2000:raise ValidationError('Import PDFs with 1–2,000 pages; split larger documents first.')
        total=0
        for n,page in enumerate(reader.pages):
            if not alive():raise ValidationError('The profile changed; the import was cancelled.')
            value=(page.extract_text() or '').strip();total+=len(value)
            if total>MAX_TEXT:raise ValidationError('The extracted text is too large; import this source in smaller sections.')
            pages.append({'text':value,'label':str(n+1)})
        metadata['text_pages']=sum(bool(x['text']) for x in pages)
        metadata['extraction_note']='Extracted text may omit diagrams or reorder columns. Always check the original page; no OCR or medical-content inference was performed.'
    elif suffix in ('png','jpg','jpeg','webp'):
        validate_image_header(data)
        blob=store.save_blob(data,suffix)
        pages=[{'text':'','image':blob,'label':'Image'}]
    elif suffix in ('txt','md','html','htm'):
        if suffix=='htm':suffix='html'
        try:value=data.decode('utf-8-sig')
        except UnicodeDecodeError:raise ValidationError('Save this text file as UTF-8 before importing.') from None
        if suffix=='html':value=plain(value)
        pages=[{'text':value,'label':'Text'}]
    elif suffix in ('docx','pptx','odt','odp'):
        from . import importers
        with _zip_entries(data) as z:
            if suffix=='pptx':pages,extra=importers.power_point(z,_xml,store,alive)
            elif suffix=='docx':pages,extra=importers.word_document(z,_xml,store)
            else:pages,extra=importers.open_document(z,_xml,suffix,store)
        metadata.update(extra)
    elif suffix in ('csv','tsv'):
        from .importers import delimited_text
        pages,extra=delimited_text(data,suffix);metadata.update(extra)
    elif suffix=='json':
        capture=json.loads(data)
        if capture.get('format')!='workshop-capture-v1':raise ValidationError('This JSON is not a Workshop browser capture.')
        value=text(capture.get('text',''),MAX_TEXT,'Captured text',True)
        title=text(capture.get('title',title),200,'Source title',True)
        pages=[{'text':value,'label':'Selection'}]
        from .network import allowed_source_url
        metadata['url']=allowed_source_url(capture.get('url',''))
        metadata['captured_at']=str(capture.get('captured_at',''))[:80]
    else:raise ValidationError('Supported sources: PDF, image, UTF-8 text, Markdown, HTML, Word, PowerPoint, OpenDocument, CSV/TSV, or Workshop capture JSON. Legacy .ppt/.doc and macro-enabled files must be exported to PDF, .pptx or .docx first.')
    blob=store.save_blob(data,suffix)
    locator=metadata.get('url','')
    if not alive():raise ValidationError('The profile changed; the import was cancelled.')
    return store.add_source(project_id,title,suffix,pages,blob,locator,source_id,metadata)

def validate_image_header(data):
    if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or (data[:4]==b'RIFF' and data[8:12]==b'WEBP')):
        raise ValidationError('Choose a PNG, JPEG, or WebP image.')

def _render_page(store,version_id,page,width=1400):
    version=store.get('version',version_id)
    page=integer(page,1,len(version['pages']),'Page');width=integer(width,320,2200,'Image width')
    record=version['pages'][page-1]
    if record.get('image'):
        return {'image':data_url(store.blob_path(record['image'])),'blob':record['image'],'text':record['text'],'page':page}
    blob=version.get('metadata',{}).get('visual_pdf') or version.get('blob','')
    if blob.endswith('.pdf'):
        try:
            from PyQt6.QtPdf import QPdfDocument
            from PyQt6.QtCore import QSize,QBuffer,QIODevice,QByteArray
        except ImportError:
            return {'image':'','text':record['text'],'page':page,'visual_unavailable':True,'message':'Qt PDF is not included in this Anki installation. Extracted text is available; use Open original for the exact page.'}
        doc=QPdfDocument(None)
        try:
            error=doc.load(str(store.blob_path(blob)))
            if getattr(error,'value',error)!=0:raise ValidationError('The original PDF page could not be opened.')
            size=doc.pagePointSize(page-1)
            if size.width()<=0:raise ValidationError('The PDF page has no drawable area.')
            height=max(1,round(width*size.height()/size.width()))
            if height>5000:width=max(320,round(width*5000/height));height=5000
            image=doc.render(page-1,QSize(width,height))
            if image.isNull():raise ValidationError('The PDF page could not be rendered.')
            raw=QByteArray();buff=QBuffer(raw);buff.open(QIODevice.OpenModeFlag.WriteOnly)
            if not image.save(buff,'PNG'):raise ValidationError('The PDF page could not be encoded.')
            buff.close();data=bytes(raw)
            return {'image':'data:image/png;base64,'+b64encode(data).decode(),'text':record['text'],'page':page,'rendered':True}
        finally:doc.close()
    return {'image':'','text':record['text'],'page':page}

def render_page(store,version_id,page,width=1400):
    out=_render_page(store,version_id,page,width)
    version=store.get('version',version_id);record=version['pages'][integer(page,1,len(version['pages']),'Page')-1]
    out['notes']=record.get('notes','')
    out['assets']=[{**a,'image':data_url(store.blob_path(a['blob']))} for a in record.get('assets',[])[:40]]
    out['asset_count']=len(record.get('assets',[]))
    out['hidden_slide']=bool(record.get('hidden_slide',False))
    return out


def attach_pdf_layout(store,version_id,path,alive=lambda:True):
    version=store.get('version',version_id);p=Path(path)
    if p.suffix.lower()!='.pdf' or not p.is_file() or p.stat().st_size>MAX_SOURCE_BYTES:
        raise ValidationError('Choose a matching PDF export smaller than 60 MB.')
    raw=p.read_bytes()
    from .vendor.pypdf import PdfReader
    reader=PdfReader(BytesIO(raw),strict=False)
    if reader.is_encrypted and not reader.decrypt(''):raise ValidationError('Remove the PDF password first.')
    if len(reader.pages)!=len(version['pages']):
        raise ValidationError(f'The PDF has {len(reader.pages)} pages but this edition has {len(version["pages"])} slides/sections. Export one PDF page per slide, including hidden slides; the source was not changed.')
    if not alive():raise ValidationError('The active profile changed.')
    blob=store.save_blob(raw,'pdf')
    payload={k:v for k,v in version.items() if k not in ('id','revision','updated')}
    payload.setdefault('metadata',{})['visual_pdf']=blob
    payload['metadata']['visual_pdf_name']=p.name
    # User explicitly picked a same-count export. Matching count is not verification
    # of semantic correspondence; the UI asks for that check before selection.
    store.put('version',version_id,payload,expected=version['revision'])
    return {'attached':True,'pages':len(reader.pages),'message':'PDF layout attached. Check the first and last slide against the source; page count alone does not prove a matching export.'}


def crop_page(store,version_id,page,rect):
    if not isinstance(rect,dict):raise ValidationError('Draw a rectangle on the image first.')
    values=[]
    for k in ('x','y','w','h'):
        try:v=float(rect[k])
        except (KeyError,TypeError,ValueError):raise ValidationError('Invalid image selection.') from None
        if not 0<=v<=1:raise ValidationError('The image selection must be inside the page.')
        values.append(v)
    x,y,w,h=values
    if w<.01 or h<.01 or x+w>1.00001 or y+h>1.00001:raise ValidationError('Draw a larger rectangle inside the page.')
    rendered=render_page(store,version_id,page,1800)
    if not rendered.get('image'):raise ValidationError('Use an image or visually rendered PDF page for region capture.')
    from base64 import b64decode
    from PyQt6.QtGui import QImage
    from PyQt6.QtCore import QBuffer,QByteArray,QIODevice
    raw=b64decode(rendered['image'].split(',',1)[1]);img=QImage.fromData(raw)
    if img.isNull():raise ValidationError('The page image could not be decoded.')
    crop=img.copy(round(x*img.width()),round(y*img.height()),max(1,round(w*img.width())),max(1,round(h*img.height())))
    payload=QByteArray();buff=QBuffer(payload);buff.open(QIODevice.OpenModeFlag.WriteOnly);crop.save(buff,'PNG');buff.close()
    name=store.save_blob(bytes(payload),'png')
    return {'blob':name,'image':data_url(store.blob_path(name)),'rect':rect}

def data_url(path:Path):
    if path.stat().st_size>20*1024*1024:raise ValidationError('This image is too large to preview.')
    mime={'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp','mp3':'audio/mpeg','wav':'audio/wav','ogg':'audio/ogg'}.get(path.suffix[1:])
    if not mime:raise ValidationError('This file cannot be previewed inline.')
    return f'data:{mime};base64,'+b64encode(path.read_bytes()).decode()

def compare_source(store,source_id):
    source=store.get('source',source_id)
    versions=sorted([v for v in store.list('version',source['project_id']) if v['source_id']==source_id],key=lambda x:x['ordinal'])
    if len(versions)<2:return {'changed':[],'removed':[],'added':[],'unchanged':{},'affected':[],'message':'This source has one version. Import a revised file to compare.'}
    old,new=versions[-2:];result=diff_pages(old['pages'],new['pages'])
    changed={x['old_page'] for x in result['changed']}|set(result['removed'])
    links=[l for l in store.list('link',source['project_id']) if l.get('source_id')==source_id and l.get('version_id')!=new['id']]
    # Older-than-previous links need review even if their page isn't in the most recent diff.
    visual_changed=old.get('blob')!=new.get('blob')
    affected=[{**l,'reason':('Linked to an older source version' if l.get('version_id')!=old['id'] else 'Linked source passage changed' if l.get('page') in changed else 'File changed; this visual / unquoted source link needs inspection')} for l in links if l.get('version_id')!=old['id'] or l.get('page') in changed or (visual_changed and not l.get('quote'))]
    return {**result,'affected':affected,'old_version':old['ordinal'],'new_version':new['ordinal'],'source':source}

def export_workspace(store,path):
    from .storage import ENTITY_KINDS
    entries={k:store.list(k) for k in ENTITY_KINDS if k not in ('settings','milestone')}
    package={'format':'workshop-library-v1','created':now(),'entities':entries,
             'notice':'Collection notes and review history are not included. Imported links are detached until explicitly matched to this collection.'}
    # Store a simple self-contained archive; profile identifiers and API credentials are absent.
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('library.json',json.dumps(package,ensure_ascii=False))
        for file in sorted(store.blobs.iterdir()):
            if re.fullmatch(r'[a-f0-9]{64}\.[a-z0-9]{2,5}',file.name):z.write(file,'sources/'+file.name)
    return {'projects':len(entries['project']),'path':str(path)}

def import_workspace(store,path):
    """Validate the entire foreign archive before one local metadata transaction."""
    from .storage import ENTITY_KINDS
    from .core import COVERS, identifier, validate_draft, safe_json
    p=Path(path)
    if p.stat().st_size>250*1024*1024:raise ValidationError('This library archive exceeds 250 MB.')
    with zipfile.ZipFile(p) as z:
        members=z.infolist();names=[m.filename for m in members]
        if len(names)!=len(set(names)):raise ValidationError('The library contains duplicate ZIP paths.')
        if any(m.flag_bits&1 for m in members):raise ValidationError('Unlock the library archive before importing.')
        if len(members)>20000 or sum(i.file_size for i in members)>500*1024*1024:raise ValidationError('This library archive is too large after expansion.')
        if 'library.json' not in names:raise ValidationError('No Workshop library was found.')
        if z.getinfo('library.json').file_size>80*1024*1024:raise ValidationError('Library metadata is too large.')
        payload=json.loads(z.read('library.json'))
        if not isinstance(payload,dict) or payload.get('format')!='workshop-library-v1':raise ValidationError('Unsupported library archive version.')
        entities=payload.get('entities',{})
        if not isinstance(entities,dict) or sum(len(v) for v in entities.values() if isinstance(v,list))>20000:raise ValidationError('Invalid library contents.')
        remap={};originals={};files={}
        for kind,items in entities.items():
            if kind not in ENTITY_KINDS or kind in ('settings','milestone') or not isinstance(items,list):raise ValidationError('Unsupported library item list.')
            for item in items:
                if not isinstance(item,dict):raise ValidationError('Invalid library record.')
                key=identifier(item.get('id'))
                if key in remap:raise ValidationError('The library contains duplicate item identifiers.')
                remap[key]=uid();originals[key]=(kind,item)
        for m in members:
            if m.filename=='library.json':continue
            if not re.fullmatch(r'sources/[a-f0-9]{64}\.[a-z0-9]{2,5}',m.filename):raise ValidationError('The archive contains an unexpected file path.')
            if m.file_size>MAX_SOURCE_BYTES:raise ValidationError('An archived source exceeds 60 MB.')
            name=m.filename.split('/')[1];data=z.read(m)
            if not data or hashlib.sha256(data).hexdigest()!=name.split('.')[0]:raise ValidationError('A source file does not match its integrity checksum.')
            files[name]=data
        def ref(value,kind,optional=False):
            if not value and optional:return ''
            if value not in originals or originals[value][0]!=kind:raise ValidationError('A library reference is missing or points to the wrong kind of record.')
            return remap[value]
        def blob(name):
            if name and name not in files:raise ValidationError('An archived source or attachment file is missing.')
            return name
        prepared=[]
        for kind,items in entities.items():
            if kind in ('link','repair','pair'):continue  # foreign note IDs cannot be trusted
            for old in items:
                item=deepcopy(old);oldid=item.pop('id');item.pop('revision',None);item.pop('updated',None)
                if kind=='project':
                    item={'title':text(item.get('title',''),120,'Project title',True)[:108]+' (imported)',
                          'description':text(item.get('description',''),1200,'Project description'),'cover':item.get('cover','botanical'),
                          'archived':bool(item.get('archived',False)),'created':now()}
                    if item['cover'] not in COVERS:raise ValidationError('The library uses an unknown binding.')
                else:
                    item['project_id']=ref(item.get('project_id'),'project')
                    if kind=='source':
                        item['title']=text(item.get('title',''),200,'Source title',True)
                        item['version_id']=ref(item.get('version_id'),'version')
                        if originals[old['version_id']][1].get('source_id')!=oldid:raise ValidationError('The source edition points to another source.')
                        from .network import allowed_source_url
                        item['locator']=allowed_source_url(item.get('locator',''))
                        item['page_count']=integer(item.get('page_count'),1,2000,'Page count')
                    if kind=='version':
                        item['source_id']=ref(item.get('source_id'),'source');item['blob']=blob(item.get('blob',''))
                        item['ordinal']=integer(item.get('ordinal'),1,1000000,'Edition')
                        pages=item.get('pages')
                        if not isinstance(pages,list) or not 1<=len(pages)<=2000:raise ValidationError('Invalid archived source pages.')
                        clean=[];total=0
                        for i,page in enumerate(pages):
                            value=text(page.get('text',''),500000,'Page text');total+=len(value)
                            if total>MAX_TEXT:raise ValidationError('An archived source has too much text.')
                            clean.append({'page':i+1,'text':value,'image':blob(page.get('image','')),'label':text(str(page.get('label',i+1)),80,'Page label')})
                        for original,row in zip(pages,clean):
                            row['notes']=text(original.get('notes',''),500_000,'Speaker notes');total+=len(row['notes'])
                            if total>MAX_TEXT:raise ValidationError('An archived source has too much text and speaker notes.')
                            raw_assets=original.get('assets',[])
                            if not isinstance(raw_assets,list) or len(raw_assets)>100:raise ValidationError('Invalid embedded figure list.')
                            row['assets']=[]
                            for a in raw_assets:
                                if not isinstance(a,dict) or not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|jpeg|webp)',str(a.get('blob',''))):raise ValidationError('Invalid archived figure.')
                                name=blob(a['blob']);validate_image_header(files[name])
                                row['assets'].append({'blob':name,'label':text(a.get('label','Figure'),160,'Figure label')})
                            row['hidden_slide']=bool(original.get('hidden_slide',False))
                        old_meta=item.get('metadata',{});meta={}
                        if old_meta.get('visual_pdf'):
                            if not isinstance(old_meta['visual_pdf'],str) or not old_meta['visual_pdf'].endswith('.pdf'):raise ValidationError('Invalid archived PDF layout.')
                            meta['visual_pdf']=blob(old_meta['visual_pdf'])
                        if old_meta.get('extraction_note'):meta['extraction_note']=text(old_meta['extraction_note'],2000,'Import note')
                        item['pages']=clean;item['metadata']=meta;item['digest']=hashlib.sha256(safe_json(clean).encode()).hexdigest()
                    if kind=='draft':
                        if item.get('source_id'):
                            original_source=item['source_id'];original_version=item.get('version_id')
                            if originals.get(original_version,('',{}))[1].get('source_id')!=original_source:raise ValidationError('A draft points to a mismatched source edition.')
                        item['source_id']=ref(item.get('source_id'),'source',True);item['version_id']=ref(item.get('version_id'),'version',True)
                        item['deck_id']=1;item['model_id']=0;item['mapping']={} # foreign collection IDs are not portable
                        item['status']='draft';item.pop('note_id',None);item['verified']=False
                        item={**item,**validate_draft(item)}
                        for media in item['media']:blob(media['blob'])
                prepared.append((kind,remap[oldid],item))
        # Additive content-addressed files may precede metadata; no existing file is overwritten.
        # A failed metadata transaction leaves at most unreferenced recoverable files, never a partial library.
        for name,data in files.items():store.save_blob(data,name.split('.')[1])
        with store.connection() as db:
            for kind,key,item in prepared:
                db.execute('INSERT INTO entities VALUES(?,?,?,?,?,?)',(kind,key,item.get('project_id',''),1,now(),safe_json(item)))
    store.event('workspace_imported',{'projects':len(entities.get('project',[]))})
    return {'projects':len(entities.get('project',[])),'detached_links':len(entities.get('link',[])),
            'notice':'Foreign note links were detached. Draft deck IDs and field mappings were reset; choose local destinations before approving.'}

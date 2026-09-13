"""Local, non-executing Office/OpenDocument/table importers.

Keeps slide order, notes, tables, and original embedded raster images. This is
structured content extraction, NOT a reconstructed or page-perfect slide render.
No macros, OLE objects, external relationships, or remote resources are executed.
"""
from __future__ import annotations
import csv
from io import StringIO
import posixpath
import re
from .core import ValidationError, MAX_TEXT

A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'a':A,'p':P,'r':R,'w':W}
RASTER=('png','jpg','jpeg','webp')


def resolve_part(base, target):
    # A relationship is a ZIP path, never a filesystem path or network location.
    if not isinstance(target,str) or not target or any(c in target for c in ('\\','\x00',':','?','#','%')):
        raise ValidationError('Unsupported embedded document relationship.')
    if target.startswith('/'):
        part=target.lstrip('/')
    else:
        part=posixpath.normpath(posixpath.join(posixpath.dirname(base),target))
    if part.startswith('../') or part == '..' or part.startswith('/'):
        raise ValidationError('A document relationship points outside its archive.')
    return part


def relationships(z, part, xml):
    rel=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
    if rel not in z.namelist():return {}
    out={}
    for n in xml(z.read(rel)):
        if n.get('TargetMode','').casefold()=='external':continue
        rid=n.get('Id','');target=n.get('Target','');kind=n.get('Type','').rsplit('/',1)[-1]
        if rid and target:
            if rid in out:raise ValidationError('This document repeats a relationship identifier.')
            out[rid]=(resolve_part(part,target),kind)
    return out


def raster_asset(z, path, store, label):
    suffix=path.rsplit('.',1)[-1].lower()
    if suffix not in RASTER:return None
    info=z.getinfo(path)
    if info.file_size>20*1024*1024:raise ValidationError('An embedded image exceeds 20 MB. Optimize the source image before importing.')
    raw=z.read(path)
    from .documents import validate_image_header
    validate_image_header(raw)
    return {'blob':store.save_blob(raw,suffix),'label':str(label)[:160]}


def drawing_text(node):
    return ''.join(t.text or '' for t in node.iter() if t.tag==f'{{{A}}}t').strip()


def slide_parts(root):
    tree=root.find('.//p:spTree',NS)
    if tree is None:return []
    out=[]
    def walk(node):
        # Each paragraph occurs once. Tables retain cell/row separators.
        if node.tag==f'{{{A}}}tbl':
            lines=[]
            for row in node.findall('a:tr',NS):
                lines.append(' | '.join(drawing_text(cell) for cell in row.findall('a:tc',NS)))
            if lines:out.append('\n'.join(lines))
            return
        if node.tag==f'{{{A}}}p':
            value=drawing_text(node)
            if value:out.append(value)
            return
        for child in node:walk(child)
    walk(tree)
    return out


def power_point(z, xml, store, alive=lambda:True):
    part='ppt/presentation.xml'
    if part not in z.namelist():raise ValidationError('The file does not contain a PowerPoint presentation.')
    root=xml(z.read(part));rels=relationships(z,part,xml)
    refs=root.findall('p:sldIdLst/p:sldId',NS)
    if not 1<=len(refs)<=2000:raise ValidationError('Use a PowerPoint presentation containing 1–2,000 slides.')
    size=root.find('p:sldSz',NS)
    pages=[];total=0;skipped=0
    for index,ref in enumerate(refs,1):
        if not alive():raise ValidationError('The profile changed; the import was cancelled.')
        rid=ref.get(f'{{{R}}}id');entry=rels.get(rid)
        if not entry or entry[1]!='slide' or entry[0] not in z.namelist():
            raise ValidationError(f'Slide {index} has a missing or unsupported internal reference.')
        path=entry[0];slide=xml(z.read(path));links=relationships(z,path,xml)
        value='\n\n'.join(slide_parts(slide));notes=[];assets=[];seen=set()
        for shape in slide.findall('.//p:pic',NS):
            blip=shape.find('.//a:blip',NS);desc=shape.find('p:nvPicPr/p:cNvPr',NS)
            image_ref=links.get(blip.get(f'{{{R}}}embed')) if blip is not None else None
            if not image_ref or image_ref[1]!='image':continue
            target=image_ref[0]
            if target in seen:continue
            seen.add(target)
            if target not in z.namelist():raise ValidationError(f'Slide {index} has a missing embedded image.')
            label=(desc.get('descr') or desc.get('name')) if desc is not None else f'Figure {len(assets)+1}'
            asset=raster_asset(z,target,store,label or 'Slide figure')
            if asset:assets.append(asset)
            else:skipped+=1
            if len(assets)>100:raise ValidationError('One slide contains more than 100 raster images. Split or simplify it first.')
        for target,kind in links.values():
            if kind!='notesSlide' or target not in z.namelist():continue
            note_root=xml(z.read(target))
            for shape in note_root.findall('.//p:sp',NS):
                ph=shape.find('.//p:ph',NS)
                if ph is not None and ph.get('type') in ('sldNum','hdr','ftr','dt','sldImg'):continue
                for paragraph in shape.findall('.//a:p',NS):
                    t=drawing_text(paragraph)
                    if t:notes.append(t)
        note_text='\n'.join(notes)
        total+=len(value)+len(note_text)
        if total>MAX_TEXT:raise ValidationError('Extracted slide text and notes exceed the import limit. Split this presentation.')
        pages.append({'text':value,'notes':note_text,'assets':assets,'label':f'Slide {index}',
                      'hidden_slide':slide.get('show')=='0'})
    return pages,{'slide_order':'presentation relationships','includes_notes':any(p['notes'] for p in pages),
                  'embedded_images':sum(len(p['assets']) for p in pages),'unsupported_images':skipped,
                  'slide_size':dict(size.attrib) if size is not None else {},
                  'extraction_note':'Slide order, text, table cells, speaker notes and embedded PNG/JPEG/WebP figures are retained. Figures are not full-slide replicas; charts, animations, cropping and layout remain in the original. Attach a matching PDF for exact exported slide pages.'}


def word_document(z, xml, store):
    part='word/document.xml'
    if part not in z.namelist():raise ValidationError('The file is not a Word document.')
    root=xml(z.read(part));body=root.find('w:body',NS);out=[]
    if body is None:raise ValidationError('The Word document has no readable body.')
    for n in body:
        if n.tag==f'{{{W}}}tbl':
            for row in n.findall('w:tr',NS):
                out.append(' | '.join(' '.join(t.text or '' for t in c.findall('.//w:t',NS)) for c in row.findall('w:tc',NS)))
        else:
            value=''.join(t.text or '' for t in n.findall('.//w:t',NS))
            if value:out.append(value)
    assets=[];seen=set();links=relationships(z,part,xml)
    for blip in root.findall('.//a:blip',NS):
        link=links.get(blip.get(f'{{{R}}}embed'))
        if not link or link[1]!='image' or link[0] in seen:continue
        seen.add(link[0]);asset=raster_asset(z,link[0],store,f'Document figure {len(assets)+1}')
        if asset:assets.append(asset)
        if len(assets)>100:raise ValidationError('Split a document with more than 100 embedded figures.')
    value='\n\n'.join(out)
    if len(value)>MAX_TEXT:raise ValidationError('This document contains too much text.')
    # Sections, not invented print page numbers. Keep each inside Store's page cap.
    pages=[];chunks=[];length=0
    for line in out:
        if len(line)>450_000:raise ValidationError('One document block is too large; split the source.')
        if length+len(line)>450_000 and chunks:
            pages.append({'text':'\n\n'.join(chunks),'label':f'Section {len(pages)+1}'});chunks=[];length=0
        chunks.append(line);length+=len(line)+2
    if chunks or not pages:pages.append({'text':'\n\n'.join(chunks),'label':f'Section {len(pages)+1}'})
    pages[0]['assets']=assets
    return pages,{'extraction_note':'Text and table rows follow document order. Sections are not printed pages. Embedded figures are available below the text; exact typography and layout remain in the original document.'}


def open_document(z, xml, kind, store):
    if 'content.xml' not in z.namelist():raise ValidationError('No OpenDocument content was found.')
    n={'text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0','draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
       'table':'urn:oasis:names:tc:opendocument:xmlns:table:1.0','xlink':'http://www.w3.org/1999/xlink'}
    root=xml(z.read('content.xml'));sections=root.findall('.//draw:page',n) if kind=='odp' else [root]
    if not 1<=len(sections)<=2000:raise ValidationError('Use an OpenDocument source with 1–2,000 sections.')
    pages=[]
    for section in sections:
        paras=[''.join(p.itertext()) for p in section.iter() if p.tag in (f'{{{n["text"]}}}p',f'{{{n["text"]}}}h')]
        assets=[];seen=set()
        for img in section.findall('.//draw:image',n):
            href=img.get(f'{{{n["xlink"]}}}href','')
            if not href or re.match(r'^[a-z]+:',href,re.I):continue
            path=resolve_part('content.xml',href)
            if path in seen or path not in z.namelist():continue
            seen.add(path);asset=raster_asset(z,path,store,f'Figure {len(assets)+1}')
            if asset:assets.append(asset)
            if len(assets)>100:raise ValidationError('This section has too many embedded figures.')
        value='\n\n'.join(paras)
        if len(value)>500_000:raise ValidationError('Split this source into smaller sections.')
        pages.append({'text':value,'assets':assets,'label':('Slide ' if kind=='odp' else 'Section ')+str(len(pages)+1)})
    return pages,{'extraction_note':'OpenDocument text and embedded raster figures, not a visual layout replica. Check the original for tables, equations and diagrams.'}


def delimited_text(data, suffix):
    try:value=data.decode('utf-8-sig')
    except UnicodeDecodeError:raise ValidationError('Save this table as UTF-8 CSV or TSV first.') from None
    rows=[];total=0
    for row in csv.reader(StringIO(value),delimiter='\t' if suffix=='tsv' else ','):
        if len(row)>200:raise ValidationError('Use source tables with at most 200 columns.')
        total+=sum(len(c) for c in row)
        if len(rows)>=20_000 or total>MAX_TEXT:raise ValidationError('This source table is too large. Split it into smaller files.')
        rows.append(row)
    if not rows:raise ValidationError('The table is empty.')
    pages=[]
    for i in range(0,len(rows),80):
        section=rows[i:i+80]
        pages.append({'text':'\n'.join(' | '.join(c.replace('\n',' / ') for c in row) for row in section),
                      'label':f'Rows {i+1}–{min(i+80,len(rows))}'})
    return pages,{'extraction_note':'Imported as reference-table text, not automatically generated flashcards. Separators preserve column order; quoted multiline values are shown with / separators.'}

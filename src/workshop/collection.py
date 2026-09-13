"""Anki collection adapter. Reads use SELECT/public APIs; writes use native note operations.

No direct SQL writes, scheduler ratings, due dates, template monkeypatching, or
review-history alterations are part of Workshop.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from copy import deepcopy
from html import escape
import hashlib
import re
import time
from typing import Any
from .core import (MAX_BATCH, ConflictError, ValidationError, clozes, escaped_field,
                   fingerprint, integer, keywords, lint_card, normalized, plain,
                   quote_status, rank_matches, safe_anki_literal, text, uid, validate_draft)

RECALL_NAME='Workshop · Recall'
CLOZE_NAME='Workshop · Cloze'
FIELDS=['Front','Back','Context','Source','WorkshopID']
CARD_CSS='''
.card{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:23px;line-height:1.7;text-align:left;color:#273932;background:#f8f7f2;margin:0;padding:clamp(20px,5vw,60px)}
.ws-card{max-width:800px;margin:auto}.ws-eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#697d72;margin-bottom:28px}.ws-question{font-weight:560;overflow-wrap:anywhere}.ws-answer{margin-top:26px;padding-top:24px;border-top:1px solid #cfd8d0;overflow-wrap:anywhere}.ws-context{font-size:17px;line-height:1.75;margin-top:25px;color:#58705f}.ws-source{font-size:12px;margin-top:38px;color:#6c7e74}.ws-source summary{cursor:pointer;padding:7px 0}.ws-source blockquote{margin:10px 0;padding-left:13px;border-left:2px solid #b5cbbd}.ws-card img{max-width:100%;height:auto}.cloze{font-weight:700;color:#386e54}.nightMode.card,.night_mode.card{color:#ecefe8;background:#202722}.nightMode .ws-context,.night_mode .ws-context{color:#b8c9b9}.nightMode .ws-source,.night_mode .ws-source{color:#aebeb4}.nightMode .cloze,.night_mode .cloze{color:#b9d8ae}.nightMode .ws-answer{border-color:#475348}
'''
FRONT='<section class="ws-card"><div class="ws-eyebrow">Recall, in your own words</div><div class="ws-question">{{Front}}</div></section>'
BACK='{{FrontSide}}<section class="ws-card"><div class="ws-answer">{{Back}}</div>{{#Context}}<div class="ws-context">{{Context}}</div>{{/Context}}{{#Source}}<details class="ws-source"><summary>Source & context</summary>{{Source}}</details>{{/Source}}</section>'
CFRONT=FRONT.replace('{{Front}}','{{cloze:Front}}')
CBACK='<section class="ws-card"><div class="ws-eyebrow">Recall, in your own words</div><div class="ws-question">{{cloze:Front}}</div>{{#Back}}<div class="ws-answer">{{Back}}</div>{{/Back}}{{#Context}}<div class="ws-context">{{Context}}</div>{{/Context}}{{#Source}}<details class="ws-source"><summary>Source & context</summary>{{Source}}</details>{{/Source}}</section>'

@dataclass
class OperationResult:
    changes: Any
    data: dict


def catalog(col):
    decks=[{'id':int(d.id),'name':str(d.name)} for d in col.decks.all_names_and_ids(include_filtered=False)]
    models=[]
    for entry in col.models.all_names_and_ids():
        m=col.models.get(entry.id)
        if not m:continue
        models.append({'id':int(m['id']),'name':m['name'],'fields':[f['name'] for f in m['flds']],
                       'type':m['type'],'templates':len(m['tmpls']),'occlusion':m.get('originalStockKind')==6})
    return {'decks':decks,'models':models,'note_count':int(col.note_count())}


def protected(note,settings):
    m=note.note_type();names=list(note.keys())
    tagged=set(note.tags)
    tag_rules=settings.get('protected_tags',[])
    managed=any(any(t.casefold()==r.casefold() or t.casefold().startswith(r.casefold()+'::') for t in tagged) for r in tag_rules)
    managed=managed or any('ankihub' in f.casefold() or 'ankicollab' in f.casefold() for f in names)
    internal=m.get('originalStockKind')==6 or 'occlusion' in m.get('name','').casefold()
    return {'managed':managed,'complex':internal,'fields':[f for f in names if f in settings.get('protected_fields',[])],
            'reason':'Managed or protected note: use the native editor or upstream suggestion workflow.' if managed else 'Image occlusion: preserve masks with Anki’s native editor.' if internal else ''}


def note_data(col,nid:int,settings):
    nid=integer(nid,1,2**53-1,'Note ID')
    note=col.get_note(nid)
    fields=dict(zip(note.keys(),note.fields));cards=list(col.card_ids_of_note(note.id))
    issues=lint_card(plain(note.fields[0]) if note.fields else '',plain(note.fields[1]) if len(note.fields)>1 else '',
                     'cloze' if note.note_type()['type']==1 else 'question')
    image_only=any(re.search(r'<img\b|\[sound:',f,re.I) for f in note.fields)
    if image_only:issues=[i for i in issues if i['code'] not in ('empty_front','empty_back','missing_context')]
    media=[]
    root=Path(col.media.dir()).resolve()
    for field in note.fields:
        try:names=col.media.files_in_str(note.mid,field)
        except Exception:names=re.findall(r'<img[^>]+src=[\"\']([^\"\']+)|\[sound:([^\]]+)\]',field)
        for raw in names:
            name=next((x for x in raw if x),'') if isinstance(raw,tuple) else str(raw)
            path=(root/name).resolve()
            external='://' in name or path.parent!=root
            exists=(not external and path.is_file())
            media.append({'name':name,'exists':exists,'external':external})
            if not exists and not external:issues.append({'code':'missing_media','severity':'error','message':'Missing media: '+name})
    stats=col.db.first('SELECT COUNT(*),COALESCE(SUM(lapses),0),COALESCE(SUM(reps),0) FROM cards WHERE nid=?',nid)
    return {'id':nid,'fields':fields,'front':plain(note.fields[0]) if note.fields else '',
            'text':'\n'.join(plain(x) for x in note.fields),'model':note.note_type()['name'],'model_id':note.mid,
            'modified':note.mod,'tags':list(note.tags),'cards':list(map(int,cards)),
            'fingerprint':fingerprint(note.fields,note.tags),'protection':protected(note,settings),'issues':issues,
            'media':media,'lapses':int(stats[1] or 0),'reviews':int(stats[2] or 0)}


def search_notes(col,query:str,settings,mode='words',deck_id:int=0,limit=60,offset=0):
    query=text(query,2000,'Search query')
    limit=integer(limit,1,200,'Result limit');offset=integer(offset,0,2000000,'Result offset')
    if mode=='anki':search=query
    elif query:
        terms=keywords(query,8)
        search=' OR '.join(safe_anki_literal(t) for t in terms) if terms else safe_anki_literal(query)
        search=f'({search})'
    else:search=''
    if deck_id:
        deck=col.decks.get(integer(deck_id,1,2**53-1,'Deck ID'),default=False)
        if not deck:raise ValidationError('That deck no longer exists.')
        search+=' deck:'+safe_anki_literal(deck['name'])
    ids=list(col.find_notes(search))
    # Every result in a bounded ranking window remains reachable. The cursor
    # advances through the ranked window, not past 340 undisplayed candidates.
    if mode=='words' and query:
        window_start=(offset//400)*400;within=offset-window_start
        chunk=ids[window_start:window_start+400]
        ranked=rank_matches(query,[note_data(col,int(n),settings) for n in chunk],400)
        rows=ranked[within:within+limit]
        if within+len(rows)<len(ranked):
            next_offset=offset+len(rows);more=True
        else:
            next_offset=window_start+len(chunk);more=next_offset<len(ids)
    else:
        chunk=ids[offset:offset+limit]
        rows=[{**note_data(col,int(n),settings),'why':'Matched Anki search' if query else 'Collection note','match':1} for n in chunk]
        next_offset=offset+len(chunk);more=next_offset<len(ids)
    return {'results':rows,'total_matches':len(ids),'query':search,'candidate_limit':len(chunk),
            'has_more':more,'next_offset':next_offset,
            'note':'Similar wording is not proof of duplicate meaning. Candidate windows are ranked locally; every window can be paged.'}


def scan_notes(col,settings,cursor=0,size=250):
    cursor=integer(cursor,0,2**53-1,'Scan cursor');size=integer(size,1,500,'Scan size')
    ids=col.db.list('SELECT id FROM notes WHERE id>? ORDER BY id LIMIT ?',cursor,size+1)
    found=[];indexed=[]
    for nid in ids[:size]:
        row=note_data(col,int(nid),settings);indexed.append(row)
        if row['issues'] or row['lapses']>=4:
            suggestions=list(row['issues'])
            if row['lapses']>=4:suggestions.append({'code':'repeated_lapses','severity':'suggestion','message':f'{row["lapses"]} recorded lapses. Check wording, prerequisites, or confusing alternatives; the cause is not known.'})
            found.append({**row,'issues':suggestions})
    return {'items':found,'scanned':min(size,len(ids)),'next_cursor':int(ids[size-1]) if len(ids)>size else None,'indexed':indexed,'complete':len(ids)<=size}


def ensure_model(col,kind):
    name=CLOZE_NAME if kind=='cloze' else RECALL_NAME
    existing=col.models.by_name(name)
    if existing:
        if [f['name'] for f in existing['flds']]!=FIELDS or existing['type']!=(1 if kind=='cloze' else 0):
            raise ValidationError(f'The “{name}” note type was customized. Restore its original field structure or map to another note type; Workshop will not overwrite it.')
        return existing
    model=col.models.new(name);model['type']=1 if kind=='cloze' else 0
    for field in FIELDS:col.models.add_field(model,col.models.new_field(field))
    template=col.models.new_template('Recall');template['qfmt']=CFRONT if kind=='cloze' else FRONT;template['afmt']=CBACK if kind=='cloze' else BACK
    col.models.add_template(model,template);model['css']=CARD_CSS
    col.models.add(model)
    return model


def source_html(store,draft):
    if not draft.get('source_id'):return ''
    source=store.get('source',draft['source_id']);version=store.get('version',draft['version_id'])
    body=f'<strong>{escape(source["title"])}</strong> · {escape(str(draft["page"]))} · version {version["ordinal"]}'
    if source.get('locator'):
        from .network import allowed_source_url
        url=allowed_source_url(source['locator']);body+=f'<br><a href="{escape(url,quote=True)}">Original source</a>'
    if draft.get('quote'):body+='<blockquote>'+escaped_field(draft['quote'])+'</blockquote>'
    body+='<br>Source-linked; approved by the author. A source link is not a correctness certification.'
    return body


def resolve_model(col,draft,create=False):
    if draft['kind']=='occlusion':
        from .masks import native_model
        return native_model(col,create)
    if not draft.get('model_id'):
        if create:return ensure_model(col,draft['kind'])
        return col.models.by_name(CLOZE_NAME if draft['kind']=='cloze' else RECALL_NAME)
    model=col.models.get(draft['model_id'])
    if not model:raise ValidationError('The selected note type no longer exists.')
    if model.get('originalStockKind')==6 or 'occlusion' in model['name'].casefold():raise ValidationError('Use the native image-occlusion handoff instead of field mapping masks.')
    fields={f['name'] for f in model['flds']};mapping=draft.get('mapping',{})
    if not mapping.get('front') or mapping['front'] not in fields:raise ValidationError('Choose a destination question field.')
    if draft['kind']!='cloze' and (not mapping.get('back') or mapping['back'] not in fields):raise ValidationError('Choose a destination answer field.')
    if len(set(mapping.values()))!=len(mapping):raise ValidationError('Map each content role to a different field.')
    if any(f not in fields for f in mapping.values()):raise ValidationError('A mapped field no longer exists.')
    if bool(model['type']==1)!=bool(draft['kind']=='cloze'):raise ValidationError('The card style and note type must agree about cloze deletions.')
    return model


def preflight(col,store,draft_ids):
    if not isinstance(draft_ids,list) or not 1<=len(draft_ids)<=MAX_BATCH or len(set(draft_ids))!=len(draft_ids):raise ValidationError('Choose 1–100 different drafts.')
    settings=store.settings();items=[];seen={}
    for did in draft_ids:
        stored=store.get('draft',did)
        if stored.get('status')=='committed':raise ValidationError('One selected draft has already been added. Refresh the workspace.')
        d={**stored,**validate_draft(stored,final=True)}
        deck=col.decks.get(d['deck_id'],default=False)
        if not deck or deck.get('dyn'):raise ValidationError('Choose a normal, existing destination deck.')
        model=resolve_model(col,d)
        if model:
            if any('ankihub' in f['name'].casefold() or 'ankicollab' in f['name'].casefold() for f in model['flds']):raise ValidationError('Use the native editor for externally managed note types.')
            protected_fields=set(settings.get('protected_fields',[]))
            if protected_fields&set(d.get('mapping',{}).values()):raise ValidationError('A destination field is protected in Workshop Settings.')
        for media in d['media']:store.blob_path(media['blob'])
        # Deterministic marker reconciliation prevents duplicate adds after interrupted bookkeeping.
        existing=col.find_notes('tag:wsd_'+d['id'])
        exact=[];duplicate_scan_partial=False
        if not existing and d['kind']!='occlusion':
            terms=keywords(d['front'],6)
            query=' OR '.join(safe_anki_literal(x) for x in terms)
            candidates=list(col.find_notes('('+query+')')) if query else []
            if len(candidates)>2000:
                # Bound a potentially broad lexical scan and disclose it in the approval preview.
                duplicate_scan_partial=True;candidates=candidates[:2000]
            for nid in candidates:
                n=col.get_note(int(nid))
                if normalized(n.fields[0])==normalized(d['front']):exact.append(int(nid))
        key=fingerprint([str(d.get('masks')),str(d['media'])]) if d['kind']=='occlusion' else normalized(d['front'])
        duplicate_batch=seen.get(key);seen[key]=d['id']
        count=d['card_count'] if d['kind'] in ('cloze','occlusion') or not model else len(model['tmpls'])
        issues=list(d['issues'])
        if d.get('source_id'):
            version=store.get('version',d['version_id'])
            if not quote_status(d['quote'],version['pages'][d['page']-1]['text']+'\n'+version['pages'][d['page']-1].get('notes','')):
                issues.append({'code':'source_quote','severity':'suggestion','message':'The selected passage is not an exact match to extracted source text. Check the original page.'})
            if store.get('source',d['source_id'])['version_id']!=d['version_id']:
                issues.append({'code':'source_old','severity':'suggestion','message':'This draft uses an older source version.'})
        items.append({'draft':d,'deck_name':deck['name'],'model_name':model['name'] if model else 'Native Image Occlusion' if d['kind']=='occlusion' else CLOZE_NAME if d['kind']=='cloze' else RECALL_NAME,
                      'estimated_cards':count,'exact_duplicates':exact,'batch_duplicate':duplicate_batch,'existing_marker':list(map(int,existing)),
                      'issues':issues,'duplicate_scan_partial':duplicate_scan_partial,'conditional_templates':bool(model and len(model['tmpls'])>1)})
    if sum(i['estimated_cards'] for i in items)>500:raise ValidationError('This batch would create more than 500 cards. Approve a smaller set of drafts.')
    return {'items':items,'total_cards':sum(i['estimated_cards'] for i in items),'notes':len(items),
            'notice':'This adds new notes; it does not answer cards or mark them learned. Conditional templates may create fewer cards. Media files are not removed by Anki undo.'}


def commit(col,store,prepared,approved_duplicates,alive=lambda:True):
    """Single native add_notes call after all validation. File copies are additive only."""
    from anki.collection import AddNoteRequest,OpChanges
    ids=[i['draft']['id'] for i in prepared['items']]
    fresh=preflight(col,store,ids)
    old={i['draft']['id']:i['draft'] for i in prepared['items']}
    for row in fresh['items']:
        d=row['draft']
        if d['revision']!=old[d['id']]['revision']:raise ConflictError('A draft changed after the approval preview. Preview the batch again.')
        if (row['exact_duplicates'] or row['batch_duplicate']) and d['id'] not in approved_duplicates:
            raise ValidationError('Review exact-wording duplicates and explicitly allow them before adding.')
    if not alive():raise ValidationError('The profile or collection changed. Nothing was added.')
    requests=[];mapping=[];reconciled=[];created_models=[]
    undo=col.add_custom_undo_entry('Workshop: add approved cards')
    try:
        for row in fresh['items']:
            d=row['draft']
            if row['existing_marker']:
                reconciled.append((d,row['existing_marker'][0]));continue
            model=resolve_model(col,d,create=True)
            note=col.new_note(model)
            if d['kind']=='occlusion':
                from .masks import fill_note
                fill_note(col,store,note,d,source_html(store,d))
            else:
                fm=d['mapping'] if d.get('model_id') else {'front':'Front','back':'Back','context':'Context','source':'Source'}
                htmls={k:escaped_field(d.get(k,'')) for k in ('front','back','context')};htmls['source']=source_html(store,d)
                for item in d['media']:
                    filename=col.media.add_file(str(store.blob_path(item['blob'])))
                    safe=escape(filename,quote=True)
                    element=f'<img src="{safe}" alt="{escape(item["alt"],quote=True)}">' if not filename.lower().endswith(('.mp3','.wav','.ogg')) else f'[sound:{filename}]'
                    htmls[item['side']]+='<br>'+element
                for role,field in fm.items():note[field]=htmls[role]
            if 'WorkshopID' in note.keys():note['WorkshopID']=d['id']
            note.tags=d['tags']+['Workshop','wsd_'+d['id'],'wsp_'+d['project_id']]
            requests.append(AddNoteRequest(note=note,deck_id=d['deck_id']));mapping.append(d)
        if requests:col.add_notes(requests)
        changes=col.merge_undo_entries(undo)
    except Exception:
        # Don't blindly undo if hooks/external ops might own the stack. Native batch itself is atomic.
        try:col.merge_undo_entries(undo)
        except Exception:pass
        raise
    linked=[];warnings=[]
    for d,nid in reconciled+[(d,int(r.note.id)) for d,r in zip(mapping,requests)]:
        try:
            n=col.get_note(nid)
            store.link_note(nid,d['project_id'],d['source_id'],d['version_id'],d['page'],d['quote'],d['id'],fingerprint(n.fields,n.tags))
            linked.append(nid)
        except Exception:
            warnings.append('Cards were added, but local source-link bookkeeping could not finish. Refresh/retry this same draft to recover via its unique marker; do not create another copy.')
    store.event('cards_committed',{'notes':len(requests),'reconciled':len(reconciled)})
    return OperationResult(changes,{'note_ids':linked,'added':len(requests),'reconciled':len(reconciled),'warnings':warnings})


def edit_preview(col,store,nid,proposed,expected):
    current=note_data(col,nid,store.settings())
    if current['fingerprint']!=expected:raise ConflictError('The note changed in Anki. Reload it before preparing this edit.')
    protection=current['protection']
    if protection['managed'] or protection['complex']:raise ValidationError(protection['reason'])
    if not isinstance(proposed,dict) or not proposed or len(proposed)>30:raise ValidationError('Choose at least one field to edit.')
    changes={}
    for field,value in proposed.items():
        if field not in current['fields'] or field in protection['fields'] or field in ('WorkshopID',):raise ValidationError('That field is missing or protected.')
        value=text(value,80000,'Field HTML')
        old=current['fields'][field]
        # Preserve Anki card structure. Structural cloze edits belong in its native editor.
        if clozes(old)!=clozes(value):raise ValidationError('This changes cloze-card structure. Use Anki’s native editor, which can show the card-generation consequences.')
        if field==list(current['fields'])[0] and not plain(value) and not re.search(r'<img|\[sound:',value):raise ValidationError('The question field cannot become empty.')
        if value!=old:changes[field]={'before':old,'after':value}
    if not changes:raise ValidationError('There are no field changes to apply.')
    return {'note_id':nid,'fingerprint':expected,'changes':changes,'summary':current['front'],'model':current['model']}


def apply_edit(col,store,prepared,alive=lambda:True):
    fresh=edit_preview(col,store,prepared['note_id'],{f:c['after'] for f,c in prepared['changes'].items()},prepared['fingerprint'])
    if not alive():raise ValidationError('The profile changed; no edits were applied.')
    n=col.get_note(prepared['note_id'])
    for field,c in fresh['changes'].items():n[field]=c['after']
    changes=col.update_note(n)
    store.event('note_edited',{'note_id':int(n.id),'fields':list(fresh['changes'])})
    return OperationResult(changes,{'note_id':int(n.id),'fields':list(fresh['changes'])})


def batch_preview(col,store,payload):
    ids=payload.get('note_ids',[])
    if not isinstance(ids,list) or not 1<=len(ids)<=200 or len(set(ids))!=len(ids):raise ValidationError('Select 1–200 unique notes for a bulk operation.')
    operation=payload.get('operation','replace')
    if operation not in ('replace','add_tag','remove_tag'):raise ValidationError('Choose a supported bulk action.')
    find=text(payload.get('find',''),1000,'Find text',True)
    replace=text(payload.get('replace',''),2000,'Replacement')
    field=text(payload.get('field',''),100,'Field')
    if operation!='replace':
        from .core import tags
        find=tags([find])[0]
    items=[]
    for nid in ids:
        note=col.get_note(integer(nid,1,2**53-1,'Note ID'));view=note_data(col,int(nid),store.settings())
        if view['protection']['managed'] or view['protection']['complex']:raise ValidationError('This selection includes a protected or occlusion note. Remove it from the batch or use its native editor.')
        changes={};newtags=list(note.tags)
        if operation=='replace':
            if field not in view['fields'] or field in view['protection']['fields'] or field=='WorkshopID':raise ValidationError('Every selected note must have the same editable target field.')
            old=view['fields'][field];new=old.replace(find,replace)
            if old!=new:
                checked=edit_preview(col,store,int(nid),{field:new},view['fingerprint']);changes=checked['changes']
        elif operation=='add_tag':
            if find not in newtags:newtags.append(find)
        else:newtags=[t for t in newtags if t!=find]
        if changes or newtags!=note.tags:items.append({'note_id':int(nid),'fingerprint':view['fingerprint'],'changes':changes,'tags_before':list(note.tags),'tags_after':newtags,'summary':view['front']})
    if not items:raise ValidationError('This operation would not change any of the selected notes.')
    return {'items':items,'operation':operation,'find':find,'replace':replace,'field':field}


def apply_batch(col,store,prepared,alive=lambda:True):
    notes=[]
    for item in prepared['items']:
        n=col.get_note(item['note_id'])
        if fingerprint(n.fields,n.tags)!=item['fingerprint']:raise ConflictError('A selected note changed. Refresh the entire bulk preview before applying it.')
        pr=protected(n,store.settings())
        if pr['managed'] or pr['complex'] or set(item['changes'])&set(pr['fields']):raise ValidationError('A selected note or field is now protected.')
        for field,change in item['changes'].items():n[field]=change['after']
        n.tags=item['tags_after'];notes.append(n)
    if not alive():raise ValidationError('The profile changed; the batch was not applied.')
    changes=col.update_notes(notes)
    store.event('batch_edited',{'notes':len(notes),'operation':prepared['operation']})
    return OperationResult(changes,{'updated':len(notes),'note_ids':[int(n.id) for n in notes]})


def media_catalog(col,query='',limit=120,offset=0):
    root=Path(col.media.dir()).resolve();query=text(query,200,'Media search').casefold();found=[]
    limit=integer(limit,1,200,'Media result limit');offset=integer(offset,0,2000000,'Media offset')
    # Native media API remains the source for writes. This is a read-only directory view.
    candidates=sorted((p for p in root.iterdir() if p.is_file() and p.resolve().parent==root and p.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.mp3','.wav','.ogg') and query in p.name.casefold()),key=lambda p:p.name.casefold())
    for p in candidates[offset:offset+limit]:found.append({'name':p.name,'bytes':p.stat().st_size,'kind':'audio' if p.suffix.lower() in ('.mp3','.wav','.ogg') else 'image'})
    return {'items':found,'total':len(candidates),'offset':offset,'has_more':offset+limit<len(candidates)}


def media_references(col,name):
    name=text(name,250,'Media filename',True)
    if Path(name).name!=name:raise ValidationError('Invalid media filename.')
    ids=col.find_notes(safe_anki_literal(name))
    actual=[]
    for nid in ids:
        n=col.get_note(int(nid))
        if any(name in col.media.files_in_str(n.mid,f) for f in n.fields):actual.append(int(nid))
    return {'note_ids':actual,'count':len(actual)}

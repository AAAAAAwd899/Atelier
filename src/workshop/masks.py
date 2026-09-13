"""Normalized rectangular occlusions published as Anki's native IO note format.

Draft IDs are local authoring identities. Question-group numbers become native
cloze ordinals; existing collection-note editing belongs to the owning editor.
"""
from __future__ import annotations
from html import escape
import math
from .core import ValidationError, integer, identifier, escaped_field

MAX_MASKS=1000
MAX_QUESTIONS=500


def validate_masks(raw, final=False):
    if not isinstance(raw,list) or len(raw)>MAX_MASKS:
        raise ValidationError('Use at most 1,000 masks on one image.')
    out=[];ids=set()
    for item in raw:
        if not isinstance(item,dict):raise ValidationError('Invalid mask. Reopen the mask editor.')
        key=identifier(item.get('id'),'Mask identity')
        if key in ids:raise ValidationError('Each mask needs its own identity.')
        ids.add(key)
        group=integer(item.get('group'),1,MAX_QUESTIONS,'Question group')
        coords={}
        for name in ('x','y','w','h'):
            val=item.get(name)
            if isinstance(val,bool):raise ValidationError('Mask coordinates must be numeric.')
            try:val=float(val)
            except (ValueError,TypeError,OverflowError):raise ValidationError('Invalid mask coordinates.') from None
            if not math.isfinite(val) or not 0<=val<=1:raise ValidationError('A mask lies outside the image.')
            coords[name]=round(val,7)
        if coords['w']<.0005 or coords['h']<.0005:raise ValidationError('A mask is too small. Draw a visible rectangle.')
        if coords['x']+coords['w']>1.000001 or coords['y']+coords['h']>1.000001:
            raise ValidationError('Keep masks completely inside the image.')
        out.append({'id':key,'group':group,**coords})
    if final and not out:raise ValidationError('Draw at least one mask before approving this image.')
    return out


def question_count(masks):
    return len({m['group'] for m in masks})


def serialize(masks, hide_others=True):
    if type(hide_others) is not bool:raise ValidationError('Choose whether other answers stay covered.')
    rows=validate_masks(masks,final=True)
    def number(value):return format(value,'.7f').rstrip('0').rstrip('.') or '0'
    return ''.join('{{c'+str(m['group'])+'::image-occlusion:rect:'+':'.join(
        name+'='+number(m[key]) for name,key in (('left','x'),('top','y'),('width','w'),('height','h')))
        +(':oi=1' if hide_others else '')+'}}<br>' for m in rows)


def native_model(col, create=False):
    def find():
        for entry in col.models.all_names_and_ids():
            model=col.models.get(entry.id)
            if model and model.get('originalStockKind')==6:return model
        return None
    model=find()
    if model or not create:return model
    backend=getattr(col,'_backend',None)
    add=getattr(backend,'add_image_occlusion_notetype',None)
    if not callable(add):raise ValidationError('This Anki version does not expose native image occlusion. Use Anki 25.09+ or its own Add editor.')
    add()
    clear=getattr(col.models,'clear_cache',None)
    if callable(clear):clear()
    model=find()
    if model is None:raise ValidationError('Anki did not provide an image-occlusion note type; no fallback format was invented.')
    return model


def fill_note(col,store,note,draft,source):
    """Fill exactly the native IO fields; keep Anki's templates and runtime."""
    backend=getattr(col,'_backend',None)
    get_fields=getattr(backend,'get_image_occlusion_fields',None)
    if not callable(get_fields):raise ValidationError('Native image-occlusion field metadata is unavailable.')
    indexes=get_fields(notetype_id=note.mid)
    indexes=getattr(indexes,'fields',indexes)
    fields={key:int(getattr(indexes,key)) for key in ('occlusions','image','header','back_extra')}
    if len(set(fields.values()))!=4 or any(i<0 or i>=len(note.fields) for i in fields.values()):
        raise ValidationError('Anki returned an unsupported image-occlusion field layout.')
    images=[m for m in draft['media'] if m['side']=='front']
    if len(images)!=1 or not images[0]['blob'].endswith(('.png','.jpg','.jpeg','.webp')):
        raise ValidationError('A masked question needs one image on its question side.')
    filename=col.media.add_file(str(store.blob_path(images[0]['blob'])))
    note.fields[fields['occlusions']]=serialize(draft['masks'],draft['hide_others'])
    note.fields[fields['image']]=f'<img src="{escape(filename,quote=True)}">'
    note.fields[fields['header']]=escaped_field(draft['front'])
    extra='<br><br>'.join(escaped_field(draft[k]) for k in ('back','context') if draft.get(k))
    if source:extra+=('<br><br>' if extra else '')+source
    for item in draft['media']:
        if item['side']!='back':continue
        fname=col.media.add_file(str(store.blob_path(item['blob'])))
        extra+='<br>'+ (f'[sound:{fname}]' if fname.endswith(('.mp3','.wav','.ogg')) else f'<img src="{escape(fname,quote=True)}">')
    note.fields[fields['back_extra']]=extra

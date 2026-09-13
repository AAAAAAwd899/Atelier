"""Presentation-independent rules for Workshop. No Anki writes, Qt, or network."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher, unified_diff
from html import escape, unescape
from html.parser import HTMLParser
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping
from uuid import uuid4

VERSION = '1.1.0-rc.1'
PACKAGE = 'daedalus_workshop'
SCHEMA = 1
MAX_SOURCE_BYTES = 60 * 1024 * 1024
MAX_TEXT = 6_000_000
MAX_FIELD = 40_000
MAX_BATCH = 100
COVERS = ('botanical', 'celestial', 'cartography', 'architect', 'ocean', 'manuscript')
THEMES = ('atelier', 'night', 'paper', 'forest')
KINDS = ('question', 'cloze', 'compare', 'sequence', 'application', 'image', 'occlusion')
STOP = frozenset('a an the and or to of in on at by with for is are was were be this that from as it its'.split())

class ValidationError(ValueError):
    pass

class ConflictError(ValidationError):
    pass

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def uid() -> str:
    return uuid4().hex

def identifier(value: Any, label: str = 'Identifier') -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{32}', value):
        raise ValidationError(f'{label} is invalid. Reopen the item and try again.')
    return value

def integer(value: Any, lo: int, hi: int, label: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f'{label} must be a whole number.')
    try:
        x = int(value)
        if float(value) != x or not lo <= x <= hi:
            raise ValueError
        return x
    except (ValueError, TypeError, OverflowError):
        raise ValidationError(f'{label} must be from {lo:,} to {hi:,}.') from None

def text(value: Any, maximum: int, label: str, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValidationError(f'{label} must be text.')
    value = value.replace('\x00', '').strip()
    if len(value) > maximum or (required and not value):
        raise ValidationError(f'{label} must contain {"1" if required else "0"}–{maximum:,} characters.')
    return value

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
        if tag in ('br', 'p', 'div', 'li', 'tr', 'h1','h2','h3'): self.parts.append('\n')
        if tag == 'img':
            alt = dict(attrs).get('alt', '')
            if alt: self.parts.append(' ' + alt + ' ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1)
        if tag in ('p','div','li','tr'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def plain(value: str) -> str:
    p = PlainText()
    try: p.feed(value)
    except Exception: return re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'[ \t]+', ' ', ''.join(p.parts)).strip()

def normalized(value: str) -> str:
    return re.sub(r'\s+', ' ', plain(value)).strip().casefold()

def fingerprint(fields: Iterable[str], tags: Iterable[str] = ()) -> str:
    payload = json.dumps([list(fields), sorted(tags)], ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()

def words(value: str) -> list[str]:
    return re.findall(r'[\w]+', normalized(value), flags=re.UNICODE)

def keywords(value: str, limit: int = 12) -> list[str]:
    counts = Counter(w for w in words(value) if len(w) > 2 and w not in STOP)
    return [w for w, _ in counts.most_common(limit)]

def escaped_field(value: str) -> str:
    """Authoring uses plain text; no pasted source can inject template scripts."""
    return escape(value).replace('\n', '<br>')

def tags(value: Any) -> list[str]:
    if isinstance(value, str): value = value.split()
    if not isinstance(value, list) or len(value) > 40:
        raise ValidationError('Use up to 40 space-separated tags.')
    out = []
    for raw in value:
        t = text(raw, 120, 'Tag', True)
        if re.search(r'\s', t) or any(c in t for c in '"<>\x1f') or t.startswith('wsd_'):
            raise ValidationError('Tags cannot contain spaces, quotes, angle brackets, or Workshop’s reserved wsd_ prefix.')
        if t not in out: out.append(t)
    return out

def clozes(value: str) -> list[int]:
    return sorted(set(int(x) for x in re.findall(r'\{\{c(\d+)::[\s\S]*?\}\}', value)))

def lint_card(front: str, back: str, kind: str = 'question') -> list[dict[str, str]]:
    notes = []
    def add(code, severity, message): notes.append({'code':code, 'severity':severity, 'message':message})
    if not front.strip(): add('empty_front', 'error', 'The question is empty.')
    if not back.strip() and kind != 'cloze': add('empty_back','error','Add an answer before approving this card.')
    if kind == 'cloze':
        nums = clozes(front)
        if not nums: add('cloze_missing','error','Hide at least one phrase with {{c1::answer}}.')
        if any(n < 1 or n > 99 for n in nums): add('cloze_range','error','Use cloze numbers from c1 through c99.')
        if len(re.findall(r'\{\{c\d+::', front)) != len(re.findall(r'\{\{c\d+::[^{}]*\}\}', front)):
            add('cloze_syntax','error','A cloze is incomplete or nested. Review its braces.')
    elif re.search(r'\{\{c\d+::', front):
        add('cloze_wrong_type','error','Choose Hide a phrase for cloze syntax, or remove the cloze braces.')
    if len(words(front)) > 65: add('long_prompt','suggestion','This prompt is long. Consider whether a shorter question tests the same idea.')
    if len(words(back)) > 160: add('long_answer','suggestion','The answer contains many details. Consider separating independent learning targets.')
    if front.count('?') > 2: add('many_questions','suggestion','Several questions share one answer. Splitting them may make feedback more useful.')
    if re.match(r'^(what is (it|this)|explain this|name these|what are they)\b', front.strip(), re.I):
        add('missing_context','suggestion','The question may rely on missing context. Name the subject or attach the relevant image.')
    if re.search(r'\b(always|never|all|none)\b', front + ' ' + back, re.I):
        add('absolute','suggestion','Check any absolute claim against your source; this is a wording prompt, not a finding of error.')
    return notes

def validate_draft(data: Mapping[str, Any], *, final: bool = False) -> dict[str, Any]:
    if not isinstance(data, Mapping): raise ValidationError('The draft must be an object.')
    kind = data.get('kind', 'question')
    if kind not in KINDS: raise ValidationError('Choose a supported card style.')
    d = {'kind':kind, 'front':text(data.get('front',''), MAX_FIELD,'Question'),
         'back':text(data.get('back',''), MAX_FIELD,'Answer'),
         'context':text(data.get('context',''), 20_000,'Explanation'),
         'quote':text(data.get('quote',''), 20_000,'Source passage'),
         'tags':tags(data.get('tags', [])), 'media':[],
         'page':integer(data.get('page',1),1,2000,'Page'),
         'deck_id':integer(data.get('deck_id',1),1,2**53-1,'Deck'),
         'model_id':integer(data.get('model_id',0),0,2**53-1,'Note type'),
         'mapping':{}, 'origin':str(data.get('origin','manual'))[:30]}
    for key in ('project_id','source_id','version_id'):
        d[key] = identifier(data[key],key) if data.get(key) else ''
    mapping = data.get('mapping', {})
    if not isinstance(mapping,dict) or len(mapping)>4:raise ValidationError('Invalid field mapping.')
    for role, field in mapping.items():
        if role not in ('front','back','context','source'):raise ValidationError('Unsupported mapped field.')
        d['mapping'][role] = text(field,100,'Field name',True)
    raw_media = data.get('media',[])
    if not isinstance(raw_media,list) or len(raw_media)>10:raise ValidationError('Attach no more than ten media items to a card.')
    for item in raw_media:
        if not isinstance(item,dict) or item.get('side') not in ('front','back'):raise ValidationError('Choose which side to attach media to.')
        name = text(item.get('blob',''),150,'Media name',True)
        if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|jpeg|webp|mp3|wav|ogg)',name):raise ValidationError('Unsupported media reference.')
        d['media'].append({'blob':name, 'side':item['side'], 'alt':text(item.get('alt',''),200,'Media description')})
    if kind=='occlusion':
        from .masks import validate_masks,question_count
        d['masks']=validate_masks(data.get('masks',[]),final=final)
        d['hide_others']=data.get('hide_others',True)
        if type(d['hide_others']) is not bool:raise ValidationError('Choose whether other answers stay hidden.')
        d['model_id']=0;d['mapping']={}
        if final:
            front_media=[m for m in d['media'] if m['side']=='front']
            if len(front_media)!=1 or not front_media[0]['blob'].endswith(('.png','.jpg','.jpeg','.webp')):
                raise ValidationError('Masked questions need exactly one image on the front.')
        issues=[] if d['front'] else [{'code':'empty_front','severity':'error','message':'Add a brief instruction above this image.'}]
    else:
        issues=lint_card(d['front'], d['back'],kind)
    if final:
        errors=[x['message'] for x in issues if x['severity']=='error']
        if errors:raise ValidationError(' '.join(errors))
        if d['origin']=='ai' and not data.get('verified'):
            raise ValidationError('Review and confirm each AI draft against its source before adding it.')
    d['verified']=bool(data.get('verified',False))
    d['issues']=issues
    d['card_count']=question_count(d['masks']) if kind=='occlusion' else len(clozes(d['front'])) if kind=='cloze' else 1
    return d

def similarity(query: str, target: str) -> tuple[float, str]:
    a, b = normalized(query), normalized(target)
    if not a or not b: return 0.0, ''
    if a == b: return 1.0, 'Exact wording after spacing and case normalization'
    aw, bw = set(words(a))-STOP,set(words(b))-STOP
    if not aw or not bw:return 0.0,''
    common=aw&bw
    containment=len(common)/len(aw)
    overlap=len(common)/max(1,len(aw|bw))
    seq=SequenceMatcher(None,a[:2000],b[:2000],autojunk=False).ratio()
    score=.5*containment+.25*overlap+.25*seq
    return min(.99,score), ('Shared terms: '+', '.join(sorted(common)[:7])) if common else 'Similar wording'

def rank_matches(query: str, rows: Iterable[dict], limit: int = 20) -> list[dict]:
    ranked=[]
    for row in rows:
        score,why=similarity(query,row.get('text',''))
        if score >= .12: ranked.append({**row,'match':round(score,3),'why':why,'exact':score==1})
    return sorted(ranked,key=lambda x:(-x['match'],str(x.get('id',''))))[:limit]

def diff_pages(old: list[dict], new: list[dict]) -> dict:
    """Align unchanged pages by normalized content so inserted pages do not flag everything."""
    old_text=[normalized(p['text']) for p in old]
    new_text=[normalized(p['text']) for p in new]
    matching=SequenceMatcher(None,old_text,new_text,autojunk=False)
    moved, changed, removed, added = {},[],[],[]
    for tag,a,b,c,d in matching.get_opcodes():
        if tag=='equal':
            for i,j in zip(range(a,b),range(c,d)):moved[i+1]=j+1
        elif tag=='replace':
            for i,j in zip(range(a,b),range(c,d)):
                changed.append({'old_page':i+1,'new_page':j+1,'before':old[i]['text'],'after':new[j]['text'],
                                'diff':'\n'.join(unified_diff(old[i]['text'].splitlines(),new[j]['text'].splitlines(),lineterm='',n=2))[:30000]})
            removed.extend(range(a+min(b-a,d-c)+1,b+1));added.extend(range(c+min(b-a,d-c)+1,d+1))
        elif tag=='delete':removed.extend(range(a+1,b+1))
        else:added.extend(range(c+1,d+1))
    return {'unchanged':moved,'changed':changed,'removed':removed,'added':added}

def quote_status(quote: str, source: str) -> bool:
    q = re.sub(r'\s+', ' ', quote).strip()
    s = re.sub(r'\s+', ' ', source).strip()
    return bool(q) and q in s

def workload(cards: int, daily: int, seconds: int) -> dict:
    cards=integer(cards,0,20000,'Cards');daily=integer(daily,1,500,'New cards per day');seconds=integer(seconds,5,300,'Seconds per answer')
    return {'cards':cards,'introduction_days':math.ceil(cards/daily),
            'first_pass_minutes':round(cards*seconds/60),
            'assumptions':f'{seconds} seconds per answer and {daily} new cards per day. First pass only; repeated learning and future reviews are not included. No schedule changes.'}

def safe_anki_literal(value: str) -> str:
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'

def safe_json(value: Any) -> str:
    return json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':'))

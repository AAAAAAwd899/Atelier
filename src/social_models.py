"""Bounded local companion/social preferences. No networking or scheduler writes."""
from __future__ import annotations
import re,uuid
from .core import ValidationError,deck_id
KEEPSAKES=(
 {'id':'journal','name':'The journal nook','reviews':10,'days':1,'description':'A cozy writing nook and your private reflection journal.'},
 {'id':'observatory','name':'The observatory','reviews':50,'days':3,'description':'An astronomer outfit, brass telescope and your study constellation.'},
 {'id':'greenhouse','name':'The greenhouse','reviews':150,'days':7,'description':'A gardening outfit and glasshouse with your current study focus.'},
)

def journey_settings(value):
 value=value if isinstance(value,dict) else {};earned={}
 for k in KEEPSAKES:
  v=value.get('earned',{}).get(k['id']) if isinstance(value.get('earned'),dict) else None
  if isinstance(v,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T[0-9:.+Z-]{1,40}',v):earned[k['id']]=v
 equipped=value.get('equipped','')
 if equipped not in earned:equipped=''
 reflection=value.get('reflection','');reflection=reflection if isinstance(reflection,str) else ''
 return {'earned':earned,'equipped':equipped,'reflection':reflection[:2000]}

def sharing_settings(value):
 value=value if isinstance(value,dict) else {};courses=[];seen=set()
 for raw in value.get('courses',[])[:25] if isinstance(value.get('courses'),list) else []:
  try:
   remote=str(uuid.UUID(raw['id']));account=str(uuid.UUID(raw['account']));origin=raw['origin']
   if remote in seen or not isinstance(origin,str) or not re.fullmatch(r'[a-f0-9]{64}',origin):continue
   if not isinstance(raw['deck_ids'],list):continue
   ids=list(dict.fromkeys(deck_id(x) for x in raw['deck_ids'][:20]))
   if not ids:continue
   title=raw.get('title','Shared course');title=title if isinstance(title,str) else 'Shared course'
   courses.append({'id':remote,'account':account,'origin':origin,'deck_ids':ids,'title':title[:100],'auto':raw.get('auto') is True,'digest':raw.get('digest') if isinstance(raw.get('digest'),str) and re.fullmatch(r'[a-f0-9]{64}',raw['digest']) else '', 'version':max(0,min(100000,int(raw.get('version',0))))})
   seen.add(remote)
  except (KeyError,ValueError,TypeError,AttributeError,ValidationError):continue
 received={}
 for key,v in list(value.get('received',{}).items())[:100] if isinstance(value.get('received'),dict) else []:
  try:
   uid=str(uuid.UUID(key))
   if type(v) is int and 0<=v<=100000:received[uid]=v
  except(ValueError,TypeError,AttributeError):pass
 return {'courses':courses,'received':received}


def service_settings(value):
 import base64,json
 from urllib.parse import urlsplit
 value=value if isinstance(value,dict) else {};url=value.get('friends_url','');key=value.get('friends_public_key','')
 if not url and not key:return {'friends_url':'','friends_public_key':''}
 if not isinstance(url,str) or not isinstance(key,str) or len(url)>300 or len(key)>2048:raise ValidationError('Check the private Friends service settings.')
 u=urlsplit(url)
 if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('','/') or u.port not in (None,443):raise ValidationError('Use the HTTPS origin of the private Friends service.')
 if key.startswith('sb_publishable_') and len(key)>=30:pass
 elif key.count('.')==2:
  try:role=json.loads(base64.urlsafe_b64decode(key.split('.')[1]+'==='))['role']
  except Exception:raise ValidationError('Use the public project key, never a secret key.')
  if role!='anon':raise ValidationError('Use the public project key, never a secret key.')
 else:raise ValidationError('Use the public project key, never a secret key.')
 return {'friends_url':u.scheme+'://'+u.netloc.lower(),'friends_public_key':key}

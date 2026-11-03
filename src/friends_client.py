"""Opt-in HTTPS client. Auth tokens stay in memory, never JavaScript or config."""
from __future__ import annotations
import hashlib,json,os,tempfile,threading,uuid,zipfile
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from .core import ValidationError
from .social_models import service_settings
MAX_BYTES=41943040
class FriendsError(ValidationError):pass
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def validate_package(path):
 p=Path(path)
 if p.suffix.lower()!='.apkg' or not p.is_file() or not 0<p.stat().st_size<=MAX_BYTES:raise FriendsError('Choose an Anki deck package no larger than 40 MiB for the private pilot.')
 try:
  with zipfile.ZipFile(p) as z:
   rows=z.infolist();names={x.filename for x in rows}
   if len(rows)>30000 or sum(x.file_size for x in rows)>2*1024**3:raise FriendsError('This package is too large to check safely.')
   if not names.intersection({'collection.anki2','collection.anki21','collection.anki21b'}):raise FriendsError('Choose a normal Anki deck package.')
   if any('/' in x.filename or '\\' in x.filename or x.filename in ('.','..') or x.flag_bits&1 for x in rows):raise FriendsError('This package contains unsupported paths or encryption.')
 except (zipfile.BadZipFile,OSError) as e:raise FriendsError('This Anki package could not be checked.') from e
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}

class CancelReader:
 def __init__(self,stream,event):self.stream=stream;self.event=event
 def read(self,n=-1):
  if self.event.is_set():raise FriendsError('The transfer was cancelled.')
  return self.stream.read(65536 if n<0 else min(n,65536))

class FriendsClient:
 def __init__(self,config,opener=None,test_url=None):
  cfg=service_settings(config);self.base=test_url or cfg['friends_url'];self.key=cfg['friends_public_key'];self.session=None;self.closed=False;self.cancelled=threading.Event();self.lock=threading.RLock();self.http=opener or build_opener(NoRedirect())
  self.origin_hash=hashlib.sha256(self.base.encode()).hexdigest()
 @property
 def configured(self):return bool(self.base and self.key)
 @property
 def account(self):
  session=self.session
  return session['user']['id'] if session else ''
 def close(self):self.closed=True;self.cancelled.set();self.session=None
 def _begin(self):
  if self.closed:raise FriendsError("This profile has closed. Open Friends again.")
  self.cancelled.clear()
 def public_state(self):return {'configured':self.configured,'signed_in':bool(self.session),'service_origin':self.base}
 def _request(self,path,method='POST',data=None,auth=False,extra=None,timeout=25,raw=False):
  if not self.configured:raise FriendsError('The private Friends service has not been connected yet.')
  if self.cancelled.is_set():raise FriendsError('The transfer was cancelled.')
  headers={'apikey':self.key,'content-type':'application/json'}
  if auth:
   if not self.session:raise FriendsError('Sign in to Friends first.')
   headers['Authorization']='Bearer '+self.session['access_token']
  if extra:headers.update(extra)
  body=json.dumps(data,separators=(',',':')).encode() if isinstance(data,dict) else data
  req=Request(self.base+path,data=body,headers=headers,method=method)
  try:
   res=self.http.open(req,timeout=timeout)
   if raw:return res
   with res:
    text=res.read(1024*1024+1)
    if len(text)>1024*1024:raise FriendsError('The Friends response was too large.')
    out=json.loads(text or b'{}')
   if isinstance(out,dict) and out.get('error'):raise FriendsError(str(out['error'])[:180])
   return out
  except HTTPError as e:
   if e.code==401:self.session=None;raise FriendsError('Your Friends session ended. Sign in again.') from None
   text=e.read(8192);message='Friends could not complete that request. Your local decks are unchanged.'
   try:
    result=json.loads(text);candidate=result.get('error')
    if isinstance(candidate,str) and len(candidate)<=180:message=candidate
   except(ValueError,TypeError):pass
   raise FriendsError(message) from None
  except FriendsError:raise
  except (URLError,TimeoutError,OSError,ValueError) as e:raise FriendsError('Friends could not connect. Your local decks are unchanged; try again when you are online.') from e
 def send_code(self,email):
  if not isinstance(email,str) or len(email)>254 or email.count('@')!=1 or any(x.isspace() for x in email):raise FriendsError('Enter the email invited to Friends.')
  with self.lock:self._begin();self._request('/auth/v1/otp',data={'email':email,'create_user':False})
  return {'sent':True}
 def verify_code(self,email,code):
  if not isinstance(code,str) or not code.isdigit() or not 6<=len(code)<=10:raise FriendsError('Enter the code from your email.')
  with self.lock:
   self._begin();out=self._request('/auth/v1/verify',data={'email':email,'token':code,'type':'email'})
   try:uuid.UUID(out['user']['id']);assert isinstance(out['access_token'],str) and 20<=len(out['access_token'])<=8192
   except(KeyError,ValueError,TypeError,AssertionError):raise FriendsError('The private service returned an invalid sign-in response.')
   self.session={'access_token':out['access_token'],'user':{'id':out['user']['id']}}
   try:return self.rpc('home')
   except Exception:self.session=None;raise
 def logout(self):
  with self.lock:
   try:
    if self.session:self._request('/auth/v1/logout',data={},auth=True)
   finally:self.session=None;self.cancelled.set()
  return {'signed_in':False}
 def rpc(self,op,payload=None):
  allowed={'home','profile','invite_create','invite_preview','invite_accept','friend_remove','course_create','course_update','snapshot_begin','snapshot_cancel','course_revoke'}
  if op not in allowed:raise FriendsError('Choose a Friends action.')
  with self.lock:
   self._begin();return self._request('/functions/v1/atelier-friends',data={'op':op,'payload':payload or {}},auth=True)
 def upload(self,snapshot_id,path):
  uuid.UUID(snapshot_id);meta=validate_package(path)
  with self.lock:
   self._begin()
   with Path(path).open('rb') as f:
    return self._request('/functions/v1/atelier-friends/upload?id='+snapshot_id,method='PUT',data=CancelReader(f,self.cancelled),auth=True,extra={'content-type':'application/octet-stream','content-length':str(meta['bytes'])},timeout=120)
 def download(self,snapshot_id,target,expected_bytes,expected_sha):
  import re
  uuid.UUID(snapshot_id)
  if type(expected_bytes) is not int or not 0<expected_bytes<=MAX_BYTES or not isinstance(expected_sha,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_sha):raise FriendsError('Refresh this shared version before downloading.')
  target=Path(target)
  if target.suffix.lower()!='.apkg':raise FriendsError('Save this as an Anki .apkg file.')
  with self.lock:
   self._begin()
   target.parent.mkdir(parents=True,exist_ok=True)
   fd,name=tempfile.mkstemp(prefix='.atelier-download-',suffix='.apkg',dir=target.parent);temp=Path(name)
   try:
    size=0;digest=hashlib.sha256()
    with os.fdopen(fd,'wb') as out,self._request('/functions/v1/atelier-friends/download?id='+snapshot_id,method='GET',auth=True,timeout=120,raw=True) as response:
     while True:
      if self.cancelled.is_set():raise FriendsError('The download was cancelled.')
      chunk=response.read(65536)
      if not chunk:break
      size+=len(chunk)
      if size>expected_bytes:raise FriendsError('The shared package size did not match.')
      out.write(chunk);digest.update(chunk)
     out.flush();os.fsync(out.fileno())
    if size!=expected_bytes or digest.hexdigest()!=expected_sha:raise FriendsError('The shared package integrity check failed. Your existing file is unchanged.')
    validate_package(temp)
    if self.closed or self.cancelled.is_set():raise FriendsError('The download was cancelled.')
    os.replace(temp,target)
    return {'saved':True,'path':str(target)}
   finally:temp.unlink(missing_ok=True)

import base64,copy,hashlib,io,json,threading,uuid,zipfile
from pathlib import Path
from types import SimpleNamespace
import pytest
from fixtures import core
from atelier_testing import social_models as models, companion_journey as journey, friends_client as client

CFG={'friends_url':'https://private.example','friends_public_key':'sb_publishable_'+'x'*32}
A='11111111-1111-4111-8111-111111111111';S='55555555-5555-4555-8555-555555555555'

def package(tmp_path):
 p=tmp_path/'course.apkg'
 with zipfile.ZipFile(p,'w') as z:z.writestr('collection.anki21b',b'native-db-fixture');z.writestr('media',b'{}')
 return p

class Opener:
 def __init__(self,responses):self.responses=list(responses);self.requests=[]
 def open(self,request,timeout):
  self.requests.append(request);data=self.responses.pop(0)
  if callable(data):data=data(request)
  return io.BytesIO(data if isinstance(data,bytes) else json.dumps(data).encode())

def signed(opener):
 c=client.FriendsClient(CFG,opener=opener);c.session={'access_token':'t'*40,'user':{'id':A}};return c

@pytest.mark.parametrize('url',['http://private.example','https://u:p@private.example','https://private.example/path','https://private.example?query=1','https://private.example:444','https://private.example/#x'])
def test_only_public_https_origin_configuration(url):
 with pytest.raises(core.ValidationError):models.service_settings(dict(CFG,friends_url=url))

@pytest.mark.parametrize('role',['service_role','authenticated','owner'])
def test_secret_legacy_keys_never_become_client_config(role):
 key='e30.'+base64.urlsafe_b64encode(json.dumps({'role':role}).encode()).decode().rstrip('=')+'.sig'
 with pytest.raises(core.ValidationError,match='public'):models.service_settings(dict(CFG,friends_public_key=key))

def test_optional_preferences_do_not_change_old_default_shape():
 assert 'journey' not in core.profile_settings({}) and 'sharing' not in core.profile_settings({})
 old=core.profile_settings({'favorites':['1'],'onboarding':{'version':1,'status':'completed'}})
 value=core.profile_settings(dict(old,journey={'earned':{'journal':'2026-11-02T00:00:00Z'},'equipped':'journal','reflection':'Private <b>text</b>'}))
 assert value['favorites']==old['favorites'] and value['onboarding']==old['onboarding']
 assert value['journey']['reflection']=='Private <b>text</b>'
 assert models.journey_settings({'earned':{'fake':'now'},'equipped':'fake'})['equipped']==''

def test_profile_store_roundtrip_retains_both_new_features_and_old_work(tmp_path):
 store=core.ProfileStore(tmp_path,'test-profile');old=store.read()
 old.update(journey={'earned':{'journal':'2026-11-02T00:00:00Z'},'equipped':'journal','reflection':'A private thought'},sharing={'courses':[{'id':S,'account':A,'origin':'a'*64,'deck_ids':['1','1'],'title':'Class','auto':True,'digest':'b'*64,'version':2}],'received':{S:1}})
 store.write(old);saved=core.ProfileStore(tmp_path,'test-profile').read()
 assert saved['journey']['reflection']=='A private thought';assert saved['sharing']['courses'][0]['deck_ids']==['1'];assert saved['sharing']['received'][S]==1

@pytest.mark.parametrize('reviews,days,expected',[(9,7,[]),(10,1,['journal']),(50,2,['journal']),(50,3,['journal','observatory']),(150,7,['journal','observatory','greenhouse'])])
def test_keepsakes_use_both_real_activity_thresholds(monkeypatch,reviews,days,expected):
 monkeypatch.setattr(journey,'read_progress',lambda *args:{'reviews':reviews,'days_studied':days,'daily':[]})
 assert [r['id'] for r in journey.status(None,{})['rewards'] if r['eligible']]==expected
 with pytest.raises(core.ValidationError):journey.claim(None,{},'not-an-award')

def test_collected_keepsakes_survive_activity_rolling_out_and_claim_is_rechecked(monkeypatch):
 monkeypatch.setattr(journey,'read_progress',lambda *args:{'reviews':0,'days_studied':0,'daily':[]})
 profile={'journey':{'earned':{'journal':'2026-10-01T00:00:00Z'},'equipped':'journal','reflection':'kept'}}
 assert journey.status(None,profile)['rewards'][0]['collected']
 assert journey.claim(None,profile,'journal')['earned']==profile['journey']['earned']
 with pytest.raises(core.ValidationError):journey.claim(None,profile,'observatory')
 with pytest.raises(core.ValidationError):journey.change(profile,'equip','observatory')
 assert journey.change(profile,'equip','')['reflection']=='kept'
 assert journey.change(profile,'reflection','New reflection')['reflection']=='New reflection'
 with pytest.raises(core.ValidationError):journey.change(profile,'reflection','a'*2001)

def test_tokens_are_memory_only_and_membership_checked_before_signin_is_exposed():
 http=Opener([{'access_token':'secret-token'*4,'refresh_token':'never-retain','user':{'id':A}},{'profile':{'id':A,'name':'Alice'},'friends':[]}]);c=client.FriendsClient(CFG,opener=http)
 c.verify_code('alice@example.com','123456')
 assert c.account==A and 'refresh_token' not in c.session
 assert 'token' not in json.dumps(c.public_state())
 assert json.loads(http.requests[0].data)['type']=='email'
 c.close();assert not c.session
 for fn in [lambda:c.rpc('home'),lambda:c.send_code('alice@example.com'),lambda:c.verify_code('alice@example.com','123456')]:
  with pytest.raises(client.FriendsError,match='closed'):fn()
 assert len(http.requests)==2

def test_otp_never_signs_up_and_redirects_never_forward_tokens():
 http=Opener([{}]);c=client.FriendsClient(CFG,opener=http);c.send_code('a@example.com')
 assert json.loads(http.requests[0].data)['create_user'] is False
 assert client.NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.example') is None

def test_failure_preserves_server_business_error_instead_of_masking_it():
 c=signed(Opener([{'error':'Choose a current friend.'}]))
 with pytest.raises(client.FriendsError,match='current friend'):c.rpc('home')

def test_partial_or_corrupt_download_cannot_replace_existing_package(tmp_path):
 p=package(tmp_path);raw=p.read_bytes();target=tmp_path/'saved.apkg';target.write_bytes(b'original')
 for data in [raw[:-1],raw+b'x',b'x'*len(raw)]:
  c=signed(Opener([data]))
  with pytest.raises(client.FriendsError):c.download(S,target,len(raw),hashlib.sha256(raw).hexdigest())
  assert target.read_bytes()==b'original' and not list(tmp_path.glob('.atelier-download-*'))
 c=signed(Opener([raw]));c.download(S,target,len(raw),hashlib.sha256(raw).hexdigest());assert target.read_bytes()==raw

def test_upload_stream_and_package_validation_are_bounded(tmp_path):
 p=package(tmp_path);raw=p.read_bytes()
 def response(request):
  got=b''.join(iter(lambda:request.data.read(65536),b''));assert got==raw;return {'published':True,'version':1}
 c=signed(Opener([response]));assert c.upload(S,p)['version']==1
 for name in ['../escape','dir/file','bad\\file']:
  bad=tmp_path/'bad.apkg'
  with zipfile.ZipFile(bad,'w') as z:z.writestr('collection.anki21b','db');z.writestr(name,'x')
  with pytest.raises(client.FriendsError):client.validate_package(bad)

def test_close_during_auth_response_does_not_resurrect_a_session():
 c=None
 def response(_):c.close();return {'access_token':'a'*40,'user':{'id':A}}
 http=Opener([response]);c=client.FriendsClient(CFG,opener=http)
 with pytest.raises(client.FriendsError,match='closed'):c.verify_code('a@example.com','123456')
 assert c.session is None

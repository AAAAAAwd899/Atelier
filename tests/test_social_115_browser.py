"""Actual shipped Friends/keepsake UI, synthetic service responses, real packaged art."""
from pathlib import Path
import sys,os,json,copy,mimetypes,hashlib
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from fixtures import core, SRC
from atelier_testing.review_model import PALETTES
from atelier_testing.social_models import KEEPSAKES
from verify_release import verification_env
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification/social-115';SH=ROOT/'screenshots/social-115'
OUT.mkdir(parents=True,exist_ok=True);SH.mkdir(parents=True,exist_ok=True)
A='11111111-1111-4111-8111-111111111111';B='22222222-2222-4222-8222-222222222222';C='55555555-5555-4555-8555-555555555555'
checks=[];errors=[];shots=[]
def check(name,value):
 assert value,name
 checks.append(name)
def state(online=False,earned=True):
 return {'configured':online,'service_origin':'https://private.example' if online else '','signed_in':online,'account':A if online else '', 'origin':'a'*64,'busy':False,'notice':'','suspended':[],
  'focus':['Cardiology · Exam 3','Pharmacotherapy · Finals'],
  'decks':[{'id':'1','name':'Cardiology'},{'id':'2','name':'Cardiology::Lecture 1'},{'id':'3','name':'Pharmacotherapy'},{'id':'4','name':'Pharmacotherapy::Long course name '*3}],
  'sharing':{'courses':[{'id':C,'account':A,'origin':'a'*64,'deck_ids':['1','3'],'auto':True}],'received':{C:1}},
  'home':{'profile':{'id':A,'name':'Alice'},'friends':[{'id':B,'name':'Bob <script>bad()</script>'}],'courses':[{'id':C,'title':'Shared Cardiology','version':2,'recipients':[B],'enabled':True}],
   'inbox':[{'id':C,'title':'Exam 3','version':2,'latest_id':C,'sender':'Bob','bytes':1048576,'sha256':'a'*64,'updated_at':'2026-11-02T12:00:00Z'}]},
  'journey':{'reviews':168 if earned else 0,'days_studied':8 if earned else 0,'basis':'Your last 30 study days. Every normal answer rating counts equally.',
   'saved':{'equipped':'','reflection':'What became clearer today?','earned':{x['id']:'2026-11-02T00:00:00Z' for x in KEEPSAKES} if earned else {}},
   'rewards':[dict(x,collected=earned,eligible=earned) for x in KEEPSAKES],
   'daily':[{'label':f'2026-10-{i+1:02}','reviews':0 if i%3 else 30} for i in range(30)]}}
def document(s,tab='journey',theme='forest'):
 p=PALETTES[theme] if theme else {};tokens=''.join('--social-'+k+':'+v+';' for k,v in p.items())
 boot={'nonce':'test','tab':tab,'dark':theme!='linen','motion':True,'assets':'http://atelier.fixture/_addons/daedalus_atelier/sprout/web/pip'}
 return '<!doctype html><meta charset="utf-8"><style>'+ (SRC/'web/social.css').read_text(encoding='utf8')+'</style><style>#atelier-social[data-dark=true],#atelier-social[data-dark=false]{'+tokens+'}</style><main id="atelier-social"></main><script>window.actions=[];window.AtelierSocialBoot='+core.json_for_html(boot)+';window.AtelierSocialBoot.request=x=>actions.push(x);</script><script>'+(SRC/'web/social.js').read_text(encoding='utf8')+'</script><script>AtelierSocial.receive({state:'+core.json_for_html(s)+'});</script>'
def assets(route):
 path=unquote(urlsplit(route.request.url).path);prefix='/_addons/daedalus_atelier/'
 p=(SRC/path[len(prefix):]).resolve() if path.startswith(prefix) else None
 if p and p.is_relative_to(SRC.resolve()) and p.is_file():route.fulfill(path=str(p),content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
 else:errors.append('Missing asset '+path);route.fulfill(status=404,body='Missing')
def shot(p,name):
 f=SH/(name+'.png');p.screenshot(path=str(f),animations='disabled',full_page=True);shots.append({'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
def run():
 os.environ.update(verification_env())
 with sync_playwright() as w:
  b=w.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox','--disable-background-networking'])
  p=b.new_page(viewport={'width':1120,'height':850});p.route('**/*',assets);p.on('pageerror',lambda e:errors.append(str(e)))
  for theme in ['forest','obsidian','linen',None]:
   p.set_content(document(state(),theme=theme));p.wait_for_function('[...document.images].every(x=>x.complete&&x.naturalWidth>0)')
   check(str(theme)+' packaged artwork decodes',p.locator('.scene-art img').evaluate('e=>e.naturalWidth>=1000'))
   for scene in ['journal','observatory','greenhouse']:
    p.locator(f'[data-op=preview][data-id={scene}]').click();p.wait_for_timeout(40)
    check(str(theme)+' '+scene+' is a distinct full scene',scene in p.locator('.scene-art img').get_attribute('src'))
    if scene=='journal':
     p.locator('[name=value]').fill('A thought <script>not HTML</script>');p.get_by_role('button',name='Save reflection').click();check('Private journal sends only a preference command',p.evaluate('actions.at(-1).op')=='journey_reflection');p.evaluate('AtelierSocial.receive({busy:false})')
    if scene=='observatory':check('Observatory shows all thirty native-shaped daily bins',p.locator('.star').count()==30 and p.locator('.star[data-lit=true]').count()==10)
    if scene=='greenhouse':check('Greenhouse links actual current focus to desk',p.get_by_role('button',name='Open study desk').count()==1 and 'Cardiology' in p.locator('.focus-keepsake').inner_text())
    if theme=='forest':shot(p,'forest-'+scene)
   check(str(theme)+' scene never overflows',p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
  p.set_content(document(state(online=True),tab='shared',theme='obsidian'))
  check('Attached course shows automatic preference',p.locator('[data-auto]').is_checked())
  p.locator('[data-auto]').uncheck();check('Automatic publishing requires explicit checkbox action',p.evaluate('actions.at(-1).op')=='automatic' and p.evaluate('actions.at(-1).data.enabled') is False)
  p.evaluate('AtelierSocial.receive({busy:false})');p.get_by_role('button',name='Choose friends').click();check('Recipient modal fits and preserves escaped names',p.locator('dialog').is_visible() and p.locator('dialog script').count()==0);shot(p,'recipients');p.evaluate('AtelierSocial.receive({state:{...AtelierSocial.getState(),notice:"Background update"}})');check('Background refresh preserves an open recipient chooser',p.locator('dialog').is_visible());p.locator('dialog button[value=cancel]').click()
  p.locator('.attach summary').click();p.locator('[name=title]').fill('Combined parents');p.locator('[data-folder="1"]').check();p.locator('[data-folder="3"]').check();p.locator('.attach [name=recipient]').check();p.locator('[name=folder_search]').fill('Lecture');check('Filtering retains both chosen parent folders',p.locator('#chosen-count').inner_text()=='2 selected');p.get_by_role('button',name='Attach selected folders').click();check('Attachment combines separate parents without merge',p.evaluate('actions.at(-1).data.deck_ids')==['1','3']);p.evaluate('AtelierSocial.receive({busy:false})');shot(p,'shared-folders')
  p.locator('[data-op=tab][data-tab=friends]').click();p.locator('form[data-form=invite_preview] input').fill('a'*64);p.get_by_role('button',name='Check invitation').click();p.evaluate('AtelierSocial.receive({inviter:{name:"Bob"}})');check('Friend invitation requires explicit acceptance',p.get_by_role('button',name='Accept invitation').count()==1 and p.evaluate('actions.at(-1).op')=='invite_preview');shot(p,'friends')
  p.locator('[data-op=tab][data-tab=inbox]').click();p.get_by_role('button',name='Download & review in Anki…').click();check('Recipient explicitly requests download/native review',p.evaluate('actions.at(-1).op')=='download');p.evaluate('AtelierSocial.receive({error:"The shared package integrity check failed. Your existing file is unchanged."})');check('Transfer failure is exposed without replacement claims',p.locator('[role=alert]').is_visible());shot(p,'updates-error')
  for width in [320,390,560,1024]:
   p.set_viewport_size({'width':width,'height':800})
   for online in [False,True]:
    for tab in ['shared','friends','inbox','journey']:
     p.set_content(document(state(online,earned=online),tab=tab,theme='forest'))
     check(f'{width} {online} {tab} no horizontal overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
     if width==390 and not online and tab=='journey':shot(p,'locked-mobile')
  p.set_viewport_size({'width':1120,'height':850});p.set_content(document(state(False),tab='shared',theme=None));p.evaluate('AtelierSocial.receive({tab:"journey"})');check('Native tab-only reopening repaints the intended page',p.locator('.journey-heading').count()==1);p.evaluate('AtelierSocial.receive({tab:"shared"})');check('Visuals-off window keeps all tabs and offline export',p.locator('nav button').count()==4 and p.get_by_role('button',name='Export Anki package…').count()==1);shot(p,'unconfigured-neutral')
  p.evaluate('AtelierSocial.receive({state:{...AtelierSocial.getState(),configured:true}})');p.locator('[name=email]').fill('invited@example.com');p.get_by_role('button',name='Email a sign-in code').click();p.evaluate('AtelierSocial.receive({code_sent:true})');check('Invited sign-in uses OTP without AnkiWeb credentials',p.locator('[name=code]').count()==1 and p.evaluate('actions.at(-1).op')=='send_code')
  p.emulate_media(reduced_motion='reduce');p.set_content(document(state(),theme='forest'));p.locator('.keepsake').first.hover();check('Reduced motion has no reward animation',p.locator('.keepsake img').first.evaluate('e=>getComputedStyle(e).animationName')=='none')
  check('No browser errors or missing assets',not errors);b.close()
 report={'category':'Shipped UI and packaged generated art with synthetic service/activity data; no live hosting or native import claim','runtime_sha256':runtime_digest(SRC),'count':len(checks),'checks':checks,'errors':errors,'captures':shots}
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'count':len(checks),'errors':errors,'captures':len(shots)}))
if __name__=='__main__':run()

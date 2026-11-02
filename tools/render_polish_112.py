"""Art-resolved render review of shipped UI. Synthetic data; no native GUI claims."""
from pathlib import Path
import sys,os,json,hashlib,mimetypes
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite,core
from bs4 import BeautifulSoup
from release_tools import runtime_digest
from verify_release import verification_env
from playwright.sync_api import sync_playwright
import planner_suite_fixture as pf
OUT=ROOT/'verification/polish-112';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/polish-112';SH.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];missing=[];captures=[];decoded=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
def assets(route):
 path=unquote(urlsplit(route.request.url).path);prefix='/_addons/daedalus_atelier/'
 if path.startswith(prefix):
  p=(ROOT/'src'/path[len(prefix):]).resolve()
  if p.is_relative_to((ROOT/'src').resolve()) and p.is_file():return route.fulfill(path=str(p),content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
 missing.append(path);route.fulfill(status=404,body='Not a packaged asset')
def doc(theme):
 soup=BeautifulSoup(home_suite(theme),'html.parser');base=soup.new_tag('base',href='http://atelier.fixture/');soup.head.insert(0,base)
 tag=soup.find(id='atelier-bootstrap');b=json.loads(tag.string);b['integrations']['onigiri']=False;b['settings']['motion']=True;b['demo']['settings']['motion']=True;tag.string=core.json_for_html(b)
 return str(soup)
def shot(p,name):
 path=SH/(name+'.png');p.screenshot(path=str(path),animations='disabled',timeout=60000);captures.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
def run():
 os.environ.update(verification_env())
 with sync_playwright() as w:
  browser=w.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox','--disable-background-networking'])
  for theme in core.THEMES:
   p=browser.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)));p.route('**/*',assets);p.set_content(doc(theme));p.locator('.world-window').wait_for()
   art=p.locator('.world-window').evaluate("""async e=>{const urls=[...getComputedStyle(e).backgroundImage.matchAll(/url\("?([^")]+)"?\)/g)].map(x=>x[1]);return await Promise.all(urls.map(url=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve({url,w:i.naturalWidth,h:i.naturalHeight});i.onerror=()=>resolve({url,w:0,h:0});i.src=url}))) }""")
   check(theme+' actual packaged scene decodes',bool(art) and all(x['w']>=1000 for x in art));decoded.extend(art)
   check(theme+' home fits',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
   shot(p,theme+'-home')
   p.locator('.folder-explorer-launch').click();p.locator('[data-action=expand-folders]').click()
   check(theme+' full course library fits',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
   colors=p.locator('.outline-row').first.evaluate("e=>{const r=e.getRootNode(),p=document.createElement('div');r.append(p);const a=['violet','blue','rose','green','amber','cyan'].map(c=>{p.className='tone-'+c;return getComputedStyle(p).getPropertyValue('--tone').trim()});p.remove();return a}")
   check(theme+' six folder hues remain distinct',len(set(colors))==6)
   shot(p,theme+'-library');p.close()
  for theme in ['forest','rose','obsidian']:
   p=browser.new_page(viewport={'width':1440,'height':1000});p.route('**/*',assets);p.set_content(doc(theme));p.locator('.folder-explorer-launch').click();p.locator('[data-action=expand-folders]').click();p.locator('.outline-row[data-node="22"] [data-action=organize]').click()
   p.wait_for_function("document.getElementById('atelier-root').dataset.folderArt==='ready'")
   positions=[]
   for key in core.FOLDER_ICONS:
    p.locator(f'[data-action=folder-icon][data-icon={key}]').click()
    check(theme+' '+key+' authored selection visible and saved',p.locator('.personalization-art [data-folder-symbol]').get_attribute('data-folder-symbol')==key and p.locator(f'[data-action=folder-icon][data-icon={key}]').get_attribute('aria-pressed')=='true')
    positions.append(p.locator(f'[data-action=folder-icon][data-icon={key}] .folder-symbol').get_attribute('style'))
   check(theme+' 24 unique atlas cells',len(set(positions))==24)
   p.locator('[data-icon=cat]').click();p.locator('.folder-personalization').scroll_into_view_if_needed();shot(p,theme+'-personalization');p.close()
  for width,height in [(1024,600),(390,720)]:
   p=browser.new_page(viewport={'width':width,'height':height});p.route('**/*',assets);p.set_content(doc('forest'));p.locator('.world-window').wait_for()
   if width<821:p.locator('[data-action=mobile]').click()
   p.locator('.folder-explorer-launch').click();p.locator('[data-action=expand-folders]').click();shot(p,f'forest-library-{width}');p.close()
  # Home controls, widgets and settings are reviewed with resolved scenery.
  p=browser.new_page(viewport={'width':1440,'height':900});p.route('**/*',assets);p.set_content(doc('obsidian'));p.locator('.world-window').wait_for()
  p.locator('[data-page=tools]').first.click();shot(p,'obsidian-tools')
  p.locator('.unified-topbar [data-action=appearance]').click();shot(p,'obsidian-worlds');p.get_by_role('button',name='Close dialog',exact=True).click()
  p.locator('.side-bottom [data-action=widget-page]').click();shot(p,'obsidian-widgets');p.close()
  for theme in ['forest','rose','obsidian']:
   p=browser.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)));pf.expose(p);p.route('**/*',assets);p.set_content(pf.html(theme));p.locator('.es-top-nav').wait_for();shot(p,theme+'-exam-studio')
   p.locator('.es-top-nav [data-view=practice]').click();shot(p,theme+'-practice')
   check(theme+' planner fits',p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'));p.close()
  browser.close()
 check('All requested packaged assets resolved',not missing);check('No uncaught errors',not errors)
 report={'version':core.VERSION,'runtime_sha256':runtime_digest(),'count':len(checks),'checks':checks,'errors':errors,'missing_assets':missing,'decoded_scenes':decoded,'captures':captures,'category':'Chromium shipped frontend and packaged art with synthetic host/data; no native Windows screenshot claim'}
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'checks':len(checks),'captures':len(captures),'errors':errors,'missing':missing}))
if __name__=='__main__':run()

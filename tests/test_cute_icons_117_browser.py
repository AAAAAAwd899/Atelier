"""Packaged art, selection, persistence and reduced-motion checks with synthetic data."""
from pathlib import Path
import sys,os,json,mimetypes
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_ui_audit_browser import sort_doc
from fixtures import core
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from release_tools import runtime_digest
OUT=ROOT/'verification/cute-icons-117';OUT.mkdir(exist_ok=True)
SH=ROOT/'screenshots/cute-icons-117';SH.mkdir(exist_ok=True)
checks=[];errors=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
def assets(route):
 rel=unquote(urlsplit(route.request.url).path);prefix='/_addons/daedalus_atelier/'
 if rel.startswith(prefix):
  p=(ROOT/'src'/rel[len(prefix):]).resolve()
  if p.is_relative_to((ROOT/'src').resolve()) and p.is_file():return route.fulfill(path=str(p),content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
 route.fulfill(status=404,body='Not a packaged asset')
def run():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
  for theme,width in [('forest',1440),('rose',1440),('obsidian',390)]:
   p=b.new_page(viewport={'width':width,'height':950});p.route('**/*',assets);p.on('pageerror',lambda e:errors.append(str(e)))
   soup=BeautifulSoup(sort_doc(),'html.parser');soup.head.insert(0,soup.new_tag('base',href='http://atelier.fixture/'))
   tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
   boot['settings']['theme']=theme;boot['demo']['settings']['theme']=theme;boot['settings']['motion']=True;boot['demo']['settings']['motion']=True;tag.string=core.json_for_html(boot)
   p.set_content(str(soup));p.wait_for_function('document.getElementById("atelier-root")?.dataset.folderCuteArt==="ready"')
   check(theme+' packaged atlas decoded',p.locator('#atelier-root').get_attribute('data-folder-cute-art')=='ready')
   if width<821:p.locator('[data-action=mobile]').click()
   p.locator('.folder-explorer-launch').click();p.locator('[data-action=expand-folders]').click();p.locator('.outline-row[data-node="99"] [data-action=organize]').click()
   check(theme+' retains all original and added choices',p.locator('[data-action=folder-icon]').count()==31)
   for token in ['bunny','teddy','cupcake','strawberry','moon','cloud']:
    button=p.locator('[data-action=folder-icon][data-icon='+token+']');button.scroll_into_view_if_needed();button.click()
    art=p.locator('.personalization-art .folder-symbol')
    check(theme+' '+token+' selected artwork and stored preference',button.get_attribute('aria-pressed')=='true' and art.get_attribute('data-folder-symbol')==token and 'folder-icons-cute-1.0.17.png' in art.evaluate('e=>getComputedStyle(e).backgroundImage'))
   p.locator('[data-icon=bunny]').scroll_into_view_if_needed();p.locator('[data-icon=bunny]').click()
   p.screenshot(path=str(SH/(theme+'-chooser.png')),animations='disabled')
   p.emulate_media(reduced_motion='reduce');p.locator('[data-icon=bunny]').hover()
   check(theme+' reduced motion stops icon animation',p.locator('[data-icon=bunny] .picker-symbol').evaluate('e=>getComputedStyle(e).animationName')=='none')
   p.get_by_role('button',name='Done',exact=True).click()
   check(theme+' choice persists on folder',p.locator('.outline-row[data-node="99"] .folder-symbol').get_attribute('data-folder-symbol')=='bunny')
   check(theme+' no workspace horizontal overflow',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
   p.close()
  b.close()
 check('No uncaught errors',not errors)
 (OUT/'results.json').write_text(json.dumps({'runtime_sha256':runtime_digest(),'count':len(checks),'checks':checks,'errors':errors,'category':'shipped frontend and packaged generated raster atlas; synthetic collection, no native Anki claim'},indent=2)+'\n')
 print('Cute icon checks',len(checks))
if __name__=='__main__':run()

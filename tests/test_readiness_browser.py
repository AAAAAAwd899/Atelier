"""Pixel/layout regressions plus keyboard, error, and preservation checks.

Baseline is the exact 0.7.1 installer. This is Chromium, not native Qt.
"""
import io,json,zipfile,tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image,ImageChops
from playwright.sync_api import sync_playwright
import fixtures as fx
import preview_071 as previews
from fixtures import ROOT,SRC,core,card,review
from preview_071 import home071
OUT=ROOT/'dist';OUT.mkdir(exist_ok=True)
checks=[];errors=[];requests=[]
def record(name,**extra):checks.append({'name':name,**extra});print('PASS',name,flush=True)
def home_theme(theme,owner='atelier'):
 soup=BeautifulSoup(home071(owner),'html.parser');boot=json.loads(soup.find(id='atelier-bootstrap').string)
 boot['settings']['theme']=theme;boot['settings']['motion']=False;boot['demo']['settings']=dict(boot['settings']);boot['version']='build'
 soup.find(id='atelier-bootstrap').string=json.dumps(boot)
 return str(soup)
def snap(page):
 return page.evaluate('''()=>{const r=document.getElementById('atelier-root').shadowRoot;return [...r.querySelectorAll('.layout,.sidebar,.topbar,.focus-panel,.library,.lecture-row,.side-exam')].map(e=>{const b=e.getBoundingClientRect();return [e.className,b.x,b.y,b.width,b.height]})}''')
with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
 baseline=Path(tmp)
 with zipfile.ZipFile(ROOT/'tests/data/baseline-071.ankiaddon') as z:
  for name in z.namelist():
   assert not name.startswith('/') and '..' not in Path(name).parts
  z.extractall(baseline)
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 def page(html,w=1440,h=900):
  p=b.new_page(viewport={'width':w,'height':h},reduced_motion='reduce');p.on('pageerror',lambda e:errors.append(str(e)))
  p.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
  p.set_default_timeout(4000);p.set_content(html);p.wait_for_timeout(220);return p
 for theme in core.THEMES:
  fx.SRC=baseline
  before=page(home_theme(theme));layout=snap(before)
  # Wordmark punctuation is the intentionally changed branding; mask that one
  # fixed component. Version text is normalized to the same test value above.
  old=before.screenshot(mask=[before.locator('.brand')]);before.close()
  fx.SRC=SRC
  after=page(home_theme(theme));assert snap(after)==layout,(theme,'layout drift')
  new=after.screenshot(mask=[after.locator('.brand')])
  diff=ImageChops.difference(Image.open(io.BytesIO(old)).convert('RGB'),Image.open(io.BytesIO(new)).convert('RGB'))
  changed=sum(1 for pixel in diff.getdata() if pixel!=(0,0,0))
  if theme in ('obsidian','glacier','bloom','midnight'):
   assert changed==0,(theme,changed)
  else:
   # Four light-theme quiet-text tokens were darkened for legibility, not the
   # surfaces or geometry. Bound the visible change to small text-only areas.
   assert changed<9000,(theme,changed)
  if theme=='midnight':after.screenshot(path=str(OUT/'Atelier-Release-Desk.png'))
  after.close();record(theme+' workspace layout identical to 0.7.1',changed_pixels=changed)
 # Reviewer CSS & JS except version is deliberately frozen; compare all 8.
 for theme in core.THEMES:
  # Only quiet text tokens differ in four palettes; main body uses normal text.
  p=page(card(theme,'basic'),1100,650)
  assert p.evaluate('document.scrollingElement.scrollHeight<=innerHeight+1')
  assert p.evaluate('originalQA===document.getElementById("qa")&&originalHTML===originalQA.innerHTML')
  assert p.locator('.atelier-review-stage').is_hidden()
  p.close();record(theme+' compact question fits viewport and preserves markup')
 # Keyboard focus stays in the existing appearance dialog, Escape exits it.
 p=page(home_theme('obsidian'))
 p.locator('.topbar [data-action="appearance"]').click()
 for _ in range(25):
  p.keyboard.press('Tab')
  assert p.evaluate('''()=>{const r=document.getElementById('atelier-root').shadowRoot;return !!r.activeElement?.closest('.dialog')}''')
 p.keyboard.press('Escape');assert p.locator('.dialog').count()==0
 p.close();record('appearance keyboard focus trap and Escape')
 # Literal malicious deck names must never execute in a search result.
 soup=BeautifulSoup(home_theme('obsidian'),'html.parser');boot=json.loads(soup.find(id='atelier-bootstrap').string)
 hostile='<img src=x onerror="window.injected=true"> & "Deck"'
 for n in boot['demo']['nodes']:
  if not n['children']:n['name']=hostile;n['path']=hostile;break
 soup.find(id='atelier-bootstrap').string=core.json_for_html(boot)
 p=page(str(soup));p.locator('.search input').fill('onerror');p.wait_for_timeout(120)
 assert not p.evaluate('Boolean(window.injected)')
 assert not p.locator('img[onerror]').count()
 p.close();record('deck names remain escaped text in search results')
 # Reduced-motion is retained, not reset by the release work.
 p=page(home_theme('midnight'));p.locator('.topbar [data-action="appearance"]').click()
 durations=p.locator('.dialog').evaluate('e=>[getComputedStyle(e).animationDuration,getComputedStyle(e).transitionDuration]')
 assert durations==['0s','0s'],durations
 p.close();record('reduced-motion preference retained')
 # Without an installed Sprout component, Practice provides information, not a
 # fake exam session or a scheduler write.
 soup=BeautifulSoup(home_theme('obsidian'),'html.parser');boot=json.loads(soup.find(id='atelier-bootstrap').string)
 boot['integrations']['exam_sprout']=False;soup.find(id='atelier-bootstrap').string=core.json_for_html(boot)
 for n in soup.select('#es-countdowns'):n.decompose()
 p=page(str(soup));buttons=p.locator('[data-action="sprout-practice"]:visible')
 if buttons.count():
  buttons.first.click();assert p.get_by_text('Practice exams use Exam Sprout.',exact=False).is_visible()
 p.close();record('missing Sprout does not fabricate a practice run')
 # No new outgoing resource requests from the release screens.
 assert not errors,errors
 # Existing independent fixture has no network assets; if this changes, fail.
 assert not requests,requests
 record('zero uncaught browser errors and zero HTTP requests in audited screens')
 b.close()
(OUT/'readiness-browser.json').write_text(json.dumps({'count':len(checks),'checks':checks,'errors':errors,'requests':requests},indent=2)+'\n')
print('TOTAL',len(checks),'PASS')

"""Exact user-uploaded Atelier front-end compatibility, with explicit synthetic Anki boot data."""
from pathlib import Path
import json,sys,zipfile,hashlib
from playwright.sync_api import sync_playwright
from ui_harness import Host,ROOT
ATELIER=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/Atelier(1).ankiaddon')
with zipfile.ZipFile(ATELIER) as z:
 acss=z.read('web/atelier.css').decode();ajs=z.read('web/atelier.js').decode();manifest=json.loads(z.read('manifest.json'))
h=Host();from addon.integration import Controller
markup=Controller.home_html(h.workspace.controller);js=(ROOT/'addon/web/home.js').read_text();css=(ROOT/'addon/web/home.css').read_text()
config={'theme':'obsidian','mode':'workspace','density':'comfortable','motion':True,'chrome':True,'view':'grid','sort':'name'}
profile={'favorites':['1'],'folders':['1'],'colors':{},'last_location':'0'}
nodes=[{'id':'1','name':'Study materials','path':'Study materials','parent':'0','children':['11'],'depth':0,'filtered':False,'new':12,'learn':3,'review':24},{'id':'11','name':'Source-aware authoring','path':'Study materials::Source-aware authoring','parent':'1','children':[],'depth':1,'filtered':False,'new':12,'learn':3,'review':24}]
demo={'settings':config,'profile':profile,'nodes':nodes,'totals':{'new':12,'learn':3,'review':24},'current':'11','studied':'Sample data. No actual review history.'}
boot={'version':manifest['human_version'],'token':'fixture','settings':config,'profile':profile,'ui':{},'openSettings':False,'preview':True,'demo':demo}
def html(order):
 scripts=[ajs,js] if order=='atelier-first' else [js,ajs]
 return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#171c1b;color:white;font:14px Arial}'+css+'</style></head><body><div id="atelier-root"></div><script id="atelier-bootstrap" type="application/json">'+json.dumps(boot).replace('<','\\u003c')+'</script><template id="atelier-style"><style>'+acss+'</style></template><div id="native-home"><div id="native-stats">Native statistics</div>'+markup+'</div><script>window.commands=[];window.pycmd=m=>commands.push(m);window.statsOriginal=document.getElementById("native-stats");</script>'+''.join('<script>'+s+'</script>' for s in scripts)+'</body></html>'
checks=[];errors=[]
def check(name,value):
 assert value,name
 checks.append(name);print('PASS',name,flush=True)
def state(p):return p.evaluate("()=>{const r=document.querySelector('#ws-home'),h=document.querySelector('#atelier-root');return {count:document.querySelectorAll('#ws-home').length,slot:r.slot,visible:!!r.getClientRects().length,overflow:document.documentElement.scrollWidth>innerWidth,expected:getComputedStyle(h).getPropertyValue('--text').trim(),actual:getComputedStyle(r).color,raw:r.style.getPropertyValue('--ws-host-text').trim(),host:r.parentElement.id};}")
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for order in ('atelier-first','workshop-first'):
  p=b.new_page(viewport={'width':1400,'height':1000});p.set_default_timeout(5000);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html(order));p.wait_for_function('document.body.classList.contains("atelier-home")')
  st=state(p);print(order,st,flush=True);check(order+': one visible additive slot',st['count']==1 and st['visible'] and st['slot']=='atelier-widgets')
  p.locator('#ws-home button').click();check(order+': one bridge command',p.evaluate('commands')==['workshop:open'])
  p.close()
 p=b.new_page(viewport={'width':1400,'height':1000});p.set_default_timeout(5000);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html('atelier-first'));p.wait_for_function('document.body.classList.contains("atelier-home")')
 p.evaluate("()=>{const d=document.createElement('div');d.id='other-widget';d.slot='atelier-widgets';d.textContent='Other add-on widget';document.querySelector('#atelier-root').append(d);window.otherWidget=d;}")
 for theme in ('obsidian','glacier','rose','bloom','linen','matcha','midnight','peach'):
  p.evaluate('window.AtelierMakeover.openAppearance()');p.locator('[data-theme-choice="'+theme+'"]').click();p.locator('.dialog-footer [data-action="close-dialog"]').click()
  st=state(p);check(theme+': mounted once and themed',st['count']==1 and st['visible'] and st['raw']==st['expected'])
  check(theme+': other widget remains identical',p.evaluate('document.querySelector("#other-widget")===otherWidget'))
 for w in (390,680,920,1100,1440):
  p.set_viewport_size({'width':w,'height':900});check(str(w)+'px: no horizontal overflow',not state(p)['overflow'])
 p.set_viewport_size({'width':1440,'height':1000})
 p.locator('.card-bottom [data-action="navigate"][data-id="1"]').click();check('Atelier folder navigation preserves Workshop',state(p)['visible'])
 p.evaluate('window.AtelierMakeover.openAppearance()');p.locator('#setting-mode').select_option('native');check('Classic view restores original native location',state(p)['host']=='native-home')
 p.locator('.dialog-footer [data-action="close-dialog"]').click();p.locator('[data-action="workspace"]').click();check('Workspace returns to existing integration slot',state(p)['slot']=='atelier-widgets')
 for i in range(5):p.add_script_tag(content=js)
 p.evaluate('commands=[];for(let i=0;i<50;i++)WorkshopHome.mount()');p.locator('#ws-home button').click();check('Repeated scripts and mounts retain one listener',p.evaluate('commands.length')==1 and state(p)['count']==1)
 check('Original native statistics survive unchanged',p.evaluate('document.querySelector("#native-stats")===statsOriginal'))
 p.evaluate('WorkshopHome.mount("")');check('Hidden home setting removes only our widget',p.locator('#ws-home').count()==0 and p.locator('#other-widget').count()==1)
 p.evaluate('h=>WorkshopHome.mount(h)',markup);check('Re-enable recreates one small entry',state(p)['count']==1 and state(p)['visible'])
 check('No uncaught Atelier/Workshop errors',not errors)
 b.close()
(ROOT/'docs/home-results.json').write_text(json.dumps({'count':len(checks),'checks':checks,'page_errors':errors,'atelier_version':manifest['human_version'],'atelier_sha256':hashlib.sha256(ATELIER.read_bytes()).hexdigest(),'native_anki':False},indent=2))
print(json.dumps({'passed':len(checks),'errors':errors},indent=2))

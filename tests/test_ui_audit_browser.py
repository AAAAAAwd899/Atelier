"""Live state, icons, sorting, keyboard, compact-window and encoding audit.
Tests the current renderer rather than screenshots or a static mockup.
"""
from suite_fixtures import *
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json,re
OUT=ROOT/'verification/ui-audit';OUT.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[]
def check(name,value=True):
 assert value,name
 CHECKS.append(name);print('PASS',name,flush=True)

def live_doc(theme='midnight'):
 soup=BeautifulSoup(home_suite(theme),'html.parser');tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
 boot['preview']=False;tag.string=core.json_for_html(boot)
 script=soup.new_tag('script')
 script.string='''window.auditConfig=CONFIG;window.auditLoad=DATA;window.settingsQueue=[];
 window.answerSetting=(ok=true)=>{const x=settingsQueue.shift();if(!x)throw Error('No pending setting');if(ok)Object.assign(auditConfig,x.data);AtelierMakeover.receive({token:TOKEN,id:x.id,...(ok?{result:{...auditConfig}}:{error:'Simulated settings save failure'})})};
 window.pycmd=msg=>{if(!msg.startsWith('atelier:v1:'))return;const p=JSON.parse(msg.split(':').slice(3).join(':'));if(p.action==='settings'){settingsQueue.push(p);return} const result=p.action==='load'?{...auditLoad,settings:{...auditConfig}}:true;queueMicrotask(()=>AtelierMakeover.receive({token:TOKEN,id:p.id,result}));};'''.replace('CONFIG',core.json_for_html(boot['settings'])).replace('DATA',core.json_for_html(boot['demo'])).replace('TOKEN',json.dumps(boot['token']))
 soup.body.insert(0,script);return str(soup)

def sort_doc():
 soup=BeautifulSoup(home_suite('forest'),'html.parser');tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
 nodes=[{'id':'90','name':'Course','path':'Course','parent':'0','children':['91','92','99'],'depth':0,'review':9,'learn':4,'new':20,'filtered':False},
 {'id':'91','name':'Lecture 10','path':'Course::Lecture 10','parent':'90','children':[],'depth':1,'review':0,'learn':2,'new':3,'filtered':False},
 {'id':'92','name':'Lecture 2','path':'Course::Lecture 2','parent':'90','children':[],'depth':1,'review':6,'learn':0,'new':2,'filtered':False},
 {'id':'99','name':'Seminar','path':'Course::Seminar','parent':'90','children':['991','992'],'depth':1,'review':3,'learn':2,'new':15,'filtered':False},
 {'id':'991','name':'Topic 10','path':'Course::Seminar::Topic 10','parent':'99','children':[],'depth':2,'review':0,'learn':0,'new':5,'filtered':False},
 {'id':'992','name':'Topic 2','path':'Course::Seminar::Topic 2','parent':'99','children':[],'depth':2,'review':3,'learn':2,'new':10,'filtered':False}]
 profile={**boot['profile'],'studies':[{'id':'one','name':'Upcoming exam','date':'2026-09-30','deck_ids':['90'],'active':True}],'focus_enabled':True,'selected_study':'all','folders':[],'recent_locations':['91','92'],'recent_added':[{'id':'992','observed':'2026-09-11T12:00:00Z'},{'id':'991','observed':'2026-09-10T12:00:00Z'}]}
 boot['profile']=profile;boot['demo'].update(profile=profile,nodes=nodes);boot['settings']['sort']='name';boot['demo']['settings']['sort']='name';tag.string=core.json_for_html(boot);return str(soup)

def large_doc():
 soup=BeautifulSoup(home_suite('obsidian',page='library'),'html.parser');tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
 nodes=[]
 for c in range(50):
  parent=str(10000+c);name=f'Course {c+1}';ids=[]
  for i in range(99):
   did=str(20000+c*100+i);ids.append(did)
   nodes.append({'id':did,'name':f'Lecture {i+1}','path':name+f'::Lecture {i+1}','parent':parent,'children':[],'depth':1,'new':5,'review':i%4,'learn':i%2,'filtered':False})
  nodes.append({'id':parent,'name':name,'path':name,'parent':'0','children':ids,'depth':0,'new':495,'review':100,'learn':45,'filtered':False})
 boot['profile'].update(studies=[],focus_enabled=False,folders=[],selected_study='all');boot['demo'].update(nodes=nodes,profile=boot['profile']);tag.string=core.json_for_html(boot)
 return str(soup)

def run():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),args=['--no-sandbox'])
  def page(doc,width=1440,height=960):
   p=b.new_page(viewport={'width':width,'height':height});p.set_default_timeout(7000);p.on('pageerror',lambda e:ERRORS.append(str(e)));p.set_content(doc);p.locator('.world-window').wait_for();return p
  def status(p):return p.evaluate("()=>{const h=document.querySelector('#atelier-root'),r=h.shadowRoot,w=r.querySelector('.world-window');return {theme:h.dataset.theme,label:w.querySelector('small').textContent,title:w.querySelector('strong').textContent,world:w.dataset.world,aria:w.getAttribute('aria-label'),art:getComputedStyle(w).backgroundImage,side:r.querySelector('.appearance-link small').textContent}}")
  p=page(home_suite('midnight'));p.locator('.unified-topbar [data-action=appearance]').click()
  p.evaluate("window.keptDialog=document.querySelector('#atelier-root').shadowRoot.querySelector('.dialog');window.keptPreview=document.querySelector('#atelier-root').shadowRoot.querySelector('.world-window')")
  for w in worlds.CATALOG:
   p.locator('[data-theme-choice='+w['id']+']').click();p.wait_for_timeout(45);s=status(p)
   check('Live switch '+w['name']+' aligns name/title/artwork/ARIA/selection',s['theme']==s['world']==w['id'] and s['label']==w['name'] and s['title']==w['title'] and w['name'] in s['aria'] and w['name'] in s['side'] and s['art']!='none' and p.locator('[data-theme-choice='+w['id']+']').get_attribute('aria-pressed')=='true')
   check(w['name']+' keeps existing dialog and world-preview nodes',p.evaluate("keptDialog===document.querySelector('#atelier-root').shadowRoot.querySelector('.dialog')&&keptPreview===document.querySelector('#atelier-root').shadowRoot.querySelector('.world-window')"))
  p.locator('[data-action=close-dialog]').first.click();p.close()
  # Live native-shaped settings bridge with queued replies and failed save.
  p=page(live_doc());p.locator('.unified-topbar [data-action=appearance]').click()
  p.locator('[data-theme-choice=rose]').click();p.wait_for_function('settingsQueue.length===1');check('Optimistic theme updates semantic label before host reply',status(p)['label']=='Rose Quartz')
  p.evaluate('answerSetting(false)');p.wait_for_timeout(80);check('Failed save restores artwork/name/selection together',status(p)['label']=='Midnight' and status(p)['theme']=='midnight' and p.locator('[data-theme-choice=midnight]').get_attribute('aria-pressed')=='true')
  p.locator('[data-theme-choice=rose]').click();p.locator('[data-theme-choice=forest]').click();p.wait_for_function('settingsQueue.length===1');p.evaluate('answerSetting(true)');p.wait_for_function('settingsQueue.length===1')
  check('Delayed earlier save cannot overwrite newer world label',status(p)['label']=='Forest');p.evaluate('answerSetting(true)');p.wait_for_timeout(60);check('Latest saved theme settles correctly',status(p)['world']=='forest')
  p.locator('#setting-density').select_option('compact');p.wait_for_function('settingsQueue.length===1');p.evaluate('answerSetting(false)');p.wait_for_timeout(60);check('Failed select save restores visible control as well as settings',p.locator('#setting-density').input_value()=='comfortable')
  p.close()
  p=page(home_suite('rose'));p.locator('.unified-topbar [data-action=appearance]').click()
  p.evaluate("window.keptDialog=document.querySelector('#atelier-root').shadowRoot.querySelector('.dialog');window.auditToken=JSON.parse(document.querySelector('#atelier-bootstrap').textContent).token")
  p.evaluate("AtelierMakeover.applyAppearance({token:auditToken,settings:{theme:'forest'}})")
  check('Planner-origin world delivery updates home label without remounting settings',status(p)['label']=='Forest' and p.evaluate("keptDialog===document.querySelector('#atelier-root').shadowRoot.querySelector('.dialog')"))
  p.evaluate("AtelierMakeover.applyAppearance({token:'stale-page',settings:{theme:'rose'}})")
  check('Old-page world delivery is ignored',status(p)['label']=='Forest');p.close()
  # Visible sort never lies about a different ordering rule.
  p=page(sort_doc());ids=lambda:p.locator('.lecture-row').evaluate_all('x=>x.map(n=>n.dataset.node)')
  check('Active lecture board exposes sibling sorting',p.locator('#atelier-sort').is_visible() and ids()==['99','992','991','92','91'])
  p.locator('#atelier-sort').select_option('due');p.wait_for_timeout(80);check('Review+learning sort reorders siblings and keeps descendants with parent',ids()==['92','99','992','991','91'])
  p.locator('#atelier-sort').select_option('recent');p.wait_for_timeout(80);check('Recent lecture sort preserves ancestry',ids()==['91','92','99','992','991'])
  p.locator('[data-action=lecture-expand]').first.click();p.locator('#atelier-sort').select_option('name');p.wait_for_timeout(80);check('Changing sort does not reopen collapsed branches',ids()==['99','92','91'])
  p.locator('[data-page=recent]').first.click();check('Recent page shows explicit chronology, not an ineffective sorter',p.locator('#atelier-sort').count()==0 and p.locator('.recent-order').inner_text()=='Newest first')
  check('Recently opened order is genuinely most-recent-first',p.locator('.deck-card').evaluate_all('x=>x.map(n=>n.dataset.node)')==['91','92'])
  p.locator('[data-filter=added]').click();check('Recently added retains observed order',p.locator('.deck-card').evaluate_all('x=>x.map(n=>n.dataset.node)')==['992','991'])
  p.locator('[data-page=library]').first.click();p.locator('.deck-card[data-node="90"] .card-title').click();p.locator('#atelier-sort').select_option('name');p.wait_for_timeout(70)
  check('Library natural names and folder-first label agree',p.locator('.deck-card').evaluate_all('x=>x.map(n=>n.dataset.node)')==['99','92','91'])
  p.locator('[data-action=view][data-view=list]').click();check('Grid to list retains identical sort order',p.locator('.deck-card').evaluate_all('x=>x.map(n=>n.dataset.node)')==['99','92','91'])
  p.locator('[data-action=up]').first.click();check('Parent navigation returns to root',p.locator('.deck-card').count()==1)
  p.close()
  for width,height in [(320,540),(390,640),(768,720),(1024,650),(1440,900),(1725,900)]:
   p=page(home_suite('rose'),width,height)
   for cmd in ['add','browse','sync']:check(str(width)+' top '+cmd+' is visible and has reachable hit target',p.locator('.unified-topbar [data-command='+cmd+']').is_visible() and p.locator('.unified-topbar [data-command='+cmd+']').evaluate('el=>{const r=el.getBoundingClientRect(),hit=el.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2);return el===hit||el.contains(hit)}'))
   check(str(width)+' search remains visible',p.locator('#atelier-search').is_visible());p.locator('#atelier-search').fill('Nothing matches qwerty123');check(str(width)+' search empty-state usable',p.locator('.empty h3').inner_text()=='No matching folders or decks.')
   p.locator('[data-action=clear-search]').click();p.locator('.unified-topbar [data-action=appearance]').click()
   for w in ['forest','rose']:
    p.locator('[data-theme-choice='+w+']').click()
   check(str(width)+' dialog footer is reachable and theme name current',status(p)['label']=='Rose Quartz' and p.locator('.dialog-footer').is_visible())
   p.keyboard.press('Escape');check(str(width)+' Escape closes theme dialog',p.locator('.dialog').count()==0)
   # Fill real search with multilingual data; no replacement characters.
   text='Électrolytes — 心臓 · الجرعة 💚';p.locator('#atelier-search').fill(text);check(str(width)+' Unicode input survives renderer',p.locator('#atelier-search').input_value()==text);p.keyboard.press('Escape')
   if width<=820:
    p.locator('[data-action=mobile]').click();p.locator('[data-page=tools]').first.click()
   else:p.locator('[data-page=tools]').first.click()
   check(str(width)+' tools main area does not overflow horizontally',p.evaluate("()=>{const n=document.querySelector('#atelier-root').shadowRoot.querySelector('.main');return n.scrollWidth<=n.clientWidth+1}"))
   p.screenshot(path=str(OUT/f'tools-{width}.png'),animations='disabled');p.close()
  p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:ERRORS.append(str(e)));p.set_content(large_doc());p.locator('.deck-card').first.wait_for()
  check('5,000-deck catalog renders bounded initial library and sidebar',p.locator('.deck-card').count()==50 and p.locator('.tree-row').count()<=240)
  p.locator('#atelier-search').fill('Lecture');p.locator('[data-action=more-results]').wait_for()
  check('Large search returns 60 rows initially without dropping total',p.locator('.deck-card').count()==60 and '4950' in p.locator('.library-foot').inner_text().replace(',',''))
  p.locator('[data-action=more-results]').click();check('Large search pagination exposes the next 60 rows',p.locator('.deck-card').count()==120)
  p.locator('#atelier-sort').select_option('name');p.wait_for_timeout(60)
  names=p.locator('.card-title').all_text_contents();check('Large search uses natural lecture numbers across courses',names[0]=='Lecture 1' and names[50]=='Lecture 2');p.close()
  p=page(home_suite('rose'));p.locator('[data-page=tools]').first.click()
  glyphs=p.locator('.tool-tile').evaluate_all('xs=>xs.map(x=>({cmd:x.dataset.command,icon:x.querySelector("svg").dataset.icon,geometry:x.querySelector("svg").innerHTML}))')
  check('All 19 native tool tiles have distinct, semantically named SVGs',len({x['geometry'] for x in glyphs})==19)
  check('Sync and refresh-library have distinct icons',p.locator('.sync-top svg').get_attribute('data-icon')=='sync' and p.locator('.refresh-library svg').get_attribute('data-icon')=='reload')
  unnamed=p.locator('button:visible').evaluate_all('xs=>xs.filter(x=>!((x.getAttribute("aria-label")||x.getAttribute("title")||x.innerText).trim())).map(x=>x.outerHTML)')
  check('Visible tool/home navigation buttons all have accessible text or labels',not unnamed)
  check('Small identity copy is readable text, not a font-icon or replacement sequence',p.locator('.brand small').inner_text().startswith('Your space to learn') and '\ufffd' not in p.locator('.brand').inner_text())
  p.close();b.close()
 check('No uncaught page exceptions in added audit workflows',not ERRORS)
 (OUT/'results.json').write_text(json.dumps({'count':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'native_windows_verified':False},indent=2))
 print('TOTAL',len(CHECKS),'PASS')
if __name__=='__main__':run()

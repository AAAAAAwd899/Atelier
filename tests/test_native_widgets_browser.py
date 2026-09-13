"""Real current widget frontend with an explicit bridge double, no Onigiri DOM.
Preserves native Anki command IDs. Never opens a real collection or provider.
"""
from pathlib import Path
import copy,json,sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from suite_fixtures import ROOT,SRC,core,home_suite
OUT=ROOT/'verification/native-widgets';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/native-widgets';SH.mkdir(parents=True,exist_ok=True)

def native_fixture(theme='ember',live=True,profile=None,onigiri=False,page='widgets'):
 s=BeautifulSoup(home_suite(theme,page=page),'html.parser')
 boot=json.loads(s.find(id='atelier-bootstrap').string)
 boot['integrations'].update(onigiri=onigiri,makeovers=[])
 s.title.string='Atelier '+core.VERSION+' · Widgets preview'
 boot['preview']=not live
 boot['demoNow']='2026-09-12T12:00:00'
 if profile:boot['profile'].update(copy.deepcopy(profile))
 boot['demo']['profile']=copy.deepcopy(boot['profile'])
 boot['demo']['settings']=copy.deepcopy(boot['settings'])
 if not onigiri:
  for n in s.select('.modern-main-menu'):n.decompose()
  for script in list(s.find_all('script')):
   if 'window.nativeSnapshot=' in (script.string or ''):script.decompose()
  note=s.new_tag('p');note['id']='original-native-fixture';note.string='Original Anki fixture — no Onigiri installed';s.body.insert(0,note)
 s.find(id='atelier-bootstrap').string=core.json_for_html(boot)
 tag=s.new_tag('script');tag.string='''
 window.widgetCalls=[];window.widgetSaved=BOOTDATA;window.widgetFailPrefs=false;window.widgetFailProgress=false;window.widgetDelay=0;window.widgetHold=false;window.widgetHeld=[];window.widgetZero=false;
 window.pycmd=(msg)=>{
  if(!msg.startsWith('atelier:v1:'))return;
  const req=JSON.parse(msg.slice(('atelier:v1:'+TOKEN+':').length));widgetCalls.push(req);
  let result=true,error='';const d=req.data, p=widgetSaved.profile;
  if(req.action==='load')result=JSON.parse(JSON.stringify(widgetSaved));
  else if(req.action==='settings'){Object.assign(widgetSaved.settings,d);result=widgetSaved.settings;}
  else if(req.action==='preference'){
   if(widgetFailPrefs){widgetFailPrefs=false;error='Fixture disk full. Your changes were not saved.';}
   else {
    if(d.key==='native_widgets')p.native_widgets=JSON.parse(JSON.stringify(d.value));
    else if(d.key==='native_widget_note')p.native_widget_note=d.value;
    else if(d.key==='selected_study')p.selected_study=d.value;
    else if(d.key==='focus_enabled')p.focus_enabled=d.value;
    else if(d.key==='study_active'){const st=p.studies.find(x=>x.id===d.id);if(st)st.active=d.value;if(!d.value&&p.selected_study===d.id)p.selected_study='all';}
    else if(d.key==='study'){const i=p.studies.findIndex(x=>x.id===d.value.id);if(i<0)p.studies.push(d.value);else p.studies[i]=d.value;}
    else if(d.key==='last_location'){p.last_location=d.value;p.recent_locations=[d.value,...p.recent_locations.filter(x=>x!==d.value)];}
    else if(d.key==='favorites'){p.favorites=p.favorites.filter(x=>x!==d.id);if(d.value)p.favorites.push(d.id);}
    else {error='Unsupported preference in bridge fixture: '+d.key;}
    result=JSON.parse(JSON.stringify(p));
   }
  }else if(req.action==='study_progress'){
    if(widgetFailProgress){widgetFailProgress=false;error='Fixture history unavailable. Retry after the operation.';}
    const daily=Array.from({length:7},(_,i)=>({label:'2026-09-'+String(i+6).padStart(2,'0'),reviews:widgetZero?0:10+i,cards:widgetZero?0:4+i,minutes:widgetZero?0:1.5+i,again:0}));
    result={days:7,daily,scope:d.scope,deck_count:2,reviews:daily.reduce((a,d)=>a+d.reviews,0),cards:20,minutes:35,again:0,days_studied:widgetZero?0:7,decks:[],attribution:'Bridge fixture only'};
  }else if(!['focus','ui','companion_palette','native_tool','suite_open','authoring_open','study_now','study','browse','options','export_deck'].includes(req.action)){error='Unsupported bridge fixture action: '+req.action;}
  const reply={token:TOKEN,id:req.id,result,error};
  if(req.action==='study_progress'&&widgetHold){widgetHeld.push(reply);return;}
  setTimeout(()=>window.AtelierMakeover.receive(reply),widgetDelay);
 };
 '''.replace('BOOTDATA',core.json_for_html(boot['demo'])).replace('TOKEN',json.dumps(boot['token']))
 s.head.append(tag)
 return str(s)


def run():
 checks=[];errors=[]
 def check(name,value):
  assert value,name
  checks.append(name);print('PASS',name,flush=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=browser.new_page(viewport={'width':1440,'height':1000});p.set_default_timeout(8000);p.on('pageerror',lambda e:errors.append(str(e)))
  def load(theme='ember',**kwargs):
   p.set_content(native_fixture(theme,**kwargs));p.locator('.nw-toolbar').wait_for();p.locator('.nw-metrics').wait_for();p.wait_for_timeout(50)
  def click(selector):p.locator(selector).first.click();p.wait_for_timeout(80)
  def arrange():click('.nw-header [data-action="nw-arrange"]');p.locator('.nw-arranged-list').wait_for()
  def close():p.keyboard.press('Escape');p.wait_for_timeout(60)
  def shot(name):p.screenshot(path=str(SH/(name+'.png')),animations='disabled')
  def saved():return p.evaluate('widgetSaved.profile.native_widgets')
  try:
   load()
   check('Page runs without Onigiri markup or global',p.locator('.modern-main-menu').count()==0 and p.evaluate('typeof window.Onigiri==="undefined"'))
   check('Exactly three primary header actions',p.locator('.nw-toolbar button').all_text_contents()==['Quick study','Practice exam','More tools'])
   check('Sidebar leads directly to the native widget page',p.locator('.native-link[data-action="widget-page"]').get_attribute('aria-current')=='page')
   check('Real today scope is requested once',len(p.evaluate('widgetCalls.filter(x=>x.action==="study_progress")'))==1)
   check('Current day cards and events are not conflated',p.locator('.nw-metrics strong').all_text_contents()==['16','10','7.5'])
   check('Activity makes no retention or mastery claim','Practice mocks stay separate' in p.locator('.nw-definitions').inner_text())
   p.evaluate('window.mountedToday=document.querySelector("#atelier-root").shadowRoot.querySelector("#nw-today-content")')
   for theme in core.THEMES:
    p.evaluate('(theme)=>AtelierMakeover.applyAppearance({token:"preview",settings:{theme}})',theme);p.wait_for_timeout(65)
    check(theme+' applies to the existing widget canvas',p.locator('#atelier-root').get_attribute('data-theme')==theme and p.evaluate('mountedToday===document.querySelector("#atelier-root").shadowRoot.querySelector("#nw-today-content")'))
    check(theme+' contained desktop widgets',p.locator('.nw-grid').evaluate('e=>e.scrollWidth<=e.clientWidth+2'))
    shot(theme+'-widgets')
   check('Theme changes do not reread study history',len(p.evaluate('widgetCalls.filter(x=>x.action==="study_progress")'))==1)
   for width,height in [(320,540),(390,740),(620,650),(940,760),(1440,900),(1725,900)]:
    p.set_viewport_size({'width':width,'height':height});p.wait_for_timeout(100)
    check(str(width)+' native widget page no horizontal overflow',p.locator('.main').evaluate('e=>e.scrollWidth<=e.clientWidth+2'))
    check(str(width)+' widget controls not under header',p.locator('.nw-toolbar').evaluate('e=>e.getBoundingClientRect().top>=e.getRootNode().querySelector(".nw-header").getBoundingClientRect().bottom-1'))
    click('.nw-toolbar [data-action="nw-tools"]');p.locator('.nw-tools-list').wait_for()
    check(str(width)+' More tools dialog has reachable actions',p.locator('.dialog').evaluate('e=>{let r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1}') and p.locator('.dialog-footer [data-action="close-dialog"]').is_visible())
    close();arrange()
    check(str(width)+' Arrange grid fits dialog',p.locator('.dialog-body').evaluate('e=>e.scrollWidth<=e.clientWidth+2'))
    p.locator('.dialog [data-action="nw-save"]').scroll_into_view_if_needed()
    check(str(width)+' Save layout can actually be hit',p.locator('.dialog [data-action="nw-save"]').evaluate('e=>{let r=e.getBoundingClientRect();return e.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest("button")===e}'))
    close()
    if width==390:shot('widgets-narrow')
   p.set_viewport_size({'width':1440,'height':1000})
   # Staged customization, failed-save preservation, persistence and home visibility.
   arrange();initial=p.locator('[data-widget-setting]').count();click('[data-action="nw-add"][data-id="notes"]')
   check('Add does not save until Save layout',saved() is None or not any(x['id']=='notes' for x in saved()['items']))
   check('Added widget gets a keyboard target',p.evaluate('document.querySelector("#atelier-root").shadowRoot.activeElement?.closest("[data-widget-setting]")?.dataset.widgetSetting')=='notes')
   close();arrange();check('Cancel kept prior layout',p.locator('[data-widget-setting]').count()==initial)
   click('[data-action="nw-add"][data-id="notes"]');p.locator('[data-nw-home="notes"]').check();p.locator('[data-nw-size="notes"]').select_option('wide')
   click('[data-action="nw-up"][data-id="notes"]')
   check('Move preserves keyboard focus on moved row',p.evaluate('document.querySelector("#atelier-root").shadowRoot.activeElement?.dataset.id')=='notes')
   p.evaluate('widgetFailPrefs=true');click('[data-action="nw-save"]')
   check('Failed layout save remains in dialog with error',p.locator('.nw-arranged-list').is_visible() and 'disk full' in p.locator('.dialog-alerts').inner_text())
   check('Failed save retains size/home selections',p.locator('[data-nw-home="notes"]').is_checked() and p.locator('[data-nw-size="notes"]').input_value()=='wide')
   click('[data-action="nw-save"]');p.locator('[data-native-widget="notes"]').wait_for()
   check('Layout save stores exact ordered selection',saved()['items'][-2]=={'id':'notes','size':'wide','home':True})
   click('[data-native-widget="notes"] [data-action="nw-note"]');p.locator('#nw-note-input').fill('Study lecture 2. 🌲\n<img src=x onerror="window.badNote=true">')
   p.evaluate('window.noteNode=document.querySelector("#atelier-root").shadowRoot.querySelector("#nw-note-input")')
   p.evaluate('AtelierMakeover.applyAppearance({token:"preview",settings:{theme:"forest"}})')
   check('Note text and node survive a world change',p.evaluate('noteNode===document.querySelector("#atelier-root").shadowRoot.querySelector("#nw-note-input")') and p.locator('#nw-note-input').input_value().startswith('Study lecture'))
   p.evaluate('widgetFailPrefs=true');click('[data-action="nw-note-save"]')
   check('Failed note save retains unsaved text',p.locator('#nw-note-input').input_value().startswith('Study lecture') and 'disk full' in p.locator('.dialog-alerts').inner_text())
   click('[data-action="nw-note-save"]');p.locator('.nw-note-text').wait_for()
   check('Note is escaped text, not HTML or scripts',p.locator('.nw-note-text img').count()==0 and not p.evaluate('window.badNote||false') and '<img' in p.locator('.nw-note-text').inner_text())
   click('.nav-row[data-action="home"]');p.locator('.nw-on-home').wait_for()
   check('Chosen home widget appears once on main Study desk',p.locator('.nw-on-home [data-native-widget="notes"]').count()==1 and p.locator('.nw-on-home [data-native-widget="today"]').count()==0)
   click('.native-link[data-action="widget-page"]');p.locator('.nw-toolbar').wait_for();arrange();click('[data-action="nw-remove"][data-id="notes"]');click('[data-action="nw-save"]')
   check('Removing note widget does not erase its saved note',p.evaluate('widgetSaved.profile.native_widget_note.startsWith("Study lecture")'))
   arrange();click('[data-action="nw-add"][data-id="notes"]');click('[data-action="nw-save"]')
   check('Re-added note restores the same data',p.locator('.nw-note-text').inner_text().startswith('Study lecture'))
   p.evaluate('AtelierMakeover.updateAuthoring({token:"preview",authoring:{available:true,projects:2,drafts:42,repairs:3}})')
   check('Live card work badges update without full page refresh','42 drafts' in p.locator('[data-native-widget="work"]').inner_text())
   p.evaluate('AtelierMakeover.updateAuthoring({token:"preview",authoring:{available:true,projects:1,drafts:1,repairs:1}})')
   check('Singular draft and repair labels are correct','1 draft to review' in p.locator('[data-native-widget="work"]').inner_text() and '1 repair to check' in p.locator('[data-native-widget="work"]').inner_text())
   shot('native-forest-with-note')
   # Actions remain the same existing routes, not copied alternatives.
   for command in ['add','browse','sync']:
    click('.nw-toolbar [data-action="nw-tools"]');click('.nw-tools-list [data-action="native-tool"][data-command="'+command+'"]')
    check(command+' uses native tool route',p.evaluate('widgetCalls.filter(x=>x.action==="native_tool").at(-1).data.command')==command)
   click('.nw-toolbar [data-action="nw-tools"]');click('.nw-tools-list [data-action="suite-open"]')
   check('Exam Studio is existing suite route',p.evaluate('widgetCalls.filter(x=>x.action==="suite_open").at(-1).data.view')=='overview')
   click('.nw-toolbar [data-action="nw-tools"]');click('.dialog [data-action="export-picker"]');p.locator('#export-search').wait_for();check('Export retains searchable native export chooser',p.locator('.export-row').count()>0);close()
   # Active-group removal and Undo use existing profile actions.
   n=p.locator('[data-native-widget="focus"] .nw-focus-row').count();click('[data-native-widget="focus"] [data-action="finish-study"]')
   check('Active group removal does not erase other groups',p.locator('[data-native-widget="focus"] .nw-focus-row').count()==n-1)
   click('[data-action="undo-exam"]')
   check('Existing Undo restores active group',p.locator('[data-native-widget="focus"] .nw-focus-row').count()==n)
   # Reload, zero, error and stale-study safeguards.
   p.evaluate('widgetFailProgress=true');click('[data-native-widget="today"] [data-action="nw-reload"]')
   p.locator('#nw-today-content [role="alert"]').wait_for();check('History error is not fabricated zero activity','history unavailable' in p.locator('#nw-today-content').inner_text() and p.locator('.nw-metrics').count()==0)
   p.evaluate('widgetZero=true');click('#nw-today-content [data-action="nw-reload"]');p.locator('.nw-metrics').wait_for()
   check('A real zero result is distinct from failure',p.locator('.nw-metrics strong').all_text_contents()==['0','0','0'] and 'No recorded answers' in p.locator('.nw-definitions').inner_text())
   p.evaluate('widgetZero=false;widgetHold=true');click('[data-native-widget="today"] [data-action="nw-reload"]')
   p.wait_for_function('widgetHeld.length>0');p.evaluate('widgetSaved.profile.selected_study="cardio";AtelierMakeover.reload()');p.wait_for_function('widgetHeld.length>1')
   p.evaluate('AtelierMakeover.receive(widgetHeld[0])');p.wait_for_timeout(40)
   check('Late previous-scope reply not shown as current data',p.locator('.nw-metrics').count()==0)
   p.evaluate('widgetHold=false;AtelierMakeover.receive(widgetHeld.at(-1))');p.locator('.nw-metrics').wait_for()
   check('Current scope reply populates the widget',p.locator('[data-native-widget="today"] .nw-caption').first.inner_text()=='Cardiology · Exam 3')
   click('[data-native-widget="today"] [data-action="nw-progress"]');p.locator('.progress-summary').wait_for()
   check('Detailed history retains the current widget scope',p.locator('#progress-scope').input_value()=='cardio' and p.evaluate('widgetCalls.filter(x=>x.action==="study_progress").at(-1).data.scope')=='cardio')
   close()
   # Trusted provider API: opt-in, isolation, lifecycle, failure and no forced Onigiri.
   p.evaluate('''window.testProvider={mount:0,cleanup:0,themes:0};window.unregisterProvider=AtelierWidgets.register({id:'addon.demo.note',title:'Installed note',description:'Fixture local provider',mount(el,ctx){testProvider.mount++;el.innerHTML='<label>Widget input<input id="provider-input"></label>';el.querySelector('input').value='Original';return ()=>{testProvider.cleanup++};},theme(el,ctx){testProvider.themes++;window.providerContext=ctx;}});void 0;''')
   check('Registration alone does not execute mount',p.evaluate('testProvider.mount')==0)
   check('Duplicate id is explicitly rejected',p.evaluate('(()=>{try{AtelierWidgets.register({id:"addon.demo.note",title:"Duplicate",mount(){}});return false}catch{return true}})()'))
   arrange();click('[data-action="nw-add"][data-id="addon.demo.note"]');click('[data-action="nw-save"]');p.locator('#provider-input').wait_for()
   check('Enabled provider mounted once',p.evaluate('testProvider.mount')==1)
   p.locator('#provider-input').fill('Retained / value');p.evaluate('window.inputIdentity=document.querySelector("#atelier-root").shadowRoot.querySelector("[data-native-provider]").shadowRoot.querySelector("input")')
   for th in ['rose','midnight','forest']:
    p.evaluate('(theme)=>AtelierMakeover.applyAppearance({token:"preview",settings:{theme}})',th)
   check('Provider input and node survive theme changes',p.locator('#provider-input').input_value()=='Retained / value' and p.evaluate('testProvider.mount')==1)
   p.locator('#provider-input').focus();p.keyboard.type('abc/');p.wait_for_timeout(90)
   check('Nested provider input is not hijacked by home shortcuts',p.locator('#provider-input').input_value().endswith('abc/') and p.evaluate('widgetCalls.filter(x=>x.action==="focus").at(-1).data.active') is True)
   p.evaluate('window.unregisterLate=AtelierWidgets.register({id:"addon.demo.late",title:"Late widget",mount(){}});void 0');p.wait_for_timeout(80)
   check('Provider gets the effective presentation owner',p.evaluate('providerContext.owner==="atelier"&&providerContext.theme==="forest"'))
   check('A late registration does not remount existing input',p.evaluate('testProvider.mount')==1 and p.locator('#provider-input').input_value().endswith('abc/'))
   p.evaluate('window.unregisterProvider()');p.wait_for_timeout(80)
   check('Unregistered provider cleanup and retained placement',p.evaluate('testProvider.cleanup')==1 and 'not loaded' in p.locator('[data-native-widget="addon.demo.note"]').inner_text() and any(x['id']=='addon.demo.note' for x in saved()['items']))
   p.evaluate('window.unregisterCrash=AtelierWidgets.register({id:"addon.demo.crash",title:"Broken fixture",mount(){throw new Error("fixture")}});void 0')
   arrange();click('[data-action="nw-add"][data-id="addon.demo.crash"]');click('[data-action="nw-save"]')
   check('A failed provider cannot take down the page',p.locator('[data-native-widget="addon.demo.crash"] [role="status"]').is_visible() and p.locator('.nw-toolbar').is_visible())
   # Deliberate empty layout, reset, persisted repaint.
   arrange()
   while p.locator('[data-action="nw-remove"]').count():click('[data-action="nw-remove"]')
   click('[data-action="nw-save"]');check('Saving an empty page keeps it empty',saved()['items']==[] and p.locator('.nw-empty').is_visible())
   p.evaluate('AtelierMakeover.reload()');p.locator('.nw-empty').wait_for();check('Redraw does not silently restore defaults',p.locator('[data-native-widget]').count()==0)
   click('.nw-empty [data-action="nw-arrange"]');click('[data-action="nw-reset"]');check('Reset is staged before Save',saved()['items']==[])
   click('[data-action="nw-save"]');p.locator('.nw-metrics').wait_for();check('Explicit default reset restores four widgets',len(saved()['items'])==4)
   # Optional Onigiri card only appears if detected; it is a shortcut, not a clone.
   load('ember',onigiri=True);arrange();check('Optional reward route is labelled as a real provider',p.locator('[data-action="nw-add"][data-id="onigiri"]').is_visible());close()
   load('ember',onigiri=False);arrange();check('No placeholder game is invented without Onigiri',p.locator('[data-action="nw-add"][data-id="onigiri"]').count()==0);shot('arrange-without-onigiri');close()
   check('No uncaught browser errors',not errors)
  except Exception:
   shot('failure');(OUT/'failure.txt').write_text(p.locator('body').inner_text());raise
  finally:
   (OUT/'results.json').write_text(json.dumps({'count':len(checks),'cases':checks,'errors':errors,'native_windows':False,'no_onigiri_document':True},indent=2)+'\n')
   browser.close()
if __name__=='__main__':run()

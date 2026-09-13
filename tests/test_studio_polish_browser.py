"""Regression coverage for the bundled Studio shell. Real shipped frontend/engine;
synthetic bridge/data only. This is not native Windows/Qt acceptance.
"""
from planner_suite_fixture import *
from playwright.sync_api import sync_playwright
import zipfile,hashlib
OUT=ROOT/'verification/studio-polish';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/studio-polish';SHOTS.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[]

def check(name,value=True):
 assert value,name
 CHECKS.append(name);print('PASS',name,flush=True)

def box(page,selector):return page.locator(selector).first.bounding_box()
def hit(page,selector):
 return page.locator(selector).first.evaluate('''el=>{const r=el.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,t=document.elementFromPoint(x,y);return x>=0&&y>=0&&x<innerWidth&&y<innerHeight&&!!t&&(el===t||el.contains(t))}''')

def layout_ok(p,stage='setup'):
 return p.evaluate('''stage=>{
 const rect=e=>e.getBoundingClientRect(),h=rect(document.querySelector('.es-app-header'));
 const controls=[...document.querySelectorAll('.es-app-header button,.es-app-header select')].filter(e=>rect(e).width>0);
 const outside=controls.filter(e=>{const r=rect(e);return r.y<h.y-1||r.bottom>h.bottom+1||r.x<0||r.right>innerWidth+1});
 const pairs=[];for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
 const a=rect(controls[i]),b=rect(controls[j]);if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)pairs.push([i,j]);}
 const title=document.querySelector(stage==='setup'?'.suite-form-heading h1':'.suite-practice-heading h1');
 const titleSafe=!title||rect(title).top>=h.bottom-1;
 const scroll=document.querySelector('.suite-setup-scroll')||document.querySelector('.es-main');
 return {outside:outside.length,pairs:pairs.length,titleSafe,documentFits:document.scrollingElement.scrollHeight<=innerHeight+1,
 horizontal:scroll.scrollWidth<=scroll.clientWidth+2&&document.documentElement.scrollWidth<=innerWidth+1,headerHeight:h.height};
 }''',stage)

def setup(p,name='Clinical science · Exam 3'):
 if p.locator('.suite-exams-toggle').is_visible():p.locator('.suite-exams-toggle').click()
 p.locator('[data-action="new"]').first.click();p.locator('[data-field="name"]').wait_for()
 p.locator('[data-field="name"]').fill(name)
 p.locator('[data-field="topics"]').fill('Core concepts, lecture notes and applied examples.')

def run():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  def page(theme='forest',width=1440,height=980,enabled=True):
   p=b.new_page(viewport={'width':width,'height':height});p.set_default_timeout(12000);p.on('pageerror',lambda e:ERRORS.append(str(e)));expose(p)
   p.set_content(html(theme,enabled));p.locator('[data-action="new"]').first.wait_for(state='attached');p.wait_for_timeout(80);return p
  # Independent stale-header reproduction, not the cleaned up release renderer.
  oldzip=Path('/mnt/data/atelier_ui_audit/project/dist/Atelier-0.8.0-rc2.ankiaddon')
  if oldzip.is_file():
   with zipfile.ZipFile(oldzip) as z:
    oldapp=z.read('sprout/web/app.js').decode();oldcss=z.read('web/worlds-planner.css').decode()
   s=BeautifulSoup(html('forest'),'html.parser')
   next(x for x in s.find_all('script') if 'function renderForm()' in (x.string or '')).string=oldapp
   st=s.find(id='atelier-world-style');st.string=(SRC/'web/worlds-planner-tokens.css').read_text()+oldcss
   p=b.new_page(viewport={'width':1000,'height':700});expose(p);p.set_content(str(s));p.locator('[data-action="new"]').first.click();p.locator('[data-field="name"]').wait_for()
   baseline=p.evaluate('''()=>{let h=document.querySelector('.es-app-header').getBoundingClientRect();return {headerBottom:h.bottom,controls:[...document.querySelectorAll('.es-app-header button,.es-app-header select')].map(e=>{let r=e.getBoundingClientRect();return {label:e.getAttribute('aria-label')||e.textContent.slice(0,24),top:r.top,bottom:r.bottom}})}}''')
   (OUT/'baseline-rc2.json').write_text(json.dumps(baseline,indent=2));p.screenshot(path=str(SHOTS/'before-rc2-1000px.png'));p.close()
  for theme in core.THEMES:
   p=page(theme);setup(p)
   geom=layout_ok(p)
   check(theme+' setup header owns its height and does not overlap',not geom['outside'] and not geom['pairs'] and geom['titleSafe'] and geom['documentFits'] and geom['horizontal'])
   check(theme+' sticky footer targets stay inside viewport',hit(p,'[data-action="next-step"]') and hit(p,'[data-action="cancel-form"]'))
   check(theme+' native date/select color scheme follows world',p.locator('[data-field=due]').evaluate('e=>getComputedStyle(e).colorScheme')==review.PALETTES[theme]['scheme'])
   check(theme+' live summary reads existing draft name',p.locator('[data-summary="name"]').inner_text()=='Clinical science · Exam 3')
   p.screenshot(path=str(SHOTS/f'{theme}-setup.png'),animations='disabled')
   p.locator('[data-action="next-step"]').click()
   p.locator('[data-special="choose-deck"]').first.check()
   check(theme+' deck selected and summary updated',p.locator('[data-summary="decks"]').inner_text().startswith('1 selected deck'))
   check(theme+' checkbox retains keyboard focus after list redraw',p.evaluate("document.activeElement?.dataset.special==='choose-deck'"))
   p.locator('[data-action="next-step"]').click();p.locator('[data-field="daily_minutes"]').fill('90')
   check(theme+' routine retains footer and valid live budget',hit(p,'[data-action="save"]') and '90 min' in p.locator('[data-summary="routine"]').inner_text())
   p.locator('[data-action=weekday]').first.click();check(theme+' weekday toggle preserves keyboard target',p.evaluate("document.activeElement?.dataset.action==='weekday'"))
   p.locator('[data-action="setup-step"][data-step="1"]').click()
   check(theme+' previous step restores original fields',p.locator('[data-field="name"]').input_value()=='Clinical science · Exam 3' and p.locator('[data-field="topics"]').input_value().startswith('Core concepts'))
   p.close()
  # Effective CSS viewports corresponding to scaled desktop/small windows.
  for w,h in [(320,540),(390,650),(620,620),(900,650),(1040,720),(1320,720),(1650,900)]:
   p=page(width=w,height=h);setup(p)
   g=layout_ok(p)
   check(f'{w}x{h} no overlap or horizontal/document clipping',not g['outside'] and not g['pairs'] and g['titleSafe'] and g['documentFits'] and g['horizontal'])
   check(f'{w}x{h} native header actions remain visible/hittable',all(hit(p,f'.suite-tool-links [data-command="{cmd}"]') for cmd in ['add','browse','sync']))
   check(f'{w}x{h} Continue & Cancel remain visible without scrolling',hit(p,'[data-action="next-step"]') and hit(p,'[data-action="cancel-form"]'))
   p.locator('[data-field="topics"]').fill('A long topic brief. '*90)
   p.locator('[data-field="topics"]').hover();p.mouse.wheel(0,600);p.wait_for_timeout(70)
   check(f'{w}x{h} wheel scroll leaves action bar stable',hit(p,'[data-action="next-step"]') and hit(p,'[data-action="cancel-form"]'))
   p.locator('[data-action="next-step"]').click();p.locator('[data-special="choose-deck"]').first.check();p.locator('[data-action="next-step"]').click()
   check(f'{w}x{h} all steps have usable actions',hit(p,'[data-action="save"]') and hit(p,'[data-action="back-step"]'))
   if w<=700:
    p.locator('.suite-exams-toggle').click();check(f'{w}px rail is deliberately expandable',p.locator('.es-sidebar').is_visible())
    p.keyboard.press('Escape');check(f'{w}px Escape closes rail and restores focus',not p.locator('.es-sidebar').is_visible() and p.locator('.suite-exams-toggle').get_attribute('aria-expanded')=='false')
   p.screenshot(path=str(SHOTS/f'forest-{w}px-step3.png'),animations='disabled');p.close()
  # Live world changes and error recovery must not rebuild typed input or current step.
  p=page();setup(p,'Keep “Ω & résumé” intact')
  p.evaluate("window.savedName=document.querySelector('[data-field=name]');window.keptForm=document.querySelector('.es-form');")
  for world in core.THEMES:
   p.locator('.suite-world-switch select').select_option(world);p.wait_for_timeout(70)
   check('live world '+world+' keeps the same form, input and summary',p.evaluate("savedName===document.querySelector('[data-field=name]')&&keptForm===document.querySelector('.es-form')") and p.locator('[data-summary="name"]').inner_text()=='Keep “Ω & résumé” intact')
  p.locator('.suite-setup-summary>summary').click();before=p.locator('.suite-setup-summary').get_attribute('open')
  p.locator('[data-action="next-step"]').click()
  check('Summary disclosure choice is preserved across steps',p.locator('.suite-setup-summary').get_attribute('open')==before)
  p.locator('[data-special="choose-deck"]').first.check();p.locator('[data-action="next-step"]').click();p.locator('[data-field="daily_minutes"]').fill('85')
  p.locator('[data-action="save"]').click();p.locator('.es-form').wait_for(state='detached');p.locator('.es-hero').wait_for()
  data=next(payload for act,payload in reversed(CALLS) if act=='save_exam')
  check('Save uses original engine payload without UI summary/schema fields',data['name']=='Keep “Ω & résumé” intact' and data['daily_minutes']==85 and len(data['scopes'])==1 and not any(x in data for x in ['summary','step','railOpen']))
  p.close()
  # Existing unsaved-draft dialog and validation stay in charge.
  p=page();setup(p,'Do not discard me');p.locator('.es-top-nav [data-view="practice"]').click();p.locator('#es-modal[open]').wait_for()
  p.locator('[data-action="close-modal"]').click()
  check('Navigation cannot silently discard an unsaved exam',p.locator('[data-field="name"]').input_value()=='Do not discard me')
  p.locator('[data-field="name"]').fill('');p.locator('[data-action="next-step"]').click();p.locator('.es-toast').wait_for()
  check('Original step validation still prevents empty-name progress',p.locator('[data-field="name"]').count()==1 and p.locator('.es-toast').inner_text()=='Give your exam a name.')
  p.close()
  # Builder summary is read-only; allocation and mock/rehearsal semantics unchanged.
  for theme in core.THEMES:
   p=page(theme);p.locator('.es-top-nav [data-view="practice"]').click();p.locator('[data-practice="size"]').fill('125');p.locator('[data-practice="minutes"]').fill('55')
   check(theme+' practice summary follows configuration without rebuilding fields',p.locator('[data-summary="size"]').inner_text()=='125' and '55 minutes' in p.locator('.suite-practice-summary-content').inner_text())
   p.locator('[data-practice="strategy"]').select_option('adaptive')
   check(theme+' manual question count clears stale preset highlight',p.locator('[data-action=question-preset][aria-pressed=true]').count()==0)
   check(theme+' strategy warning and unchanged scheduling disclosure visible', 'not representative' in p.locator('.suite-practice-summary-content').inner_text() and 'does not change scheduling' in p.locator('.suite-schedule-safe').inner_text())
   check(theme+' one original preview action and all bounds preserved',p.locator('[data-action="prepare"]').count()==1 and p.locator('[data-practice="size"]').get_attribute('max')=='500' and p.locator('[data-practice="minutes"]').get_attribute('max')=='720')
   p.screenshot(path=str(SHOTS/f'{theme}-practice.png'),animations='disabled');p.close()
  # Presentation adapts to fallback/native palette without relying on a selected world.
  p=page(enabled=False);setup(p);g=layout_ok(p)
  check('Passive-owner planner keeps its own palette with safe new layout',not g['outside'] and not g['pairs'] and g['documentFits'])
  p.close()
  check('No uncaught errors in Studio shell scenarios',not ERRORS)
  b.close()
 (OUT/'results.json').write_text(json.dumps({'count':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'native_windows_verified':False},indent=2))
 print('TOTAL',len(CHECKS),'PASS',flush=True)
if __name__=='__main__':run()

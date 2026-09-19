"""Current unified-home + exact bundled planner presentation and routing matrix.
Fictional collection; native calls are explicit host doubles, not Anki/Qt.
"""
from suite_fixtures import *
import planner_suite_fixture as pf
from playwright.sync_api import sync_playwright
import re, time
OUT=ROOT/'verification/world-suite';OUT.mkdir(parents=True,exist_ok=True)
SHOTS=ROOT/'screenshots/worlds';SHOTS.mkdir(parents=True,exist_ok=True)
CHECKS=[];ERRORS=[];NETWORK=[]
def check(name,condition=True):
    assert condition,name
    CHECKS.append(name);print('PASS',name,flush=True)
def overflow(page):
    return page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
def home_overflow(page):
    return page.evaluate('''()=>{let r=document.getElementById('atelier-root').shadowRoot;let n=r.querySelector('.main');return n&&n.scrollWidth>n.clientWidth+1}''')
def companion_family(theme):
    if theme in ('rose','bloom','peach','castle','lavender','sky'):return 'cutesy'
    if theme in ('forest','matcha','cabin','sage'):return 'green'
    if theme in ('tidal','glacier','sunset-beach'):return 'water'
    if theme in ('midnight','obsidian','celestial','mythic'):return 'orbit'
    if theme in ('ember','underworld'):return 'ember'
    return 'linen'
def capture(page,path):
    page.screenshot(path=str(path),animations='disabled',timeout=60000)

def run():
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  def homepage(theme='forest',width=1440,height=1000):
    p=browser.new_page(viewport={'width':width,'height':height});p.set_default_timeout(9000);p.on('pageerror',lambda e:ERRORS.append(str(e)))
    p.set_content(home_suite(theme));p.locator('.suite-plan').first.wait_for();p.wait_for_timeout(120)
    p.evaluate("window.events=[];for(let n of ['atelier:preview-native','atelier:preview-suite'])window.addEventListener(n,e=>events.push({type:n,...e.detail}));")
    return p
  fonts=set();images=set();radii=set()
  for theme in core.THEMES:
    p=homepage(theme)
    meta=p.evaluate('''()=>{const r=document.getElementById('atelier-root').shadowRoot;const h=r.querySelector('.quiet-focus h1'),w=r.querySelector('.world-window');return {font:getComputedStyle(h).fontFamily,art:getComputedStyle(w).backgroundImage,radius:getComputedStyle(r.querySelector('.quiet-focus')).borderRadius}}''')
    fonts.add(meta['font']);images.add(meta['art']);radii.add(meta['radius'])
    expected_font=next(w['font'] for w in worlds.CATALOG if w['id']==theme)
    check(theme+' heading uses the canonical local font stack',meta['font']==expected_font)
    check(theme+' home world renders real art, native controls, canonical plans',meta['art']!='none' and p.locator('.unified-topbar [data-command]').count()==3 and p.locator('.suite-plan').count()==2 and not home_overflow(p))
    # The graphic theme truly acts on the shadow host, not dead :host:not syntax.
    if theme in ('forest','linen','rose'):check(theme+' custom heading font applied','Georgia' in meta['font'])
    capture(p,SHOTS/f'{theme}-home.png')
    p.locator('.unified-topbar [data-command="add"]').click();p.locator('.dialog').wait_for()
    check(theme+' Add cards dispatch is explicit and does not replace editor',p.evaluate('events.at(-1).command')=='add')
    p.locator('[data-action="close-dialog"]').first.click()
    p.locator('.suite-plan').first.locator('[data-view="practice"]').click();p.locator('.dialog').wait_for()
    check(theme+' plan-specific Practice carries original record id',p.evaluate('events.at(-1)')=={'type':'atelier:preview-suite','view':'practice','id':'pharm3'})
    p.close()
  # 1.0.3 retires the duplicate home layer's incidental third font stack.
  # Assert exact catalog typography above, while preserving scene/shape variety.
  check('Themes differ in scenery, catalog heading families and silhouettes',len(images)==len(core.THEMES) and len(fonts)==len({w['font'] for w in worlds.CATALOG}) and len(radii)>=6)
  # Native operations remain discoverable from a single tools page.
  p=homepage();p.locator('[data-page="tools"]').first.click()
  expected=['add','browse','stats','sync','import','export','preferences','addons','note_types','profiles','help','undo','redo','check_media','check_database','filtered_deck','empty_cards','fullscreen','check_updates']
  for cmd in expected:
    l=p.locator('.tools-page [data-command="'+cmd+'"]');check('Native tool '+cmd+' accessible',l.count()==1 and l.is_enabled())
  capture(p,SHOTS/'forest-tools.png')
  for width in (390,620,940):
    p.set_viewport_size({'width':width,'height':800})
    check(str(width)+' tools natural scroll/no horizontal clipping',not home_overflow(p))
  p.close()
  for width in (390,620,940):
    p=homepage(width=width,height=800)
    check(str(width)+' essential home actions remain reachable',p.locator('.unified-topbar [data-command="sync"]').is_visible() and p.locator('.unified-topbar [data-command="add"]').is_visible() and not home_overflow(p))
    p.locator('.unified-topbar [data-action="appearance"]').click();p.locator('.dialog').wait_for()
    check(str(width)+' all worlds in accessible appearance dialog',p.locator('[data-theme-choice]').count()==len(core.THEMES))
    # Select a world without rebuilding the dialog or discarding its scroll.
    p.evaluate("window.keptDialog=document.getElementById('atelier-root').shadowRoot.querySelector('.dialog');")
    p.locator('[data-theme-choice="tidal"]').click();p.wait_for_timeout(80)
    check(str(width)+' theme changes retain original dialog node',p.evaluate("keptDialog===document.getElementById('atelier-root').shadowRoot.querySelector('.dialog')"))
    p.locator('[data-action="close-dialog"]').first.click();p.close()
  # All worlds applied to actual bundled planner/assessment, not mock static cards.
  for theme in core.THEMES:
    p=browser.new_page(viewport={'width':1440,'height':1020});p.set_default_timeout(15000);p.on('pageerror',lambda e:ERRORS.append(str(e)));pf.expose(p)
    p.set_content(pf.html(theme));p.locator('.es-readiness-grade').wait_for();p.wait_for_timeout(200)
    check(theme+' planner uses shared world and all native links',p.evaluate('document.documentElement.dataset.atelierWorld')==theme and p.locator('.suite-tool-links [data-command]').count()==3 and not overflow(p))
    # Both font and the Pip footer, which originally retained a dark blue fixed skin.
    colours=p.evaluate('''()=>({text:getComputedStyle(document.querySelector('.es-pip-progress>strong')).color, panel:getComputedStyle(document.querySelector('.es-pip-progress')).backgroundImage,hero:getComputedStyle(document.querySelector('.es-hero')).backgroundImage,pipBackdrop:getComputedStyle(document.querySelector('.pip-card'),'::before').backgroundImage,pipButton:getComputedStyle(document.querySelector('.pip-actions button')).backgroundImage})''')
    family=companion_family(theme);pip=p.locator('.pip-card')
    check(theme+' planner/Pip surfaces are from the same world','rgb(20, 42, 49)' not in colours['panel'] and '15, 34, 42' not in colours['pipBackdrop'] and colours['pipButton']=='none' and colours['hero']!='none' and pip.get_attribute('data-pip-world')==family and f'companion-{family}-1.0.3.png' in p.locator('.pip-image').get_attribute('src') and pip.get_attribute('data-pip-renderer')=='portrait' and p.locator('.es-pip-stage-label').inner_text().removesuffix(' stage') in p.locator('.es-growth-steps span').all_inner_texts())
    capture(p,SHOTS/f'{theme}-planner.png')
    p.locator('.es-top-nav [data-view="practice"]').click()
    check(theme+' original practice limits/strategy survive',p.locator('[data-practice="size"]').get_attribute('max')=='500' and p.locator('[data-practice="minutes"]').get_attribute('max')=='720' and p.locator('[data-practice="strategy"]').count()==1)
    capture(p,SHOTS/f'{theme}-practice.png')
    p.locator('.suite-tool-links [data-command="browse"]').click();p.wait_for_timeout(30)
    check(theme+' planner native tool routes once',pf.CALLS[-1]==('suite_native',{'command':'browse'}))
    if theme=='forest':
      # Open the existing native engine form; edit, then cross-theme. Native delivery
      # is mimicked using the same world config + token update, not a form re-render.
      p.evaluate('ExamSprout.event("suite-navigate",{view:"new",setup:{name:"Unsaved exam",deck_ids:[11]}})')
      p.locator('[data-field="name"]').wait_for();p.locator('[data-field="name"]').fill('Keep this unfinished draft')
      p.evaluate('window.originalInput=document.querySelector(\'[data-field="name"]\')')
      p.locator('[aria-label="Study world"]').select_option('rose');p.wait_for_timeout(120)
      cfg=core.settings({'theme':'rose','visual_owner':'atelier'})
      p.evaluate('(c)=>AtelierWorlds.configure(c)',worlds.runtime_config(cfg));p.evaluate('(css)=>document.getElementById("atelier-sprout-tokens").textContent=css',pf.link.tokens_css(cfg))
      check('Cross-page world switch preserves unfinished form and input identity',p.locator('[data-field="name"]').input_value()=='Keep this unfinished draft' and p.evaluate('originalInput===document.querySelector(\'[data-field="name"]\')'))
      p.evaluate('ExamSprout.event("suite-navigate",{view:"practice",id:"pharm3"})')
      p.locator('#es-modal[open]').wait_for();check('Suite navigation cannot silently discard unsaved form','unsaved' in p.locator('#es-modal').inner_text())
      p.locator('[data-action="close-modal"]').click();check('Cancel retains unsaved exam name',p.locator('[data-field="name"]').input_value()=='Keep this unfinished draft')
    p.close()
  check('No uncaught errors across unified world workflows',not ERRORS)
  browser.close()
 (OUT/'results.json').write_text(json.dumps({'count':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'native_anki_tested':False,'renderer':'Chromium; Pip animated fallback'},indent=2))
 print('TOTAL',len(CHECKS),'PASS',flush=True)
if __name__=='__main__':run()

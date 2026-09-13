"""Browser compatibility test: exact uploaded Atelier assets, sample data.

Usage: python tools/test_atelier.py /path/to/Atelier.ankiaddon
This is NOT an installed Anki test and does not run native Qt or card rendering.
The Atelier archive is read, not changed or repackaged.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from addon.storage import Store
from addon.widget import countdown_html
OUT=ROOT/'docs'/'compatibility';OUT.mkdir(parents=True,exist_ok=True)
ATELIER=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/Atelier(1).ankiaddon')
with zipfile.ZipFile(ATELIER) as archive:
    ACSS=archive.read('web/atelier.css').decode()
    AJS=archive.read('web/atelier.js').decode()
    AMANIFEST=json.loads(archive.read('manifest.json'))
SCSS=(ROOT/'addon/web/countdown.css').read_text()
SJS=(ROOT/'addon/web/countdown.js').read_text()
THEMES=['obsidian','glacier','rose','bloom','linen','matcha','midnight','peach']
PRESETS=['inherit','sage','lavender','peach','rose','sky','midnight']
TMP=tempfile.TemporaryDirectory(prefix='sprout-atelier-');STORE=Store(TMP.name)
for eid,name,days,did in [('pharm','Pharmacotherapy · Exam 3',12,11),('micro','Microbiology quiz',18,21)]:
    STORE.save_exam({'id':eid,'name':name,'due':(datetime.now()+timedelta(days=days)).isoformat(timespec='minutes'),'scopes':[{'deck_id':did,'name':name}]})
config={'theme':'obsidian','mode':'workspace','density':'comfortable','motion':True,'chrome':True,'view':'grid','sort':'name'}
profile={'favorites':['1','2'],'folders':['1','2','3'],'colors':{},'last_location':'0'}
nodes=[]
for did,name,children in [('1','Pharmacotherapy',[('11','Cardiology',42,12,2),('12','Renal & electrolytes',26,8,1),('13','Endocrinology',17,4,0)]),('2','Microbiology',[('21','Antimicrobials',24,9,1),('22','Organisms',16,6,0)]),('3','Clinical skills',[('31','Counseling',12,4,0)])]:
    nodes.append(dict(id=did,name=name,path=name,parent='0',children=[c[0] for c in children],depth=0,filtered=False,new=sum(c[3] for c in children),learn=sum(c[4] for c in children),review=sum(c[2] for c in children)))
    for cid,cn,reviews,new,learn in children:nodes.append(dict(id=cid,name=cn,path=name+'::'+cn,parent=did,children=[],depth=1,filtered=False,new=new,learn=learn,review=reviews))
demo={'settings':config,'profile':profile,'nodes':nodes,'totals':{'new':43,'learn':4,'review':137},'current':'11','studied':'Sample library · no actual cards or schedules are changed.'}

CHECKS=[];errors=[]
def check(name,value=True):
    assert value,name
    CHECKS.append(name);print('PASS',name,flush=True)

def html(order='atelier-first',empty=False,hidden=False):
    boot={'version':AMANIFEST['human_version'],'token':'fixture','settings':config,'profile':profile,'ui':{},'openSettings':False,'preview':True,'demo':demo}
    markup=countdown_html(Store(TMP.name+'/empty') if empty else STORE)
    if hidden:markup=''
    scripts=[AJS,SJS] if order=='atelier-first' else [SJS,AJS] if order=='sprout-first' else [AJS]
    return '<!doctype html><html><head><base href="http://sprout.test/"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0;background:#252525;color:#eee;font:14px Arial,sans-serif}.test-label{font:10px/1.4 Arial,sans-serif;letter-spacing:.7px;text-align:center;padding:8px;background:#17161f;color:#b1aabb}.test-nav{display:flex;justify-content:center;gap:26px;padding:14px;font:13px Arial;background:#17161f;color:#eee}'+SCSS+'</style></head><body><div class="test-label">BROWSER COMPATIBILITY TEST · EXACT UPLOADED ATELIER UI + EXAM SPROUT · SAMPLE DATA, NOT AN INSTALLED ANKI SCREENSHOT</div><nav class="test-nav"><span>Decks</span><span>Add</span><span>Browse</span><span>Stats</span><span>Sync</span><span>Exams</span></nav><div id="atelier-root"></div><script id="atelier-bootstrap" type="application/json">'+json.dumps(boot).replace('<','\\u003c')+'</script><template id="atelier-style"><style>'+ACSS+'</style></template><center id="native-home"><table><tr class="deck" id="1"><td><a class="deck">Pharmacotherapy</a></td></tr></table>'+markup+'<div id="native-stats">Native Anki statistics fixture</div><div id="third-party-widget">Other add-on content is retained.</div></center><script>window.commands=[];window.pycmd=m=>window.commands.push(m);window.originalNative=document.getElementById("native-home");window.originalStats=document.getElementById("native-stats");window.intervals=new Set();const realSI=window.setInterval, realCI=window.clearInterval;window.setInterval=(...a)=>{const id=realSI(...a);window.intervals.add(id);return id};window.clearInterval=id=>{window.intervals.delete(id);return realCI(id)};</script>'+''.join('<script>'+s+'</script>' for s in scripts)+'</body></html>'

def widget_state(p):
    return p.evaluate('''() => {
      const r=document.getElementById('es-countdowns'),h=document.getElementById('atelier-root');
      const hero=h.shadowRoot?.querySelector('.hero');
      const rect=r?.getBoundingClientRect();
      return {count:document.querySelectorAll('#es-countdowns').length,slot:r?.slot,host:r?.dataset.host,
      dark:r?.dataset.dark,accent:r?getComputedStyle(r).getPropertyValue('--es-accent').trim():null,
      expected:getComputedStyle(h).getPropertyValue('--accent').trim(),
      width:rect?.width,height:rect?.height,top:rect?.top,beforeHero:hero&&rect?.bottom<=hero.getBoundingClientRect().top,
      slots:h.shadowRoot?.querySelectorAll('slot[data-exam-sprout-slot]').length,
      originalSlot:h.shadowRoot?.querySelectorAll('slot[name="atelier-widgets"]').length,
      intervals:window.intervals.size,overflow:document.documentElement.scrollWidth>innerWidth};
    }''')

def choose(p,theme):
    p.evaluate('window.AtelierMakeover.openAppearance()')
    p.locator(f'[data-theme-choice="{theme}"]').click()
    p.wait_for_function('(t)=>document.getElementById("atelier-root").dataset.theme===t',arg=theme)
    p.locator('.dialog-footer [data-action="close-dialog"]').click()

def fresh(browser,order='atelier-first',**kw):
    p=browser.new_page(viewport={'width':1446,'height':1000},device_scale_factor=1)
    p.on('pageerror',lambda error:errors.append(str(error)))
    def assets(route):
        target=(ROOT/'addon/web'/route.request.url.split('/web/',1)[-1]).resolve()
        if (ROOT/'addon/web').resolve() in target.parents and target.is_file():route.fulfill(path=str(target))
        else:route.fulfill(status=404,body='')
    p.route('**/_addons/exam_sprout/web/**',assets)

    p.set_default_timeout(5000)
    p.set_content(html(order,**kw))
    p.wait_for_function('document.body.classList.contains("atelier-home")')
    return p

def run():
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        for order in ['atelier-first','sprout-first']:
            p=fresh(b,order)
            s=widget_state(p)
            check(order+': countdown appears above hero',s['beforeHero'] and s['height']>30)
            check(order+': exactly one component, slot and timer',s['count']==s['slots']==s['intervals']==1)
            check(order+': existing extension slot retained',s['originalSlot']==1)
            check(order+': inherits live palette',s['accent']==s['expected'])
            p.locator('.es-chip').first.click()
            check(order+': one bridge action per click',p.evaluate('window.commands')==['exam-sprout:open:pharm'])
            p.close()
        p=fresh(b,'late-sprout');p.add_script_tag(content=SJS)
        check('Late-loaded countdown docks without needing another theme change',widget_state(p)['beforeHero'])
        p.close()
        p=fresh(b)
        for theme in THEMES:
            choose(p,theme)
            s=widget_state(p)
            check(theme+': theme and placement survive real Atelier rerender',s['accent']==s['expected'] and s['beforeHero'])
            check(theme+': no duplicate countdowns or timers',s['count']==s['slots']==s['intervals']==1)
            check(theme+': dark/light follows Atelier, not OS',s['dark']==str(theme in ['obsidian','glacier','midnight']).lower())
            for preset in PRESETS:
                p.evaluate('(t)=>{document.getElementById("es-countdowns").dataset.theme=t;window.ExamSproutCountdown.mount()}',preset)
                st=widget_state(p)
                check(f'{theme}/{preset}: preset retained and fits',p.locator('#es-countdowns').get_attribute('data-theme')==preset and not st['overflow'] and st['width']>0)
            p.evaluate('document.getElementById("es-countdowns").dataset.theme="inherit";window.ExamSproutCountdown.mount()')
            if theme in ['obsidian','rose','matcha']:
                p.screenshot(path=str(OUT/f'Exam_Sprout_Atelier_{theme.title()}.png'),full_page=False)
        choose(p,'obsidian')
        for width,height in [(1100,850),(850,800),(720,1024),(560,740),(390,844)]:
            p.set_viewport_size({'width':width,'height':height});p.wait_for_timeout(70)
            s=widget_state(p)
            check(f'{width}px: countdown remains above hero, inside viewport',s['beforeHero'] and not s['overflow'] and s['width']>0)
            if width==720:p.screenshot(path=str(OUT/'Exam_Sprout_Atelier_Narrow.png'))
        p.set_viewport_size({'width':1446,'height':1000})
        # Navigate a folder: the complete Atelier main panel is rebuilt.
        p.locator('.card-bottom [data-action="navigate"][data-id="1"]').click()
        check('Folder navigation preserves visible countdown',widget_state(p)['beforeHero'])
        p.locator('.breadcrumbs [data-action="home"]').click()
        check('Return to parent preserves one countdown',widget_state(p)['count']==1)
        p.evaluate('window.AtelierMakeover.openAppearance()')
        p.locator('#setting-mode').select_option('hybrid')
        check('Hybrid mode retains the original deck row',p.locator('#native-home tr.deck').is_visible())
        p.locator('#setting-mode').select_option('native')
        check('Classic view restores countdown to native content',p.locator('#native-home #es-countdowns').count()==1 and p.locator('#es-countdowns').is_visible())
        p.locator('.dialog-footer [data-action="close-dialog"]').click()
        p.locator('[data-action="workspace"]').click()
        check('Re-enabling workspace re-docks single component',widget_state(p)['beforeHero'] and widget_state(p)['slots']==1)
        check('Original nodes and third-party content are preserved',p.evaluate('document.getElementById("native-home")===window.originalNative && document.getElementById("native-stats")===window.originalStats && !!document.getElementById("third-party-widget")'))
        # Re-running scripts or mount calls must not stack click listeners.
        for _ in range(3):p.add_script_tag(content=SJS)
        p.evaluate('window.commands=[];for(let i=0;i<50;i++)window.ExamSproutCountdown.mount()')
        p.locator('.es-chip').first.click()
        check('Repeated script/mount calls do not stack clicks',p.evaluate('window.commands.length')==1)
        check('Repeated script/mount calls leave one timer',p.evaluate('window.intervals.size')==1)
        # External home refresh removes and later reuses the exact same node.
        p.evaluate('window.detachedSprout=document.getElementById("es-countdowns");window.detachedSprout.remove();window.ExamSproutCountdown.mount()')
        check('Removed root releases the timer',p.evaluate('window.intervals.size')==0)
        p.evaluate('document.getElementById("native-home").append(window.detachedSprout);window.commands=[];window.ExamSproutCountdown.mount()')
        p.locator('.es-chip').first.click()
        check('Reinserting a detached root binds exactly one action',p.evaluate('window.commands.length')==1)
        check('Reinserted root docks above hero with one timer',widget_state(p)['beforeHero'] and p.evaluate('window.intervals.size')==1)
        p.emulate_media(reduced_motion='reduce')
        check('System reduced motion respected',p.locator('.es-chip').first.evaluate('e=>getComputedStyle(e).transitionDuration')=='0s')
        p.emulate_media(reduced_motion='no-preference')
        p.evaluate('window.AtelierMakeover.openAppearance()')
        p.locator('[data-action="toggle-setting"][data-key="motion"]').click()
        p.locator('.dialog-footer [data-action="close-dialog"]').click()
        check('Atelier motion toggle respected',p.locator('.es-chip').first.evaluate('e=>getComputedStyle(e).transitionDuration')=='0s')
        p.evaluate('window.ExamSproutCountdown.dispose();window.commands=[]')
        check('Teardown removes timer and owned slot',p.evaluate('window.intervals.size')==0 and widget_state(p)['slots']==0)
        check('Teardown restores original home location',p.locator('#native-home #es-countdowns').count()==1)
        p.locator('.es-chip').first.click()
        check('Teardown removes countdown click listener',p.evaluate('window.commands.length')==0)
        p.add_script_tag(content=SJS)
        p.locator('.es-chip').first.click()
        check('Reinitialize after disposal restores exactly one action',p.evaluate('window.commands.length')==1)
        check('Reinitialize after disposal restores one timer and top slot',widget_state(p)['beforeHero'] and p.evaluate('window.intervals.size')==1)
        p.close()
        p=fresh(b,empty=True)
        check('New installation shows Add first exam on Atelier home',p.locator('.es-chip-empty').is_visible() and widget_state(p)['beforeHero'])
        p.locator('.es-chip-empty').click()
        check('Empty state opens exam setup',p.evaluate('window.commands')==['exam-sprout:open:'])
        p.close()
        p=fresh(b,hidden=True)
        check('Disabled countdown adds neither space nor timer',p.locator('#es-countdowns').count()==0 and p.evaluate('window.intervals.size')==0)
        p.close()
        check('No uncaught browser errors',not errors)
        b.close()
    (OUT/'atelier-results.json').write_text(json.dumps({'runtime':'Headless Chromium; production JS/CSS, sample data; NOT native Anki/Qt','atelier_manifest':AMANIFEST,'atelier_archive_sha256':hashlib.sha256(ATELIER.read_bytes()).hexdigest(),'atelier_js_sha256':hashlib.sha256(AJS.encode()).hexdigest(),'atelier_css_sha256':hashlib.sha256(ACSS.encode()).hexdigest(),'passed':len(CHECKS),'checks':CHECKS,'browser_errors':errors},indent=2))
    print(f'{len(CHECKS)} compatibility checks passed')
if __name__=='__main__':run()

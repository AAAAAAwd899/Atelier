"""Executable Chromium smoke/regression checks. Run as a script, not pytest.
Uses shipped CSS/JS and native-shaped DOM. Not Qt or the full Onigiri runtime.
"""
from fixtures import *
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import itertools

R=ROOT; out=R/'dist';out.mkdir(exist_ok=True)
checks=[]
def record(name):checks.append(name);print('PASS',name,flush=True)

def home(owner='ask'):
    template=(ROOT/'tests/data/ownership-preview.html').read_text()
    soup=BeautifulSoup(template,'html.parser')
    boot=json.loads(soup.find(id='atelier-bootstrap').string)
    boot['version']=core.VERSION
    boot['settings'].update(visual_owner=owner,mode='native' if owner=='onigiri' else 'workspace')
    boot['demo']['settings']=dict(boot['settings'])
    soup.find(id='atelier-bootstrap').string=json.dumps(boot)
    soup.find(id='atelier-shared-style').string=asset('shared.css')
    soup.find(id='atelier-style').find('style').string=asset('atelier.css')
    # Replace the pre-paint guard, not only CSS on the eventual page.
    soup.find(id='atelier-paint-style').decompose()
    original_guard=next(s for s in soup.find_all('script') if 'const c={' in (s.string or ''))
    original_guard.decompose()
    for prefix,name in [('/* Palette ownership.','ownership.js'),('/* Framework-independent','model.js'),('/* Stable, additive','cohesion.js'),('/* Atelier Shared Home','home.js'),('/* Atelier 0.7.0','atelier.js')]:
        tag=next(s for s in soup.find_all('script') if (s.string or '').startswith(prefix))
        tag.string=asset(name)
    guard_soup=BeautifulSoup(guard.home_guard(boot['settings']),'html.parser')
    for n in list(guard_soup.contents):soup.head.append(n.extract())
    return str(soup)

with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 errors=[]
 def page_for(html,w=1200,h=700):
    p=b.new_page(viewport={'width':w,'height':h});p.set_default_timeout(4000)
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.set_content(html);p.wait_for_timeout(70);return p
 for theme,w,stage in itertools.product(core.THEMES,[390,720,1440],['question','answer']):
    p=page_for(footer(theme,stage,'old',conflict=True),w,84)
    h=p.evaluate('AtelierReview.measureFooter().height');p.set_viewport_size({'width':w,'height':h});p.wait_for_timeout(35)
    info=p.evaluate('''()=>({same:originalButtons.every(b=>b.isConnected),bad:[...document.querySelectorAll('#outer button,#outer .stattxt,#outer .nobold')].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.getBoundingClientRect()).some(r=>r.top<-.5||r.bottom>innerHeight+.5||r.left<-.5||r.right>innerWidth+.5)})''')
    assert info['same'] and not info['bad'],(theme,w,stage,info)
    p.locator('#middle button').first.click()
    assert p.evaluate('commands.filter(x=>!x.startsWith("atelier:")).at(-1)')==('ans' if stage=='question' else 'ease1')
    if theme=='obsidian' and w==1440 and stage=='answer':p.screenshot(path=str(out/'Atelier-current-Review-Bar.png'))
    p.close();record(f'footer {theme} {w} {stage}')
 for theme in core.THEMES:
    p=page_for(card(theme,'basic'),1100,650)
    assert p.evaluate('document.scrollingElement.scrollHeight<=innerHeight+1'),theme
    metrics=p.evaluate('''()=>{const h=document.getElementById('atelier-review-header').getBoundingClientRect(),q=document.getElementById('qa').getBoundingClientRect();return {center:(h.top+q.bottom)/2,height:innerHeight,markup:originalHTML===originalQA.innerHTML};}''')
    assert abs(metrics['center']-metrics['height']/2)<20 and metrics['markup'],metrics
    p.evaluate("document.getElementById('qa').innerHTML='<p>Long answer</p>'.repeat(100);AtelierReview.setCard({id:'one',eligible:true,stage:'answer',path:['Course','Lecture']});")
    p.wait_for_timeout(40);p.evaluate('window.scrollTo(0,900)');assert p.evaluate('scrollY')>0
    p.evaluate("document.getElementById('qa').innerHTML='<p>A fresh question.</p>';AtelierReview.setCard({id:'two',eligible:true,stage:'question',path:['Course','Lecture']});")
    p.wait_for_timeout(60);assert p.evaluate('scrollY')==0
    assert p.evaluate('document.scrollingElement.scrollHeight<=innerHeight+1')
    if theme=='obsidian':p.screenshot(path=str(out/'Atelier-current-Reviewer.png'))
    p.close();record('centering and next-question scroll '+theme)
    p=page_for(card(theme,'io'),1000,620)
    assert p.evaluate("JSON.stringify(beforeGeometry)===JSON.stringify([...document.querySelectorAll('#io-wrapper,#original-image,#io-overlay,.mask')].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]}))")
    assert p.evaluate('originalQA===document.getElementById("qa")&&originalQA.innerHTML===originalHTML')
    p.close();record('occlusion fixture geometry '+theme)
 # Exact exported 0.7.0 frontend, with current release prepaint/styles/scripts.
 p=page_for(home(),1400,900)
 assert p.locator('[data-action="choose-owner"]').count()==3
 p.screenshot(path=str(out/'Atelier-current-Choose-Owner.png'))
 p.locator('[data-action="choose-owner"][data-owner="atelier"]').click()
 p.locator('.focus-actions [data-action="quick-session"]').click()
 assert p.locator('.dialog [data-action="study-now"]').count()>0
 p.locator('.dialog [data-action="study-now"]').first.click()
 assert p.get_by_text('The installed add-on starts native Anki review for this lecture only.',exact=False).is_visible()
 p.locator('[data-action="close-dialog"]').first.click()
 p.screenshot(path=str(out/'Atelier-current-Study-Desk.png'));p.close();record('owner choice and quick study UI')
 p=page_for(home('onigiri'),1400,900)
 assert p.evaluate("document.documentElement.dataset.atelierShared==='false'")
 assert p.evaluate("getComputedStyle(document.querySelector('.modern-main-menu')).backgroundColor")== 'rgb(45, 53, 35)'
 assert p.locator('[data-atelier-native-rail]').is_visible()
 p.close();record('Onigiri companion keeps original color')
 assert not errors,errors
 b.close()
(out/'browser-verification.json').write_text(json.dumps({'checks':checks,'count':len(checks),'errors':errors},indent=2))
print('TOTAL',len(checks),'PASS')

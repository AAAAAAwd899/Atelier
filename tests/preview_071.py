"""Render current release assets against an independent native-shaped fixture."""
from fixtures import *
from bs4 import BeautifulSoup

def home071(owner='atelier',onigiri=True,others=None,mixed=False,layout=False,shortcuts=False):
    soup=BeautifulSoup((ROOT/'tests/data/ownership-preview.html').read_text(),'html.parser')
    boot=json.loads(soup.find(id='atelier-bootstrap').string)
    boot['version']=core.VERSION
    boot['integrations'].update(onigiri=onigiri,makeovers=others or [],metadata_checked=True)
    cfg=core.settings({**boot['settings'],'visual_owner':owner,'mode':'native' if owner in ('onigiri','external') else 'workspace','companion_shortcuts':shortcuts})
    boot['settings']=cfg;boot['demo']['settings']=dict(cfg)
    for profile in [boot['profile'],boot['demo']['profile']]:
        profile['home_layout']={'enabled':layout,'columns':1,'items':[]}
    soup.find(id='atelier-bootstrap').string=json.dumps(boot)
    soup.find(id='atelier-shared-style').decompose()
    soup.find(id='atelier-style').find('style').string=asset('atelier.css')
    soup.find(id='atelier-paint-style').decompose()
    old=next(s for s in soup.find_all('script') if 'const c={' in (s.string or ''));old.decompose()
    for prefix,name in [('/* Palette ownership.','ownership.js'),('/* Framework-independent','model.js'),('/* Stable, additive','cohesion.js'),('/* Atelier Shared Home','home.js'),('/* Atelier 0.7.0','atelier.js')]:
        next(s for s in soup.find_all('script') if (s.string or '').startswith(prefix)).string=asset(name)
    for name in ['widget-registry.js','native-widgets.js']:
        tag=soup.new_tag('script');tag.string=asset(name)
        first_app=next(s for s in soup.find_all('script') if (s.string or '').startswith('/* Atelier '+core.VERSION))
        first_app.insert_before(tag)
    if mixed:
        t=soup.new_tag('style');t['id']='native-mixed-scheme';t.string='''html,body,.modern-main-menu{background:#f7efd8!important;color:#1d261d}.modern-main-menu .stat-card{background:#495233!important;color:#eef1da}.modern-main-menu .sidebar-left{background:#5c6348!important}.main-content{color:#1d261d}.stat-card .stat-value{color:#eef1da!important}''';soup.head.append(t)
    guard_soup=BeautifulSoup(guard.home_guard(cfg),'html.parser')
    for n in list(guard_soup.contents):soup.head.append(n.extract())
    # Capture dimensions and identity before Atelier's runtime scripts execute.
    before=soup.new_tag('script');before.string='''window.nativeSnapshot=()=>{const menu=document.querySelector('.modern-main-menu');return {markup:menu.innerHTML,classes:menu.className,parts:[menu,document.body,...menu.querySelectorAll('.sidebar-left,.stat-card,.unified-grid,a.deck,input')].map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return [r.x,r.y,r.width,r.height,s.background,s.color,s.fontFamily,s.display,e.getAttribute('style')||'']})}};window.originalNative=nativeSnapshot();window.originalNativeNode=document.querySelector('.modern-main-menu');'''
    first=next(s for s in soup.find_all('script') if (s.string or '').startswith('/* Palette ownership.'));first.insert_before(before)
    return str(soup)

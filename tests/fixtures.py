"""Native-shaped documents plus independent CSS collision reproductions.
No Onigiri source/assets are bundled. This exercises the conflicting structure
observed in public source, not the installed Onigiri application itself.
"""
from pathlib import Path
import json, sys, types, importlib, zipfile
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'
package=types.ModuleType('atelier_testing');package.__path__=[str(SRC)];sys.modules.setdefault('atelier_testing',package)
core=importlib.import_module('atelier_testing.core')
review=importlib.import_module('atelier_testing.review_model')
guard=importlib.import_module('atelier_testing.surfaces')

def asset(name):
    text=(SRC/'web'/name).read_text()
    if name in ('atelier.css','reviewer.css'):
        from atelier_testing.worlds import home_css, reviewer_css
        text+='\n'+(home_css() if name=='atelier.css' else reviewer_css())
    return text

BASE_CSS='''html,body{padding:0;margin:0;background:#f6eed7;color:#333;font:14px Arial}body{overflow:hidden}table{border-spacing:0}button{font:14px Arial;background:#303030;color:white;border:1px solid #444;border-radius:12px;padding:10px}#outer{width:100%}.stattxt{font-size:12px}.new-count{color:#6f9bef}.learn-count{color:#efa2bc}.review-count{color:#8dd4b2}'''
# Reproduces fixed cap, percent-height chain, and absolute stats independently.
CONFLICT_CSS='''html,body{--onigiri-reviewer-bottom-bar-height:84px;height:var(--onigiri-reviewer-bottom-bar-height)!important;min-height:var(--onigiri-reviewer-bottom-bar-height)!important;max-height:var(--onigiri-reviewer-bottom-bar-height)!important;overflow:hidden!important;background:#f6eed7!important}
#outer{height:84px!important;max-height:84px!important;overflow:hidden!important;padding:0!important}
#outer>table,#outer>table tbody,#outer>table tr{height:100%!important;max-height:84px!important}
#outer>table tr{display:flex!important;align-items:center!important;justify-content:space-between!important}
#outer>table td{height:100%!important;display:flex!important;align-items:center!important;position:relative!important}
#outer button:not(.exclude):not(.keep):not(.special):not(.x){height:62px!important;max-height:62px!important;background:#393939!important;padding:15px!important}
#outer button:hover{transform:translateY(-2px)!important}
#ansbut{min-width:148px!important;position:relative!important}
#outer .stattxt{position:absolute!important;bottom:calc(100% + 7px)!important;left:50%!important;transform:translateX(-50%)!important;white-space:nowrap!important}
#outer .onigiri-pre-answer-counts{position:absolute!important;bottom:100%!important;left:50%!important;transform:translateX(-50%)!important;display:flex!important}
#outer .onigiri-show-answer-label,#outer .onigiri-answer-label{position:absolute!important;top:50%!important;transform:translateY(-50%)!important}
#outer .onigiri-answer-hover-number{position:absolute!important;top:50%!important;opacity:0!important}
#outer button:hover .onigiri-answer-label{opacity:0!important}
'''

def footer_body(stage='question',variant='old',extra=False):
    counts='<span class="new-count">8</span> + <span class="learn-count">0</span> + <span class="review-count">152</span>'
    if stage=='question':
        inside=f'<span class="label">Show Answer</span><div class="stattxt"><table><tbody><tr><td class="stat2">{counts}</td></tr></tbody></table></div>'
        if variant=='overlay':
            inside=f'<span class="onigiri-show-answer-label">Show Answer</span><div class="stattxt onigiri-stattxt-source" style="display:none!important">{counts}</div><div class="onigiri-pre-answer-counts"><span class="onigiri-count-pill onigiri-count-pill-new">8 new</span><span class="onigiri-count-pill onigiri-count-pill-learn">0 learn</span><span class="onigiri-count-pill onigiri-count-pill-review">152 review</span></div>'
        middle=f'<table><tbody><tr><td><button id="ansbut" onclick="pycmd(\'ans\')">{inside}</button></td></tr></tbody></table>'
    else:
        buttons=[]
        for i,(label,time) in enumerate([('Again','<1m'),('Hard','6m'),('Good','10m'),('Easy','4d')],1):
            if variant=='overlay':inside=f'<span class="onigiri-answer-label">{label}</span><span class="onigiri-answer-hover-number">{time.replace("<","&lt;")}</span><span class="nobold onigiri-native-number-source" style="display:none!important">hidden source</span>'
            else:inside=f'<span class="label">{label}</span><span class="nobold">{time.replace("<","&lt;")}</span>'
            buttons.append(f'<td><button data-ease="{i}" '+('id="defease" ' if i==3 else '')+f'onclick="pycmd(\'ease{i}\')">{inside}</button></td>')
        middle='<table><tbody><tr>'+''.join(buttons)+'</tr></tbody></table>'
    extra_cell='<td class="addon-cell"><button onclick="pycmd(\'extra\')">Extra</button></td>' if extra else ''
    return f'''<center id="outer"><table id="innertable" width="100%"><tbody><tr><td class="stat"><button onclick="pycmd('edit')">Edit</button></td>{extra_cell}<td id="middle">{middle}</td><td class="stat"><button onclick="pycmd('more')">More ▾</button><span class="stattxt" id="time">0:02</span></td></tr></tbody></table></center>'''

def footer(theme='obsidian',stage='question',variant='old',conflict=True,old=False,extra=False):
    js=asset('reviewer.js');css=asset('reviewer.css')
    if old:
        css=(ROOT/'tests/data/baseline-050-reviewer.css').read_text();js=(ROOT/'tests/data/baseline-050-reviewer.js').read_text()
    config={'screen':'review-bottom','style':'adaptive','theme':theme,'width':'standard','motion':False,'layoutToken':'fixture-token'}
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+BASE_CSS+'</style><style id="atelier-review-tokens">'+review.theme_tokens(theme)+'</style><style>'+css+'</style>'+('<style id="collision">'+CONFLICT_CSS+'</style>' if conflict else '')+'<script id="atelier-review-boot" type="application/json">'+json.dumps(config)+'</script></head><body>'+footer_body(stage,variant,extra)+'<script>window.commands=[];window.pycmd=(x)=>commands.push(x);window.originalButtons=[...document.querySelectorAll("button")];window.originalHTML=document.getElementById("outer").innerHTML;</script><script>'+js+'</script></body></html>'

CARD_CSS='''html,body{background:#f6eed7;margin:0;font:18px/1.5 Arial;color:#222}body.card{box-sizing:border-box;text-align:center;padding:24px}#qa{margin:0 auto}#io-wrapper{position:relative;display:inline-block;width:600px;height:280px;max-width:none}#io-overlay{position:absolute;inset:0;width:600px;height:280px}#original-image{width:600px;height:280px}.mask{position:absolute;left:336px;top:198px;width:176px;height:32px;background:#ef7e81;border:1px solid #444}#custom-ui{background:#f2ebe0;color:#202020}'''
SVG='''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="280" viewBox="0 0 600 280"><rect width="600" height="280" fill="white"/><g fill="none" stroke="#222" stroke-width="3"><path d="M50 150V90l50-30 50 30v60l-50 30-50-30m100-60 50-30 50 30v60l-50 30-50-30M350 150V90l50-30 50 30v60l-50 30-50-30m100-60 50-30 50 30v60l-50 30-50-30"/></g><rect x="118" y="198" width="160" height="32" fill="#fff0b3" stroke="#444"/></svg>'''
def card(theme='obsidian',kind='io',protected=False):
    import base64
    if kind=='io':html='<div id="io-wrapper"><img id="original-image" src="data:image/svg+xml;base64,'+base64.b64encode(SVG.encode()).decode()+'"><div id="io-overlay"><div class="mask"></div></div></div>'
    elif kind=='basic':html='<p>What makes an effective study session?</p><p id="answer" hidden>One clear objective. A manageable set of questions.</p>'
    elif kind=='typed':html='<p>Type the missing word.</p><input id="typeans" value="retained input"><button onclick="pycmd(\'play\')">Replay audio</button>'
    else:html='<div id="custom-ui"><canvas width="200" height="100"></canvas><input value="keep my input"><button onclick="pycmd(\'custom\')">Custom control</button></div>'
    info={'eligible':kind in ('basic','typed'), 'imageOcclusion':kind=='io','protected':protected,'path':['Sample collection','Study skills','Lecture 1'],'stage':'question'}
    cfg={'screen':'review','style':'adaptive','theme':theme,'width':'standard','motion':False}
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+CARD_CSS+'</style><style id="atelier-review-tokens">'+review.theme_tokens(theme)+'</style><style>'+asset('reviewer.css')+'</style><script id="atelier-review-boot" type="application/json">'+json.dumps(cfg)+'</script></head><body class="card nightMode"><div id="qa">'+html+'</div><script>window.pycmd=()=>{};window.__atelierReviewCard='+json.dumps(info)+';window.originalQA=document.getElementById("qa");window.originalHTML=originalQA.innerHTML;window.beforeGeometry=[...document.querySelectorAll("#io-wrapper,#original-image,#io-overlay,.mask")].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]});</script><script>'+asset('reviewer.js')+'</script></body></html>'


def home(mode='workspace',live=False,delay=1000,js=True):
    from bs4 import BeautifulSoup
    source=(ROOT/'tests/data/home-sample.html').read_text()
    soup=BeautifulSoup(source,'html.parser')
    boot=json.loads(soup.find(id='atelier-bootstrap').text)
    boot['version']='0.6.1';boot['settings']['mode']=mode;boot['settings']['surface_revision']=1;boot['preview']=not live
    boot['demo']['settings']['mode']=mode;boot['demo']['settings']['surface_revision']=1
    boot['settings']['motion']=False;boot['demo']['settings']['motion']=False
    # Keep original-home fixture and its event handlers, but remove old renderer/assets.
    for tag in soup.find_all('script'):tag.decompose()
    soup.find(id='atelier-style').decompose()
    h=soup.find(id='atelier-root');h.decompose()
    original=str(soup.body)
    original=original[original.index('>')+1:original.rindex('</body>')]
    head=''.join(str(t) for t in soup.head.contents)
    bg=guard.home_guard(core.settings(boot['settings']))
    bridge=''
    if live:
        bridge='window.pycmd=msg=>{if(!msg.startsWith("atelier:v1:"))return;let d=JSON.parse(msg.slice(msg.indexOf(":",11)+1));if(d.action==="load")setTimeout(()=>window.AtelierMakeover.receive({token:"preview",id:d.id,result:DEMO}),DELAY);};'.replace('DEMO',json.dumps(boot['demo'])).replace('DELAY',str(delay))
    scripts='<script>'+bridge+'</script>'+''.join('<script>'+asset(n)+'</script>' for n in ('widget-registry.js','native-widgets.js','model.js','cohesion.js','home.js','atelier.js')) if js else ''
    return '<!doctype html><html><head>'+bg+head+'</head><body><div id="atelier-root"></div><script id="atelier-bootstrap" type="application/json">'+core.json_for_html(boot)+'</script><template id="atelier-style"><style>'+asset('atelier.css')+'</style></template>'+original+scripts+'</body></html>'

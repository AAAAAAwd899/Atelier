"""Pre-paint ownership and scoped shared-home palette; no foreign DOM replacement."""
from .review_model import PALETTES
from .core import json_for_html
from pathlib import Path

def home_guard(config: dict) -> str:
    p = PALETTES.get(config['theme'], PALETTES['obsidian'])
    mode = 'original' if config['mode'] == 'native' and config.get('visual_owner') != 'ask' else 'workspace'
    data = json_for_html({'mode':mode, 'bg':p['bg'], 'text':p['text'], 'tokens':p, 'shared':config.get('visual_owner', 'atelier') == 'atelier', 'sprout':config.get('visual_owner') == 'atelier' and config.get('match_sprout', True), 'owner':config.get('visual_owner', 'ask')})
    # The original body retains its dimensions and nodes but is not composited
    # in workspace mode. Opacity on the ancestor also covers descendants with
    # explicit visibility rules. No race against collection snapshot loading.
    css = '\nhtml[data-atelier-home="workspace"] {background:var(--atelier-load-bg)!important;overflow:hidden!important;}\nhtml[data-atelier-home="workspace"] body {opacity:0!important;pointer-events:none!important;max-width:100vw!important;width:100%!important;overflow:hidden!important;}\nhtml[data-atelier-home="workspace"] #atelier-root {opacity:1!important;}\nhtml[data-atelier-home="workspace"]::before {content:""!important;position:fixed!important;inset:0!important;background:var(--atelier-load-bg)!important;z-index:2147482000!important;pointer-events:none!important;}\nhtml[data-atelier-home="workspace"][data-atelier-mounted]::before {content:none!important;}\n#atelier-paint-fallback{all:initial!important;position:fixed!important;z-index:2147483200!important;inset:0!important;background:var(--atelier-load-bg)!important;color:var(--atelier-load-fg)!important;display:grid!important;place-content:center!important;gap:18px!important;text-align:center!important;font:16px/1.5 system-ui,sans-serif!important;}\n#atelier-paint-fallback button{all:initial;cursor:pointer;font:600 14px system-ui;color:inherit;border:1px solid currentColor;border-radius:9px;padding:13px 20px;text-align:center;}\n'
    js = r'''
(()=>{'use strict';const c=CONFIG,r=document.documentElement;
for(const [k,v] of Object.entries(c.tokens))r.style.setProperty('--ats-'+k,v);r.dataset.atelierShared=String(c.shared);r.dataset.atelierMatchSprout=String(c.sprout);
r.style.setProperty('--atelier-load-bg',c.bg);r.style.setProperty('--atelier-load-fg',c.text);r.dataset.atelierHome=c.mode;r.dataset.atelierOwner=c.owner;
let mounted=false, timer;
function original(){clearTimeout(timer);delete r.dataset.atelierShared;delete r.dataset.atelierMatchSprout;document.body?.classList.remove('atelier-home');delete r.dataset.atelierHome;delete r.dataset.atelierMounted;document.getElementById('atelier-paint-fallback')?.remove();const h=document.getElementById('atelier-root');if(h)h.style.setProperty('display','none','important');if(document.body){document.body.removeAttribute('inert');document.body.removeAttribute('aria-hidden');}}
function ready(mode){mounted=true;clearTimeout(timer);document.getElementById('atelier-paint-fallback')?.remove();r.dataset.atelierMounted='true';r.dataset.atelierHome=mode==='native'?'original':'workspace';}
window.AtelierPaint=Object.freeze({ready,original});
if(c.mode==='workspace')timer=setTimeout(()=>{if(mounted)return;const n=document.createElement('section');n.id='atelier-paint-fallback';const t=document.createElement('strong');t.textContent='The study desk could not finish opening.';const b=document.createElement('button');b.textContent='Use original Anki home';b.onclick=original;n.append(t,b);r.append(n);},7000);
})();
'''.replace('CONFIG',data)
    shared = (Path(__file__).parent / 'web' / 'shared.css').read_text(encoding='utf-8') if config.get('visual_owner', 'atelier') == 'atelier' else ''
    return '<style id="atelier-shared-style">'+shared+'</style><style id="atelier-paint-style">'+css+'</style><script>'+js+'</script>'

"""One-time, reviewable presentation migration from the verified source."""
from pathlib import Path
import json,re
from generate_design import ROLE_KEYS,generate
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'src'/'web'
def edit(name,transform):
    p=ROOT/name;p.write_text(transform(p.read_text(encoding='utf8')),encoding='utf8')
palettes=json.loads((WEB/'palettes.json').read_text(encoding='utf8'))
contract={'schema':1,'measurements':{'font':'"Segoe UI", -apple-system, BlinkMacSystemFont, system-ui, sans-serif','body':'15px','helper':'13px','control':'40px','rail':'240px','gutter':'28px','radius':'12px','motion':'160ms'},'worlds':{}}
for name,p in palettes.items():
    p['input']=p['panel']
    contract['worlds'][name]={'roles':{role:p[key] for role,key in ROLE_KEYS.items()},'compatibility':{k:v for k,v in p.items() if k not in ROLE_KEYS.values()}}
(WEB/'design-contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf8')
# Remove obsolete color definitions from the base sheet: the generated token sheet owns them.
keys=set(palettes['obsidian'])
edit('src/web/atelier.css',lambda s:re.sub(r'--([a-z-]+)\s*:\s*([^;{}]+);',lambda m:'' if m[1] in keys else m[0],s).replace('grid-template-columns:260px minmax(0,1fr)','grid-template-columns:240px minmax(0,1fr)').replace('font-family:Inter,"Segoe UI",-apple-system,BlinkMacSystemFont,Arial,sans-serif;font-size:14px','font-family:var(--atelier-font);font-size:15px'))
# Merge the small shared header layer into its existing layout owner, no extra trailing sheet.
header=(WEB/'studio-home.css').read_text(encoding='utf8')
edit('src/web/home-shell.css',lambda s:header+'\n'+s)
edit('src/worlds.py',lambda s:s.replace("'studio-home.css',",''))
(WEB/'studio-home.css').write_text('/* Retired in 1.0.3: shared header components now live in home-shell.css. */\n',encoding='utf8')
def home(s):
    s=s.replace('min-height:78px','min-height:72px').replace('padding:14px 28px','padding:12px 28px')
    s=s.replace('min-height:38px;padding:8px 11px;font-size:13px','min-height:40px;padding:9px 11px;font-size:14px')
    s=s.replace('padding:25px 27px 24px','padding:19px 24px 20px').replace('clamp(25px,2.55vw,37px)','clamp(26px,2.4vw,34px)')
    s=s.replace('margin-bottom:13px','margin-bottom:8px').replace('margin-top:12px;max-width:60ch;font-size:13px','margin-top:8px;max-width:60ch;font-size:14px')
    s=s.replace('margin-top:18px;gap:9px','margin-top:14px;gap:9px').replace('min-height:39px;font-size:12px','min-height:40px;font-size:14px')
    s=s.replace('height:174px;min-height:174px','height:174px;min-height:174px')
    s=s.replace('font-size:10px;','font-size:13px;').replace('font-size:11px;','font-size:13px;').replace('font-size:12px;','font-size:14px;')
    s=s.replace('padding:12px 13px','padding:10px 12px').replace('margin-top:17px','margin-top:12px')
    return s
edit('src/web/home-shell.css',home)
edit('src/web/worlds-home.css',lambda s:s.replace('background:radial-gradient(ellipse at 92% 0%,var(--hero-end),transparent 65%),var(--bg);','background:linear-gradient(180deg,var(--bg) 0%,transparent 58%),var(--world-art) center bottom / cover fixed,var(--bg);').replace('background:linear-gradient(125deg,var(--hero),var(--hero-end));','background:var(--panel);'))
edit('src/web/native-widgets.css',lambda s:s.replace('max-width:1280px;padding:24px clamp(18px,3vw,42px) 36px;margin:0 auto','max-width:1490px;padding:24px 28px 36px;margin:0').replace('min-height:94px;padding:22px clamp(18px,3vw,42px)','min-height:80px;padding:16px 28px').replace('background:linear-gradient(135deg,var(--panel),var(--side))','background:var(--panel)').replace('border-radius:var(--world-radius,20px)','border-radius:var(--atelier-radius,12px)').replace('font-size:12px;','font-size:13px;'))
edit('src/web/atelier.js',lambda s:s.replace("'Pick up where you left off.'","'Welcome back.'").replace("'Choose your next lecture.'","'Choose your next lecture.'"))
worlds=json.loads((WEB/'worlds.json').read_text(encoding='utf8'))
for w in worlds:
    if w['id']=='midnight':w['font']='"Segoe UI", system-ui, sans-serif'
    w['radius']=min(w['radius'],18)
(WEB/'worlds.json').write_text(json.dumps(worlds,indent=2)+'\n',encoding='utf8')
generate()

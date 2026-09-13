"""One-time 1.0.3 visual refinement; generated adapters rebuilt separately."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'src/web'
def edit(name, pairs):
    p=WEB/name;text=p.read_text(encoding='utf8')
    for before,after in pairs:
        if before not in text:raise ValueError((name,before))
        text=text.replace(before,after)
    p.write_text(text,encoding='utf8')
edit('atelier.css',[
 ('padding:30px 16px 16px','padding:20px 16px 16px'),
 ('padding:0 10px 27px','padding:0 10px 22px'),
 ('.brand strong{font-size:32px;letter-spacing:-1.8px}', '.brand strong{font-size:23px;letter-spacing:-.7px}'),
 ('padding-top:28px;', 'padding-top:20px;'),
 ('font-size:29px;letter-spacing:-1.45px','font-size:23px;letter-spacing:-.7px'),
 ('.brand strong{font-size:26px;}', '.brand strong{font-size:23px;}')])
edit('worlds-home.css',[
 ('background:var(--world-art) center 48%/cover','background:var(--world-scene,var(--world-art)) center 65%/cover')])
edit('shared.css',[
 ('grid-template-columns:36px minmax(0,1fr) auto 16px', 'grid-template-columns:28px minmax(0,1fr) auto 16px'),
 ('min-height:78px!important;', 'min-height:48px!important;'),
 ('padding:14px!important;border-radius:16px!important;', 'padding:10px 14px!important;border-radius:10px!important;')])
c=json.loads((WEB/'design-contract.json').read_text(encoding='utf8'))
f=c['worlds']['forest']
f['roles'].update({'canvas':'#0c171c','sidebar':'#101f24','panel':'#172930','raised':'#20343b','input':'#172930','selected':'#25443f','border':'#31494f','strong-border':'#4b696e','text':'#e9f2f0','muted':'#b7ccc8','action':'#a4d7bb','action-text':'#10291f','focus':'#c7e8d8'})
f['compatibility'].update({'hover':'#29453f','quiet':'#aac3bc','hero':'#1d353b','hero-end':'#172930','glow':'#a4d7bb','glow2':'#91c9ce','shadow':'rgba(0,0,0,.22)'})
(WEB/'design-contract.json').write_text(json.dumps(c,indent=2)+'\n',encoding='utf8')
worlds=json.loads((WEB/'worlds.json').read_text(encoding='utf8'))
for w in worlds:
    if w['id'] in ('forest','midnight','rose'):w['scene']='world-art/'+w['id']+'-1.0.3.png'
(WEB/'worlds.json').write_text(json.dumps(worlds,indent=2)+'\n',encoding='utf8')

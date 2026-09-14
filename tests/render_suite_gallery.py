"""Render/current-code visual review and self-contained screenshot gallery.
No native Qt, mockup images or generated fake application screens.
"""
from suite_fixtures import *
from playwright.sync_api import sync_playwright
from PIL import Image,ImageDraw,ImageFont
import base64,io,html as htmlmod,hashlib,shutil
D=ROOT/'dist';D.mkdir(parents=True,exist_ok=True);S=ROOT/'screenshots/worlds';S.mkdir(parents=True,exist_ok=True)

def reviewer_page(theme):
    main=card(theme,'basic')
    old='<p>What makes an effective study session?</p><p id="answer" hidden>One clear objective. A manageable set of questions.</p>'
    main=main.replace(old,'<p>Which ideas connect these two concepts?</p>')
    bar=footer(theme,'question','old',True)
    p=review.PALETTES[theme]
    top='''<!doctype html><html><head><style>html,body{margin:0;font:12px "Segoe UI",Arial;background:BG;color:TEXT}nav{height:54px;display:flex;justify-content:center;align-items:center;gap:9px}button{font:inherit;border:1px solid LINE;background:PANEL;border-radius:8px;padding:8px 14px;color:inherit}.sample{position:absolute;left:18px;top:21px;font:9px system-ui;letter-spacing:1px;color:MUTED}</style></head><body><div class="sample">SAMPLE NAVIGATION</div><nav><button>Home</button><button>Add cards</button><button>Browse</button><button>Statistics</button><button>Sync</button></nav></body></html>'''
    for k,v in {'BG':p['bg'],'TEXT':p['text'],'LINE':p['line'],'PANEL':p['panel'],'MUTED':p['muted']}.items():top=top.replace(k,v)
    return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier reviewer — browser fixture</title><style>html,body{margin:0;height:100%;overflow:hidden}.app{height:100dvh;display:grid;grid-template-rows:54px minmax(0,1fr) 116px}iframe{border:0;width:100%;height:100%;min-height:0;display:block}</style></head><body><div class="app">'''+''.join('<iframe title="'+title+'" srcdoc="'+htmlmod.escape(doc,quote=True)+'"></iframe>' for title,doc in [('Sample navigation',top),('Current reviewer styles',main),('Current review controls',bar)])+'</div></body></html>'

def enc(path,width=1440):
    im=Image.open(path).convert('RGB');im.thumbnail((width,1500));f=io.BytesIO();im.save(f,format='WEBP',quality=86,method=3)
    return 'data:image/webp;base64,'+base64.b64encode(f.getvalue()).decode()

def main():
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        p=b.new_page(viewport={'width':1440,'height':850});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        for world in worlds.CATALOG:
            print('Reviewer',world['id'],flush=True)
            p.set_content(reviewer_page(world['id']));p.wait_for_timeout(140)
            p.screenshot(path=str(S/f"{world['id']}-reviewer.png"),animations='disabled')
        p.set_viewport_size({'width':390,'height':800});p.set_content(home_suite('forest'),wait_until='domcontentloaded');p.locator('.layout').wait_for(timeout=10000);p.screenshot(path=str(D/'Atelier-Narrow-Home.png'),animations='disabled')
        assert not errors,errors
        b.close()
    # Home is the actual program with explicit offline native-action notices.
    (D/'Atelier-Preview.html').write_text(home_suite('forest'))
    (D/'Atelier-Reviewer-Preview.html').write_text(reviewer_page('forest'))
    for original,dest in [('forest-home','Atelier-Forest'),('forest-planner','Atelier-Exam-Studio'),('forest-practice','Atelier-Practice'),('forest-reviewer','Atelier-Reviewer'),('forest-tools','Atelier-Anki-Tools'),('rose-home','Atelier-Rose'),('celestial-home','Atelier-Celestial')]:
        shutil.copyfile(S/(original+'.png'),D/(dest+'.png'))
    dataset=[]
    for w in worlds.CATALOG:
        screens={key:enc(S/f"{w['id']}-{key}.png") for key in ['home','planner','practice','reviewer']}
        dataset.append({**w,'screens':screens})
    data=json.dumps(dataset).replace('</','<\\/')
    gallery='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier — Study Worlds</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101820;color:#e4ebe8;font:15px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:40px 28px}header{max-width:800px;margin-bottom:30px}h1{font:500 clamp(32px,4vw,58px)/1.15 Georgia,serif;margin:12px 0}p{color:#adbeb7}small{color:#adbeb7}.kicker{letter-spacing:2px;font-size:11px;color:#afc596}.controls{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}button{font:inherit;color:inherit;background:#19272c;border:1px solid #38494c;border-radius:10px;padding:9px 14px;cursor:pointer}button:hover,button.active{background:#2b433e;border-color:#91af85}button:focus-visible{outline:3px solid #b8cf96;outline-offset:3px}.stage{background:#142026;border:1px solid #344447;border-radius:18px;overflow:hidden}.stage img{width:100%;height:auto;display:block}.description{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin:24px 0 8px}.description h2{font:30px Georgia;margin:0}.note{font-size:12px;margin:14px 0;color:#a7bbb2}.foot{margin-top:32px;border-top:1px solid #334347;padding-top:18px}.badge{padding:3px 8px;border:1px solid #445850;border-radius:5px;font-size:10px}a{color:#c1d6a9}@media(max-width:600px){main{padding:24px 14px}.controls{gap:6px}button{font-size:12px;padding:7px 10px}}</style>
<main><header><div class="kicker">ATELIER / 0.8.0-rc6 / STUDY, CREATE & ORGANIZE</div><h1>Many worlds.<br>One complete study space.</h1><p>Original scenery, typography, silhouettes and materials—coordinated across the real home, bundled Exam Studio, practice builder and reviewer.</p><span class="badge">CAPTURECOUNT actual browser screenshots</span></header><nav class="controls" id="worlds" aria-label="Choose world"></nav><div class="description"><h2 id="title"></h2><span id="subtitle"></span></div><p id="description"></p><nav class="controls" id="screens" aria-label="Choose screen"></nav><div class="stage"><img id="display" alt=""></div><p class="note">Current packaged interface, rendered in Chromium with fictional sample data. This gallery is screenshot navigation, not a running Anki collection. Reviewer navigation is a browser fixture, not native Qt. Pip screenshots use the available animated fallback; live WebGL is not verified here.</p><p class="foot">One installable addon. Original Anki controls remain accessible. Onigiri stays optional. User-reported visual and primary testing is recorded separately from automated browser checks. No AnkiWeb upload was performed.<br>Daedalus Works · Atelier</p></main><script>const worlds=DATA;let wi=8,screen='home';const names={home:'Study desk',planner:'Exam Studio',practice:'Practice & mocks',reviewer:'Reviewer'};function render(){const w=worlds[wi];document.getElementById('title').textContent=w.name;document.getElementById('subtitle').textContent=w.title;document.getElementById('description').textContent=w.description;const im=document.getElementById('display');im.src=w.screens[screen];im.alt=w.name+' — '+names[screen]+' actual browser screenshot';document.getElementById('worlds').replaceChildren(...worlds.map((x,i)=>{const b=document.createElement('button');b.textContent=x.name;b.className=i===wi?'active':'';b.setAttribute('aria-pressed',i===wi);b.onclick=()=>{wi=i;render()};return b}));document.getElementById('screens').replaceChildren(...Object.entries(names).map(([k,n])=>{const b=document.createElement('button');b.textContent=n;b.className=k===screen?'active':'';b.setAttribute('aria-pressed',k===screen);b.onclick=()=>{screen=k;render()};return b}));}render();</script></html>'''.replace('DATA',data).replace('CAPTURECOUNT',str(len(worlds.CATALOG)*4)).replace('0.8.0-rc6',core.VERSION)
    (D/'Atelier-Worlds-Gallery.html').write_text(gallery)
    # Visual review contact sheets from genuine full screenshots.
    for screen in ('home','planner','practice','reviewer'):
        sheet=Image.new('RGB',(1440,4*300),(235,236,232));draw=ImageDraw.Draw(sheet)
        for i,w in enumerate(worlds.CATALOG):
            im=Image.open(S/f"{w['id']}-{screen}.png").convert('RGB');im.thumbnail((460,260))
            x=(i%3)*480+10;y=(i//3)*300+25;sheet.paste(im,(x,y));draw.text((x,y-18),w['name']+' / '+screen,fill=(20,26,22))
        sheet.save(D/f'Atelier-{screen.title()}-Contact-Sheet.png')
    print('Gallery and 12 reviewer screenshots created from shipped code.')
if __name__=='__main__':main()

"""Real renderer screenshots and offline preview of the no-Onigiri widgets page."""
from pathlib import Path
import base64,io,json,hashlib,shutil,sys
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from test_native_widgets_browser import native_fixture,ROOT,SRC,core
sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
D=ROOT/'dist';SH=ROOT/'screenshots/native-widgets-release';SH.mkdir(parents=True,exist_ok=True)

def main():
 entries=[];errors=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':1000});p.on('pageerror',lambda e:errors.append(str(e)))
  def shot(title,name):
   dest=SH/(name+'.png');p.screenshot(path=str(dest),animations='disabled');entries.append((title,dest));return dest
  for theme in core.THEMES:
   p.set_content(native_fixture(theme,live=False));p.locator('.nw-metrics').wait_for();p.wait_for_timeout(80)
   dest=shot(theme+' · Widgets without Onigiri',theme+'-widgets')
   if theme=='ember':shutil.copy(dest,D/'Atelier-Native-Widgets.png')
   if theme=='forest':shutil.copy(dest,D/'Atelier-Native-Widgets-Forest.png')
  p.set_content(native_fixture('ember',live=False));p.locator('.nw-metrics').wait_for()
  p.locator('.nw-toolbar [data-action="nw-tools"]').click();p.locator('.nw-tools-list').wait_for();p.wait_for_timeout(60)
  shutil.copy(shot('More tools · same native routes','more-tools'),D/'Atelier-Widget-Tools.png');p.keyboard.press('Escape')
  p.locator('.nw-header [data-action="nw-arrange"]').click();p.locator('.nw-arranged-list').wait_for()
  shutil.copy(shot('Arrange widgets · choose, order and place','arrange'),D/'Atelier-Arrange-Widgets.png')
  p.locator('[data-action="nw-add"][data-id="notes"]').click();p.locator('[data-nw-home="notes"]').check();p.locator('[data-nw-size="notes"]').select_option('wide');p.locator('[data-action="nw-save"]').click()
  p.locator('[data-native-widget="notes"] [data-action="nw-note"]').click();p.locator('#nw-note-input').fill('Before the next session\nReview the lecture summary, then rehearse one topic at a time.');p.locator('[data-action="nw-note-save"]').click();p.locator('.nav-row[data-action="home"]').click();p.locator('.nw-on-home').wait_for()
  shutil.copy(shot('Your widget on the main Study desk','home-with-note'),D/'Atelier-Home-With-Widget.png')
  p.locator('.native-link[data-action="widget-page"]').click();p.locator('.nw-toolbar').wait_for();p.set_viewport_size({'width':390,'height':820});p.wait_for_timeout(120)
  shutil.copy(shot('Widgets · narrow desktop webview','narrow'),D/'Atelier-Native-Widgets-Narrow.png')
  assert not errors,errors;b.close()
 (D/'Atelier-Native-Widgets-Preview.html').write_text(native_fixture('ember',live=False),encoding='utf8')
 records=[];images=[]
 for label,path in entries:
  image=Image.open(path).convert('RGB');image.thumbnail((1440,1600));buf=io.BytesIO();image.save(buf,'WEBP',quality=88,method=3)
  images.append({'title':label,'image':'data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()})
  records.append({'title':label,'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':list(Image.open(path).size)})
 page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier · Native home widgets</title><style>*{box-sizing:border-box}body{margin:0;background:#161c1b;color:#ecede8;font:15px/1.6 system-ui}main{max-width:1480px;margin:auto;padding:32px 24px}h1{font:500 clamp(28px,4vw,50px)/1.18 Georgia,serif}p{color:#bac8c0;max-width:900px}select{font:inherit;padding:10px 14px;color:inherit;background:#20362c;border:1px solid #667766;border-radius:8px;margin:12px 0 20px;max-width:100%}img{width:100%;height:auto;display:block;border:1px solid #586d60;border-radius:12px}select:focus-visible{outline:3px solid #c2d5a4;outline-offset:3px}small{display:block;color:#b2c4b7;padding-top:12px}@media(max-width:500px){main{padding:24px 12px}}</style></head><body><main><h1>Your Anki home.<br>No Onigiri required.</h1><p>Atelier VERSION: a three-action header, real built-in study widgets, and a customizable home. These are actual Chromium screenshots of the shipped code with fictional preview data. No restaurant or reward progress is recreated. The layouts run without an Onigiri document.</p><label>View <select id="pick"></select></label><img id="shot" alt=""><small id="caption"></small><p>Visual and primary acceptance was reported by the project owner; these images are browser renders, not independent native Windows certification. Optional installed add-ons can register their own widgets; legacy provider games remain accessible through their original page. This gallery switches images, not your study records.</p></main><script>const data=DATA;const pick=document.getElementById('pick');for(let i=0;i<data.length;i++){let o=document.createElement('option');o.value=i;o.textContent=data[i].title;pick.append(o)}function show(){const s=data[+pick.value];document.getElementById('shot').src=s.image;document.getElementById('shot').alt=s.title;document.getElementById('caption').textContent=s.title+' · sample data · actual browser render, not native Windows';}pick.onchange=show;pick.value=7;show();</script></body></html>'''.replace('VERSION',core.VERSION).replace('DATA',json.dumps(images).replace('</',r'<\/'))
 (D/'Atelier-Native-Widgets-Gallery.html').write_text(page,encoding='utf8')
 (D/'Atelier-Native-Widgets-Evidence.json').write_text(json.dumps({'version':core.VERSION,'runtime_sha256':runtime_digest(),'captures':records,'browser_errors':errors,'native_windows':False},indent=2)+'\n')
 sheet=Image.new('RGB',(1440,1320),'#dddeda');draw=ImageDraw.Draw(sheet)
 for i,(label,path) in enumerate(entries[:12]):
  im=Image.open(path).convert('RGB');im.thumbnail((462,300));x=i%3*480+8;y=i//3*330+24;sheet.paste(im,(x,y));draw.text((x,y-18),label,fill='#1a211e')
 sheet.save(D/'Atelier-Native-Widgets-Contact-Sheet.png')
 print(len(entries),'actual no-Onigiri/arrangement/home screenshot views')
if __name__=='__main__':main()

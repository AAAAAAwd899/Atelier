from pathlib import Path
from playwright.sync_api import sync_playwright
import json
R=Path(__file__).resolve().parents[1];D=R/'dist';results=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for filename,total,mode in [('Atelier-Native-Widgets-Gallery.html',16,'native'),('Atelier-Complete-Gallery.html',120,'complete')]:
  p=b.new_page(viewport={'width':1440,'height':900});errors=[];external=[]
  p.on('pageerror',lambda e:errors.append(str(e)))
  p.on('request',lambda r:external.append(r.url) if r.url.startswith(('http://','https://')) else None)
  p.set_content((D/filename).read_text(encoding='utf8'), wait_until='load')
  count=p.evaluate('''async (mode)=>{const urls=mode==='native'?data.map(d=>d.image):data.flatMap(d=>Object.values(d.screens));for(const url of urls){const im=new Image();im.src=url;await im.decode();if(!im.naturalWidth||!im.naturalHeight)throw Error('Invalid capture');}return urls.length}''',mode)
  assert count==total,(filename,count)
  p.locator('select').first.select_option('0')
  p.locator('img').first.evaluate('(e)=>e.decode()')
  p.set_viewport_size({'width':390,'height':800})
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not errors and not external,(errors,external)
  results.append({'gallery':filename,'decoded':count,'controls':True,'width_390_contains':True,'page_errors':errors,'external_requests':external})
  p.close()
 b.close()
(R/'verification/native-widgets/gallery-check.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))

"""Validate the current self-contained120capture gallery; not native application testing."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
def main():
 errors=[];remote=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1280,'height':850});p.on('pageerror',lambda e:errors.append(str(e)))
  p.on('request',lambda r:remote.append(r.url) if r.url.startswith(('http:','https:')) else None)
  p.set_content((R/'dist/Atelier-Complete-Gallery.html').read_text(),wait_until='load')
  dims=p.evaluate('''async()=>{const rows=[];for(const w of data){for(const [view,src] of Object.entries(w.screens)){const im=new Image();im.src=src;await im.decode();rows.push({world:w.id,view,width:im.naturalWidth,height:im.naturalHeight});}}return rows;}''')
  assert len(dims)==120 and all(x['width']>200 and x['height']>200 for x in dims)
  p.select_option('#world','2');p.locator('[data-view="sources"]').click()
  assert 'Rose Quartz' in p.locator('#name').text_content() and 'Sources' in p.locator('#caption').text_content()
  p.set_viewport_size({'width':390,'height':760});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not errors and not remote
  b.close()
 report={'count':120,'errors':errors,'external_requests':remote,'current_gallery_views':'12 worlds x 10 screens','native_windows':False,'images':dims}
 (R/'verification/gallery-final.json').write_text(json.dumps(report,indent=2)+'\n')
 print('120 image decodes; live world/view changes; narrow containment; zero errors/remote requests')
if __name__=='__main__':main()

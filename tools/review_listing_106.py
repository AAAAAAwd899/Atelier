"""Render the owner listing preview; this does not submit to AnkiWeb."""
from pathlib import Path
import hashlib,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'listing/ankiweb-1.0.6';out=ROOT/'screenshots/listing-review-106';out.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width,height in [(1440,900),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((folder/'preview.html').as_uri());page.locator('img').last.wait_for()
        page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
        state=page.evaluate('''()=>({images:document.images.length,imagesLoaded:[...document.images].every(i=>i.naturalWidth>0),noHorizontalOverflow:document.documentElement.scrollWidth<=innerWidth,links:[...document.querySelectorAll('a')].map(a=>a.href),headings:[...document.querySelectorAll('h2')].map(e=>e.textContent),alt:[...document.images].every(i=>!!i.alt)})''')
        page.screenshot(path=str(out/f'preview-{width}-top.png'))
        page.evaluate('window.scrollTo(0,document.body.scrollHeight)');page.screenshot(path=str(out/f'preview-{width}-bottom.png'))
        assert state['imagesLoaded'] and state['noHorizontalOverflow'] and state['alt'] and not errors
        results.append({'viewport':[width,height],**state,'errors':errors});page.close()
    browser.close()
report={'category':'local listing preview, not AnkiWeb upload editor','description_sha256':hashlib.sha256((folder/'description.html').read_bytes()).hexdigest(),'views':results,'submission_performed':False}
(ROOT/'verification/listing-preview-106.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({'views':len(results),'checks_passed':True}))

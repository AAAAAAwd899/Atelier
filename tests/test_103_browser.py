"""After-render IO view geometry with explicit native-template/renderer stand-ins."""
from fixtures import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/playwright/reviewer-103';OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def check(name,value):
    assert value,name
    checks.append(name)
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/chromium')
    p=b.new_page(viewport={'width':1000,'height':720})
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.set_content(card('midnight','basic'))
    p.evaluate('''()=>{
      window.anki={imageOcclusion:{setup(){}}};
      const q=document.getElementById('qa');
      q.innerHTML='<div id="image-occlusion-container" style="position:relative;width:800px;height:1200px;margin:0 auto"><img style="width:800px;height:1200px" src="data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1200"><rect width="800" height="1200" fill="white"/><path d="M0 600h800M400 0v1200" stroke="black" stroke-width="4"/><rect x="200" y="300" width="180" height="100" fill="#cde"/></svg>')+'"><canvas id="image-occlusion-canvas" width="800" height="1200" style="position:absolute;inset:0;width:800px;height:1200px"></canvas></div>';
      window.originalStage=q.firstElementChild;window.originalImage=originalStage.children[0];window.originalCanvas=originalStage.children[1];
      const ctx=originalCanvas.getContext('2d');ctx.fillStyle='#ed9399';ctx.fillRect(200,300,180,100);
      window.imageBefore=originalImage.outerHTML;window.canvasBefore=originalCanvas.toDataURL();window.stageBefore=originalStage.getAttribute('style');
      window.ioInfo={id:'native-io-1',stage:'question',eligible:false,ioFit:true,imageOcclusion:true,path:['Sample course','Current lecture']};
      AtelierReview.painted(ioInfo);
      requestAnimationFrame(()=>AtelierReview.settled(ioInfo));
    }''')
    p.locator('#atelier-image-fit').wait_for();p.wait_for_timeout(250)
    for width,height in [(1000,720),(800,600),(1440,900)]:
        p.set_viewport_size({'width':width,'height':height});p.wait_for_timeout(150)
        result=p.evaluate('''()=>{const i=originalImage.getBoundingClientRect(),c=originalCanvas.getBoundingClientRect(),stage=originalStage.getBoundingClientRect();return {registered:Math.abs(i.x-c.x)<.5&&Math.abs(i.y-c.y)<.5&&Math.abs(i.width-c.width)<.5&&Math.abs(i.height-c.height)<.5, fits:stage.bottom<=innerHeight+2, retained:originalImage.outerHTML===imageBefore&&originalCanvas.toDataURL()===canvasBefore&&originalStage.getAttribute('style')===stageBefore, scale:i.width/800, wrappers:document.querySelectorAll('.atelier-image-fit-box').length}}''')
        check(f'{width}x{height} full image/canvas registration',result['registered'])
        check(f'{width}x{height} fits without mask or source changes',result['fits'] and result['retained'])
        check(f'{width}x{height} one bounded wrapper',result['wrappers']==1)
        p.screenshot(path=str(OUT/f'known-io-question-{width}.png'))
    p.locator('#atelier-image-fit').click();p.wait_for_timeout(100)
    check('Actual size restores original node and geometry',p.evaluate('originalStage.parentElement.id==="qa"&&originalStage.getBoundingClientRect().height===1200'))
    p.locator('#atelier-image-fit').click();p.wait_for_timeout(100)
    p.evaluate('AtelierReview.configure({style:"off"})');p.wait_for_timeout(100)
    check('Disable restores layout and removes owned controls',p.evaluate('originalStage.parentElement.id==="qa"&&!document.getElementById("atelier-image-fit")'))
    p.evaluate('AtelierReview.configure({style:"adaptive"});AtelierReview.painted({...ioInfo,id:"unknown",ioFit:false,protected:true})');p.wait_for_timeout(100)
    check('Unknown custom template untouched',p.evaluate('originalStage.parentElement.id==="qa"&&!document.getElementById("atelier-image-fit")'))
    check('No browser errors',not errors)
    b.close()
(OUT/'results.json').write_text(json.dumps({'category':'browser fixture; renderer stand-in, not native mask rendering','count':len(checks),'checks':checks,'errors':errors},indent=2)+'\n')
print(len(checks),'IO view checks passed')

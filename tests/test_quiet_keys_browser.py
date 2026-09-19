"""Exercise the shipped card-local keyboard script in Chromium, not a Qt mockup."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
OUT=R/'verification/quiet-keys';OUT.mkdir(parents=True,exist_ok=True)
JS=(R/'src/sprout/web/review_keys.js').read_text()

def main():
    results=[];errors=[]
    def check(name,v):
        if not v:raise AssertionError(name)
        results.append(name)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1100,'height':760})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content('''<!doctype html><html><body tabindex="-1"><main id="qa"><p id="question">What is 12 × 8?</p><div id="image" style="position:relative;width:600px;height:300px"><img style="width:600px;height:300px" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='300'%3E%3Crect width='600' height='300' fill='%237ca890'/%3E%3C/svg%3E"><div id="mask" style="position:absolute;left:20%;top:20%;width:30%;height:15%;background:salmon"></div></div><input id="typed"><textarea id="notes"></textarea><select id="choices"><option>One</option><option>Two</option></select><div contenteditable="true" id="editable"></div><button id="button">Card control</button><div data-atelier-keys="off" id="custom" tabindex="0">Custom widget</div><div id="shadow"></div></main><script>window.sent=[];window.pycmd=s=>window.sent.push(s);</script></body></html>''')
        baseline=page.locator('#mask').bounding_box();html=page.locator('#qa').inner_html()
        page.add_script_tag(content=JS)
        actions={' ':'primary','Enter':'primary','1':'grade:0','2':'grade:0.5','3':'grade:1','t':'tools'}
        page.evaluate('(actions)=>AtelierReviewKeys.update({token:"abc",actions})',actions)
        page.locator('body').focus();page.keyboard.press('Space')
        check('Space on card emits one current-token primary',page.evaluate('JSON.parse(sent[0].split(":").slice(1).join(":"))')=={'token':'abc','key':' '})
        page.evaluate('sent=[]')
        for sel in ['#typed','#notes','#editable']:
            page.locator(sel).focus();page.keyboard.type('t 123');page.keyboard.press('Enter')
            check(sel+' typing and Enter are not grading shortcuts',page.evaluate('sent.length')==0)
        for sel in ['#button','#choices','#custom']:
            page.locator(sel).focus();page.keyboard.press('Space');page.keyboard.press('1');page.keyboard.press('t')
            check(sel+' owns its keyboard',page.evaluate('sent.length')==0)
        page.evaluate('''()=>{const s=document.getElementById('shadow').attachShadow({mode:'open'});s.innerHTML='<input>';s.querySelector('input').focus();}''')
        page.keyboard.type('t 123')
        check('Editable shadow DOM is protected',page.evaluate('sent.length')==0)
        page.locator('body').focus()
        for opts in [{'key':' ','repeat':True},{'key':'1','isComposing':True},{'key':'t','altKey':True},{'key':'1','metaKey':True},{'key':'1','ctrlKey':True}]:
            page.evaluate('(opts)=>dispatchEvent(new KeyboardEvent("keydown",{bubbles:true,cancelable:true,...opts}))',opts)
            check('repeat/composition/modifier protected '+str(opts),page.evaluate('sent.length')==0)
        page.evaluate('''()=>{const range=document.createRange();range.selectNodeContents(document.getElementById('question'));getSelection().removeAllRanges();getSelection().addRange(range);}''')
        page.keyboard.press('1');check('Selected text is not graded',page.evaluate('sent.length')==0)
        page.evaluate('getSelection().removeAllRanges()')
        page.evaluate('document.addEventListener("keydown",e=>e.preventDefault(),{once:true})')
        page.keyboard.press('Space');check('Card handler default prevention is respected',page.evaluate('sent.length')==0)
        for _ in range(20):page.add_script_tag(content=JS)
        page.keyboard.press('t');check('Repeated installation keeps one listener',page.evaluate('sent.length')==1)
        page.evaluate('sent=[]; AtelierReviewKeys.update({token:"changed",actions:{"1":"learn:1"}})')
        page.keyboard.press('Space');check('Keys absent from current state do nothing',page.evaluate('sent.length')==0)
        page.keyboard.press('1');check('New state carries new token',page.evaluate('JSON.parse(sent[0].slice("atelier-review-key:".length)).token')=='changed')
        page.evaluate('sent=[];AtelierReviewKeys.update(null)');page.keyboard.press('1')
        check('Invalid update disables all actions',page.evaluate('sent.length')==0)
        page.evaluate('AtelierReviewKeys.dispose()');page.keyboard.press('t')
        check('Disposal removes listener',page.evaluate('sent.length')==0)
        check('Native mask rectangle unmodified',page.locator('#mask').bounding_box()==baseline)
        # Input contents changed by deliberate typing, but no nodes were moved or wrapped.
        check('Native question and mask structure retained',page.locator('#image > #mask').count()==1 and page.locator('#qa > #image').count()==1)
        check('No injected control UI inside the card',page.locator('#qa button').count()==1)
        check('No page errors',not errors)
        browser.close()
    report={'count':len(results),'cases':results,'errors':errors,'native_qt':False}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()

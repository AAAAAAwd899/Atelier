"""Real browser reproduction of spacing/IO protections and remote focus permission."""
from fixtures import *
from playwright.sync_api import sync_playwright
from pathlib import Path
OUT=ROOT/'verification'/'1.0.1';OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def check(name,value=True):
 assert value,name
 checks.append(name)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 def page(html,w=1100,h=430):
  p=b.new_page(viewport={'width':w,'height':h});p.set_default_timeout(5000);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html);p.wait_for_timeout(80);return p
 for theme in core.THEMES:
  p=page(card(theme,'basic'))
  p.evaluate('''()=>{window.onigiriReviewerHeaderOffsetPx=78;const q=document.getElementById('qa');q.style.setProperty('margin-top','calc(0px + 78px)','important');q.innerHTML='<p>A medium-length question with four lines.</p><p>Think about the lecture.</p><p>Consider the supplied information.</p>';window.dispatchEvent(new Event('onigiri-reviewer-header-offset'));AtelierReview.painted({id:1,stage:'question',eligible:true,path:['Course','Lecture']});}''')
  p.wait_for_timeout(80)
  check(theme+' duplicate gap removed',p.evaluate("getComputedStyle(document.getElementById('qa')).marginTop==='0px'"))
  check(theme+' medium question fits',p.evaluate('document.scrollingElement.scrollHeight<=innerHeight+1'))
  if theme=='forest':p.screenshot(path=str(OUT/'Atelier-Reviewer-Short.png'))
  p.evaluate('''()=>{document.getElementById('qa').innerHTML='<p>Question</p><hr id="answer"><p>The answer is here.</p>';AtelierReview.painted({id:1,stage:'answer',eligible:true,path:['Course','Lecture']});document.getElementById('answer').scrollIntoView();AtelierReview.settled({id:1,stage:'answer',eligible:true,path:['Course','Lecture']});}''')
  p.wait_for_timeout(80);check(theme+' short reveal has no unnecessary scroll',p.evaluate('scrollY===0&&document.scrollingElement.scrollHeight<=innerHeight+1'))
  p.evaluate('''()=>{document.getElementById('qa').innerHTML='<p>Question</p><hr id="answer">'+('<p>Long answer, preserved reading content.</p>'.repeat(60));AtelierReview.painted({id:1,stage:'answer',eligible:true,path:['Course','Lecture']});}''')
  p.wait_for_function('document.documentElement.dataset.atelierFit==="scroll"');p.evaluate('window.scrollTo(0,800);window.dispatchEvent(new WheelEvent("wheel"))');p.wait_for_timeout(80)
  check(theme+' long answer stays scrollable',p.evaluate('scrollY>0&&document.documentElement.dataset.atelierFit==="scroll"'))
  p.evaluate('''()=>{document.getElementById('qa').innerHTML='<p>Next question.</p>';AtelierReview.painted({id:2,stage:'question',eligible:true,path:['Course','Lecture']});}''')
  p.wait_for_timeout(70);check(theme+' next card resets once',p.evaluate('scrollY===0'))
  p.evaluate("AtelierReview.configure({context:'hidden'});")
  p.wait_for_timeout(60)
  check(theme+' card-only centered',p.evaluate('''()=>{const r=document.getElementById('qa').getBoundingClientRect();return Math.abs((r.top+r.bottom)/2-(innerHeight+78)/2)<18;}'''))
  p.close()
 # IO forms preserve literal markup, size, transforms and pseudo-mask content.
 for kind in ('io','custom'):
  p=page(card('forest',kind),900,600)
  check(kind+' original content unchanged',p.evaluate('originalQA.innerHTML===originalHTML'))
  if kind=='io':check('IO exact image/mask geometry',p.evaluate("JSON.stringify(beforeGeometry)===JSON.stringify([...document.querySelectorAll('#io-wrapper,#original-image,#io-overlay,.mask')].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]}))"))
  p.close()
 p=page(card('forest','basic'),900,500)
 p.evaluate('''()=>{const q=document.getElementById('qa');q.innerHTML='<div id="io-container"><img id="io-original"><img id="io-qmask" style="position:absolute;left:0;top:0"></div>';AtelierReview.setCard({id:5,stage:'question',eligible:true,path:[]});}''')
 p.wait_for_timeout(80);check('legacy IO misclassification corrected',p.evaluate("document.documentElement.dataset.atelierCard!=='reading'"));check('release external top margin when protecting IO',p.evaluate("document.getElementById('qa').style.marginTop!== '0px'"));p.close()
 p=page('<html><body><div tabindex="0" id="stage">Review stage</div><input id="typeans"><div contenteditable="true" id="notes"></div><dialog id="modal">Modal</dialog><script>window.pycmd=x=>(window.messages??=[]).push(x);window.AtelierRemoteToken="test";</script><script>'+asset('remote-input.js')+'</script></body></html>',900,500)
 p.locator('#stage').focus();p.wait_for_timeout(20);check('remote permitted on non-editable reviewer',p.evaluate('AtelierRemoteInput.check().ready'))
 p.locator('#typeans').fill('retain text');check('remote blocked in typed answer',not p.evaluate('AtelierRemoteInput.check().ready'))
 p.locator('#notes').fill('keep notes');check('remote blocked in editable region',not p.evaluate('AtelierRemoteInput.check().ready'))
 p.locator('#stage').focus();p.evaluate('document.getElementById("modal").showModal()');check('remote blocked in dialog',not p.evaluate('AtelierRemoteInput.check(true).ready'));p.evaluate('document.getElementById("modal").close()')
 for i in range(12):p.evaluate(asset('remote-input.js'))
 check('reconfiguration retains written text',p.locator('#typeans').input_value()=='retain text' and p.locator('#notes').inner_text()=='keep notes')
 p.evaluate('AtelierRemoteInput.dispose()');check('disposed input permission false',not p.evaluate('AtelierRemoteInput.check().ready'));p.close()
 check('no uncaught browser errors',not errors)
 b.close()
(OUT/'browser-results.json').write_text(json.dumps({'version':core.VERSION,'count':len(checks),'checks':checks,'errors':errors},indent=2)+'\n')
print('PASS',len(checks))

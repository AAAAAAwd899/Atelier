from widget_route_helpers import open_original_provider
"""Targeted original-theme preservation, startup routing and quiet-review tests.
These are Chromium fixtures, NOT native Anki or the installed Onigiri runtime.
"""
from preview_071 import *
from playwright.sync_api import sync_playwright
import itertools
OUT=ROOT/'dist';OUT.mkdir(exist_ok=True)
checks=[];errors=[]
def ok(name):checks.append(name);print('PASS',name,flush=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),args=['--no-sandbox'])
 def page(html,w=1400,h=900):
  p=b.new_page(viewport={'width':w,'height':h});p.set_default_timeout(3500);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html);p.wait_for_timeout(160);return p
 for owner,mixed,layout in itertools.product(['onigiri','external'],[False,True],[False,True]):
  p=page(home071(owner,mixed=mixed,layout=layout))
  assert p.evaluate('JSON.stringify(nativeSnapshot())===JSON.stringify(originalNative)'),(owner,mixed,layout,p.evaluate('[originalNative,nativeSnapshot()]'))
  assert p.locator('[data-atelier-row-control]').count()==0
  assert p.locator('.companion-dock').is_visible()
  assert p.locator('.companion-dock').bounding_box()['height']<80
  assert not p.locator('.rail').count()
  assert p.evaluate('document.querySelector("#atelier-shared-style").textContent===""')
  # Text is contrasted against OUR dark surface, not the unrelated light canvas.
  contrast=p.evaluate('''()=>{const t=AtelierOwnership.get();const lum=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);return Math.min(...['text','muted','quiet','accent'].flatMap(k=>['bg','panel','raised','hover'].map(s=>(Math.max(lum(t[k]),lum(t[s]))+.05)/(Math.min(lum(t[k]),lum(t[s]))+.05))))}''')
  assert contrast>=4.5,contrast
  p.locator('.dock-details summary').click();assert p.locator('.dock-popover').is_visible()
  p.locator('.dock-popover .exam-remove').first.click();p.wait_for_timeout(80)
  assert p.locator('.dock-popover .exam-remove').count()==1
  assert p.evaluate('originalNativeNode===document.querySelector(".modern-main-menu")')
  # Opening and returning from the organizer must restore exact original page.
  p.locator('.dock-open').click();assert p.locator('.topbar').is_visible()
  open_original_provider(p);p.wait_for_timeout(60)
  assert p.evaluate('JSON.stringify(nativeSnapshot())===JSON.stringify(originalNative)')
  if owner=='onigiri' and mixed and layout:p.screenshot(path=str(OUT/'Atelier-0.7.1-Native-Companion.png'))
  p.close();ok(f'{owner} preserves native markup/geometry/colors with mixed={mixed} saved_layout={layout}; readable own controls')
 p=page(home071('onigiri',shortcuts=True))
 assert p.locator('[data-atelier-row-control]').count()>0
 p.locator('[data-atelier-row-control] button').first.click();p.wait_for_timeout(100)
 assert p.locator('[data-atelier-row-control] button').first.get_attribute('aria-pressed')=='true'
 p.close();ok('original sidebar exam controls are opt-in and functional')
 p=page(home071('ask',onigiri=False))
 assert not p.locator('.owner-screen').count() and p.locator('.topbar').is_visible()
 p.close();ok('no Onigiri/no makeover opens directly without chooser')
 p=page(home071('ask',onigiri=False,others=[{'id':'123','name':'ReColor'}]))
 assert p.locator('.owner-screen').is_visible()
 assert p.get_by_text('Another possible makeover was detected: ReColor.',exact=False).is_visible()
 assert not p.locator('[data-owner="onigiri"]').count()
 assert p.locator('[data-action="choose-owner"][data-owner="external"]').is_visible()
 p.screenshot(path=str(OUT/'Atelier-0.7.1-Makeover-Check.png'))
 p.locator('[data-action="choose-owner"][data-owner="external"]').click();assert p.locator('.companion-dock').is_visible()
 p.close();ok('other makeover gets named warning and original-theme choice')
 p=page(home071('atelier'))
 p.locator('.topbar [data-action="appearance"]').click()
 p.get_by_label('Review context',exact=True).select_option('hidden')
 p.wait_for_timeout(80)
 assert p.get_by_label('Review context',exact=True).input_value()=='hidden'
 p.locator('[data-action="rescan-makeovers"]').click()
 assert p.get_by_text('Another makeover or theme is installed?',exact=True).is_visible()
 p.close();ok('compact/full/card-only setting persists; manual rescan available')
 for mode in ['compact','hidden','full']:
  p=page(card('obsidian','basic'),1100,650)
  p.evaluate('(context)=>AtelierReview.configure({context})',mode);p.wait_for_timeout(50)
  assert p.evaluate('originalQA===document.getElementById("qa")&&originalHTML===originalQA.innerHTML')
  if mode=='compact':
   assert not p.locator('.atelier-review-stage').is_visible()
   assert not p.locator('.atelier-review-path').is_visible()
   p.locator('.atelier-review-details').click();assert p.locator('.atelier-review-path').is_visible()
   p.locator('.atelier-review-details').click()
  elif mode=='hidden':assert p.locator('#atelier-review-header').count()==0
  else:assert p.locator('.atelier-review-stage').is_visible() and p.locator('.atelier-review-path').is_visible()
  assert p.evaluate('document.scrollingElement.scrollHeight<=innerHeight+1')
  p.close();ok('review context '+mode+' preserves markup and no short-card scroll')
 # Preserve the actual native overview click handlers while correcting its known container.
 overview='<html><head><style>html,body{background:#f7efd8;font:18px Arial;margin:0}.stats-container{background:#495233!important;color:#f0efd7;padding:25px}.stats-row{display:flex;justify-content:space-between;padding:14px}.overview-center-container{max-width:650px;margin:70px auto}.new-count-bubble{background:#62a4dd}.learn-count-bubble{background:#d9656d}.review-count-bubble{background:#6dd892}</style><style>'+review.theme_tokens('obsidian')+'</style><style>'+asset('reviewer.css')+'</style><script>document.documentElement.dataset.atelierScreen="overview";window.commands=[]</script></head><body><div class="overview-center-container"><h3 class="overview-title">A clear study overview</h3><div class="overview-container"><div class="stats-container"><div class="stats-row"><span>New</span><span class="new-count-bubble">162</span></div><div class="stats-row"><span>Learning</span><span class="learn-count-bubble">0</span></div><div class="stats-row"><span>Review</span><span class="review-count-bubble">0</span></div></div><button id="study" onclick="commands.push(\'study\')">Study Now</button></div></div></body></html>'
 p=page(overview,900,650)
 assert p.locator('.stats-container').evaluate('e=>getComputedStyle(e).backgroundColor')!='rgb(73, 82, 51)'
 p.locator('#study').click();assert p.evaluate('commands')==['study']
 p.close();ok('known Onigiri overview panel uses Atelier palette; original study handler survives')
 # Width regressions for launcher and compact title.
 for width in [390,650,1650]:
  p=page(home071('onigiri',mixed=True),width,800)
  box=p.locator('.companion-dock').bounding_box();assert box['x']>=0 and box['x']+box['width']<=width+.5
  p.close();ok(f'companion launcher stays in viewport at {width}px')
 assert not errors,errors
 b.close()
(OUT/'boundary-verification.json').write_text(json.dumps({'checks':checks,'count':len(checks),'errors':errors},indent=2))
print('TOTAL',len(checks),'PASS')

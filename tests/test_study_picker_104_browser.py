"""Study picker ordering/alignment against the shipped frontend and sample data.

Browser fixture only. Native Anki supplies card creation IDs at runtime.
"""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
from test_ui_audit_browser import sort_doc
from fixtures import ROOT

OUT=ROOT/'verification/study-picker-104';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/study-picker-104';SH.mkdir(parents=True,exist_ok=True)

def run():
    checks=[];errors=[]
    def check(name,value):
        assert value,name
        checks.append(name)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        for width,height in [(1114,600),(390,700)]:
            page=browser.new_page(viewport={'width':width,'height':height})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content(sort_doc())
            page.locator('.world-window').wait_for()
            page.locator('[data-action="studies"]').first.evaluate('(e)=>e.click()')
            page.locator('.dialog [data-action="new-study"]').click()
            picker=page.locator('#deck-picker')
            order=picker.locator('[data-pick-deck]').evaluate_all('xs=>xs.map(x=>x.dataset.pickDeck)')
            check(f'{width} recent card deck and parent lead picker',order[:2]==['90','92'])
            check(f'{width} recent observed subfolders follow before old decks',order.index('992')<order.index('991')<order.index('91'))
            field=page.locator('#picker-search');field.focus()
            geometry=field.evaluate('''e=>{const a=e.closest('.picker-search'),b=e.closest('form').querySelector('.deck-picker'),r=a.getBoundingClientRect(),s=b.getBoundingClientRect(),cs=getComputedStyle(a),ci=getComputedStyle(e);return {aligned:Math.abs(r.left-s.left)<2&&Math.abs(r.right-s.right)<2,outer:cs.outlineWidth,inner:ci.outlineStyle,overflow:r.right>innerWidth}}''')
            check(f'{width} one aligned search focus ring',geometry['aligned'] and geometry['outer']=='2px' and geometry['inner']=='none' and not geometry['overflow'])
            field.fill('Topic')
            check(f'{width} search retains recency order',picker.locator('[data-pick-deck]').evaluate_all('xs=>xs.map(x=>x.dataset.pickDeck)')==['992','991'])
            field.fill('')
            page.locator('[data-pick-deck="90"]').check()
            page.locator('[data-pick-deck="92"]').check()
            check(f'{width} overlapping parent and child count once','1 parent folder / deck' in page.locator('#picker-summary').inner_text())
            page.screenshot(path=str(SH/f'study-picker-{width}.png'),animations='disabled')
            page.close()
        browser.close()
    check('No uncaught browser errors',not errors)
    (OUT/'results.json').write_text(json.dumps({'category':'Chromium fixture, not native Anki','checks':checks,'count':len(checks),'errors':errors},indent=2)+'\n')
    print('CHECKS',len(checks))

if __name__=='__main__':run()

"""Full shipped home/reviewer screens; synthetic browser data, no native claim."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite,core
from fixtures import card
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/playwright/final-matrix';OUT.mkdir(parents=True,exist_ok=True)
records=[];errors=[];fingerprint=runtime_digest()
def shot(p,theme,screen,w,h):
    p.wait_for_timeout(120)
    file=OUT/f'{theme}-{screen}-{w}x{h}.png';p.screenshot(path=str(file),animations='disabled',timeout=60000)
    overflow=p.evaluate('''()=>{const root=document.getElementById('atelier-root')?.shadowRoot;const s=root?.querySelector('.main')||document.scrollingElement;return s.scrollWidth>s.clientWidth+2}''')
    records.append({'file':file.name,'world':theme,'screen':screen,'viewport':[w,h],'horizontal_overflow':overflow,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
def save():
    (OUT/'results.json').write_text(json.dumps({'category':'real shipped frontend, fictional browser fixtures','runtime_sha256':fingerprint,'records':records,'errors':errors,'complete':len(records)==len(core.THEMES)*5*6},indent=2)+'\n')
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=__import__('os').environ.get('ATELIER_TEST_BROWSER'))
    try:
        for theme in core.THEMES:
            for w,h in [(1440,900),(1280,720),(1024,768),(800,600),(390,720)]:
                p=browser.new_page(viewport={'width':w,'height':h});p.set_default_timeout(10000);p.on('pageerror',lambda e:errors.append(str(e)))
                for screen,page in [('home','desk'),('library','library'),('widgets','widgets'),('tools','tools')]:
                    p.set_content(home_suite(theme,page=page));p.locator('.main').wait_for();shot(p,theme,screen,w,h)
                # Follow Anki's actual question -> answer lifecycle in one
                # document. page.set_content() preserves Window properties, so
                # rebuilding the answer document would leave the frozen
                # reviewer controller bound to the discarded question DOM.
                p.set_content(card(theme,'basic'))
                shot(p,theme,'question',w,h)
                p.evaluate("""() => {
                    document.getElementById('answer').hidden=false;
                    document.getElementById('answer-copy').hidden=false;
                    const info={...window.__atelierReviewCard,stage:'answer'};
                    window.__atelierReviewCard=info;
                    AtelierReview.painted(info);
                    AtelierReview.settled(info);
                }""")
                shot(p,theme,'answer',w,h)
                p.close();save()
            print('Captured',theme,flush=True)
        assert runtime_digest()==fingerprint,'Source changed during capture'
        for width,height in [(1440,900),(1280,720),(1024,768),(800,600),(390,720)]:
            answer_hashes={r['sha256'] for r in records if r['screen']=='answer' and r['viewport']==[width,height]}
            assert len(answer_hashes)==len(core.THEMES),f'Answer evidence is not world-distinct at {width}x{height}'
    finally:save();browser.close()

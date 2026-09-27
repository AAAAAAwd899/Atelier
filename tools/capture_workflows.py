"""Additional workflow matrix using existing real dispatchers and synthetic stores."""
from pathlib import Path
import sys,json,hashlib,os
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from release_tools import runtime_digest
from artwork_fixture import install_artwork_route,with_artwork_base,wait_for_world_art
from playwright.sync_api import sync_playwright
component=sys.argv[1];OUT=ROOT/'output/playwright'/('final-'+component);OUT.mkdir(parents=True,exist_ok=True)
records=[];errors=[];fingerprint=runtime_digest()
def shots(p,theme,screen):
    for w,h in [(1440,900),(1280,720),(1024,768),(800,600),(390,720)]:
        p.set_viewport_size({'width':w,'height':h});p.wait_for_timeout(180)
        file=OUT/f'{theme}-{screen}-{w}x{h}.png';p.screenshot(path=str(file),animations='disabled',timeout=60000)
        records.append({'file':file.name,'world':theme,'screen':screen,'viewport':[w,h],'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'page_overflow':p.evaluate('document.documentElement.scrollWidth>innerWidth+2')})
    p.set_viewport_size({'width':1440,'height':900})
def save():
    (OUT/'results.json').write_text(json.dumps({'category':'shipped frontend; synthetic fixtures and native API doubles','runtime_sha256':fingerprint,'records':records,'errors':errors},indent=2)+'\n')
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
    try:
        if component=='home-workflows':
            from suite_fixtures import home_suite,core
            for theme in core.THEMES:
                p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)))
                install_artwork_route(p)
                p.set_content(with_artwork_base(home_suite(theme,page='library')));p.locator('.main').wait_for();wait_for_world_art(p,theme)
                for view in ['grid','list']:
                    p.locator(f'[data-action="view"][data-view="{view}"]').click();shots(p,theme,'library-'+view)
                p.locator('.nav-row[data-action="study-progress"]').click();p.locator('#progress-results .progress-summary').wait_for(state='attached',timeout=10000);shots(p,theme,'progress')
                p.close();save();print(theme,flush=True)
        elif component=='planner':
            import test_session_slice_browser as fixture
            for theme in fixture.core.THEMES:
                p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)));fixture.expose(p)
                install_artwork_route(p)
                for screen,view in [('exam-setup','new'),('practice-builder','practice'),('pip','pip'),('results','overview')]:
                    p.set_content(with_artwork_base(fixture.html(theme)));p.locator('.es-hero').wait_for();wait_for_world_art(p,theme)
                    if screen=='results':fixture.show(p,fixture.result(12))
                    else:p.evaluate('(view)=>ExamSprout.event("suite-navigate",{view})',view)
                    p.wait_for_timeout(250);shots(p,theme,screen)
                p.close();save();print(theme,flush=True)
        elif component=='card':
            from card_studio_harness import UnifiedHost
            from tests.authoring_fixtures import enable_native_io
            from reportlab.pdfgen.canvas import Canvas
            import fitz
            h=UnifiedHost();enable_native_io(h.col)
            pdf=OUT/'qa-source.pdf';c=Canvas(str(pdf),pagesize=(900,540));c.setFont('Helvetica',24);c.drawString(55,450,'Synthetic source: learning design');c.setFont('Helvetica',18)
            for y,line in [(350,'Identify one clear target'),(260,'Distinguish close alternatives'),(170,'Explain the reason')]:c.rect(45,y-15,780,55);c.drawString(65,y,line)
            c.save()
            with fitz.open(pdf) as doc:data=doc[0].get_pixmap().tobytes('png')
            blob=h.store.save_blob(data,'png');source=h.store.add_source(h.primary_project,'Learning design · synthetic source','png',[{'image':blob,'text':''}])['source']
            for world in h.appearance_module.CATALOG:
                theme=world['id'];h.settings['theme']=theme
                p=b.new_page(viewport={'width':1440,'height':900});p.on('pageerror',lambda e:errors.append(str(e)));p.expose_function('nativeBridge',h.dispatch)
                install_artwork_route(p)
                p.set_content(with_artwork_base(h.html()));p.locator('.shelf-grid').wait_for();wait_for_world_art(p,theme);p.locator(f'[data-action="open-project"][data-id="{h.primary_project}"]').first.click();p.locator(f'[data-action="open-source"][data-id="{source["id"]}"]').first.click()
                p.locator('[data-draft="front"]').wait_for();shots(p,theme,'card-studio')
                p.locator('[data-action="mask-source"]:not([disabled])').click();p.locator('.mask-image-area img').wait_for();p.wait_for_function('document.querySelector(".mask-image-area img").naturalWidth>0')
                p.locator('[data-mask-action="same"]').click();area=p.locator('.mask-image-area').bounding_box()
                p.mouse.move(area['x']+area['width']*.07,area['y']+area['height']*.27);p.mouse.down();p.mouse.move(area['x']+area['width']*.46,area['y']+area['height']*.35,steps=8);p.mouse.up();p.locator('.mask-rect:not([data-mask-id="temporary"])').first.wait_for();shots(p,theme,'mask-studio')
                p.close();save();print(theme,flush=True)
        else:raise ValueError(component)
        assert runtime_digest()==fingerprint,'Runtime changed during captures'
    finally:save();b.close()

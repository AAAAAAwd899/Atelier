"""Actual packaged UI clicks; explicit bridge, not a native scheduler test."""
from test_native_widgets_browser import native_fixture
from suite_fixtures import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification'/'1.0.2';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots'/'1.0.2';SH.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]

def check(name,ok):
    assert ok,name
    checks.append(name)

def setup(theme):
    soup=BeautifulSoup(native_fixture(theme,live=True,page='desk'),'html.parser')
    script=soup.new_tag('script');script.string='''
      window.folderCalls=[];window.holdFolder=false;window.folderError='';window.pendingFolder=[];
      const prior=window.pycmd;
      window.pycmd=(msg)=>{
        if(!msg.startsWith('atelier:v1:preview:'))return prior(msg);
        const req=JSON.parse(msg.slice('atelier:v1:preview:'.length));
        if(req.action!=='study_folder')return prior(msg);
        folderCalls.push(req);
        const reply={token:'preview',id:req.id,result:true,error:folderError};
        if(holdFolder)pendingFolder.push(reply);else setTimeout(()=>AtelierMakeover.receive(reply),10);
      };
    '''
    # pycmd was defined in head; insert wrapper immediately afterwards, before UI startup.
    soup.head.append(script)
    return str(soup)

with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for theme in core.THEMES:
        p=b.new_page(viewport={'width':1440,'height':920});p.set_default_timeout(6000);p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(setup(theme));p.locator('.layout[data-page="desk"]').wait_for()
        link=p.locator('[data-action="study"][data-id="22"]').first
        link.click();p.locator('#folder-study-order').wait_for()
        check(theme+' shuffle is the default',p.locator('#folder-study-order').input_value()=='shuffle')
        check(theme+' opening does not mutate collection',len(p.evaluate('folderCalls'))==0)
        p.locator('.folder-order-details summary').click()
        check(theme+' persistent option change is disclosed', 'saves this parent folder' in p.locator('.folder-order-details').inner_text())
        check(theme+' explanation available', 'syncs with Anki' in p.locator('.folder-order-details').inner_text())
        if theme in ['forest','rose','glacier','ember']:
            p.screenshot(path=str(SH/f'{theme}-folder-shuffle.png'),animations='disabled')
        p.locator('.dialog [data-action="study"][data-confirmed="true"]').click()
        p.wait_for_function('folderCalls.length===1')
        check(theme+' sends original parent ID and path',p.evaluate('folderCalls[0].data')=={'id':'22','expected':'Pharmacy School::Section 5::Advanced Cardiology::Exam 3','order':'shuffle'})
        p.locator('.dialog').wait_for(state='hidden')
        link.click();p.locator('#folder-study-order').select_option('current')
        p.locator('.dialog [data-action="study"][data-confirmed="true"]').click();p.wait_for_function('folderCalls.length===2')
        check(theme+' native-order option reaches same scope',p.evaluate('folderCalls[1].data.order')=='current')
        p.close()
    for width,height in [(320,540),(390,700),(620,600),(940,700),(1440,900)]:
        p=b.new_page(viewport={'width':width,'height':height});p.set_default_timeout(6000);p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(setup('rose'));p.locator('[data-action="study"][data-id="22"]').first.click()
        p.locator('.folder-order-details summary').click()
        check(str(width)+' dialog contained',p.locator('.dialog').evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1}'))
        check(str(width)+' primary button can be hit',p.locator('.dialog-footer [data-action="study"]').evaluate('e=>{const r=e.getBoundingClientRect();return e.contains(e.getRootNode().elementFromPoint(r.x+r.width/2,r.y+r.height/2))}'))
        p.locator('.dialog-body').hover();p.mouse.wheel(0,600);p.wait_for_timeout(150)
        check(str(width)+' footer stays available after scrolling',p.locator('.dialog-footer [data-action="study"]').is_visible())
        p.keyboard.press('Escape');check(str(width)+' cancel emits no study command',not p.evaluate('folderCalls'))
        p.close()
    p=b.new_page(viewport={'width':1100,'height':760});p.set_default_timeout(6000);p.on('pageerror',lambda e:errors.append(str(e)))
    p.set_content(setup('glacier'));p.locator('[data-action="study"][data-id="22"]').first.click()
    p.evaluate("folderError='Anki could not save the shuffled order. Please retry.'")
    p.locator('.dialog-footer [data-action="study"]').click();p.locator('#folder-study-error').get_by_text('Anki could not',exact=False).wait_for()
    check('failed write keeps selection and dialog',p.locator('#folder-study-order').input_value()=='shuffle' and p.locator('.dialog').is_visible())
    p.evaluate("folderError='';holdFolder=true")
    p.locator('.dialog-footer [data-action="study"]').click();p.wait_for_function('pendingFolder.length===1')
    check('pending request blocks duplicate clicks',p.locator('.dialog-footer [data-action="study"]').is_disabled() and p.evaluate('folderCalls.length')==2)
    p.evaluate('AtelierMakeover.receive(pendingFolder.shift())');p.locator('.dialog').wait_for(state='hidden')
    check('successful retry completes',len(p.evaluate('folderCalls'))==2)
    # Existing leaf command remains individual/native, no folder settings route.
    p.locator('[data-action="study-now"]').first.click();p.wait_for_timeout(80)
    check('individual lecture route unchanged',any(x['action']=='study_now' for x in p.evaluate('widgetCalls')) and len(p.evaluate('folderCalls'))==2)
    p.close()
    check('no page errors',not errors);b.close()
(OUT/'browser-results.json').write_text(json.dumps({'count':len(checks),'checks':checks,'errors':errors,'native_scheduler':False},indent=2)+'\n')
print('PASS',len(checks))

"""Shipped destination browser; synthetic collection, no native scheduler claim."""
from test_ui_audit_browser import sort_doc
from fixtures import ROOT, core
from suite_fixtures import home_suite,worlds
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os,json

OUT=ROOT/'verification/folder-move-108';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/folder-move-108';SH.mkdir(parents=True,exist_ok=True)

def document(theme=None):
    soup=BeautifulSoup(sort_doc(),'html.parser');tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
    boot['demo']['nodes'] += [
        {'id':'200','name':'Second course','path':'Second course','parent':'0','children':['201'],'depth':0,'review':0,'learn':0,'new':0,'filtered':False},
        {'id':'201','name':'Seminar','path':'Second course::Seminar','parent':'200','children':[],'depth':1,'review':0,'learn':0,'new':0,'filtered':False},
        {'id':'300','name':'Filtered practice','path':'Filtered practice','parent':'0','children':[],'depth':0,'review':0,'learn':0,'new':0,'filtered':True}]
    if theme:
        themed=BeautifulSoup(home_suite(theme,page='library'),'html.parser');t=themed.find(id='atelier-bootstrap');b=json.loads(t.string);b['demo']['nodes']=boot['demo']['nodes'];b['profile']=boot['profile'];b['demo']['profile']=boot['demo']['profile'];t.string=core.json_for_html(b);return str(themed)
    tag.string=core.json_for_html(boot);return str(soup)

def run():
    checks=[];errors=[]
    def check(name,value):
        assert value,name
        checks.append(name);print('PASS',name,flush=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ['ATELIER_TEST_BROWSER'],args=['--no-sandbox'])
        for width,height in [(1440,900),(1024,600),(390,720)]:
            p=browser.new_page(viewport={'width':width,'height':height});p.set_default_timeout(9000);p.on('pageerror',lambda e:errors.append(str(e)))
            p.set_content(document());p.locator('.unified-topbar').wait_for()
            if width<820:p.locator('[data-action=mobile]').click()
            p.locator('[data-page=library]').first.click()
            # Real context menu event, with the branch expanded through its parent.
            p.locator('[data-action=navigate][data-id="90"]').first.evaluate('(e)=>e.click()')
            p.locator('.library [data-node="99"]').scroll_into_view_if_needed();p.wait_for_timeout(150);p.locator('.library [data-node="99"]').click(button='right')
            p.locator('.context-menu [data-action=move]').click()
            search=p.locator('#move-search');submit=p.locator('[form=organize-form]')
            check(f'{width} current parent selected and no-op blocked',submit.is_disabled() and 'Already here' in p.locator('#move-feedback').inner_text())
            search.fill('Topic');search.press('Enter')
            check(f'{width} Enter in search never submits a move',p.locator('.dialog').count()==1 and submit.is_disabled())
            check(f'{width} source descendants excluded even in search',p.locator('.move-folder').count()==0)
            search.fill('Filtered')
            check(f'{width} filtered destinations excluded',p.locator('.move-folder').count()==0)
            search.fill('Second course')
            p.locator('.move-folder[data-id="200"]').click()
            check(f'{width} same-name collision blocked with explanation',submit.is_disabled() and 'already there' in p.locator('#move-feedback').inner_text())
            p.locator('.move-crumbs [data-id="0"]').click()
            check(f'{width} root move-out enabled and exact path preview',submit.is_enabled() and p.locator('#path-preview').inner_text()=='TO · All folders › Seminar')
            check(f'{width} original path stays visible','Course › Seminar' in p.locator('.move-from').inner_text())
            search.fill('Lecture 2');search.press('Tab');p.locator('.move-folder[data-id="92"]').focus();p.keyboard.press('Enter')
            check(f'{width} keyboard can choose a normal leaf deck',submit.is_enabled() and 'Course › Lecture 2 › Seminar' in p.locator('#path-preview').inner_text())
            check(f'{width} breadcrumb has stable keyboard focus',p.evaluate("document.querySelector('#atelier-root').shadowRoot.activeElement?.getAttribute('aria-current')")=='location')
            p.screenshot(path=str(SH/f'move-preview-{width}.png'),animations='disabled')
            geometry=p.locator('.dialog').evaluate('e=>({width:e.scrollWidth,client:e.clientWidth})')
            check(f'{width} dialog has no horizontal overflow',geometry['width']<=geometry['client']+1)
            p.get_by_role('button',name='Cancel',exact=True).click()
            check(f'{width} cancellation leaves branch in place',p.locator('[data-node="99"]').count()>0)
            p.locator('.library [data-node="99"]').scroll_into_view_if_needed();p.wait_for_timeout(150);p.locator('.library [data-node="99"]').click(button='right');p.locator('.context-menu [data-action=move]').click()
            p.locator('.move-crumbs [data-id="0"]').click();p.locator('[form=organize-form]').click()
            p.locator('.dialog').wait_for(state='detached')
            check(f'{width} confirmation opens destination with moved branch',p.locator('.library [data-node="99"]').count()>0)
            p.close()
        for world in worlds.CATALOG:
            p=browser.new_page(viewport={'width':1280,'height':720});p.on('pageerror',lambda e:errors.append(str(e)))
            p.set_content(document(world['id']));p.locator('.unified-topbar').wait_for()
            p.locator('.library [data-action=organize][data-id="90"]').click();p.locator('.menu-actions [data-action=move]').click()
            check(world['id']+' move picker keeps theme and readable content',p.locator('#move-search').is_visible() and p.locator('.dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
            if world['id']=='rose':p.screenshot(path=str(SH/'move-light-world.png'),animations='disabled')
            p.close()
        browser.close()
    check('No uncaught browser errors',not errors)
    (OUT/'results.json').write_text(json.dumps({'category':'Chromium synthetic collection','count':len(checks),'checks':checks,'errors':errors},indent=2)+'\n')
    print('CHECKS',len(checks))

if __name__=='__main__':run()

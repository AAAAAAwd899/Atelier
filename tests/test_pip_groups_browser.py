from planner_suite_fixture import *
from playwright.sync_api import sync_playwright
OUT=ROOT/'verification/pip-groups';OUT.mkdir(parents=True,exist_ok=True)
SH=ROOT/'screenshots/release-finish';SH.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];launches=[];original_command=original.command

def command(a,data):
 if a=='suite_groups':return [{'id':'active-course','name':'Active class · exact folders','deck_ids':['11'],'available':True},{'id':'missing','name':'Missing lecture','available':False}]
 if a=='pip_study':launches.append(data);return {'started':True,'questions':data['size']}
 return original_command(a,data)
original.command=command

def check(name,v):
 assert v,name
 checks.append(name);print('PASS',name,flush=True)

def run():
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=b.new_page(viewport={'width':1440,'height':980});p.set_default_timeout(30000);p.on('pageerror',lambda e:errors.append(str(e)));expose(p)
  try:
   p.set_content(html('forest'));p.locator('.es-hero').wait_for();p.locator('[data-action="pip-study"]').first.click();p.locator('#suite-pip-material').wait_for()
   check('Active groups before saved plans',p.locator('#suite-pip-material optgroup').first.get_attribute('label')=='Active study groups')
   check('Missing groups remain disabled',p.locator('#suite-pip-material option[value="group:missing"]').evaluate('e=>e.disabled&&e.matches(":disabled")'))
   p.locator('#suite-pip-material').select_option('group:active-course');p.locator('#es-teach-new').uncheck();p.locator('#es-pip-count').fill('20')
   check('Rehearsal effect explicitly described','Rehearsal only' in p.locator('#suite-pip-mode').inner_text())
   p.screenshot(path=str(SH/'pip-groups.png'));p.locator('[data-action="begin-pip-study"]').click();p.wait_for_timeout(100)
   check('Exact group, size, explicit non-learning dispatch',launches==[{'group_id':'active-course','size':20,'teach_new':False}])
   for width in (390,620):
    p.set_viewport_size({'width':width,'height':740});p.evaluate('ExamSprout.event("suite-navigate",{view:"pip"})');p.locator('#suite-pip-material').wait_for()
    check(str(width)+' material selector contained',p.locator('#suite-pip-material').evaluate('e=>{let r=e.getBoundingClientRect();return r.x>=0&&r.right<=innerWidth}'))
    p.keyboard.press('Escape')
   check('No unrequested saved exam record',not any(a=='save_exam' for a,d in CALLS))
   check('No uncaught page error',not errors)
  finally:
   (OUT/'results.json').write_text(json.dumps({'count':len(checks),'cases':checks,'errors':errors,'native_windows':False},indent=2));b.close()
if __name__=='__main__':run()

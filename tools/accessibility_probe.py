"""Scoped axe checks of the owned home UI; browser fixtures, not certification."""
from pathlib import Path
import sys,os,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite
from release_tools import runtime_digest
from playwright.sync_api import sync_playwright
OUT=ROOT/'output/accessibility';OUT.mkdir(parents=True,exist_ok=True)
rows=[]
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get('ATELIER_TEST_BROWSER'))
    for world in ['midnight','rose','forest']:
        for screen in ['desk','widgets','tools']:
            p=b.new_page(viewport={'width':1280,'height':720});p.set_content(home_suite(world,page=screen));p.locator('.main').wait_for();p.wait_for_timeout(300)
            p.add_script_tag(path=str(ROOT/'output/qa-node/node_modules/axe-core/axe.min.js'))
            result=p.evaluate('''async()=>{const r=await axe.run({include:[['#atelier-root']]},{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return {version:r.testEngine.version,violations:r.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,help:v.helpUrl,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.length})),passes:r.passes.length}}''')
            rows.append({'world':world,'screen':screen,**result});p.close();print(world,screen,len(result['violations']),flush=True)
            (OUT/'results.json').write_text(json.dumps({'runtime_sha256':runtime_digest(),'category':'axe browser scan restricted to Atelier-owned shadow host, fictional data; manual checks remain separate','rows':rows},indent=2)+'\n')
    b.close()

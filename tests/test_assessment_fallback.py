"""Run original assessment UI scenarios with the merged presentation.
The ONLY renderer requirement change is explicit fallback acceptance because the
container has no WebGL2. This does not validate live GPU geometry/animation.
"""
from planner_suite_fixture import *
import inspect, hashlib
assessment.OUT=ROOT/'verification/assessment-fallback';assessment.OUT.mkdir(exist_ok=True)
assessment.CHECKS.clear();assessment.ERRORS.clear()
source=inspect.getsource(assessment.run)
needle='page.locator(\'.pip-card[data-pip-renderer="webgl2"]\').wait_for()'
assert needle in source
source=source.replace('page.route(\'**/*\',u.route)','page.route(\'**/*\',suite_route)').replace('page.set_content(u.html())','page.set_content(suite_html())')
source=source.replace(needle, "page.locator('.pip-card').wait_for();page.wait_for_timeout(600);check('Pip fallback artwork available without WebGL2',page.locator('.pip-card').is_visible() and page.locator('.pip-card img').count()>0)")
source=source.replace("'bridge':'synthetic; actual assessment, storage and WebGL code exercised'", "'bridge':'synthetic; actual assessment and storage; live WebGL unavailable, animated fallback tested'")
ns=assessment.__dict__;ns['suite_html']=html;ns['suite_route']=route
exec(compile(source,'merged_assessment_fallback','exec'),ns)
if __name__=='__main__':
    assessment.run()
    out=assessment.OUT/'ui-results.json';data=json.loads(out.read_text());data['renderer']='animated fallback; live GPU unverified';data['original_suite_sha256']=hashlib.sha256((ROOT/'vendor_tests/tools/test_ui_0100.py').read_bytes()).hexdigest();out.write_text(json.dumps(data,indent=2))

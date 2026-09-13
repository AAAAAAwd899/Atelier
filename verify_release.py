"""Full current-runtime verification. No production profile, network provider or publication.
All engine code executes from src/test-only copies; native Anki/Qt is explicit doubles.
"""
from __future__ import annotations
from pathlib import Path
import datetime,json,subprocess,sys,xml.etree.ElementTree as ET,shutil
from concurrent.futures import ThreadPoolExecutor,as_completed
from release_tools import *
V=ROOT/'verification';V.mkdir(exist_ok=True);DIST.mkdir(exist_ok=True)
def setup_vendor():
 for component,target in [('sprout','vendor_tests/addon'),('workshop','workshop_checks/addon')]:
  dest=ROOT/target
  if dest.is_symlink():dest.unlink()
  elif dest.exists():shutil.rmtree(dest)
  shutil.copytree(SRC/component,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
def run(cmd,name,cwd=ROOT,timeout=700):
 with (V/(name+'.log')).open('w') as stream:
  result=subprocess.run(cmd,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
 (V/(name+'.exit')).write_text(str(result.returncode))
 if result.returncode:raise RuntimeError(name+' failed; see verification log')
def cases(path):
 records=list(ET.parse(path).getroot().iter('testcase'))
 if any(r.find('error') is not None or r.find('failure') is not None or r.find('skipped') is not None for r in records):raise RuntimeError('Failed/skipped unit tests '+str(path))
 return len(records)
def main():
 setup_vendor();fingerprint=runtime_digest()
 for p in sorted(SRC.rglob('*.js')):subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
 root_tests=['test_core.py','test_sprout_link.py','test_release.py','test_071.py','test_readiness.py','test_suite.py','test_ui_model_audit.py','test_studio_polish.py','test_home_slice_model.py','test_session_slice.py','test_world_finish.py','test_complete_integration.py','test_usability_contract.py','test_release_finish.py','test_native_widgets.py','test_widget_routing.py','test_release_one.py','test_101.py','test_102.py']
 run([sys.executable,'-m','pytest',*[f'tests/{n}' for n in root_tests],'-q','--junitxml=verification/atelier-unit.xml'],'atelier-unit')
 run([sys.executable,'-m','pytest','tests','-q','--junitxml='+str(V/'sprout-unit.xml')],'sprout-unit',ROOT/'vendor_tests')
 run([sys.executable,'-m','pytest','tests','-q','--junitxml='+str(V/'workshop-unit.xml')],'workshop-unit',ROOT/'workshop_checks')
 suites=[('tests/test_102_browser.py','folder-shuffle',V/'1.0.2/browser-results.json',ROOT),('tests/test_101_browser.py','review-101',V/'1.0.1/browser-results.json',ROOT),('tests/test_release_one_card_browser.py','release-one-card',V/'release-one-card/results.json',ROOT),
 ('tests/test_release_one_browser.py','release-one',V/'release-one/results.json',ROOT),
 ('tests/test_widget_routing_browser.py','widget-routing',V/'widget-routing/results.json',ROOT),
 ('tests/test_native_widgets_browser.py','native-widgets',V/'native-widgets/results.json',ROOT),
 ('tests/test_browser_release.py','atelier-browser',DIST/'browser-verification.json',ROOT),
 ('tests/test_boundary_browser.py','boundary-browser',DIST/'boundary-verification.json',ROOT),
 ('tests/test_assessment_fallback.py','assessment-fallback',V/'assessment-fallback/ui-results.json',ROOT),
 ('tests/test_world_suite_browser.py','world-suite',V/'world-suite/results.json',ROOT),
 ('tests/test_ui_audit_browser.py','ui-audit',V/'ui-audit/results.json',ROOT),
 ('tests/test_studio_polish_browser.py','studio-polish',V/'studio-polish/results.json',ROOT),
 ('tests/test_home_slice_browser.py','home-polish',V/'home-polish/results.json',ROOT),
 ('tests/test_session_slice_browser.py','session-polish',V/'session-polish/results.json',ROOT),
 ('tests/test_world_finish_browser.py','world-finish',V/'world-finish/results.json',ROOT),
 ('tests/test_quiet_keys_browser.py','quiet-keys',V/'quiet-keys/results.json',ROOT),
 ('tests/test_complete_browser.py','complete-browser',V/'complete-browser/results.json',ROOT),
 ('tests/test_complete_home_browser.py','complete-home',V/'complete-home/results.json',ROOT),
 ('tests/test_plan_handoff_browser.py','plan-handoff',V/'plan-handoff/results.json',ROOT),
 ('tests/test_usability_browser.py','usability-audit',V/'usability-audit/results.json',ROOT),
 ('tests/test_release_finish_browser.py','release-finish',V/'release-finish/results.json',ROOT),
 ('tests/test_pip_groups_browser.py','pip-groups',V/'pip-groups/results.json',ROOT),
 ('tools/test_ui.py','card-studio',ROOT/'workshop_checks/docs/browser-results.json',ROOT/'workshop_checks'),
 ('tools/test_advanced_ui.py','card-advanced',ROOT/'workshop_checks/docs/advanced-browser-results.json',ROOT/'workshop_checks'),
 ('tools/test_first_run.py','card-first-run',ROOT/'workshop_checks/docs/first-run-results.json',ROOT/'workshop_checks'),
 ('tools/test_mask_ui.py','mask-studio',ROOT/'workshop_checks/docs/authoring-110/results.json',ROOT/'workshop_checks')]
 outcomes={}
 def browser_job(job):
  script,name,path,cwd=job;run([sys.executable,script],name,cwd)
  result=json.loads(path.read_text());count=result.get('count',result.get('checks'))
  if not isinstance(count,int) or count<1 or result.get('errors'):raise RuntimeError('Browser evidence invalid '+name)
  (V/(name+'-results.json')).write_text(json.dumps(result,indent=2)+'\n');return name,count
 with ThreadPoolExecutor(max_workers=2) as pool:
  for future in as_completed([pool.submit(browser_job,j) for j in suites]):
   name,count=future.result();outcomes[name]=count;print('PASS',name,count,flush=True)
 if runtime_digest()!=fingerprint:raise RuntimeError('Runtime changed during verification; rerun')
 report={'version':version(),'runtime_sha256':fingerprint,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'python_suites':{'suite_integration_and_preservation':cases(V/'atelier-unit.xml'),'exam_engine_and_quiet_review':cases(V/'sprout-unit.xml'),'card_studio_importers_publishers_and_routes':cases(V/'workshop-unit.xml')},
 'python_failed':0,'python_skipped':0,'browser_suites':outcomes,'browser_errors':0,'native_windows_verified':False,'native_qt_verified':False,'live_webgl_verified':False,
 'pip_browser_renderer':'shipped animated fallback; no live GPU claim','phase':'1.0.2 native whole-folder display-order patch; no native scheduler execution or hardware acceptance claimed', 'acceptance':json.loads((ROOT/'RELEASE-ACCEPTANCE.json').read_text())}
 report['python_total']=sum(report['python_suites'].values());report['browser_total']=sum(outcomes.values())
 (V/'verified.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()

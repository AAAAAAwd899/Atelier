"""Fail-closed exact-installer test execution and byte-for-byte packaging receipt."""
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,zipfile,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from addon.core import VERSION,PACKAGE
from build import include,source_archive

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,cwd,log):
 with log.open('w') as f:
  r=subprocess.run(command,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 if r.returncode:raise RuntimeError(f'Verification failed ({r.returncode}): {command}. Details: {log}')
 print('PASS',' '.join(map(str,command)),flush=True)
def verify(out,atelier):
 out.mkdir(parents=True,exist_ok=True);receipt=out/'Package_Verification.json';receipt.unlink(missing_ok=True)
 installer=out/f'Workshop_{VERSION}.ankiaddon'
 if not installer.is_file():raise FileNotFoundError(installer)
 work=Path(tempfile.mkdtemp(prefix='workshop-exact-release-'));release=work/'Workshop';ad=release/'addon';ad.mkdir(parents=True)
 integrity=[]
 with zipfile.ZipFile(installer) as z:
  assert z.testzip() is None;assert len(set(z.namelist()))==len(z.namelist())
  for name in z.namelist():
   parts=Path(name).parts
   assert not Path(name).is_absolute() and '..' not in parts and '\\' not in name
   assert not any(x in parts for x in ('__pycache__','tests','tools','.git'))
   assert Path(name).suffix.lower() not in ('.pyc','.pyo','.ttf','.otf','.woff','.woff2','.sqlite3','.db','.sqlite')
  z.extractall(ad)
  assert json.loads(z.read('manifest.json'))['package']==PACKAGE
  assert json.loads(z.read('manifest.json'))['human_version']==VERSION
  for p in sorted((ROOT/'addon').rglob('*')):
   if include(p):
    name=p.relative_to(ROOT/'addon').as_posix();assert z.read(name)==p.read_bytes(),name
    integrity.append({'path':name,'sha256':sha(p),'bytes':p.stat().st_size})
 for name in ('__init__.py','core.py','storage.py','collection.py','documents.py','integration.py','network.py','preview.py','web/app.js','web/app.css','web/art.js','web/icons.js','web/home.js','vendor/pypdf/LICENSE'):assert (ad/name).is_file()
 for p in ad.rglob('*.py'):compile(p.read_bytes(),str(p),'exec')
 for p in (ad/'web').glob('*.js'):run(['node','--check',str(p)],release,out/('syntax-'+p.stem+'.log'))
 for folder in ('tests','tools'):
  shutil.copytree(ROOT/folder,release/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copy2(ROOT/'pytest.ini',release/'pytest.ini');(release/'docs').mkdir(exist_ok=True)
 run([sys.executable,'-m','pytest','-q','--junitxml=docs/unit-results.xml'],release,out/'Python_Tests.log')
 for script,log in [('test_ui.py','Interface_Tests.log'),('test_advanced_ui.py','Advanced_Workflow_Tests.log'),('test_first_run.py','First_Run_Tests.log'),('test_home.py','Atelier_Tests.log')]:
  cmd=[sys.executable,'tools/'+script]
  if script=='test_home.py':cmd.append(str(atelier))
  run(cmd,release,out/log)
 root=ET.parse(release/'docs/unit-results.xml').getroot();suites=root.findall('testsuite') if root.tag=='testsuites' else [root]
 totals={k:sum(int(x.get(k,0)) for x in suites) for k in ('tests','failures','errors','skipped')}
 assert not any(totals[k] for k in ('failures','errors','skipped')),totals
 browsers={}
 for name in ('browser-results.json','advanced-browser-results.json','first-run-results.json','home-results.json'):
  data=json.loads((release/'docs'/name).read_text());assert not data.get('page_errors'),name
  browsers[name]=data['count'];shutil.copy2(release/'docs'/name,ROOT/'docs'/name)
 shutil.copy2(release/'docs/unit-results.xml',ROOT/'docs/unit-results.xml')
 for p in (release/'docs/screenshots').glob('*.png'):
  target=ROOT/'docs/screenshots'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);shutil.copy2(p,out/p.name)
 # Fixture identity belongs only to test tools; installed runtime never seeds a library.
 assert not (ad/'tests').exists() and not (ad/'tools').exists()
 result={'product':'Workshop','version':VERSION,'package':PACKAGE,'created_utc':datetime.now(timezone.utc).isoformat(),
         'installer':installer.name,'bytes':installer.stat().st_size,'sha256':sha(installer),
         'python':totals,'browser_suites':browsers,'browser_total':sum(browsers.values()),'runtime_files':integrity,
         'test_boundary':'Exact installed runtime extracted into a clean test tree. Tests/tools are copied separately and never ship in the installer. Actual production UI and Python dispatcher run with real local SQLite; Anki/Qt are explicit doubles. Provider HTTP transport is mocked.',
         'native_anki_tested':False,'windows_tested':False,'external_provider_tested':False,
         'atelier_fixture_sha256':sha(atelier),'atelier_fixture_version':json.loads((release/'docs/home-results.json').read_text())['atelier_version'],
         'release_status':'Native-acceptance candidate; not published on AnkiWeb.'}
 receipt.write_text(json.dumps(result,indent=2));shutil.copy2(receipt,ROOT/'docs/Package_Verification.json')
 report=f'''# Workshop {VERSION} — verification of the exact installer

## Current results

| Check | Result |
|---|---:|
| Python logic, SQLite and native-contract tests | {totals['tests']} passed |
| Production interface/workflow browser checks | {browsers['browser-results.json']} passed |
| Advanced source/AI-consent/media/editing checks | {browsers['advanced-browser-results.json']} passed |
| Empty-library first-run checks | {browsers['first-run-results.json']} passed |
| Exact supplied Atelier front-end checks | {browsers['home-results.json']} passed |
| Total browser checks | {sum(browsers.values())} passed |
| Python failures / errors / skips | 0 / 0 / 0 |
| Browser uncaught exceptions | 0 |

Installer: `{installer.name}` ({installer.stat().st_size:,} bytes).
SHA-256: `{sha(installer)}`.

## What ran

These suites ran using a clean extraction of this exact installer. The test harness
loads the real production JavaScript/CSS/artwork and the real Python request
dispatcher, with a real local Workshop database and SQLite collection fixtures.
The installer contains no test stubs, sample projects, credentials, source documents,
font files or other add-on implementations. Every runtime file was byte-compared
against source; Python/JS syntax, root packaging, version identity, licenses and ZIP
integrity passed. Exact files/hashes are in Package_Verification.json.

Coverage includes first-run empty states, project bindings, local drafts and approval,
source versions/citations/updates, all-page search, protected fields, managed/occlusion
handoffs, undo authorization, stale/profile-change guards, duplicate prevention,
repair/bulk/split/compare, media reuse, archive hashes and atomic import, AI output
validation and per-request consent, restored privacy settings, command-menu and
narrow layouts, Atelier theme/remount/restoration, one-use native source contexts,
and recoverable failures. An intentionally invalid empty title and denied consent
are validation cases, not uncaught browser exceptions.

## What has not run

**No actual Windows Anki 25.09.5 / Qt process ran here.** Anki/Qt contracts use explicit
test doubles. Chromium renders the actual interface but does not create a native
Anki editor, reviewer, scheduler, PDF renderer or sync connection. Optional chat and
embedding transport is mocked; no external provider received data. The supplied
Atelier fixture is version {result['atelier_fixture_version']}, not the user's newer
0.7.1. The complete installed-add-on combination is not certified.

The remaining public-release gate is docs/NATIVE_ACCEPTANCE.md: real installation,
new note generation, native undo across add/edit/bulk operations, actual image
occlusion, original card scripts/audio, Qt PDF rendering/cropping, sync, profile
switching, upgrades and interference checks. No AnkiWeb upload or install code was
created. Core features are implemented, but passing synthetic integration contracts
must not be represented as native compatibility certification.

## Deliberate feature boundaries

PDF text extraction is bundled; visual pages/cropping need optional Qt PDF. DOCX/PPTX
are text imports, not visual replicas. No OCR. Semantic assistance reranks up to 30
visible results, not an unapproved whole-collection upload. Native occlusion,
HyperTTS, controller support and shared decks remain in their own editors/services.
Sprout receives an exact note-scope clipboard handoff; users choose covering decks
and paste it. Nothing writes private Sprout files. Prepared project milestones are
not learning/readiness scores. See docs/FEATURES.md and docs/PRIVACY.md for details.

## Reproduction

`python tools/build.py /path/to/output`

`python tools/verify_release.py /path/to/output --atelier /path/to/Atelier.ankiaddon`

The verifier fails without issuing a successful receipt if any suite or integrity
check fails. Test screenshots are marked sample data; the first-run screenshot has
no seeded projects. A source archive is generated after verification and includes
these tests, current screenshots and receipt.
'''
 (out/f'Workshop_{VERSION}_Test_Report.md').write_text(report);(ROOT/'docs/TEST_REPORT.md').write_text(report)
 source_archive(out)
 sums=[]
 for p in (installer,out/f'Workshop_Source_{VERSION}.zip'):sums.append(sha(p)+'  '+p.name)
 (out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
 shutil.rmtree(work)
 print(json.dumps({k:v for k,v in result.items() if k!='runtime_files'},indent=2))
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--atelier',type=Path,required=True);a=parser.parse_args()
 verify(a.output.resolve(),a.atelier.resolve())

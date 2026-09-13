"""Verify the complete installer, then run tests from its clean extraction.
No real Anki/Qt process is used by the native API-contract test doubles.
"""
from pathlib import Path
import argparse,hashlib,io,json,shutil,subprocess,sys,zipfile,xml.etree.ElementTree as ET
from PIL import Image,ImageSequence
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from addon.core import VERSION
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('output',type=Path)
parser.add_argument('--atelier',type=Path,required=True,help='Exact Atelier .ankiaddon to test')
parser.add_argument('--baseline',type=Path,required=True,help='Actual 0.10.0 installer to compare against')
args=parser.parse_args()
OUT=args.output.resolve(); ARCHIVE=OUT/f'Exam_Sprout_{VERSION}.ankiaddon'
ATELIER=args.atelier.resolve()
if not ATELIER.is_file(): raise FileNotFoundError(ATELIER)
WORK=OUT/'verification-work'
if WORK.exists():shutil.rmtree(WORK)
(WORK/'addon').mkdir(parents=True)
checks=[]
def checked(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
with zipfile.ZipFile(ARCHIVE) as z:
    checked('ZIP CRC integrity',z.testzip() is None)
    names=z.namelist()
    checked('No wrapper folder', '__init__.py' in names and 'manifest.json' in names)
    manifest=json.loads(z.read('manifest.json'))
    checked('Stable complete-addon package ID',manifest['package']=='exam_sprout')
    checked('Correct human version',manifest['human_version'].startswith(VERSION))
    checked('No caches or profile state',not any('__pycache__' in n or n.endswith(('.pyc','state.json','practice_answers.json','active_exam.json','pip_progress.json')) for n in names))
    required=['__init__.py','core.py','integration.py','runner.py','companion.py','companion_layout.py','session_tools.py','answers.py','storage.py','collection_reader.py','widget.py','diagnostics.py','web/app.js','web/app.css','web/pip.js','web/pip-scene.js','web/pip.css','web/pip/asset_manifest.json','readiness.py','evidence.py','exam_engine.py','exam_session.py','new_learning.py','progress.py','drafts.py','docs/READINESS_METHOD.md','docs/PRIVACY.md','docs/ANKIWEB_PUBLISHING.md']
    checked('Entire study/exam/mistake/companion implementation included',all(n in names for n in required))
    for source in (ROOT/'addon').rglob('*'):
        if not source.is_file() or '__pycache__' in source.parts or source.suffix in ('.pyc','.pyo'):continue
        n=source.relative_to(ROOT/'addon').as_posix()
        if n not in names or z.read(n)!=source.read_bytes():raise AssertionError('Source/archive mismatch: '+n)
    checked('All packaged addon files byte-identical to source',True)
    with zipfile.ZipFile(args.baseline) as base:
        original={n for n in base.namelist() if not n.startswith('docs/') and n not in ('README.md','LICENSE')}
        current={n for n in names if not n.startswith('docs/') and n not in ('README.md','LICENSE')}
        checked('No baseline runtime files removed or extra replacements introduced',original==current)
        delta={n for n in original if base.read(n)!=z.read(n)}
        checked('Only companion loader and version metadata changed',delta=={'companion.py','core.py','manifest.json'})
        checked('Core logic preserved except VERSION',base.read('core.py').replace(b'VERSION = "0.10.0"',b'VERSION = "0.10.1"')==z.read('core.py'))
        checked('Entire frontend and all artwork retained byte-for-byte',all(base.read(n)==z.read(n) for n in original if n.startswith('web/')))
        checked('Windows recovery instructions packaged','docs/WINDOWS_UPDATE_RECOVERY.md' in names)
        native_code=z.read('companion.py').decode()
        checked('No filename-backed native movie path remains','self.movie.setFileName(' not in native_code)
        checked('Owned in-memory device supplies the movie','self._movie_buffer = QBuffer(self.movie)' in native_code and 'self.movie.setDevice(self._movie_buffer)' in native_code)

    for n in names:
        if n.endswith('.py'):compile(z.read(n),n,'exec')
    checked('All packaged Python syntax compiled',True)
    art=json.loads(z.read('web/pip/asset_manifest.json'))
    checked('Live model and frame export bound by SHA-256',art['scene_sha256']==hashlib.sha256(z.read('web/pip-scene.js')).hexdigest())
    checked('24 high-quality/native animation assets',len(art['assets'])==24)
    frames=0
    for name,data in art['assets'].items():
        payload=z.read('web/pip/'+name)
        if hashlib.sha256(payload).hexdigest()!=data['sha256']:raise AssertionError('Art checksum '+name)
        idle='-idle.' in name
        with Image.open(io.BytesIO(payload)) as image:
            assert image.n_frames==(180 if idle else 96)
            assert image.size==((96,96) if name.startswith('tiny-') else (480,480))
            assert image.info['loop']==(0 if idle else 1)
            duration=0
            for frame in ImageSequence.Iterator(image):
                frame.load()
                assert frame.convert('RGBA').getchannel('A').getbbox()
                assert frame.info['duration'] in (33,34)
                duration+=frame.info['duration'];frames+=1
            assert duration==data['duration_ms']==(6000 if idle else 3200)
    checked('2976 nonblank frames at exact 30fps cadence',frames==2976)
    checked('Bounded native frame-cache pixel payload under 7 MB',art['reviewer']['maximum_decoded_frame_bytes']<=7_000_000)
    code=z.read('web/app.js').decode();native=z.read('companion.py').decode()
    checked('Separate Study, Focus and Browse actions',all('data-action="'+v+'"' in code for v in ['study','focus','browse']))
    checked('No inconsistent progression portrait markup','es-pip-stages' not in code)
    checked('No reviewer sidebar or extra mascot webview','QDockWidget' not in native and 'AnkiWebView' not in native)
    checked('Native animation pauses rather than rewinds on hide','self.movie.setPaused(True)' in native)
    checked('Archive paths cannot escape extraction root',all(not n.startswith('/') and '..' not in Path(n).parts for n in names))
    upload=OUT/'AnkiWeb_Publication'/f'UPLOAD_ONLY_Exam_Sprout_{VERSION}.ankiaddon'
    with zipfile.ZipFile(upload) as uz:
        checked('Upload-only ZIP CRC integrity',uz.testzip() is None)
        checked('Upload-only files match local package inventory',set(uz.namelist())==set(names))
        for name in names:
            if name=='manifest.json': continue
            if uz.read(name)!=z.read(name):raise AssertionError('Upload variant source mismatch: '+name)
        m=json.loads(uz.read('manifest.json'))
        checked('Numeric install disables old sideload only',m['conflicts']==['exam_sprout'])
        m['conflicts']=[]
        checked('Upload-only manifest has no other differences',m==manifest)
    checked('Upload variant code and artwork exactly match tested installer',True)
    z.extractall(WORK/'addon')
for p in (WORK/'addon/web').glob('*.js'):
    subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
checked('All packaged JavaScript syntax checked',True)
shutil.copytree(ROOT/'tests',WORK/'tests',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(ROOT/'tools',WORK/'tools',ignore=shutil.ignore_patterns('__pycache__'))
(WORK/'docs').mkdir(exist_ok=True)
shutil.copy2(ROOT/'pytest.ini',WORK/'pytest.ini')
runs=[('python-tests',[sys.executable,'-m','pytest','-q','--junitxml=docs/installer-unit-results.xml']),
      ('webgl-ui',['xvfb-run','-a',sys.executable,'tools/test_ui_096.py']),
      ('motion-readiness-ui',['xvfb-run','-a',sys.executable,'tools/test_ui_097.py']),
      ('assessment-ui',['xvfb-run','-a',sys.executable,'tools/test_ui_0100.py']),
      ('atelier',[sys.executable,'tools/test_atelier.py',str(ATELIER)])]
for name,cmd in runs:
    with (OUT/(name+'.log')).open('w') as log:
        result=subprocess.run(cmd,cwd=WORK,stdout=log,stderr=subprocess.STDOUT)
    checked('Clean installer extraction: '+name,result.returncode==0)
    print('PASS exact installer',name,flush=True)
suites=ET.parse(WORK/'docs/installer-unit-results.xml').getroot().iter('testsuite')
counts={k:0 for k in ['tests','failures','errors','skipped']}
for suite in suites:
    for k in counts:counts[k]+=int(suite.attrib.get(k,0))
def check_count(path):
    data=json.loads(path.read_text())
    val=data['checks']
    return val if isinstance(val,int) else len(val)
ui=check_count(WORK/'docs/ui-096-results.json')
motion=check_count(WORK/'docs/ui-097-results.json')
atelier=check_count(WORK/'docs/compatibility/atelier-results.json')
assessment=check_count(WORK/'docs/readiness-0100/ui-results.json')
checked('No Python failures, errors or skipped tests',all(counts[k]==0 for k in ('failures','errors','skipped')))
# A numeric add-on folder must not break pure relative imports; this is not a
# native Anki installation or proof of its exported web paths.
numeric_script='''
import importlib.util,sys
from pathlib import Path
root=Path(sys.argv[1]); name="1234567890"
spec=importlib.util.spec_from_file_location(name,root/"__init__.py",submodule_search_locations=[str(root)])
module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
for part in ["core","storage","readiness","evidence","exam_engine","exam_session","new_learning","progress","drafts"]:
    importlib.import_module(name+"."+part)
'''
subprocess.run([sys.executable,'-c',numeric_script,str(WORK/'addon')],check=True)
checked('Pure modules import under numeric AnkiWeb-style folder name',True)
report={'release':VERSION,'artifact':ARCHIVE.name,'bytes':ARCHIVE.stat().st_size,
        'sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),'checks':checks,
        'python_tests':counts,'ui_checks':ui,'motion_readiness_checks':motion,
        'atelier_browser_checks':atelier,'assessment_ui_checks':assessment,'browser_checks_total':ui+motion+assessment+atelier,
        'decoded_animation_frames':frames,'native_anki_windows_tested':False,
        'real_webgl2_tested':True,'native_api_contracts':'test doubles, not Qt',
        'collection_bridge_in_browser':'synthetic','hardware_fps_benchmarked':False,'native_new_card_scheduler_tested':False,
        'readiness_model_empirically_validated':False,'ankiweb_published':False,'baseline_runtime_delta':sorted(delta),'native_windows_installer_tested':False,
        'ankiweb_server_acceptance_tested':False,'upload_variant_difference':'manifest conflicts only'}
(OUT/'Package_Verification.json').write_text(json.dumps(report,indent=2))
for src,dest in [('installer-unit-results.xml','Installer_Tests.xml'),('ui-096-results.json','UI_Verification.json'),('ui-097-results.json','Motion_Readiness_Verification.json'),('compatibility/atelier-results.json','Atelier_Verification.json'),('readiness-0100/ui-results.json','Assessment_UI_Verification.json')]:
    shutil.copy2(WORK/'docs'/src,OUT/dest)
print(json.dumps(report,indent=2),flush=True)

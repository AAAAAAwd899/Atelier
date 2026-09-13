"""Package the exact verified cumulative runtime; deterministic, offline and unpublished."""
from __future__ import annotations
import hashlib,json,subprocess,tempfile,zipfile,shutil
from pathlib import Path
from release_tools import *
from release_copy import before_release_copy
V=ROOT/'verification'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    DIST.mkdir(parents=True,exist_ok=True)
    proof=json.loads((V/'verified.json').read_text());v=version()
    if proof['version']!=v or proof['runtime_sha256']!=runtime_digest():raise RuntimeError('Runtime differs from executed verification; rerun verify_release.py')
    if proof['python_failed'] or proof['python_skipped'] or proof['browser_errors']:raise RuntimeError('Verification was not clean')
    for name,count in proof['browser_suites'].items():
        r=json.loads((V/(name+'-results.json')).read_text())
        if r.get('errors') or r.get('count',r.get('checks'))!=count:raise RuntimeError('Browser evidence mismatch: '+name)
    for p in sorted(SRC.rglob('*.js')):subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
    baseline=json.loads((ROOT/'vendor-baseline.json').read_text())['sha256']
    changed=[name for name,sha in baseline.items() if digest(SRC/'sprout'/name)!=sha]
    if set(changed)!={'__init__.py','integration.py','runner.py','web/app.js'}:raise RuntimeError('Original exam engine boundary changed')
    inputs=json.loads((ROOT/'integration-baselines.json').read_text())
    workshop={n:h for n,h in inputs['incoming'].items() if n.startswith('workshop/')}
    workshop_changes=[n for n,h in workshop.items() if not (SRC/n).exists() or digest(SRC/n)!=h]
    if set(workshop_changes)!={'workshop/integration.py','workshop/web/app.js'}:raise RuntimeError('Incoming authoring engine boundary changed')
    # The final release may change only the audited consumer copy/version.
    # Reconstruct exact accepted bytes; arbitrary code differences still fail.
    previous=json.loads((ROOT/'release-1-baseline.json').read_text())
    edits=json.loads((ROOT/'release-copy-changes.json').read_text())
    def comparison(source_hashes):
        differing=[n for n,h in source_hashes.items() if not (SRC/n).exists() or digest(SRC/n)!=h]
        return {'files':len(source_hashes),'byte_identical':len(source_hashes)-len(differing),'changed_files':sorted(differing)}
    runtime_ext={'.py','.js','.css','.json','.svg','.png','.webp'}
    expected_runtime={n:h for n,h in previous.items() if Path(n).suffix in runtime_ext and 'user_files' not in Path(n).parts}
    for n,h in expected_runtime.items():
        if hashlib.sha256(before_release_copy(n)).hexdigest()!=h:
            raise RuntimeError('Undeclared code/asset/default change since accepted rc6: '+n)
    actual_runtime={p.relative_to(SRC).as_posix() for p in SRC.rglob('*') if p.is_file() and p.suffix in runtime_ext and '__pycache__' not in p.parts and 'user_files' not in p.relative_to(SRC).parts}
    if actual_runtime!=set(expected_runtime):raise RuntimeError('Undeclared runtime file added/removed')
    preservation={'version':v,'runtime_sha256':proof['runtime_sha256'],'baseline':'delivered 0.9.0-rc6',
        'reviewed_copy_files':sorted(edits['files']), 'exact_copy_substitutions':sum(len(x) for x in edits['files'].values()),
        'accepted_runtime_reconstructed':True,'style_art_icons_defaults_algorithms_unchanged':True,
        'comparisons':{
        'rc6_sprout':comparison({n:h for n,h in previous.items() if n.startswith('sprout/')}),
        'rc6_workshop':comparison({n:h for n,h in previous.items() if n.startswith('workshop/')}),
        'original_sprout_0101':comparison({'sprout/'+n:h for n,h in baseline.items()}),
        'incoming_workshop':comparison(workshop),'previous_rc6':comparison(previous)},
        'data_formats_paths_provider_consent_unchanged':True,'added_store_schema':None}
    (DIST/f'Atelier-{v}-Preservation.json').write_text(json.dumps(preservation,indent=2)+'\n')
    visual=DIST/'Atelier-Visual-Evidence.json';visual_data=json.loads(visual.read_text())
    if visual_data['runtime_sha256']!=proof['runtime_sha256'] or visual_data['capture_count']!=120:raise RuntimeError('Visual evidence not current')
    for c in visual_data['captures']:
        if digest(ROOT/c['source'])!=c['sha256']:raise RuntimeError('Visual capture changed: '+c['source'])
    gallery=DIST/'Atelier-Complete-Gallery.html'
    if not gallery.exists():raise RuntimeError('Complete gallery missing')
    installer=DIST/f'Atelier-{v}.ankiaddon';assets=build_installer(installer)
    with tempfile.TemporaryDirectory() as tmp:
        second=Path(tmp)/'repeat.ankiaddon';build_installer(second)
        if digest(second)!=digest(installer):raise RuntimeError('Nondeterministic installer')
        with zipfile.ZipFile(installer) as z:
            out=Path(tmp)/'extracted';z.extractall(out)
            if runtime_digest(out)!=proof['runtime_sha256']:raise RuntimeError('Packaged runtime mismatch')
            if len(z.namelist())!=len(assets) or len(set(z.namelist()))!=len(assets) or z.testzip():raise RuntimeError('ZIP entries/CRC failed')
            for p,n in assets:
                if z.read(n)!=p.read_bytes():raise RuntimeError('Packaged byte mismatch '+n)
    file_manifest={n:{'bytes':p.stat().st_size,'sha256':digest(p)} for p,n in assets}
    mf=DIST/f'Atelier-{v}-Files.json';mf.write_text(json.dumps({'version':v,'runtime_sha256':proof['runtime_sha256'],'files':file_manifest},indent=2)+'\n')
    record={**proof,'package':'daedalus_atelier','bundled_exam_engine':'Exam Sprout 0.10.1','bundled_card_studio':'Workshop 1.1.0-rc.1',
        'installer':installer.name,'installer_sha256':digest(installer),'installer_bytes':installer.stat().st_size,'file_count':len(assets),
        'sprout_original_files':len(baseline),'sprout_original_changed_files':changed,'incoming_workshop_files':len(workshop),
        'incoming_workshop_changed_files':workshop_changes,'reproducible_installer':True,'exact_packaged_bytes_verified':True,
        'gallery_capture_count':120,'published':False,'release_channel':'direct-install 1.0.0','acceptance':json.loads((ROOT/'RELEASE-ACCEPTANCE.json').read_text()),'copy_and_version_only_release':True}
    exact_path=V/'exact-installer.json'
    if exact_path.exists():
        exact=json.loads(exact_path.read_text())
        if exact.get('exact_installer_sha256')!=record['installer_sha256'] or exact['runtime_sha256']!=proof['runtime_sha256'] or exact['python_total']!=proof['python_total'] or exact['browser_total']!=proof['browser_total']:raise RuntimeError('Exact-installer rerun mismatch')
        record.update(exact_installer_full_verifier_repeated=True,exact_installer_verified_utc=exact['completed_utc'])
    build=DIST/f'Atelier-{v}-Build.json';build.write_text(json.dumps(record,indent=2)+'\n')
    for source,dest in [('src/USER-GUIDE.md','User-Guide'),('src/USER-GUIDE.md','Install-and-Recovery'),('src/RELEASE-NOTES.md','Release-Notes'),('src/SUPPORT.md','Support'),('ANKIWEB-LISTING-DRAFT.md','Listing-Text'),('AUDIT-REPORT.md','Verification'),('FEATURE-PRESERVATION.md','Feature-Preservation'),('src/PRIVACY.md','Privacy'),('RELEASE-GATES.md','Release-Gates')]:
        shutil.copyfile(ROOT/source,DIST/f'Atelier-{v}-{dest}.md')
    prefix=f'Atelier-{v}/';kitfiles=[(p,prefix+'src/'+n) for p,n in assets]
    for folder in ('tests','vendor_tests/tests','vendor_tests/tools','workshop_checks/tests','workshop_checks/tools'):
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or '.pytest_cache' in p.parts or p.suffix in ('.pyc','.pyo'):continue
            if p.suffix.lower() in ('.ttf','.otf','.woff','.woff2'):raise RuntimeError('Font in source kit')
            if p.suffix not in ('.py','.html','.css','.js','.json','.ankiaddon','.md','.txt'):continue
            # Historical install fixtures must not become a back door for private/font assets.
            if p.suffix=='.ankiaddon':
                with zipfile.ZipFile(p) as fixture:
                    if any(Path(n).suffix.lower() in ('.ttf','.otf','.woff','.woff2') for n in fixture.namelist()):raise RuntimeError('Font in historic test archive')
            kitfiles.append((p,prefix+p.relative_to(ROOT).as_posix()))
    for p in sorted(V.rglob('*')):
        if p.is_file() and p.suffix in ('.json','.xml','.log','.exit') and '__pycache__' not in p.parts:
            kitfiles.append((p,prefix+p.relative_to(ROOT).as_posix()))
    names=['release_copy.py','release-copy-changes.json','release-1-baseline.json','RELEASE-ACCEPTANCE.json','README.md','AUDIT-REPORT.md','FEATURE-PRESERVATION.md','RELEASE-GATES.md','MIGRATION.md','HANDOFF.md','ANKIWEB-LISTING-DRAFT.md','requirements-dev.txt','verify_release.py','package_release.py','release_tools.py','vendor-baseline.json','home-slice-baseline.json','session-slice-baseline.json','world-pass-baseline.json','usability-baseline.json','release-finish-baseline.json','native-widgets-baseline.json','widget-routing-baseline.json','WIDGET-API.md','integration-baselines.json','authoring-baseline-atelier-runtime.json','authoring-baseline-workshop-runtime.json']
    for name in names:kitfiles.append((ROOT/name,prefix+name))
    for p in (build,mf,visual,DIST/f'Atelier-{v}-Preservation.json'):
        kitfiles.append((p,prefix+'dist/'+p.name))
    # Gallery contains only compressed, current sample screenshots, no fonts or remote assets.
    kitfiles.append((gallery,prefix+'dist/'+gallery.name))
    for extra in ('Atelier-Native-Widgets-Gallery.html','Atelier-Native-Widgets-Evidence.json'):
        p=DIST/extra
        if p.exists():kitfiles.append((p,prefix+'dist/'+extra))
    if len({n for _,n in kitfiles})!=len(kitfiles):raise RuntimeError('Duplicate source entries')
    source=DIST/f'Atelier-{v}-Source.zip';write_archive(source,kitfiles)
    with tempfile.TemporaryDirectory() as tmp:
        repeat=Path(tmp)/'source-repeat.zip';write_archive(repeat,kitfiles)
        if digest(repeat)!=digest(source):raise RuntimeError('Nondeterministic source archive')
    checks=[installer,source,gallery,visual,build,mf,DIST/f'Atelier-{v}-Preservation.json']
    (DIST/f'Atelier-{v}-SHA256.txt').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in checks))
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()

"""Build Atelier 1.0.1 from fresh tests and an exact reviewed patch manifest.
No network, publication, collection access, or user data manipulation.
"""
from __future__ import annotations
import ast, hashlib, json, shutil, subprocess, tempfile, zipfile
from pathlib import Path
from release_tools import ROOT, SRC, DIST, runtime_digest, version, production_files, build_installer, write_archive

V=ROOT/'verification'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    v=version();assert v=='1.0.1'
    proof=json.loads((V/'verified.json').read_text())
    if proof['version']!=v or proof['runtime_sha256']!=runtime_digest():raise RuntimeError('Fresh verification required for these exact bytes')
    if proof['python_failed'] or proof['python_skipped'] or proof['browser_errors']:raise RuntimeError('Failed or skipped verification')
    for name,count in proof['browser_suites'].items():
        result=json.loads((V/(name+'-results.json')).read_text())
        if result.get('errors') or result.get('count',result.get('checks'))!=count:raise RuntimeError('Browser evidence mismatch: '+name)
    for p in SRC.rglob('*.js'):subprocess.run(['node','--check',str(p)],capture_output=True,check=True)
    baseline=json.loads((ROOT/'baseline-1.0.0.json').read_text())
    patch=json.loads((ROOT/'patch-101-changes.json').read_text())
    assets=production_files();actual={n:digest(p) for p,n in assets}
    if set(baseline)-set(actual):raise RuntimeError('Original file removed')
    changed={n:h for n,h in actual.items() if n in baseline and h!=baseline[n]}
    added={n:h for n,h in actual.items() if n not in baseline}
    if changed!=patch['changed'] or added!=patch['added']:raise RuntimeError('Unreviewed source modification')
    embedded={n:h for n,h in baseline.items() if n.startswith(('sprout/','workshop/'))}
    if any(actual.get(n)!=h for n,h in embedded.items()):raise RuntimeError('Embedded assessment or authoring engine changed')
    # Historical freeze helpers must be able to reconstruct genuine baseline bytes,
    # not just permit broad exceptions for a changing integration file.
    from patch_preservation import before_patch
    for n in changed:
        if hashlib.sha256(before_patch(n)).hexdigest()!=baseline[n]:raise RuntimeError('Baseline reconstruction mismatch: '+n)
    visual=DIST/f'Atelier-{v}-Visual-Evidence.json';vv=json.loads(visual.read_text())
    if vv['runtime_sha256']!=proof['runtime_sha256']:raise RuntimeError('Visual evidence not current')
    for c in vv['captures']:
        if digest(DIST/c['file'])!=c['sha256']:raise RuntimeError('Screenshot modified')
    installer=DIST/f'Atelier-{v}.ankiaddon';build_installer(installer)
    with tempfile.TemporaryDirectory() as temp:
        repeat=Path(temp)/'repeat.ankiaddon';build_installer(repeat)
        if digest(repeat)!=digest(installer):raise RuntimeError('Installer not reproducible')
        with zipfile.ZipFile(installer) as z:
            if z.testzip() or len(z.namelist())!=len(assets) or len(set(z.namelist()))!=len(assets):raise RuntimeError('ZIP integrity failure')
            if any(z.read(n)!=p.read_bytes() for p,n in assets):raise RuntimeError('Packaged byte mismatch')
            extracted=Path(temp)/'src';z.extractall(extracted)
            if runtime_digest(extracted)!=proof['runtime_sha256']:raise RuntimeError('Extracted runtime mismatch')
    preservation={'version':v,'baseline':'exact delivered Atelier 1.0.0','unchanged_files':len(baseline)-len(changed),
                  'original_files':len(baseline),'changed_files':sorted(changed),'added_files':sorted(added),
                  'embedded_sprout_files_unchanged':sum(n.startswith('sprout/') for n in embedded),
                  'embedded_workshop_files_unchanged':sum(n.startswith('workshop/') for n in embedded),
                  'all_existing_source_exam_stores_unchanged':True,'native_or_hardware_tested':False}
    preserved=DIST/f'Atelier-{v}-Preservation.json';preserved.write_text(json.dumps(preservation,indent=2)+'\n')
    record={**proof,'package':'daedalus_atelier','name':'Atelier','installer':installer.name,
            'installer_sha256':digest(installer),'installer_bytes':installer.stat().st_size,'file_count':len(assets),
            'reproducible_installer':True,'exact_packaged_bytes_verified':True,'published':False,
            'release_channel':'direct-install maintenance update','visual_capture_count':len(vv['captures']),
            'physical_remote_tested':False,'bluetooth_pairing_driver':False,
            'remote_support':'keyboard/HID mode; operating-system pairing; custom mappings opt-in and scheduled-review only',
            'missing_user_mask_screenshot':True}
    exact_path=V/'1.0.1/exact-targeted.json'
    if exact_path.exists():
        exact=json.loads(exact_path.read_text())
        if exact['exact_installer_sha256']!=record['installer_sha256'] or exact['runtime_sha256']!=record['runtime_sha256'] or exact['failed'] or exact['skipped']:raise RuntimeError('Exact-installer targeted evidence mismatch')
        record['exact_installer_targeted']=exact
    build=DIST/f'Atelier-{v}-Build.json';build.write_text(json.dumps(record,indent=2)+'\n')
    fm=DIST/f'Atelier-{v}-Files.json';fm.write_text(json.dumps({'version':v,'runtime_sha256':proof['runtime_sha256'],'files':{n:{'sha256':digest(p),'bytes':p.stat().st_size} for p,n in assets}},indent=2)+'\n')
    for src,label in [('src/USER-GUIDE.md','User-Guide'),('src/RELEASE-NOTES.md','Release-Notes'),('AUDIT-1.0.1.md','Verification'),('INSTALL-1.0.1.md','Install-and-Test')]:
        shutil.copyfile(ROOT/src,DIST/f'Atelier-{v}-{label}.md')
    prefix=f'Atelier-{v}/';kit=[(p,prefix+'src/'+n) for p,n in assets]
    for folder in ('tests','vendor_tests/tests','vendor_tests/tools','workshop_checks/tests','workshop_checks/tools'):
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file() or any(x in p.parts for x in ('__pycache__','.pytest_cache')):continue
            if p.suffix.lower() in ('.ttf','.otf','.woff','.woff2'):raise RuntimeError('Font in source kit')
            if p.suffix not in ('.py','.html','.css','.js','.json','.ankiaddon','.md','.txt'):continue
            if p.suffix=='.ankiaddon':
                with zipfile.ZipFile(p) as z:
                    if any(Path(n).suffix.lower() in ('.ttf','.otf','.woff','.woff2') for n in z.namelist()):raise RuntimeError('Font in historical test fixture')
            kit.append((p,prefix+p.relative_to(ROOT).as_posix()))
    for p in sorted(V.rglob('*')):
        if p.is_file() and p.suffix in ('.json','.xml','.log','.exit') and '__pycache__' not in p.parts:
            kit.append((p,prefix+p.relative_to(ROOT).as_posix()))
    # Old evidence is explicitly historical; current entry point is package_101.py.
    for p in sorted(ROOT.iterdir()):
        if p.is_file() and p.suffix in ('.py','.json','.md','.txt'):
            kit.append((p,prefix+p.name))
    outputs=[build,fm,preserved,visual,*[DIST/c['file'] for c in vv['captures']],DIST/f'Atelier-{v}-Reviewer-Preview.html']
    for p in outputs:kit.append((p,prefix+'dist/'+p.name))
    if len(kit)!=len({n for _,n in kit}):raise RuntimeError('Duplicate source entry')
    source=DIST/f'Atelier-{v}-Source.zip';write_archive(source,kit)
    with tempfile.TemporaryDirectory() as temp:
        repeat=Path(temp)/'source.zip';write_archive(repeat,kit)
        if digest(source)!=digest(repeat):raise RuntimeError('Source archive not reproducible')
    checks=[installer,source,build,fm,preserved,visual]
    (DIST/f'Atelier-{v}-SHA256.txt').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in checks))
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()

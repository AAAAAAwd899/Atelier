"""Deterministic owner handoff packaging. Never publishes or accesses a profile."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,zipfile
from release_tools import ROOT,SRC,DIST,version,runtime_digest,production_files,build_installer,write_archive

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',action='store_true',help='Package with explicitly incomplete release gates');ap.add_argument('--proof-dir',type=Path,default=ROOT/'verification');args=ap.parse_args()
    assert version()=='1.0.16';DIST.mkdir(exist_ok=True)
    fingerprint=runtime_digest();proofpath=args.proof_dir/'verified.json'
    proof=json.loads(proofpath.read_text()) if proofpath.is_file() else {}
    verified=proof.get('runtime_sha256')==fingerprint and proof.get('python_failed')==0 and proof.get('python_skipped')==0 and proof.get('browser_errors')==0
    if not verified and not args.candidate:raise RuntimeError('Full current verification missing. Explicit --candidate retains incomplete status; it does not waive release gates.')
    if verified:
        for name,count in proof['browser_suites'].items():
            receipt=json.loads((args.proof_dir/(name+'-results.json')).read_text())
            assert not receipt.get('errors') and receipt.get('count',receipt.get('checks'))==count
            assert (args.proof_dir/(name+'.exit')).read_text().strip()=='0'
    subprocess.run([__import__('sys').executable,str(ROOT/'tools/generate_design.py'),'--check'],check=True)
    for p in SRC.rglob('*.js'):subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
    assets=production_files();actual={n:sha(p) for p,n in assets}
    baseline=json.loads((ROOT/'baseline-1.0.2.json').read_text());patch=json.loads((ROOT/'patch-116-changes.json').read_text())
    parser=json.loads((ROOT/'PYPDF-VENDOR-6.21.4.json').read_text())
    assert sorted(set(baseline)-set(actual))==patch['removed']==parser['retired_baseline_modules']
    assert {n:h for n,h in actual.items() if n.startswith('workshop/vendor/pypdf/')}==parser['files']
    assert {n:h for n,h in actual.items() if n in baseline and h!=baseline[n]}==patch['changed']
    assert {n:h for n,h in actual.items() if n not in baseline}==patch['added']
    allowed_workshop_presentation={'workshop/web/app.js','workshop/web/app.css','sprout/web/app.js','sprout/web/pip.css','sprout/web/pip.js'}
    assert all(
        actual[n]==h
        for n,h in baseline.items()
        if n.startswith(('sprout/','workshop/')) and n not in allowed_workshop_presentation and n not in parser['files'] and n not in parser['retired_baseline_modules']
    )
    for native in ['native-social-116.json','native-sharing-116.json','native-onigiri-116.json','native-install-116.json']:
        result=json.loads((ROOT/'verification'/native).read_text())
        assert result['runtime_sha256']==fingerprint and not result['errors'] and all(result['checks'].values()),native
    service=json.loads((ROOT/'verification/social-116/service-results.json').read_text())
    assert service['runtime_sha256']==fingerprint and service['service_test_count']>=28 and not service['errors']
    installer=DIST/'Atelier-1.0.16.ankiaddon';build_installer(installer)
    assert sha(installer)==json.loads((ROOT/'verification/native-install-116.json').read_text())['installer_sha256']
    subprocess.run([__import__('sys').executable,str(ROOT/'tools/check_anki_addon.py'),str(installer),'--report',str(ROOT/'verification/anki-addon-116.json')],check=True)
    extracted=ROOT/'output/extracted-1.0.16';extracted.mkdir(parents=True,exist_ok=True)
    repeat_installer=DIST/'.Atelier-1.0.16-repeat.ankiaddon'
    try:
        build_installer(repeat_installer);assert sha(installer)==sha(repeat_installer)
        with zipfile.ZipFile(installer) as z:
            assert not z.testzip() and len(z.namelist())==len(assets)==len(set(z.namelist()))
            assert all(z.read(n)==p.read_bytes() for p,n in assets)
            z.extractall(extracted)
    finally:
        repeat_installer.unlink(missing_ok=True)
    assert runtime_digest(extracted)==fingerprint
    (ROOT/'verification/build-runtime-116.json').write_text(json.dumps({'runtime_sha256':fingerprint,'installer_sha256':sha(installer),'source_files_equal':True})+'\n')
    # Reuse only the exact installer's completed browser proof when rebuilding
    # documentation/source archives; changing any runtime byte forces the run.
    extracted_receipt=ROOT/'verification/installer-extracted-116.json'
    cached=json.loads(extracted_receipt.read_text()) if extracted_receipt.exists() else {}
    if not (cached.get('runtime_sha256')==fingerprint and cached.get('installer_sha256')==sha(installer) and cached.get('checks')==31 and cached.get('errors')==[]):
        from verify_release import verification_env
        env=verification_env();env['ATELIER_FIXTURE_SRC']=str(extracted)
        log=ROOT/'verification/folder-order-116-extracted.log'
        with log.open('w') as stream:
            subprocess.run([__import__('sys').executable,str(ROOT/'tests/test_folder_order_110_browser.py')],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=240)
        extracted_proof=json.loads((ROOT/'verification/folder-order-110/results.json').read_text())
        assert extracted_proof['count']==31 and not extracted_proof['errors']
        (ROOT/'verification/installer-extracted-116.json').write_text(json.dumps({'runtime_sha256':fingerprint,'installer_sha256':sha(installer),'checks':31,'category':'shipped frontend loaded from actual extracted installer; Chromium synthetic collection, not native Anki','errors':[]},indent=2)+'\n')
    # The extracted tree is only a verification scratch copy. Keep its hash
    # receipt and the 1.0.3 rollback artifacts, not another full runtime copy.
    from verify_release import verification_env
    env=verification_env();env['ATELIER_FIXTURE_SRC']=str(extracted)
    with (ROOT/'verification/library-polish-116-extracted.log').open('w',encoding='utf-8') as log:
        subprocess.run([__import__('sys').executable,'tests/test_library_polish_112_browser.py'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    (ROOT/'verification/library-polish-116-extracted.json').write_text(json.dumps({'runtime_sha256':fingerprint,'installer_sha256':sha(installer),'checks':json.loads((ROOT/'verification/library-polish-112/results.json').read_text())['count'],'category':'extracted installer task flow in headless Chromium; synthetic data','errors':[]},indent=2)+'\n')
    with (ROOT/'verification/social-116-extracted.log').open('w',encoding='utf-8') as log:
        subprocess.run([__import__('sys').executable,'tests/test_social_115_browser.py'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    social_proof=json.loads((ROOT/'verification/social-115/results.json').read_text())
    assert social_proof['runtime_sha256']==fingerprint and not social_proof['errors'] and social_proof['count']>=78
    (ROOT/'verification/social-116-extracted.json').write_text(json.dumps({'runtime_sha256':fingerprint,'installer_sha256':sha(installer),'checks':social_proof['count'],'category':'actual extracted installer UI and packaged art; synthetic service data, not native/hosted proof','errors':[]},indent=2)+'\n')
    assert extracted.resolve().is_relative_to(ROOT.resolve()) and extracted.name=='extracted-1.0.16'
    shutil.rmtree(extracted)
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    files=[(ROOT/n,'Atelier-1.0.16/'+n) for n in sorted(set(names)) if n and (ROOT/n).is_file()]
    forbidden=('.anki2','.sqlite3','.pem','.key','.ttf','.otf','.woff','.woff2')
    assert not any(p.suffix.lower() in forbidden or p.name.startswith('.env') for p,_ in files)
    source=DIST/'Atelier-1.0.16-Source.zip';write_archive(source,files)
    repeat_source=DIST/'.Atelier-1.0.16-repeat-source.zip'
    try:
        write_archive(repeat_source,files);assert sha(source)==sha(repeat_source)
    finally:
        repeat_source.unlink(missing_ok=True)
    with zipfile.ZipFile(source) as z:
        assert all(z.read('Atelier-1.0.16/src/'+n)==p.read_bytes() for p,n in assets)
    filemap=DIST/'Atelier-1.0.16-Files.json';filemap.write_text(json.dumps({'runtime_sha256':fingerprint,'files':actual},indent=2)+'\n')
    record={'name':'Atelier','version':version(),'package':'daedalus_atelier','channel':'owner handoff; AnkiWeb unpublished','owner_accepted':False,'publicly_published':False,'runtime_sha256':fingerprint,'installer_sha256':sha(installer),'source_sha256':sha(source),'runtime_file_count':len(assets),'original_files_unchanged':len(baseline)-len(patch['changed'])-len(patch['removed']),'changed':len(patch['changed']),'added':len(patch['added']),'removed':len(patch['removed']),'installer_source_bytes_equal':True,'zip_crc_passed':True,'repeat_installer_equal':True,'repeat_source_equal':True,'extracted_installer_browser_checks':87+social_proof['count'],'full_automated_verification':verified,'verification':proof if verified else {'status':'incomplete; see AUDIT-1.0.16.md and individual logs'},'native_evidence':'separate synthetic-profile evidence; not universal host acceptance','git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()}
    build=DIST/'Atelier-1.0.16-Build.json';build.write_text(json.dumps(record,indent=2)+'\n')
    (DIST/'Atelier-1.0.16-SHA256.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in [installer,source,build,filemap]))
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()

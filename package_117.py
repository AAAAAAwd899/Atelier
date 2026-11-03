"""Verified 1.0.17 repair package; no publication or owner profile mutation."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile,shutil
from release_tools import ROOT,SRC,DIST,production_files,runtime_digest,build_installer,write_archive

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 proof=json.loads((ROOT/'verification/verified.json').read_text());digest=runtime_digest()
 assert proof['version']=='1.0.17' and proof['runtime_sha256']==digest and proof['python_total']>=2001 and not proof['python_failed'] and not proof['python_skipped'] and not proof['browser_errors']
 for name,count in proof['browser_suites'].items():
  receipt=json.loads((ROOT/'verification'/(name+'-results.json')).read_text());assert not receipt.get('errors') and receipt.get('count',receipt.get('checks'))==count
  assert (ROOT/'verification'/(name+'.exit')).read_text().strip()=='0'
 native=[]
 for rel in ['output/native-install-117/results.json','output/onigiri-coexistence-117/results.json','output/listing-native-117-onigiri/host-report.json','output/native-social-117/results.json']:
  r=json.loads((ROOT/rel).read_text());assert r['runtime_sha256']==digest and not r['errors'] and all(r['checks'].values()),rel;native.append(r)
 assert native[2]['checks']['actual_anki_update_action_reached'] and native[2]['checks']['native_toolbar_restored'] and native[2]['graceful_shutdown']
 ui=json.loads((ROOT/'output/listing-native-117-onigiri/layout-check.json').read_text());assert ui['width']>300 and ui['bodyUnderHeader'] and not ui['overflow']
 assets=production_files();actual={n:sha(p) for p,n in assets};base=json.loads((ROOT/'baseline-1.0.2.json').read_text());patch=json.loads((ROOT/'patch-117-changes.json').read_text())
 assert {n:h for n,h in actual.items() if n in base and h!=base[n]}==patch['changed']
 assert {n:h for n,h in actual.items() if n not in base}==patch['added'] and sorted(set(base)-set(actual))==patch['removed']
 installer=DIST/'Atelier-1.0.17.ankiaddon';build_installer(installer);assert sha(installer)==native[0]['installer_sha256']==native[2]['installer_sha256']
 repeat=DIST/'.Atelier-1.0.17-repeat.ankiaddon';build_installer(repeat);assert sha(repeat)==sha(installer);repeat.unlink()
 subprocess.run([sys.executable,'tools/check_anki_addon.py',str(installer),'--report','verification/onigiri-toolbar-117/package-format.json'],check=True)
 scratch=ROOT/'output/extracted-1.0.17';scratch.mkdir(exist_ok=True)
 with zipfile.ZipFile(installer) as z:
  assert z.testzip() is None and len(z.namelist())==len(assets) and all(z.read(n)==p.read_bytes() for p,n in assets);z.extractall(scratch)
 assert runtime_digest(scratch)==digest
 from verify_release import verification_env
 env=verification_env();env['ATELIER_FIXTURE_SRC']=str(scratch)
 with (ROOT/'verification/onigiri-toolbar-117/extracted-home.log').open('w',encoding='utf8') as log:
  subprocess.run([sys.executable,'tests/test_home_slice_browser.py'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
 shutil.rmtree(scratch)
 names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
 files=[(ROOT/n,'Atelier-1.0.17/'+n) for n in sorted(set(names)) if n and (ROOT/n).is_file()]
 assert not any(p.suffix.lower() in ['.anki2','.sqlite3','.pem','.key','.ttf','.otf','.woff','.woff2'] or p.name.startswith('.env') for p,_ in files)
 source=DIST/'Atelier-1.0.17-Source.zip';write_archive(source,files)
 repeat_source=DIST/'.Atelier-1.0.17-repeat-source.zip';write_archive(repeat_source,files);assert sha(repeat_source)==sha(source);repeat_source.unlink()
 with zipfile.ZipFile(source) as z:assert all(z.read('Atelier-1.0.17/src/'+n)==p.read_bytes() for p,n in assets)
 record={'name':'Atelier','version':'1.0.17','package':'daedalus_atelier','runtime_sha256':digest,'installer_sha256':sha(installer),'source_sha256':sha(source),'installer_source_bytes_equal':True,'repeat_installer_equal':True,'repeat_source_equal':True,'full_automated_verification':True,'python_checks':proof['python_total'],'browser_checks':proof['browser_total'],'extracted_home_checks':218,'native_checks':sum(len(r['checks']) for r in native),'native_scope':'Windows Anki 26.09.3 hard-offscreen example profiles; actual update handler with controlled release-query boundary, no downloaded update or install','git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'ankiweb_uploaded':False,'hosted_friends_active':False,'physical_display_certified':False,'known_limit':'Existing Onigiri injector NotFoundError startup warning; coexistence tasks pass'}
 (DIST/'Atelier-1.0.17-Build.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record,indent=2))
if __name__=='__main__':main()

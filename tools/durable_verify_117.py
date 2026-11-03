"""Persist the owned release-check job across chat/tool interruptions."""
from pathlib import Path
import sys,os,json,subprocess,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
OUT=ROOT/'verification/onigiri-toolbar-117';OUT.mkdir(exist_ok=True)
status=OUT/'verification-job.json'
if '--worker' in sys.argv:
 record={'runtime_sha256':runtime_digest(),'pid':os.getpid(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'running','scope':'owned local verification subprocess; no owner profile or visible Anki app'}
 status.write_text(json.dumps(record,indent=2)+'\n')
 try:
  from verify_release import verification_env
  with (OUT/'full-ready.log').open('w',encoding='utf8') as log:
   result=subprocess.run([sys.executable,str(ROOT/'verify_release.py')],cwd=ROOT,env=verification_env(),stdout=log,stderr=subprocess.STDOUT)
  record['exit_code']=result.returncode;record['state']='passed' if result.returncode==0 else 'failed'
 except Exception as exc:record.update(state='failed',error=type(exc).__name__+': '+str(exc))
 record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();status.write_text(json.dumps(record,indent=2)+'\n')
else:
 if status.exists():
  old=json.loads(status.read_text())
  if old.get('state')=='running':raise SystemExit('An owned verification job is already recorded as running; inspect its status before starting another')
 with (OUT/'verification-launcher.log').open('w') as log:
  child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
 print(json.dumps({'pid':child.pid,'status_file':str(status),'window':'hidden'}))

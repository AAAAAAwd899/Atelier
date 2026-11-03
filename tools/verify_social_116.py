"""Prepared service and local client evidence gate; never deploys or sends email."""
from pathlib import Path
import sys,os,json,hashlib,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from verify_release import verification_env
from release_tools import runtime_digest
OUT=ROOT/'verification/social-116';OUT.mkdir(parents=True,exist_ok=True)
service=ROOT/'services/friends'
files={p.relative_to(service).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in service.rglob('*') if p.is_file() and 'node_modules' not in p.parts}
fingerprint=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
cmd=['node','--test','--test-reporter=junit','services/friends/tests/database.test.mjs','services/friends/tests/handler.test.mjs']
with (OUT/'service-tests.xml').open('w',encoding='utf8') as f:subprocess.run(cmd,cwd=ROOT,env=verification_env(),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
cases=list(ET.parse(OUT/'service-tests.xml').getroot().iter('testcase'));assert len(cases)>=28 and not any(x.find('failure') is not None or x.find('error') is not None or x.find('skipped') is not None for x in cases)
subprocess.run(['node','--check',str(service/'supabase/functions/atelier-friends/handler.mjs')],check=True)
report={'category':'Prepared service: real local PostgreSQL and Web Streams/controlled upstream tests; no hosted deployment or production concurrency proof','service_sha256':fingerprint,'service_files':files,'runtime_sha256':runtime_digest(),'service_test_count':len(cases),'errors':[],'hosted_service_verified':False,'deployed':False,'owner_activation_approved':False}
(OUT/'service-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='service_files'}))

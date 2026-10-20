"""Bounded, read-only pre-publication scan of reachable Git blobs; never prints secrets.

This detects known credential signatures and excluded data paths, not all possible
secrets. Source/runtime, licenses and asset provenance need their separate review.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
rows=git('rev-list','--objects','--all').decode().splitlines();objects={}
for row in rows:
    oid,_,name=row.partition(' ');objects.setdefault(oid,name)
query=''.join(oid+'\n' for oid in objects).encode()
meta=subprocess.run(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],input=query,cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
patterns={'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'openai_key':re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}'),
 'github_token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
 'aws_access_key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'google_key':re.compile(rb'\bAIza[A-Za-z0-9_-]{35}\b'),
 'slack_token':re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{20,}')}
findings=[];blobs=0;text_blobs=0;text_bytes=0
selected=[]
for row in meta:
    oid,kind,size=row.split();p=PurePosixPath(objects[oid])
    if kind=='blob' and int(size)<=4_000_000 and p.suffix.lower() in ['.py','.js','.json','.md','.txt','.html','.yml','.yaml','.toml','.css','.xml','.svg']:
        selected.append(oid)
# One bounded batch avoids spawning a Git process for each historical text blob.
batch=subprocess.run(['git','cat-file','--batch'],input=''.join(oid+'\n' for oid in selected).encode(),capture_output=True,check=True,cwd=ROOT).stdout
texts={};offset=0
for expected in selected:
    end=batch.index(b'\n',offset);oid,kind,size=batch[offset:end].decode().split();size=int(size)
    assert oid==expected and kind=='blob'
    offset=end+1;texts[oid]=batch[offset:offset+size];offset+=size+1
assert offset==len(batch)
for row in meta:
    oid,kind,size=row.split();size=int(size)
    if kind!='blob':continue
    blobs+=1;name=objects[oid];p=PurePosixPath(name)
    if p.suffix.lower() in ['.anki2','.sqlite','.sqlite3','.db','.colpkg','.apkg','.pem','.key','.pfx'] or p.name.startswith('.env') and p.name!='.env.example' or 'user_files' in p.parts and p.name!='README.txt':
        findings.append({'type':'excluded_data_path','path':name,'blob':oid})
    if size<=4_000_000 and p.suffix.lower() in ['.py','.js','.json','.md','.txt','.html','.yml','.yaml','.toml','.css','.xml','.svg']:
        data=texts[oid];text_blobs+=1;text_bytes+=len(data)
        for label,pattern in patterns.items():
            if pattern.search(data):findings.append({'type':label,'path':name,'blob':oid})
report={'commit':git('rev-parse','HEAD').decode().strip(),'reachable_commits':int(git('rev-list','--all','--count')),'reachable_blobs':blobs,'text_blobs_scanned':text_blobs,'text_bytes_scanned':text_bytes,'findings':findings,'large_binary_assets':'Reviewed by source paths, current file manifests and ASSET-PROVENANCE-1.0.3 records; not a binary content malware scan.','limits':'Known-signature scan, not proof that no secret can exist. No history rewrite or remote change performed.'}
dest=ROOT/'verification/public-source-audit-106.json';dest.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['findings']}));print('Findings:',len(findings))
if findings:print(json.dumps(findings[:10],indent=2));raise SystemExit(1)

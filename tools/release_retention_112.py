"""Exact Git-backed archive recovery proof; never touches Git objects or owner data."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile,copy,shutil,re,io,atexit
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification/retention-112';OUT.mkdir(parents=True,exist_ok=True)
D=ROOT/'dist';TMP=ROOT/'output/retention-112';TMP.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blobindex():
 ids=[line.split()[0] for line in git('rev-list','--objects','--all').splitlines()]
 info=subprocess.check_output(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],cwd=ROOT,input=b'\n'.join(ids)+b'\n')
 blobs=[line.split()[0] for line in info.splitlines() if line.split()[1]==b'blob']
 p=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
 result={}
 for oid in blobs:
  p.stdin.write(oid+b'\n');p.stdin.flush();head=p.stdout.readline().split();n=int(head[2]);h=hashlib.sha256()
  while n:
   b=p.stdout.read(min(n,1024*1024));assert b;n-=len(b);h.update(b)
  assert p.stdout.read(1)==b'\n';result.setdefault(h.hexdigest(),{'kind':'git','oid':oid.decode()})
 p.stdin.close();p.wait();assert p.returncode==0
 for rel in git('ls-files','-z').decode().split('\0'):
  path=ROOT/rel
  if rel and path.is_file():result.setdefault(sha(path),{'kind':'file','path':rel})
 for p in (ROOT/'.recovery/metadata').glob('*'):
  assert p.name==sha(p);result.setdefault(p.name,{'kind':'file','path':p.relative_to(ROOT).as_posix(),'reason':'small immutable historical container metadata delta'})
 return result

def audit():
 assert shutil.disk_usage(ROOT).free>50*1024**3+700_000_000
 index=blobindex();records=[]
 # Retained historical evidence is an independent leaf, never a deletion candidate.
 for p in D.glob('*.zip'):
  if 'Evidence' in p.name or 'Screenshots' in p.name:index.setdefault(sha(p),{'kind':'file','path':p.relative_to(ROOT).as_posix(),'reason':'historical acceptance evidence; not duplicated into source'})
 candidates=[]
 for p in D.iterdir():
  match=re.match(r'Atelier-1\.0\.(\d+)(?:-|\.)',p.name)
  if match and 3<=int(match[1])<=10 and (p.name.endswith('-Source.zip') or p.suffix=='.ankiaddon'):candidates.append(p)
 for p in sorted(candidates):
  records.append(prove(p,index))
 # Listing/full kits contain the already-proven primitives and retained listing files.
 for p in sorted(D.glob('*.zip')):
  if any(t in p.name for t in ['Full-Publish-Package','AnkiWeb-Listing-Kit']):records.append(prove(p,index))
 report={'scope':'old installer/source and redundant listing/publish containers only','current':'1.0.12','rollback':'1.0.11','protected_baseline':'untouched 1.0.2 implementation kit','proof':'all members independently restored from retained Git blobs/files; restored ZIP SHA256 must equal original','records':records,'eligible_bytes':sum(r['bytes'] for r in records if r['eligible']),'held':[r['path'] for r in records if not r['eligible']]}
 (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'eligible':sum(r['eligible'] for r in records),'bytes':report['eligible_bytes'],'held':report['held']}))

def prove(p,index):
 cached=OUT/(p.name+'.recovery.json')
 if cached.exists():
  r=json.loads(cached.read_text(encoding='utf-8'))
  if r.get('eligible') and r.get('restored_sha256')==sha(p)==r['sha256'] and all('metadata' in m for m in r['members']):
   index[r['sha256']]={'kind':'artifact','path':p.relative_to(ROOT).as_posix(),'proof':cached.relative_to(ROOT).as_posix()};return r
 r={'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size,'eligible':False,'members':[],'unmatched':[]}
 with zipfile.ZipFile(p) as z:
  r['archive_comment']=z.comment.hex()
  for i in z.infolist():
   if i.is_dir():continue
   data=z.read(i.filename);digest=hashlib.sha256(data).hexdigest();src=index.get(digest)
   row={'name':i.filename,'sha256':digest,'bytes':len(data),'source':src,'metadata':metadata(i)};r['members'].append(row)
   if src is None:r['unmatched'].append({'name':i.filename,'sha256':digest,'bytes':len(data)})
  if not r['unmatched']:
   # One bounded restored archive, using independent retained bytes.
   target=TMP/'restored.zip'
   try:target.write_bytes(restore_bytes(r))
   except AssertionError:
    target.unlink(missing_ok=True);r['restore_error']='Restored container SHA does not match';return r
   r['restored_sha256']=sha(target);r['eligible']=r['restored_sha256']==r['sha256'];target.unlink()
   if r['eligible']:
    proof=OUT/(p.name+'.recovery.json');proof.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    index[r['sha256']]={'kind':'artifact','path':p.relative_to(ROOT).as_posix(),'proof':proof.relative_to(ROOT).as_posix()}
 return r

_reader=None

def readsource(src):
 global _reader
 if src['kind']=='git':
  if _reader is None:_reader=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
  _reader.stdin.write(src['oid'].encode()+b'\n');_reader.stdin.flush();header=_reader.stdout.readline().split();assert header[1]==b'blob';data=_reader.stdout.read(int(header[2]));assert _reader.stdout.read(1)==b'\n';return data
 if src['kind']=='artifact':return restore_bytes(json.loads((ROOT/src['proof']).read_text(encoding='utf-8')))
 return (ROOT/src['path']).read_bytes()

def close_reader():
 if _reader is not None:_reader.stdin.close();_reader.wait()
atexit.register(close_reader)

def metadata(i):
 return {'date_time':list(i.date_time),'compress_type':i.compress_type,'comment':i.comment.hex(),'extra':i.extra.hex(),'create_system':i.create_system,'create_version':i.create_version,'extract_version':i.extract_version,'reserved':i.reserved,'flag_bits':i.flag_bits,'volume':i.volume,'internal_attr':i.internal_attr,'external_attr':i.external_attr}

def restore_bytes(record):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as z:
  z.comment=bytes.fromhex(record.get('archive_comment',''))
  for row in record['members']:
   data=readsource(row['source']);assert hashlib.sha256(data).hexdigest()==row['sha256']
   m=row['metadata'];i=zipfile.ZipInfo(row['name'],tuple(m['date_time']))
   for k,v in m.items():
    if k!='date_time':setattr(i,k,bytes.fromhex(v) if k in {'comment','extra'} else v)
   z.writestr(i,data,compress_type=i.compress_type,compresslevel=9)
 data=out.getvalue();assert hashlib.sha256(data).hexdigest()==record['sha256'];return data

def retire():
 report=json.loads((OUT/'audit.json').read_text(encoding='utf-8'))
 for v in ['1.0.11','1.0.12']:
  build=json.loads((D/f'Atelier-{v}-Build.json').read_text(encoding='utf-8'));assert build['full_automated_verification'] and sha(D/f'Atelier-{v}.ankiaddon')==build['installer_sha256'];assert sha(D/f'Atelier-{v}-Source.zip')==build['source_sha256']
 rows=[r for r in report['records'] if r['eligible']];before=shutil.disk_usage(ROOT).free
 # Validate every immutable proof leaf, and each original container, before removing any.
 for r in rows:
  p=(ROOT/r['path']).resolve();assert p.parent==D.resolve() and '1.0.11' not in p.name and '1.0.12' not in p.name and sha(p)==r['sha256']
  for member in r['members']:
   src=member['source'];data=readsource(src);assert hashlib.sha256(data).hexdigest()==member['sha256']
 receipt={'scope':report['scope'],'protected':['current 1.0.12','rollback 1.0.11','untouched 1.0.2 kit','unique historical native/visual evidence'],'free_before':before,'logical_bytes':sum(r['bytes'] for r in rows),'removed':[]}
 (OUT/'removal.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 for r in reversed(rows):
  p=(ROOT/r['path']).resolve();p.unlink();receipt['removed'].append({'path':r['path'],'sha256':r['sha256'],'bytes':r['bytes'],'recovery':(OUT/(p.name+'.recovery.json')).relative_to(ROOT).as_posix()})
  (OUT/'removal.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 receipt['free_after']=shutil.disk_usage(ROOT).free;(OUT/'removal.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'removed':len(rows),'logical_bytes':receipt['logical_bytes'],'free_after':receipt['free_after']}))

def restore(name):
 assert Path(name).name==name
 record=json.loads((OUT/(name+'.recovery.json')).read_text(encoding='utf-8'))
 assert shutil.disk_usage(ROOT).free>50*1024**3+700_000_000
 target=TMP/name
 if target.exists():assert sha(target)==record['sha256']
 else:target.write_bytes(restore_bytes(record))
 assert sha(target)==record['sha256']
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 print(json.dumps({'restored':str(target.relative_to(ROOT)),'sha256':sha(target),'bytes':target.stat().st_size}))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--retire',action='store_true');parser.add_argument('--restore');args=parser.parse_args();restore(args.restore) if args.restore else retire() if args.retire else audit()

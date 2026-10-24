"""Rerun initial sequential browser jobs that preceded the final source freeze.

Later jobs in that same complete run began after the saved boundary. No prior
release receipts are substituted; full aggregation still requires every suite.
"""
from pathlib import Path
import sys,ast,json,datetime
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import verify_release as v
from release_tools import runtime_digest
record=json.loads((v.V/'browser-cutover-108.json').read_text())
assert record['runtime_sha256']==runtime_digest()
tree=ast.parse((ROOT/'verify_release.py').read_text())
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
assignment=next(n for n in main.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='suites' for t in n.targets))
jobs=eval(compile(ast.Expression(assignment.value),'browser-job-list','eval'),vars(v))[:14]
assert [j[1] for j in jobs]==record['rerun_suites']
def run(job):
    script,name,path,cwd=job
    assert runtime_digest()==record['runtime_sha256']
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    v.run([sys.executable,script],name,cwd)
    assert runtime_digest()==record['runtime_sha256']
    result=json.loads(path.read_text());count=result.get('count',result.get('checks'))
    assert isinstance(count,int) and count>0 and not result.get('errors')
    result['runtime_sha256']=record['runtime_sha256'];result['started_utc']=started
    (v.V/(name+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    return {'suite':name,'count':count,'started_utc':started}
out=[]
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run,job) for job in jobs]):
        item=future.result();out.append(item);print('PASS',item['suite'],item['count'],flush=True)
record['rerun_results']=out;record['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(v.V/'browser-cutover-108.json').write_text(json.dumps(record,indent=2)+'\n')

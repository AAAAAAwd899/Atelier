"""Record exact 1.0.3 deltas; never rewrite historical patch manifests."""
from pathlib import Path
import json,hashlib,subprocess,tarfile,io
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'src'
def sha(data):return hashlib.sha256(data).hexdigest()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive','main','src'],cwd=ROOT))) as archive:
    old={m.name[4:]:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
current={p.relative_to(SRC).as_posix():p.read_bytes() for p in SRC.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
changed={n:sha(b) for n,b in current.items() if n in old and b!=old[n]}
added={n:sha(b) for n,b in current.items() if n not in old}
removed=sorted(set(old)-set(current))
if removed:raise SystemExit('Unexpected runtime removal: '+str(removed))
(ROOT/'baseline-1.0.2.json').write_text(json.dumps({n:sha(b) for n,b in old.items()},indent=2)+'\n',encoding='utf8',newline='\n')
(ROOT/'tests/data/release-102-baseline.json').write_text(json.dumps({n:old[n].decode('utf8') for n in changed},ensure_ascii=True)+'\n',encoding='utf8',newline='\n')
(ROOT/'patch-103-changes.json').write_text(json.dumps({'baseline':'verified Atelier 1.0.2 source','changed':changed,'added':added,'removed':removed},indent=2)+'\n',encoding='utf8',newline='\n')
print('Declared',len(changed),'changed;',len(added),'added; zero removed runtime files.')

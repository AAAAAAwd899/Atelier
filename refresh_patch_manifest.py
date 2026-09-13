from pathlib import Path
import json,hashlib,zipfile
from release_tools import SRC,ROOT
baseline=json.loads((ROOT/'baseline-1.0.0.json').read_text())
files={p.relative_to(SRC).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
changed={n:h for n,h in files.items() if n in baseline and baseline[n]!=h}
added={n:h for n,h in files.items() if n not in baseline}
with zipfile.ZipFile('/mnt/data/atelier_v1/project/dist/Atelier-1.0.0.ankiaddon') as z:
 old={n:z.read(n).decode('utf8') for n in changed}
(ROOT/'tests/data/release-100-baseline.json').write_text(json.dumps(old,ensure_ascii=True)+'\n')
(ROOT/'patch-101-changes.json').write_text(json.dumps({'baseline':'Atelier 1.0.0 delivered installer','changed':changed,'added':added},indent=2)+'\n')
print('Changed:',list(changed),'Added:',list(added))

"""Normalize intentionally edited text, then record the reviewed runtime delta."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
changed=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT).decode().splitlines()
added=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT).decode().splitlines()
def normalize(names):
    for name in names:
        p=ROOT/name
        if p.is_file() and (p.suffix in ('.py','.js','.css','.json','.md','.txt','.yml','.yaml','.html') or p.name in ('.gitignore','.gitattributes')):
            data=p.read_bytes();p.write_bytes(data.replace(b'\r\n',b'\n'))
normalize(changed+added)
subprocess.run([sys.executable,str(ROOT/'tools/declare_upgrade.py')],cwd=ROOT,check=True)
normalize(['baseline-1.0.2.json','patch-103-changes.json','tests/data/release-102-baseline.json'])

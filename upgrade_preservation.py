"""Reconstruct historical bytes only after checking exact declared upgrade hashes.

Current runtime behavior is tested separately. A changed byte outside the reviewed
manifest always fails; old assertions and historical manifests stay meaningful.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
def before_upgrade(name,data=None):
    if data is None:data=(ROOT/'src'/name).read_bytes()
    record=json.loads((ROOT/'patch-103-changes.json').read_text())
    if name in record['changed']:
        assert hashlib.sha256(data).hexdigest()==record['changed'][name], 'Undeclared 1.0.3 bytes: '+name
        data=json.loads((ROOT/'tests/data/release-102-baseline.json').read_text())[name].encode('utf8')
    baseline=json.loads((ROOT/'baseline-1.0.2.json').read_text())
    if name in baseline:assert hashlib.sha256(data).hexdigest()==baseline[name], 'Lost 1.0.2 baseline: '+name
    return data

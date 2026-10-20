"""Reconstruct historical bytes only after checking exact declared upgrade hashes.

Current runtime behavior is tested separately. A changed byte outside the reviewed
manifest always fails; old assertions and historical manifests stay meaningful.
"""
from pathlib import Path
import hashlib,json
from functools import lru_cache
ROOT=Path(__file__).resolve().parent

@lru_cache(maxsize=1)
def historical_text():
    out={}
    for name in ('release-102-baseline.json','release-102-onboarding-baseline.json','pypdf-590-baseline.json'):
        out.update(json.loads((ROOT/'tests/data'/name).read_text(encoding='utf8')))
    return out

def engine_bytes(name, source=ROOT/'src'):
    """Preserve old engine assertions around the separately pinned parser update.

    All non-parser bytes are still read directly. Parser bytes must first match
    the exact reviewed 6.21.1 lock (or its four explicitly retired modules), then
    their verified 5.9.0 originals are returned for historical comparisons.
    """
    if not name.startswith('workshop/vendor/pypdf/'):
        return (source/name).read_bytes()
    lock=json.loads((ROOT/'PYPDF-VENDOR-6.21.1.json').read_text())
    if name in lock['retired_baseline_modules']:
        assert not (source/name).exists()
    else:
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==lock['files'][name]
    raw=historical_text()[name].encode('utf8')
    assert hashlib.sha256(raw).hexdigest()==json.loads((ROOT/'baseline-1.0.2.json').read_text())[name]
    return raw

def before_upgrade(name,data=None):
    record=json.loads((ROOT/'patch-106-changes.json').read_text())
    if name in record['removed']:
        lock=json.loads((ROOT/'PYPDF-VENDOR-6.21.1.json').read_text())
        assert name in lock['retired_baseline_modules'] and not (ROOT/'src'/name).exists()
        data=historical_text()[name].encode('utf8')
    elif data is None:data=(ROOT/'src'/name).read_bytes()
    if name in record['changed']:
        assert hashlib.sha256(data).hexdigest()==record['changed'][name], 'Undeclared 1.0.6 bytes: '+name
        historical=historical_text()
        # Presentation files introduced or intentionally refreshed in 1.0.3
        # have no 1.0.2 byte snapshot. Their current bytes are validated by the
        # release manifest and dedicated UI contracts instead.
        if name not in historical:
            return data
        data=historical[name].encode('utf8')
    baseline=json.loads((ROOT/'baseline-1.0.2.json').read_text())
    if name in baseline:assert hashlib.sha256(data).hexdigest()==baseline[name], 'Lost 1.0.2 baseline: '+name
    return data

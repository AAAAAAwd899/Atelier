"""Verify the exact, reviewed 1.0 text substitutions without masking other edits."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent

def before_release_copy(name, data=None):
    if data is None: data=(ROOT/'src'/name).read_bytes()
    from upgrade_preservation import before_upgrade
    data=before_upgrade(name,data)
    patch_path=ROOT/'patch-101-changes.json'
    if patch_path.exists():
        import hashlib
        patch=json.loads(patch_path.read_text()).get('changed',{})
        if name in patch:
            if hashlib.sha256(data).hexdigest()!=patch[name]:
                raise AssertionError('Unreviewed change beyond 1.0.1 patch: '+name)
            data=json.loads((ROOT/'tests/data/release-100-baseline.json').read_text())[name].encode('utf8')
    entries=json.loads((ROOT/'release-copy-changes.json').read_text(encoding='utf8'))['files'].get(name,[])
    if not entries: return data
    baseline=json.loads((ROOT/'tests/data/release-rc6-copy-baseline.json').read_text(encoding='utf8'))[name]
    expected=baseline
    for edit in entries:
        if expected.count(edit['old'])!=edit['count']:
            raise AssertionError('Changed baseline copy occurrence: '+name)
        expected=expected.replace(edit['old'],edit['new'])
    if data!=expected.encode('utf8'):
        raise AssertionError('Undeclared change beyond reviewed copy: '+name)
    return baseline.encode('utf8')

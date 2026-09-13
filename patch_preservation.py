"""Exact 1.0.0 reconstruction for historical freeze tests only.
Current 1.0.1 functions are exercised separately in test_101 and browser tests.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent

def before_patch(name):
 data=(ROOT/'src'/name).read_bytes()
 allowed=json.loads((ROOT/'patch-101-changes.json').read_text())['changed']
 if name in allowed:
  if hashlib.sha256(data).hexdigest()!=allowed[name]:raise AssertionError('Undeclared patch byte change: '+name)
  data=json.loads((ROOT/'tests/data/release-100-baseline.json').read_text())[name].encode('utf8')
 baseline=json.loads((ROOT/'baseline-1.0.0.json').read_text())
 if name in baseline and hashlib.sha256(data).hexdigest()!=baseline[name]:raise AssertionError('Lost 1.0.0 baseline: '+name)
 return data

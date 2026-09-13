"""Fail-closed recognition for the stock native image-occlusion presentation.

No source image, mask coordinate or note template is changed. A user-edited or
unknown stock template remains owned by Anki until separately verified.
"""
import hashlib
import json
from pathlib import Path

CONTRACT=json.loads((Path(__file__).parent/'web'/'native-io-contract.json').read_text(encoding='utf8'))

def fingerprint(model):
    return hashlib.sha256(json.dumps({'css':model.get('css',''),
        'templates':[{k:t.get(k,'') for k in ('qfmt','afmt')} for t in model.get('tmpls',[])]},
        sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()

def recognized(model):
    return isinstance(model,dict) and model.get('originalStockKind')==6 and fingerprint(model) in CONTRACT['fingerprints']

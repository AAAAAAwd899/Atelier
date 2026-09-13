"""Optional response retention outside the collection; bounded to ten results.
Off by default. Never included in diagnostics. Turning off removes saved answers.
"""
from __future__ import annotations
import json
from .storage import Store
from .core import MAX_QUESTIONS


def clean_responses(responses):
    if not isinstance(responses, dict): return {}
    return {str(int(cid)): text[:10000] for cid, text in list(responses.items())[:MAX_QUESTIONS]
            if str(cid).isdigit() and 0 < int(cid) < 2**53 and isinstance(text, str)}


def load_answers(store):
    p = store.folder / 'practice_answers.json'
    if not store.state['settings'].get('remember_answers') or not p.exists(): return {}
    try:
        if p.stat().st_size > 11_000_000: return {}
        data = json.loads(p.read_text(encoding='utf8'))
        if not isinstance(data, dict): return {}
        return {str(k): clean_responses(v) for k, v in list(data.items())[-10:] if isinstance(k,str) and len(k) <= 64}
    except (OSError, ValueError, TypeError): return {}


def save_answers(store, result_id, responses):
    if store.read_only or not store.state['settings'].get('remember_answers'): return
    data = load_answers(store)
    data.pop(result_id, None); data[result_id] = clean_responses(responses)
    data = dict(list(data.items())[-10:])
    payload = json.dumps(data, ensure_ascii=False).encode('utf8')
    while len(payload) > 10_000_000 and len(data) > 1:
        data.pop(next(iter(data)))
        payload = json.dumps(data, ensure_ascii=False).encode('utf8')
    Store._atomic(store.folder / 'practice_answers.json', payload)


def clear_answers(store):
    (store.folder / 'practice_answers.json').unlink(missing_ok=True)


def remove_answers(store, result_ids):
    """Erase deleted-exam prose too, without touching other retained sessions."""
    if store.read_only:
        return
    path = store.folder / 'practice_answers.json'
    if not path.exists():
        return
    ids = set(result_ids)
    data = {k: v for k, v in load_answers(store).items() if k not in ids}
    if data:
        Store._atomic(path, json.dumps(data, ensure_ascii=False).encode('utf8'))
    else:
        path.unlink(missing_ok=True)

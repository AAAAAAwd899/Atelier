"""Explicit Save & close only: one local exam draft, with a visible privacy notice."""
import json
from .exam_session import ExamSession
from .storage import Store


def load_draft(store):
    p=store.folder/'active_exam.json'
    if not p.exists():return None
    if p.stat().st_size>25_000_000:raise ValueError('Saved exam exceeds the safety size limit.')
    return ExamSession.restore(json.loads(p.read_text(encoding='utf8')))


def save_draft(store,session):
    if store.read_only:raise ValueError('Your local exam folder is read-only.')
    data=session.serialize()
    ExamSession.restore(data)  # validate before replacing the last recoverable draft
    Store._atomic(store.folder/'active_exam.json',json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf8'))


def discard_draft(store,session_id=None):
    if session_id:
        draft=load_draft(store)
        if draft is not None and draft.id!=session_id:return
    (store.folder/'active_exam.json').unlink(missing_ok=True)


def draft_summary(store):
    try:
        s=load_draft(store)
        return {'id':s.id,'exam_id':s.exam_id,'questions':len(s.cards),'at':s.index+1,'phase':s.phase,
                'timed':bool(s.minutes),'deadline':s.deadline} if s else None
    except (OSError,ValueError,KeyError,TypeError):
        return {'error':'The saved exam cannot be read. It was not overwritten. Discard it explicitly to remove it.'}

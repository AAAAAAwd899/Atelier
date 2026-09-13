"""Integration-only adapters for the bundled, separately hardened Sprout engine.

No scheduling, sample construction, readiness scoring, result/draft persistence,
written-answer storage or Pip effort logic is implemented here.
"""
from __future__ import annotations
import hashlib
from typing import Any
from .core import (ValidationError, canonical_profile, canonical_study, fresh_catalog,
                   study_signature, set_study_active, upsert_study)


def active_engine(mw: Any):
    c = getattr(mw, '_exam_sprout_controller', None)
    return c if c is not None and getattr(c, 'mw', None) is mw else None


def summary(mw: Any) -> dict:
    """Small main-thread view of the SAME plan records, without reading card evidence."""
    c = active_engine(mw)
    if c is None or getattr(c, 'store', None) is None:
        return {'available': c is not None, 'plans': [], 'warning': 'Exam data is not open yet.'}
    store = c.store
    try:
        from .sprout.drafts import draft_summary
        plans = [{'id':e.id, 'name':e.name, 'due':e.due, 'archived':e.archived,
                  'deck_ids':[str(s.deck_id) for s in e.scopes if s.weight > 0],
                  'filtered':bool(e.query), 'mode':e.mode, 'format':e.exam_format}
                 for e in store.exams()]
        return {'available':True, 'engine':'0.10.1', 'plans':plans,
                'draft':draft_summary(store), 'read_only':store.read_only,
                'warning':store.warning, 'effort':c.pip_signal(),
                'history_count':len(store.state.get('history', []))}
    except (ValueError, OSError, TypeError, KeyError):
        return {'available':True, 'plans':[], 'warning':'Exam records need attention. Open Exam Studio diagnostics; no data has been reset.'}


def focus_exam(owner: Any, exam_id: str) -> dict:
    """Explicit pin of a plan's folders; native normal-review scope, not a mock.

    Search-filtered plans cannot silently turn into unfiltered scheduled review.
    No plan is copied, renamed or rewritten. Equivalent old shortcuts are reused.
    """
    from aqt import mw
    c = active_engine(mw)
    if c is None or not mw.col or c.store is None or c.store.read_only:
        raise ValidationError('Open a writable Exam Studio profile first.')
    exam = c.store.get_exam(exam_id)
    if exam.archived:
        raise ValidationError('Reactivate this archived exam in Exam Studio first.')
    if exam.query:
        raise ValidationError('This exam uses a search filter. Use its planner or practice actions to preserve that filter; pin folders separately for normal review.')
    owner.ensure_store()
    catalog = fresh_catalog(mw.col)
    sid = 'plan-' + hashlib.sha256(exam.id.encode()).hexdigest()[:24]
    candidate = canonical_study({'id':sid, 'name':exam.name[:100], 'date':exam.due[:10],
                                'deck_ids':[str(s.deck_id) for s in exam.scopes if s.weight > 0],
                                'active':True}, catalog, require_present=True)
    updated = canonical_profile(owner.profile, catalog)
    old = next((s for s in updated['studies'] if study_signature(s) == study_signature(candidate)), None)
    if old is not None:
        updated = set_study_active(updated, old['id'], True)
        target = old['id']
    else:
        updated = upsert_study(updated, candidate, catalog)
        target = candidate['id']
    updated['selected_study'] = target
    owner.store.write(updated)
    owner.profile = updated
    return {'focused':True, 'study_id':target, 'reused':old is not None}


def install_engine(owner: Any, registration: Any) -> None:
    """One transaction, one profile store, one hook set and one Pip singleton."""
    from aqt import mw
    from .lifecycle import StartupBlocked
    existing = active_engine(mw)
    if existing is not None:
        raise StartupBlocked('Standalone Exam Sprout is still running. Keep Atelier enabled, disable the separate Exam Sprout entry, then fully restart Anki. Your existing plans, results, draft and Pip effort remain in the same profile folder; do not delete them.')
    from .sprout import integration as engine
    def cleanup():
        c = engine.CONTROLLER
        if c is not None and getattr(c, 'suite', None) is owner:
            try:
                c.profile_close()
            finally:
                if getattr(mw, '_exam_sprout_controller', None) is c:
                    delattr(mw, '_exam_sprout_controller')
                engine.CONTROLLER = None
    registration.cleanup(cleanup)
    # The unchanged Pip component registers three callbacks itself. Own their
    # rollback here as well, without changing its hardened animation/lifetime code.
    def cleanup_companion_callbacks():
        from aqt import gui_hooks
        for name in ("reviewer_did_answer_card", "reviewer_did_show_question", "reviewer_did_show_answer"):
            hook = getattr(gui_hooks, name, None)
            if hook is None:
                continue
            for callback in tuple(hook):
                component = getattr(callback, "__self__", None)
                c = getattr(component, "controller", None)
                if c is not None and getattr(c, "suite", None) is owner:
                    hook.remove(callback)
    registration.cleanup(cleanup_companion_callbacks)
    c = engine.install(suite=owner, register=registration.hook)
    owner.exam_engine = c
    def palette():
        cfg = owner.get_config()
        if cfg['visual_owner'] != 'atelier' or not cfg.get('match_sprout', True):
            return None
        from .review_model import PALETTES
        return dict(PALETTES[cfg['theme']])
    c.suite_palette = palette
    from .quiet_navigation import QuestionNavigation
    c.suite_navigation_factory = QuestionNavigation

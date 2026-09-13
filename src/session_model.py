"""Read-only presentation for the existing exam state machine.

No clock writes, grading, persistence, navigation or card-field access. Indices
are validated against the existing session; the original runner owns actions.
"""
from __future__ import annotations
from typing import Any

FILTERS = ('all', 'unanswered', 'flagged')
PAGE_SIZE = 24

def question_indices(session: Any, view: str = 'all') -> list[int]:
    if view not in FILTERS:
        raise ValueError('Unknown question filter')
    attempted = getattr(session, 'attempted', set())
    flags = getattr(session, 'flags', set())
    return [i for i, c in enumerate(session.cards)
            if view == 'all' or view == 'unanswered' and c.id not in attempted
            or view == 'flagged' and c.id in flags]

def next_question(session: Any, view: str) -> int | None:
    """Next matching question, wrapping once. No reveal or auto-marking."""
    if session.phase != 'answering':
        return None
    indices = question_indices(session, view)
    later = [i for i in indices if i > session.index]
    earlier = [i for i in indices if i < session.index]
    return next(iter(later + earlier), None)

def question_page(session: Any, view: str = 'all', page: int = 0) -> dict:
    if type(page) is not int or page < 0:
        raise ValueError('Invalid question page')
    indices = question_indices(session, view)
    pages = max(1, (len(indices) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages - 1)
    attempted = getattr(session, 'attempted', set())
    flags = getattr(session, 'flags', set())
    rows = []
    for i in indices[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        cid = session.cards[i].id
        answered, flagged = cid in attempted, cid in flags
        rows.append({'index': i, 'number': i + 1, 'current': i == session.index,
                     'answered': answered, 'flagged': flagged,
                     'label': f'Question {i + 1} · {"answered" if answered else "unanswered"}'
                              + (' · flagged' if flagged else '')})
    return {'rows': rows, 'page': page, 'pages': pages, 'total': len(indices),
            'label': f'{len(indices)} matching · page {page + 1} of {pages}'}

def presentation(session: Any, *, read_only: bool = False,
                 current_new: bool = False, render_error: bool = False) -> dict:
    """Copy of display information, never an inferred/automatic scheduling mode."""
    total = len(session.cards)
    attempted = len(getattr(session, 'attempted', set()))
    flagged = len(getattr(session, 'flags', set()))
    graded = len(session.grades)
    native = bool(current_new and not read_only)
    if read_only:
        phase, title, note = 'read-only', 'Original-card review', 'Read-only · existing results and Anki schedules are unchanged'
    elif native:
        phase, title, note = 'learning', 'New-card learning', 'A real Anki rating changes this new card’s normal learning schedule'
    elif session.phase == 'grading':
        phase, title, note = 'grading', 'Self-marking', 'Responses are locked · self-marks do not reschedule cards'
    elif session.phase == 'answering':
        phase, title, note = 'mock', 'Mock exam', 'Answers locked until submission · Anki schedules are unchanged'
    else:
        phase = 'rehearsal'
        title = 'Pip rehearsal' if getattr(session, 'pip_study', False) else 'Focus practice'
        note = 'Recall, reveal, then self-mark · this card’s Anki schedule is unchanged'
    progress = session.index + 1 if read_only else graded if session.phase == 'grading' else attempted
    return {'phase': phase, 'title': title, 'note': note, 'total': total,
            'position': session.index + 1, 'answered': attempted, 'unanswered': total - attempted,
            'flagged': flagged, 'graded': graded, 'progress': min(progress, total),
            'navigation': not read_only and session.phase == 'answering',
            'native_rating': native, 'render_error': bool(render_error),
            'summary': f'{graded}/{total} self-marked' if session.phase == 'grading' and not read_only
                       else f'{session.index + 1}/{total} inspected' if read_only
                       else f'{attempted}/{total} answered · {flagged} flagged'}

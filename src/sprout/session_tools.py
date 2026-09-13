"""Pure study routing, readable sampling coverage, and mistake-review selectors."""
from __future__ import annotations
from .core import Exam, CardInfo, Snapshot


def needs_focus_session(exam: Exam, deck_id: int, names: dict[int, str]) -> bool:
    if deck_id not in {s.deck_id for s in exam.scopes}:
        raise ValueError('That deck is outside this exam.')
    if deck_id not in names:
        raise ValueError('This deck no longer exists.')
    path = names[deck_id] + '::'
    return bool(exam.query) or any(s.deck_id != deck_id and names.get(s.deck_id, '').startswith(path) for s in exam.scopes)


def practice_weights(exam, snap, cards, mode, custom):
    """Do not allocate a second quota to a parent whose cards live in child rows."""
    scopes = [s for s in exam.scopes if not snap.stats[s.deck_id].covered_elsewhere]
    counts = {s.deck_id: sum(c.owner == s.deck_id for c in cards) for s in scopes}
    if mode == 'custom': values = {s.deck_id: custom[s.deck_id] for s in scopes}
    elif mode == 'equal': values = {s.deck_id: 1 for s in scopes}
    elif mode == 'size':
        high = max(counts.values(), default=1) or 1
        values = {k: v / high * 100 for k, v in counts.items()}
    else: values = {s.deck_id: s.weight for s in scopes}
    # Excluded/empty groups are described in coverage, not fed to the sampler.
    return {k: value for k, value in values.items() if counts[k] > 0 and value > 0}


def sampling_coverage(exam, snap, cards, counts):
    rows = []
    for s in exam.scopes:
        st = snap.stats[s.deck_id]
        available = sum(c.owner == s.deck_id for c in cards)
        status = 'Covered through selected subdecks' if st.covered_elsewhere else 'Deck no longer exists' if st.missing else 'No cards match the inclusion settings' if not available else 'Included' if counts.get(s.deck_id, 0) else 'Not drawn in this session'
        rows.append({'deck_id': s.deck_id, 'name': st.name, 'available': available, 'drawn': counts.get(s.deck_id, 0), 'status': status})
    return rows


def review_items(result: dict) -> list[dict]:
    items = result.get('items')
    if isinstance(items, list):
        return [dict(x) for x in items if x.get('grade') is None or x.get('grade') < 1]
    # Old builds retained only explicitly missed IDs. They did not retain unanswered IDs.
    return [{'card_id': cid, 'note_id': cid, 'deck_id': row['deck_id'], 'grade': 0}
            for row in result.get('breakdown', []) for cid in row.get('missed_ids', [])]


def growth_signal(exam, stats):
    """A labeled study heuristic, never an exam-score or FSRS probability claim."""
    rows = [(s, stats[s.deck_id]) for s in exam.scopes if s.deck_id in stats and not stats[s.deck_id].covered_elsewhere and not stats[s.deck_id].missing and stats[s.deck_id].total and s.weight > 0]
    if not rows: return {'score': 0, 'stage': 1, 'label': 'Just planted'}
    numerator = denominator = 0.
    for scope, st in rows:
        familiarity = max(0., 1 - st.new / st.total)
        attempts = st.attempts + st.practice_attempts
        misses = st.again + st.practice_misses
        recall = (attempts - misses) / attempts if attempts else 0.
        evidence = min(1., attempts / max(5., st.total * .3))
        signal = .45 * familiarity + .30 * recall * evidence + .25 * (scope.confidence - 1) / 4
        weight = scope.weight * st.total
        numerator += signal * weight; denominator += weight
    score = round(100 * numerator / denominator)
    stage = 1 if score < 25 else 2 if score < 50 else 3 if score < 75 else 4
    return {'score': score, 'stage': stage, 'label': ['Just planted', 'Taking root', 'Growing strong', 'Sturdy little tree'][stage-1]}


def named_sample_warnings(warnings, stats):
    """Use deck names in residual coverage warnings; never hide a real shortfall."""
    import re
    def replace(match):
        did = int(match.group(1))
        st = stats.get(did)
        return f'“{st.name}”' if st is not None else 'A selected deck'
    return [re.sub(r'^Deck (\d+)(?= has no eligible cards)', replace, w) for w in warnings]

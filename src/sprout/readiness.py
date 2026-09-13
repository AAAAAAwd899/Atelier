"""Experimental readiness index v1, not a calibrated course-grade predictor.

No fitted coefficients, AI service or hidden claims of validation. The arbitrary
index weights/grade thresholds are a published product heuristic. Self confidence
never earns grade points. Precision/evidence strength is displayed separately.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import math
from .core import due_local

DISCLAIMER = ('Experimental projected readiness, based on observed study patterns and self-marked card correctness. '
              'This is not a promise, guarantee, or certainty of your actual exam grade. '
              'It does not measure unrepresented material or replace case/application practice.')
GRADE_BANDS = [(99, 'S'), (97, 'A+'), (93, 'A'), (90, 'A-'), (87, 'B+'), (83, 'B'), (80, 'B-'),
               (77, 'C+'), (73, 'C'), (70, 'C-'), (67, 'D+'), (63, 'D'), (60, 'D-'),
               (50, 'F+'), (30, 'F'), (0, 'F-')]


def letter(score):
    if score is None: return '—'
    return next(name for cutoff, name in GRADE_BANDS if max(0, min(100, score)) >= cutoff)


def daily_first(events, now):
    """First note retrieval per UTC day. Repeat/cloze sibling success cannot farm scores."""
    clean = []
    for e in events:
        try:
            ts, score = float(e['ts']), float(e['score'])
            if not math.isfinite(ts) or not math.isfinite(score) or not 0 <= score <= 1: continue
            if not now - 90*86400 <= ts <= now+60: continue
            if type(e['note_id']) is not int or e['note_id'] <= 0: continue
            clean.append(e)
        except (ValueError, KeyError, TypeError): continue
    seen, out = set(), []
    for e in sorted(clean, key=lambda e: (e['ts'], e['card_id'])):
        key = (e['note_id'], int(e['ts'] // 86400))
        if key in seen: continue
        seen.add(key); out.append(e)
    return out


def posterior(events, at):
    """Beta(1,1) mean with decayed note-day weights; bounds are sensitivity only."""
    weights = [2 ** (-max(0, at-e['ts'])/(14*86400)) * (.5 if e.get('legacy') else 1) for e in events]
    n = sum(weights); success = sum(w*e['score'] for w,e in zip(weights, events))
    p = (success+1)/(n+2)
    # Posterior dispersion of fractional-weight beta; NOT an exam confidence interval.
    spread = 1.96*math.sqrt(p*(1-p)/(n+3))
    return p, max(0, p-spread), min(1, p+spread), n


def readiness(exam, snapshot, now=None):
    now_dt = now or datetime.now(timezone.utc)
    now_ts = now_dt.timestamp()
    target = max(now_ts, due_local(exam.due).timestamp())
    events = daily_first(snapshot.evidence.get('events', []), now_ts)
    by_owner = defaultdict(list)
    for e in events: by_owner[e['owner']].append(e)
    rows = []; all_notes = set(); observed = set(); delayed_notes = set(); active_days = set()
    cold_sessions = defaultdict(list)
    for e in events:
        active_days.add(int(e['ts']//86400))
        if e.get('source') == 'exam' and e.get('delayed') and e.get('sampling') == 'representative':
            cold_sessions[e.get('session_id')].append(e)
    # Aggregate by exam-emphasis, not by number of cards in a topic.
    for scope in exam.scopes:
        st = snapshot.stats.get(scope.deck_id)
        if scope.weight <= 0 or (st and st.covered_elsewhere): continue
        cards = [c for c in snapshot.cards if c.owner == scope.deck_id]
        notes = {c.note_id for c in cards}; all_notes |= notes
        known_notes = {c.note_id for c in cards if not c.is_new}
        eligible_ids={c.id for c in cards}
        es = [e for e in by_owner.get(scope.deck_id, []) if e['card_id'] in eligible_ids]
        observed |= {e['note_id'] for e in es}
        recent = {e['card_id'] for e in es if target-e['ts'] <= 14*86400}
        delayed = {e['card_id'] for e in es if e.get('delayed') and target-e['ts'] <= 14*86400}
        delayed_notes |= delayed
        mock = [e for e in es if e.get('source')=='exam' and e.get('delayed')
                and e.get('sampling')=='representative']
        recall, lo, hi, effective = posterior(es, target)
        recall=min(recall,posterior(es,now_ts)[0])
        exam_recall = min(posterior(mock, target)[0],posterior(mock,now_ts)[0]) if mock else recall
        known = sum(not c.is_new for c in cards)/len(cards) if cards else 0
        coverage = len(recent)/len(cards) if cards else 0
        delayed_coverage = len(delayed)/len(cards) if cards else 0
        # Missing/unobserved topics remain in the weighted denominator (zero).
        signal = (.45*recall + .25*exam_recall + .20*known + .10*delayed_coverage)
        multiplier = .65 + .35*coverage
        score = 100*signal*multiplier if es and notes else 0.
        low = 100*(.70*lo+.20*known+.10*delayed_coverage)*multiplier if es else 0.
        high = 100*(.70*hi+.20*known+.10*delayed_coverage)*multiplier if es else 0.
        confident_misses = sum(e['score'] < 1 and e.get('confidence')==3 for e in es)
        rows.append({'deck_id': scope.deck_id, 'name': st.name if st else scope.name,
                     'weight': scope.weight, 'notes': len(notes), 'variants':len(cards), 'observed': len({e['note_id'] for e in es}),
                     'coverage': round(100*coverage), 'known': round(100*known),
                     'delayed': round(100*delayed_coverage), 'accuracy': round(100*recall) if es else None,
                     'score': round(score), 'low': round(low), 'high': round(high),
                     'effective': round(effective, 1), 'confident_misses': confident_misses,
                     'status': 'Missing deck' if not st or st.missing else 'No eligible material' if not notes else
                               'Needs a first check' if not es else 'Needs delayed practice' if not delayed else 'Evidence available'})
    weight = sum(r['weight'] for r in rows) or 1.
    wavg = lambda key: sum(r['weight']*r[key] for r in rows)/weight
    has_evidence = bool(observed)
    strength = 'Collecting evidence' if not has_evidence else 'Low' if len(observed)<20 or len(active_days)<2 else 'Moderate'
    note_coverage = len(observed)/len(all_notes) if all_notes else 0
    if len(observed)>=80 and len(active_days)>=4 and note_coverage>=.75: strength='High'
    row_weights={r['deck_id']:r['weight'] for r in rows}
    valid_mocks = [es for es in cold_sessions.values() if es and len(es)>=min(30, len(all_notes))
                   and sum(row_weights.get(owner,0) for owner in {e['owner'] for e in es})/weight>=.80]
    mock_days = {int(min(e['ts'] for e in es)//86400) for es in valid_mocks}
    score = round(wavg('score')) if has_evidence else None
    caps = []
    if score is not None:
        if snapshot.evidence.get('truncated'): caps.append((79,'Evidence exceeded the local safety limit; the estimate is capped and incomplete.'))
        if strength == 'Low': caps.append((79, 'Limited independent evidence caps the grade below B.'))
        if not valid_mocks: caps.append((89, 'No cold mock with enough questions and at least 80% topic-weight coverage yet; A/S readiness is not assigned.'))
        if any(r['weight']/weight>=.15 and r['coverage']<50 for r in rows):
            caps.append((79, 'A high-emphasis topic has less than 50% recent coverage.'))
        s_ready = (len(mock_days)>=2 and strength=='High' and wavg('coverage')>=90
                   and all(r['score']>=90 for r in rows if r['weight']/weight>=.1))
        if not s_ready: caps.append((98, 'S requires broad, repeated cold-exam evidence on separate days.'))
        score = min([score]+[x[0] for x in caps])
    reasons = [message for cap,message in caps if (round(wavg('score'))>=cap or cap<90)]
    if not has_evidence: reasons.insert(0, 'No usable answer evidence yet. Missing evidence is not a failing grade.')
    if exam.exam_format in ('mixed','application'): reasons.append('Explain mechanisms and practise cases outside these cards; card recall is not case competence.')
    return {'model': 'readiness-v1', 'grade': letter(score), 'score': score, 'evidence': strength,
            'label': 'Projected readiness · experimental', 'disclaimer': DISCLAIMER,
            'as_of': now_dt.isoformat(), 'target_date': exam.due,
            'observed_notes': len(observed), 'eligible_notes': len(all_notes), 'days': len(active_days),
            'coverage': round(wavg('coverage')), 'delayed_coverage': round(wavg('delayed')),
            'cold_mocks': len(valid_mocks), 'confident_misses': sum(r['confident_misses'] for r in rows),
            'sensitivity': [max(0, round(wavg('low'))), min(100, round(wavg('high')))] if has_evidence else None,
            'sensitivity_label': 'Heuristic evidence-sensitivity range; NOT an exam-score confidence interval.',
            'rows': sorted(rows, key=lambda r: (r['score'], -r['weight'])), 'limits': reasons,
            'method': '45% recency-weighted observed recall + 25% cold-mock recall (or observed recall when absent) '
                      '+ 20% introduced-card coverage + 10% delayed retrieval coverage. '
                      'Coverage uses actual card variants, not sibling notes. A recent-coverage penalty and evidence caps apply. First retrieval per note/UTC day only; '
                      '14-day evidence half-life; Beta(1,1) shrinkage. Projected to the exam date assuming no further learning. '
                      'Evidence weakens, but waiting alone cannot improve the projected recall component. Self-confidence and pet interactions add no grade points. Weights/thresholds are unvalidated design choices.',
            'bands': [{'minimum': n, 'grade': g} for n,g in GRADE_BANDS]}

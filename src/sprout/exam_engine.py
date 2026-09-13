"""Exam rehearsal: fixed blueprints, adaptive retrieval and explainable item risk.
A mock is fixed at sampling time. Answers cannot change its remaining questions.
"""
from __future__ import annotations
from collections import defaultdict
import random
import math
import time
from .core import Sample, sample_cards, apportion, bounded_int, MAX_QUESTIONS
from .session_tools import practice_weights


def note_history(snapshot):
    out = defaultdict(list)
    for e in snapshot.evidence.get('events', []): out[e['note_id']].append(e)
    return out


def item_priority(card, snapshot, now=None, indexed=None):
    now = now or time.time()
    es = sorted((indexed if indexed is not None else note_history(snapshot)).get(card.note_id, []), key=lambda e:e['ts'])
    recent = es[-1] if es else None
    last = snapshot.evidence.get('last_seen', {}).get(card.note_id, 0)
    if card.is_new: return 2.5, 'New material: learn it, then check it again later.'
    failures=[e for e in es if e['score']<1 and now-e['ts']<14*86400]
    unresolved=failures[-1] if failures else None
    if unresolved and any(e['score']==1 and e['ts']-unresolved['ts']>=86400 for e in es):unresolved=None
    if unresolved and unresolved.get('confidence')==3:
        return 5., 'Confident mistake: explain the reasoning before revealing.'
    if unresolved: return 4., 'Recent miss or partial answer: retrieve, then explain why.'
    if not es: return 3., 'Not yet independently checked: try an uncued answer.'
    if now-last<86400 and recent and recent['score']==1:
        return .25, 'Recently correct: a contrast or application check, not another easy repetition.'
    if card.is_due: return 2.8, 'Due material: use an explanation or example, not recognition.'
    return min(3., 1.+max(0,now-last)/(21*86400)), 'Delayed retrieval: recall first, then give an example or contrast.'


def interleave(cards, rng):
    """Shuffle topic queues, avoid consecutive same-topic items where possible."""
    groups=defaultdict(list)
    for card in cards: groups[card.owner].append(card)
    for group in groups.values(): rng.shuffle(group)
    out=[]; last=None
    while groups:
        choices=[k for k in groups if k!=last] or list(groups)
        owner=rng.choices(choices, weights=[len(groups[k]) for k in choices])[0]
        out.append(groups[owner].pop()); last=owner
        if not groups[owner]: del groups[owner]
    return out


def sample_exam(exam, snap, size, *, weighting='emphasis', custom=None, strategy='representative',
                include_new=True, one_per_note=True, ensure_coverage=True, cold_only=False, rng=None):
    size=bounded_int(size,1,MAX_QUESTIONS,'Questions')
    if strategy not in ('representative','adaptive'): raise ValueError('Unknown exam sampling strategy.')
    if weighting not in ('emphasis','equal','size','custom'):raise ValueError('Unknown blueprint weighting.')
    if any(type(v) is not bool for v in (include_new,one_per_note,ensure_coverage,cold_only)):raise ValueError('Exam inclusion options must be true or false.')
    rng=rng or random.SystemRandom(); now=time.time()
    cards=[c for c in snap.cards if include_new or not c.is_new]
    indexed=note_history(snap)
    excluded=0
    if cold_only:
        last=snap.evidence.get('last_seen',{})
        kept=[c for c in cards if not c.is_new and last.get(c.note_id,0)>0 and now-last[c.note_id]>=86400]
        excluded=len(cards)-len(kept); cards=kept
    weights=practice_weights(exam,snap,cards,weighting,custom or {s.deck_id:s.weight for s in exam.scopes})
    if not weights: raise ValueError('No cards match this blueprint. Cold-only excludes new cards and notes seen in the last 24 hours; adjust settings or wait.')
    if strategy=='representative':
        sample=sample_cards(cards,size,weights,one_per_note,ensure_coverage,rng)
    else:
        # Fix unique-note ownership/quotas using the proven sampler, then take a
        # weighted-without-replacement draw inside each owner. No item repeats.
        pool=[c for c in cards if weights.get(c.owner,0)>0]
        priorities={c.id:item_priority(c,snap,now,indexed)[0] for c in pool}
        rng.shuffle(pool)
        if one_per_note:
            # Prefer the most at-risk sibling. Cross-owner coverage uses the
            # existing bipartite matcher before adaptive selection when needed.
            selected=sample_cards(pool,min(MAX_QUESTIONS,len(pool)),weights,True,ensure_coverage,rng)
            reserved={c.note_id:c for c in selected.cards}
            all_notes=defaultdict(list)
            for c in pool:all_notes[c.note_id].append(c)
            pool=[reserved.get(n) or rng.choices(cs,weights=[priorities[c.id] for c in cs])[0]
                  for n,cs in all_notes.items()]
        groups=defaultdict(list)
        for c in pool:groups[c.owner].append(c)
        quotas=apportion(size,weights,{k:len(v) for k,v in groups.items()},ensure_coverage)
        chosen=[]
        for owner,n in quotas.items():
            chosen.extend(sorted(groups[owner],key=lambda c: -math.log(max(1e-15,rng.random()))/priorities[c.id])[:n])
        sample=Sample(chosen,quotas,size,len(pool),[])
        if len(chosen)<size:sample.warnings.append(f'Only {len(chosen)} eligible unique items remain; no repeats were added.')
        if size<len(groups):sample.warnings.append('Too few questions to include every positive-weight topic.')
        sample.warnings.append('Targeted rehearsal is intentionally harder/biased toward weak material; it is not a representative mock exam.')
    sample.cards=interleave(sample.cards,rng)
    if excluded:sample.warnings.append(f'{excluded} cards excluded by the 24-hour cold-retrieval rule (includes new cards, unknown exposure dates and note siblings).')
    return sample, cards

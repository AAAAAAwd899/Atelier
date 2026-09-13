"""Read-only detailed evidence; one SELECT per chunk, no collection writes.

Raw card text is never read here. Daily rollups bound rows even for intense cramming.
The model uses UTC note-days consistently, not Anki's configurable day boundary.
"""
from __future__ import annotations
from datetime import datetime, timezone
from .collection_reader import read_snapshot, chunks

LOOKBACK_DAYS = 90
MAX_EVENTS = 250_000


def collect_evidence(col, snapshot, exam, history=(), now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = int((now.timestamp() - LOOKBACK_DAYS * 86400) * 1000)
    cards = {c.id: c for c in snapshot.cards}
    events = []
    last = {}
    truncated = False
    for ids in chunks(cards):
        marks = ','.join('?' for _ in ids)
        # First review per CARD/UTC day at SQL level. Note/day sibling dedup is
        # then done across both normal and practice sources in readiness.py.
        rows = col.db.all(
            f'SELECT r.cid, r.id, r.ease, r.time, r.type, r.lastIvl FROM revlog r '
            f'JOIN (SELECT MIN(id) first_id FROM revlog WHERE cid IN ({marks}) '
            'AND id >= ? AND ease BETWEEN 1 AND 4 AND type IN (0,1,2) '
            'GROUP BY cid, CAST(id / 86400000 AS INTEGER)) d ON r.id = d.first_id',
            *ids, cutoff)
        for cid, stamp, ease, milliseconds, kind, interval in rows:
            if len(events)>=MAX_EVENTS:
                truncated=True;break
            card = cards.get(int(cid))
            if not card: continue
            events.append({'card_id': card.id, 'note_id': card.note_id, 'owner': card.owner,
                           'ts': int(stamp)/1000, 'score': 0. if ease == 1 else 1.,
                           'source': 'anki', 'seconds': max(0, int(milliseconds))/1000,
                           'delayed': bool(kind in (1, 2) and interval > 0), 'confidence': 0})
        for cid, stamp in col.db.all(
                f'SELECT cid, MAX(id) FROM revlog WHERE cid IN ({marks}) '
                'AND ease BETWEEN 1 AND 4 AND type IN (0,1,2) GROUP BY cid', *ids):
            card = cards.get(int(cid))
            if card: last[card.note_id] = max(last.get(card.note_id, 0), int(stamp)/1000)
    # Remap history by current card IDs/owners: renaming/reparenting/selecting a
    # different exam scope does not attribute a prior result to the wrong topic.
    for result in history:
        same_exam = result.get('exam_id') == exam.id
        try:
            stamp = datetime.fromisoformat(result['finished_at']).timestamp()
        except (ValueError, KeyError, TypeError): continue
        for item in result.get('items', []):
            card = cards.get(item.get('card_id'))
            if not card: continue
            # A learning rating is already in native revlog; never count it twice.
            if item.get('scheduled'): continue
            ts = item.get('answered_at') or stamp
            if type(ts) not in (float, int) or not 0 < ts <= now.timestamp()+60: continue
            if item.get('seen', item.get('grade') is not None):
                last[card.note_id] = max(last.get(card.note_id, 0), ts)
            score = item.get('grade')
            # A completed, submitted exam's unanswered items are no-credit.
            # Render errors, unfinished sessions and unmarked responses aren't failures.
            if score is None:
                if result.get('interrupted') or item.get('render_error') or item.get('attempted', True): continue
                score = 0.
            if ts*1000 < cutoff: continue
            if len(events)>=MAX_EVENTS:
                truncated=True;continue
            events.append({'card_id': card.id, 'note_id': card.note_id, 'owner': card.owner,
                           'ts': ts, 'score': score,
                           'source': 'exam' if result.get('kind') == 'exam' and same_exam else 'practice',
                           'seconds': item.get('seconds', 0), 'confidence': item.get('confidence', 0),
                           'delayed': bool(item.get('cold', False)),
                           'session_id': result['id'], 'legacy': 'answered_at' not in item,
                           'sampling': result.get('sampling', 'legacy')})
    return {'events': events, 'last_seen': last, 'as_of': now.isoformat(), 'truncated':truncated}


def read_exam_snapshot(col, exam, history=None, include_suspended=False, include_buried=False):
    snap = read_snapshot(col, exam, history, include_suspended, include_buried)
    snap.evidence = collect_evidence(col, snap, exam, history or ())
    return snap

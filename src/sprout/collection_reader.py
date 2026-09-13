"""Read-only Anki adapter. All large reads run inside a serialized QueryOp.

Only SELECT SQL is used. No sqlite3 connection is created or shared between
threads. Card IDs and scheduling facts, not field contents, are returned.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .core import CardInfo, DeckStats, Exam, Snapshot, scope_owners


def chunks(items: Iterable[int], size: int = 400):
    values = list(items)
    for i in range(0, len(values), size):
        yield values[i:i + size]


def deck_list(col) -> list[dict[str, Any]]:
    return [{"id": int(d.id), "name": str(d.name)} for d in col.decks.all_names_and_ids(include_filtered=False)]


def read_snapshot(col, exam: Exam, history: list[dict[str, Any]] | None = None,
                  include_suspended: bool = False, include_buried: bool = False) -> Snapshot:
    decks = deck_list(col)
    names = {d["id"]: d["name"] for d in decks}
    owners = scope_owners(exam.scopes, names)
    stats = {s.deck_id: DeckStats(s.deck_id, names.get(s.deck_id, s.name), missing=s.deck_id not in names) for s in exam.scopes}
    warnings = []
    missing_ids = [s.deck_id for s in exam.scopes if s.deck_id not in names]
    if missing_ids:
        warnings.append("One or more selected decks are missing. No substitute deck was selected.")
    # Use Anki's own due predicate instead of reimplementing scheduler semantics.
    due_ids = set(int(cid) for cid in col.find_cards("is:due")) if owners else set()
    allowed_ids = set(int(cid) for cid in col.find_cards(exam.query)) if exam.query else None
    by_id: dict[int, CardInfo] = {}
    for dids in chunks(owners):
        marks = ",".join("?" for _ in dids)
        rows = col.db.all(
            f"SELECT id, nid, did, odid, queue, type, lapses FROM cards "
            f"WHERE (CASE WHEN odid != 0 THEN odid ELSE did END) IN ({marks})", *dids,
        )
        for cid, nid, did, odid, queue, card_type, lapses in rows:
            cid = int(cid)
            if queue == -1 and not include_suspended:
                continue
            if queue in (-2, -3) and not include_buried:
                continue
            if queue < -3:
                continue
            if allowed_ids is not None and cid not in allowed_ids:
                continue
            owner = owners.get(int(odid or did))
            if owner is None:
                continue
            info = CardInfo(cid, int(nid), owner, card_type == 0, cid in due_ids, int(lapses))
            by_id[cid] = info
            st = stats[owner]
            st.total += 1
            st.new += int(info.is_new)
            st.due += int(info.is_due)
    # Selecting both a parent deck and its child decks is allowed. In that case
    # cards intentionally belong to the most specific selected deck, so the
    # parent can look empty even though all content is still covered below it.
    selected_names = {s.deck_id: names.get(s.deck_id, s.name) for s in exam.scopes}
    for scope in exam.scopes:
        st = stats[scope.deck_id]
        if st.missing or st.total:
            continue
        prefix = selected_names.get(scope.deck_id, scope.name) + "::"
        if any(other.deck_id != scope.deck_id and not stats[other.deck_id].missing and stats[other.deck_id].total
               and selected_names.get(other.deck_id, other.name).startswith(prefix)
               for other in exam.scopes):
            st.covered_elsewhere = True

    cutoff = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
    for cids in chunks(by_id):
        marks = ",".join("?" for _ in cids)
        rows = col.db.all(
            f"SELECT cid, COUNT(*), SUM(CASE WHEN ease = 1 THEN 1 ELSE 0 END), SUM(time) "
            f"FROM revlog WHERE cid IN ({marks}) AND id >= ? AND ease BETWEEN 1 AND 4 "
            f"AND type IN (0,1,2) GROUP BY cid", *cids, cutoff,
        )
        for cid, attempts, again, milliseconds in rows:
            st = stats[by_id[int(cid)].owner]
            st.attempts += int(attempts)
            st.again += int(again or 0)
            st.seconds += float(milliseconds or 0) / 1000
    # Only recent attempts for this specific exam contribute; incomplete or
    # ungraded questions do not count as misses in the recommendation engine.
    recent = [r for r in (history or []) if r.get("exam_id") == exam.id][-3:]
    for result in recent:
        try:
            when = datetime.fromisoformat(result["finished_at"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - when).days > 30:
                continue
            for row in result.get("breakdown", []):
                st = stats.get(int(row["deck_id"]))
                if st:
                    attempts = max(0, min(500, int(row["graded"])))
                    points = max(0, min(attempts, float(row["points"])))
                    st.practice_attempts += attempts
                    st.practice_misses += attempts - points
        except (ValueError, TypeError, KeyError):
            warnings.append("An invalid historical result was ignored for planning.")
    return Snapshot(decks, stats, list(by_id.values()), warnings)

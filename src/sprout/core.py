"""Exam Sprout's pure, testable planning and sampling logic.

No Anki imports, network access, collection writes, or scheduler calls belong here.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
import math
import random
import re
import time
from typing import Any, Mapping, Sequence
from uuid import uuid4

VERSION = "0.10.1"
SCHEMA = 1
MAX_QUESTIONS = 500
MAX_SESSION_MINUTES = 720
THEMES = ("inherit", "sage", "lavender", "peach", "rose", "sky", "midnight")
MODES = ("auto", "steady", "cram")
FORMATS = ("mixed", "recall", "application")


def bounded_int(value: Any, lo: int, hi: int, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a whole number.")
    try:
        n = int(value)
        if float(value) != n or not lo <= n <= hi:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label} must be a whole number from {lo} to {hi}.") from None
    return n


def finite_weight(value: Any, label: str = "Weight") -> float:
    try:
        x = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label} must be a number from 0 to 1000.") from None
    if not math.isfinite(x) or not 0 <= x <= 1000 or isinstance(value, bool):
        raise ValueError(f"{label} must be a number from 0 to 1000.")
    return x


def text(value: Any, maximum: int, label: str, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise ValueError(f"{label} must contain {'1' if required else '0'}–{maximum} characters.")
    return value


def due_local(value: str) -> datetime:
    """Exam deadlines are local wall-clock times, not fixed UTC offsets.

    This avoids retaining a stale offset across a local DST transition. Users
    travelling to a different timezone should update the exam's local time.
    """
    try:
        d = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Choose a valid exam date and time.") from None
    if d.tzinfo is not None or not 2000 <= d.year <= 2100:
        raise ValueError("Use a local exam date and time between 2000 and 2100.")
    return d


@dataclass(frozen=True)
class Scope:
    deck_id: int
    name: str
    confidence: int = 3
    weight: float = 1.0

    @classmethod
    def parse(cls, data: Mapping[str, Any]) -> "Scope":
        if not isinstance(data, Mapping):
            raise ValueError("Each deck selection must be an object.")
        return cls(
            bounded_int(data.get("deck_id"), 1, 2**53 - 1, "Deck ID"),
            text(data.get("name", ""), 1000, "Deck name"),
            bounded_int(data.get("confidence", 3), 1, 5, "Confidence"),
            finite_weight(data.get("weight", 1), "Exam emphasis"),
        )


@dataclass(frozen=True)
class Exam:
    id: str
    name: str
    due: str
    topics: str = ""
    mode: str = "auto"
    exam_format: str = "mixed"
    daily_minutes: int = 60
    weekdays: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    scopes: tuple[Scope, ...] = ()
    query: str = ""
    archived: bool = False
    created: str = ""

    @classmethod
    def parse(cls, data: Mapping[str, Any]) -> "Exam":
        if not isinstance(data, Mapping):
            raise ValueError("An exam must be an object.")
        eid = data.get("id") or uuid4().hex
        if not isinstance(eid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", eid):
            raise ValueError("Invalid exam identifier.")
        due = text(data.get("due", ""), 32, "Exam date", True)
        due_local(due)
        mode = data.get("mode", "auto")
        fmt = data.get("exam_format", "mixed")
        if mode not in MODES or fmt not in FORMATS:
            raise ValueError("Choose a supported study mode and exam format.")
        days = data.get("weekdays", list(range(7)))
        if not isinstance(days, (list, tuple)) or not days:
            raise ValueError("Choose at least one study day.")
        days = tuple(sorted({bounded_int(x, 0, 6, "Study day") for x in days}))
        raw_scopes = data.get("scopes", [])
        if not isinstance(raw_scopes, (list, tuple)) or not 1 <= len(raw_scopes) <= 100:
            raise ValueError("Choose between 1 and 100 exam decks.")
        scopes = tuple(Scope.parse(x) for x in raw_scopes)
        if len({s.deck_id for s in scopes}) != len(scopes):
            raise ValueError("A deck can only be selected once.")
        if not any(s.weight > 0 for s in scopes):
            raise ValueError("At least one exam deck needs a positive emphasis.")
        if type(data.get("archived", False)) is not bool:
            raise ValueError("Archived must be true or false.")
        return cls(
            id=eid, name=text(data.get("name", ""), 120, "Exam name", True),
            due=due, topics=text(data.get("topics", ""), 3000, "Exam topics"),
            mode=mode, exam_format=fmt,
            daily_minutes=bounded_int(data.get("daily_minutes", 60), 5, 480, "Daily minutes"),
            weekdays=days, scopes=scopes,
            query=text(data.get("query", ""), 2000, "Anki search filter"),
            archived=bool(data.get("archived", False)),
            created=text(data.get("created") or datetime.now(timezone.utc).isoformat(), 64, "Created time"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CardInfo:
    id: int
    note_id: int
    owner: int
    is_new: bool = False
    is_due: bool = False
    lapses: int = 0


@dataclass
class DeckStats:
    deck_id: int
    name: str
    total: int = 0
    new: int = 0
    due: int = 0
    attempts: int = 0
    again: int = 0
    seconds: float = 0
    practice_attempts: int = 0
    practice_misses: float = 0
    missing: bool = False
    covered_elsewhere: bool = False

    @property
    def seconds_per_card(self) -> float:
        if self.attempts >= 5 and self.seconds > 0:
            return min(90, max(8, self.seconds / self.attempts))
        return 25.0


@dataclass
class Snapshot:
    decks: list[dict[str, Any]]
    stats: dict[int, DeckStats]
    cards: list[CardInfo]
    warnings: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


def scope_owners(scopes: Sequence[Scope], deck_names: Mapping[int, str]) -> dict[int, int]:
    """A card belongs to its most specific selected ancestor; never both.

    Resolve by stable deck ID and *current* deck name, so renames are harmless.
    Missing IDs are not silently remapped to similarly named decks.
    """
    roots = [(s.deck_id, deck_names[s.deck_id]) for s in scopes if s.deck_id in deck_names]
    roots.sort(key=lambda x: (x[1].count("::"), len(x[1]), x[0]), reverse=True)
    return {
        did: next(root for root, name in roots if path == name or path.startswith(name + "::"))
        for did, path in deck_names.items()
        if any(path == name or path.startswith(name + "::") for _, name in roots)
    }


def apportion(total: int, weights: Mapping[int, float], capacities: Mapping[int, int],
              ensure_coverage: bool = False) -> dict[int, int]:
    """Capped largest-remainder allocation. Zero weights remain excluded.

    When coverage is enabled and the requested size permits it, reserve one
    card per nonempty, positive-weight group before allocating the remainder.
    """
    total = bounded_int(total, 0, 1_000_000, "Allocation size")
    w = {k: finite_weight(v) for k, v in weights.items()}
    caps = {k: max(0, int(capacities.get(k, 0))) for k in w}
    out = {k: 0 for k in w}
    active = [k for k in w if w[k] > 0 and caps[k] > 0]
    remaining = min(total, sum(caps[k] for k in active))
    if ensure_coverage and len(active) <= remaining:
        for k in active:
            out[k] = 1
        remaining -= len(active)
    while remaining > 0:
        active = [k for k in active if out[k] < caps[k]]
        if not active:
            break
        denominator = sum(w[k] for k in active)
        shares = {k: remaining * w[k] / denominator for k in active}
        additions = {k: min(caps[k] - out[k], math.floor(shares[k])) for k in active}
        used = sum(additions.values())
        for k, v in additions.items():
            out[k] += v
        remaining -= used
        if not remaining:
            break
        # Saturated groups relinquish excess to the next iteration.
        if any(out[k] == caps[k] and shares[k] > additions[k] for k in active):
            continue
        ordered = sorted(active, key=lambda k: (-(shares[k] - math.floor(shares[k])), -w[k], k))
        for k in ordered:
            if remaining and out[k] < caps[k]:
                out[k] += 1
                remaining -= 1
    return out


@dataclass
class Sample:
    cards: list[CardInfo]
    counts: dict[int, int]
    requested: int
    available: int
    warnings: list[str]


def sample_cards(cards: Sequence[CardInfo], size: int, weights: Mapping[int, float],
                 one_per_note: bool = True, ensure_coverage: bool = True,
                 rng: random.Random | None = None) -> Sample:
    size = bounded_int(size, 1, MAX_QUESTIONS, "Practice cards")
    rng = rng or random.SystemRandom()
    weights = {int(k): finite_weight(v) for k, v in weights.items()}
    if not any(v > 0 for v in weights.values()):
        raise ValueError("Give at least one deck a positive practice weight.")
    by_id = {c.id: c for c in cards if weights.get(c.owner, 0) > 0}
    pool = list(by_id.values())
    rng.shuffle(pool)
    if one_per_note:
        # Choose a single representative per note BEFORE quotas. Across decks,
        # prefer higher-weight groups probabilistically, never duplicate a note.
        notes: dict[int, list[CardInfo]] = defaultdict(list)
        for card in pool:
            notes[card.note_id].append(card)
        # Reserve a distinct note per owner with bipartite matching. A random
        # representative alone can accidentally erase an otherwise coverable
        # deck when reversed/cloze siblings live in different decks.
        owners_to_notes: dict[int, list[int]] = defaultdict(list)
        for nid, siblings in notes.items():
            for owner in {c.owner for c in siblings}:
                owners_to_notes[owner].append(nid)
        matched: dict[int, int] = {}  # note -> owner
        if ensure_coverage and len(owners_to_notes) <= size:
            for note_ids in owners_to_notes.values():
                rng.shuffle(note_ids)

            def assign(owner: int, visited: set[int]) -> bool:
                for nid in owners_to_notes[owner]:
                    if nid in visited:
                        continue
                    visited.add(nid)
                    if nid not in matched or assign(matched[nid], visited):
                        matched[nid] = owner
                        return True
                return False

            owner_order = list(owners_to_notes)
            rng.shuffle(owner_order)
            owner_order.sort(key=lambda x: len(owners_to_notes[x]))
            for owner in owner_order:
                assign(owner, set())
        pool = []
        for nid, siblings in notes.items():
            groups: dict[int, list[CardInfo]] = defaultdict(list)
            for card in siblings:
                groups[card.owner].append(card)
            owners = list(groups)
            owner = matched.get(nid)
            if owner is None:
                owner = rng.choices(owners, weights=[weights[x] for x in owners], k=1)[0]
            pool.append(rng.choice(groups[owner]))
    grouped: dict[int, list[CardInfo]] = defaultdict(list)
    for c in pool:
        grouped[c.owner].append(c)
    counts = apportion(size, weights, {k: len(v) for k, v in grouped.items()}, ensure_coverage)
    chosen: list[CardInfo] = []
    for owner, n in counts.items():
        if n:
            chosen.extend(rng.sample(grouped[owner], n))
    rng.shuffle(chosen)
    warnings = []
    if len(chosen) < size:
        warnings.append(f"Only {len(chosen)} eligible {'notes' if one_per_note else 'cards'} are available; no cards will be repeated.")
    if size < sum(bool(v) and weights.get(k, 0) > 0 for k, v in grouped.items()):
        warnings.append("This exam is too short to include every selected deck. Increase the number of cards for full deck coverage.")
    if one_per_note and len(pool) < len(by_id):
        warnings.append("Sibling cards were deduplicated: one card per note, including cloze siblings.")
    empty = sum(1 for k, w in weights.items() if w > 0 and not grouped.get(k))
    if empty:
        warnings.append(f"{empty} group(s) could not supply a unique eligible card. See the named coverage details.")
    return Sample(chosen, counts, size, len(pool), warnings)


def study_days(exam: Exam, now: datetime) -> list[date]:
    deadline = due_local(exam.due)
    if deadline <= now:
        return []
    days = []
    d = now.date()
    # User may enter an exam far in the future; bounded by supported year range.
    while d <= deadline.date():
        if d.weekday() in exam.weekdays:
            # Exam-day time is not promised as a study session. Only count it
            # when today IS exam day and time remains right now.
            if d < deadline.date() or d == now.date():
                days.append(d)
        d += timedelta(days=1)
    return days


def plan_exam(exam: Exam, stats: Mapping[int, DeckStats], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now()
    deadline = due_local(exam.due)
    hours = (deadline.timestamp() - now.timestamp()) / 3600
    mode = "cram" if exam.mode == "cram" or (exam.mode == "auto" and hours <= 72) else "steady"
    days = study_days(exam, now)
    warnings: list[str] = []
    remaining_minutes = max(0, math.floor(hours * 60))
    available_today = min(exam.daily_minutes, remaining_minutes) if now.weekday() in exam.weekdays else 0
    if hours <= 0:
        available_today = 0
        warnings.append("This exam time has passed. Update its date or archive it; practice is still available.")
    elif not days:
        warnings.append("There are no selected study days before this exam. Adjust your study days or use a practice session.")
    elif available_today == 0:
        warnings.append("Today is a rest day in your plan. The allocation below is for your next selected study day.")
    budget = available_today if available_today else (exam.daily_minutes if days else 0)
    breaks = int(budget // 30) * 5
    focus = max(0, budget - breaks)
    scores: dict[int, float] = {}
    rows = []
    workload = 0.0
    for scope in exam.scopes:
        st = stats.get(scope.deck_id, DeckStats(scope.deck_id, scope.name, missing=True))
        gap = (5 - scope.confidence) / 4
        attempts = st.attempts + st.practice_attempts
        failures = st.again + st.practice_misses
        # A small neutral prior stops a single failure from dominating a plan.
        difficulty = (failures + 2) / (attempts + 8)
        new_ratio = st.new / st.total if st.total else 0
        due_ratio = st.due / st.total if st.total else 0
        if mode == "cram":
            score = scope.weight * (.30 + .55 * gap + .30 * difficulty + .12 * due_ratio + .08 * new_ratio)
        else:
            score = scope.weight * (.30 + .38 * gap + .22 * new_ratio + .20 * difficulty + .15 * due_ratio)
        scores[scope.deck_id] = score if st.total and not st.missing else 0
        reasons = []
        if scope.confidence <= 2:
            reasons.append("you marked this as unfamiliar")
        if attempts >= 5 and failures / attempts >= .25:
            reasons.append("recent answers suggest extra practice")
        if st.new:
            reasons.append(f"{st.new} unseen cards")
        if st.due:
            reasons.append(f"{st.due} cards due")
        if not reasons:
            reasons.append("maintain recall with a brief mixed check")
        if st.missing:
            warnings.append(f"“{scope.name}” is missing. Re-select its deck; it has not been replaced automatically.")
        elif not st.total and not st.covered_elsewhere:
            warnings.append(f"“{st.name}” has no eligible cards in the current scope.")
        if scope.weight > 0:
            workload += (st.total + 2 * st.new) * st.seconds_per_card / 60
        rows.append({
            "deck_id": scope.deck_id, "name": st.name, "total": st.total,
            "new": st.new, "due": st.due, "confidence": scope.confidence,
            "weight": scope.weight, "reason": "; ".join(reasons),
            "recent_attempts": attempts, "recent_misses": failures,
            "seconds_per_card": round(st.seconds_per_card), "missing": st.missing,
            "covered_elsewhere": st.covered_elsewhere,
        })
    # The score can exceed 1000 when an emphasis is 1000; normalize first.
    high = max(scores.values(), default=0)
    normalized = {k: v / high * 100 if high else 0 for k, v in scores.items()}
    mins = apportion(focus, normalized, {k: focus for k in scores})
    shares = apportion(100, normalized, {k: 100 for k in scores})
    for row in rows:
        k = row["deck_id"]
        row["minutes"] = mins[k]
        row["share"] = shares[k]
        row["card_target"] = min(row["total"], int(mins[k] * 60 / row["seconds_per_card"]))
    rows.sort(key=lambda r: (-r["minutes"], -r["share"], r["name"].casefold()))
    total_focus = len(days) * (exam.daily_minutes - (exam.daily_minutes // 30) * 5)
    if days and now.date() in days:
        total_focus += focus - (exam.daily_minutes - (exam.daily_minutes // 30) * 5)
    if workload > total_focus > 0:
        warnings.append("Your time budget is smaller than an estimated first pass through the selected material. Prioritize the highest-emphasis weak areas; full coverage is not promised.")
    guidance = (
        "Start with the highest-priority weak topic, then mix in the other exam decks. Use short recall blocks and a mixed practice check. Do not sacrifice sleep to finish a card count."
        if mode == "cram" else
        "Build familiarity first, revisit missed material on later study days, and finish with mixed practice. Keep Anki’s normal due reviews alongside this exam plan."
    )
    if exam.exam_format in ("application", "mixed"):
        guidance += " For application questions, explain why the answer is correct and work cases outside Anki; recall cards alone do not recreate a case-based exam."
    phases = (
        [{"title": "Triage", "body": "Begin with the weakest high-emphasis deck."},
         {"title": "Mix & check", "body": "Use a short mixed practice session; revisit your misses."},
         {"title": "Wind down", "body": "Leave room for breaks and sleep, not one more full deck."}]
        if mode == "cram" else
        [{"title": "Build", "body": "Learn unfamiliar topics in focused blocks."},
         {"title": "Revisit", "body": "Return to mistakes on later selected study days."},
         {"title": "Rehearse", "body": "Try a mixed exam, then review what you missed."}]
    )
    return {
        "mode": mode, "hours_left": max(0, hours), "days_left": max(0, math.ceil(hours / 24)),
        "study_days_left": len(days), "next_study_day": days[0].isoformat() if days else None,
        "today_is_study_day": bool(available_today), "budget_minutes": budget,
        "focus_minutes": sum(mins.values()), "break_minutes": breaks,
        "rows": rows, "warnings": warnings, "guidance": guidance, "phases": phases,
        "estimated_first_pass_minutes": round(workload),
        "method": "Transparent planning heuristic, not a prediction of your exam score. Exam emphasis × a blend of self-rated confidence, unseen material, due cards, and recent misses. Recent history is smoothed; time/card counts are estimates.",
    }


def suggest_decks(topics: str, decks: Sequence[Mapping[str, Any]]) -> list[int]:
    """Literal deck-name hints, not an AI interpretation of card contents."""
    stop = {"the", "and", "exam", "test", "on", "of", "for", "with", "in", "to", "a"}
    tokens = {x for x in re.findall(r"[\w]+", topics.casefold()) if len(x) > 2 and x not in stop}
    scored = []
    for deck in decks:
        name = str(deck["name"]).casefold()
        hits = sum(1 for t in tokens if t in name)
        if hits:
            scored.append((-hits, name, int(deck["id"])))
    return [did for _, _, did in sorted(scored)[:15]]


class PracticeSession:
    """A local self-assessment state machine; deliberately knows nothing of Anki."""
    def __init__(self, exam_id: str, cards: Sequence[CardInfo], kind: str = "exam", minutes: int = 0):
        if not 1 <= len(cards) <= MAX_QUESTIONS or len({x.id for x in cards}) != len(cards):
            raise ValueError("A session needs 1–500 distinct cards.")
        if kind not in ("exam", "practice"):
            raise ValueError("Unknown session type.")
        self.id = uuid4().hex
        self.exam_id = exam_id
        self.cards = list(cards)
        self.kind = kind
        self.minutes = bounded_int(minutes, 0, MAX_SESSION_MINUTES, "Time limit")
        self.responses: dict[int, str] = {}
        self.grades: dict[int, float] = {}
        self.flags: set[int] = set()
        self.skipped: set[int] = set()
        self.index = 0
        self.phase = "answering" if kind == "exam" else "practice"
        self.revealed = False
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.start_clock = time.monotonic()
        self.ended_clock: float | None = None
        self.timed_out = False

    @property
    def current(self) -> CardInfo:
        return self.cards[self.index]

    def remaining_seconds(self, clock: float | None = None) -> int | None:
        if not self.minutes or self.phase in ("grading", "finished"):
            return None
        # Round below a microsecond before ceiling: floating-point subtraction
        # at an exact second boundary must not add an extra displayed second.
        remaining = self.minutes * 60 - ((clock if clock is not None else time.monotonic()) - self.start_clock)
        return max(0, math.ceil(round(remaining, 6)))

    def save_response(self, response: str) -> None:
        if self.phase not in ("answering", "practice"):
            return
        self.responses[self.current.id] = response[:10000]

    def go(self, delta: int) -> None:
        if self.phase != "answering":
            raise ValueError("Navigation is only available before submitting an exam.")
        self.index = max(0, min(len(self.cards) - 1, self.index + delta))
        self.revealed = False

    def submit(self, timed_out: bool = False) -> None:
        if self.phase not in ("answering", "practice"):
            return
        self.timed_out = timed_out
        self.ended_clock = time.monotonic()
        if self.kind == "exam":
            self.phase = "grading"
            self.index = 0
            self.revealed = True
        else:
            self.phase = "finished"

    def reveal(self) -> None:
        if self.phase not in ("practice", "grading"):
            raise ValueError("Answers stay hidden until the exam is submitted.")
        self.revealed = True

    def grade(self, value: float) -> None:
        if self.phase not in ("practice", "grading") or not self.revealed:
            raise ValueError("Reveal the answer before marking it.")
        if value not in (0, .5, 1):
            raise ValueError("Use missed, partial, or correct.")
        self.grades[self.current.id] = value
        self.advance()

    def advance(self) -> None:
        if self.phase not in ("practice", "grading"):
            raise ValueError("Cannot advance a submitted session this way.")
        if self.index + 1 == len(self.cards):
            self.phase = "finished"
            if self.ended_clock is None:
                self.ended_clock = time.monotonic()
        else:
            self.index += 1
            self.revealed = self.phase == "grading"

    def skip(self) -> None:
        if self.phase == "answering":
            self.skipped.add(self.current.id)
            self.go(1)
        elif self.phase in ("practice", "grading"):
            self.skipped.add(self.current.id)
            self.advance()

    def result(self, interrupted: bool = False) -> dict[str, Any]:
        breakdown: dict[int, dict[str, Any]] = {}
        for c in self.cards:
            row = breakdown.setdefault(c.owner, {"deck_id": c.owner, "total": 0, "graded": 0, "points": 0, "missed_ids": []})
            row["total"] += 1
            if c.id in self.grades:
                row["graded"] += 1
                row["points"] += self.grades[c.id]
                if self.grades[c.id] < 1:
                    row["missed_ids"].append(c.id)
        graded = len(self.grades)
        points = sum(self.grades.values())
        return {
            "id": self.id, "exam_id": self.exam_id, "kind": self.kind,
            "started_at": self.started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
            "total": len(self.cards), "graded": graded, "points": points,
            "percent": round(100 * points / len(self.cards)),
            "ungraded": len(self.cards) - graded,
            "elapsed_seconds": max(0, int((self.ended_clock or time.monotonic()) - self.start_clock)),
            "interrupted": interrupted, "timed_out": self.timed_out,
            "breakdown": list(breakdown.values()),
            "items": [{"card_id": c.id, "note_id": c.note_id, "deck_id": c.owner,
                       "grade": self.grades.get(c.id)} for c in self.cards],
            "flagged_ids": sorted(self.flags),
            # Free-text responses never leave this in-memory object.
        }

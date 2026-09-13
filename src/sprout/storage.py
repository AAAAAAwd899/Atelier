"""Atomic, profile-local state. Never stored in the collection database."""
from __future__ import annotations
from copy import deepcopy
import json
import os
import math
import re
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Any

from .core import Exam, SCHEMA, THEMES, MAX_QUESTIONS

DEFAULT_SETTINGS = {"theme": "inherit", "show_countdown": True, "compact": True, "show_toolbar": True, "max_countdowns": 2, "show_pip": True, "reviewer_pip": True, "animate_pip": True, "remember_answers": False}


def settings_from(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Settings must be an object.")
    out = dict(DEFAULT_SETTINGS)
    for key in ("show_countdown", "compact", "show_toolbar", "show_pip", "reviewer_pip", "animate_pip", "remember_answers"):
        if key in data:
            if not isinstance(data[key], bool):
                raise ValueError(f"{key} must be true or false.")
            out[key] = data[key]
    theme = data.get("theme", "inherit")
    if theme not in THEMES:
        raise ValueError("Choose an available theme.")
    out["theme"] = theme
    maximum = data.get("max_countdowns", 2)
    if type(maximum) is not int or maximum not in (1, 2, 3):
        raise ValueError("Show 1, 2, or 3 countdowns.")
    out["max_countdowns"] = maximum
    return out


def validate_result(data: Any) -> dict[str, Any]:
    """Validate persisted card identifiers and grades; never retain response text here."""
    if not isinstance(data, dict):
        raise ValueError("Invalid practice result.")
    def integer(key, lo, hi, obj=data):
        value = obj.get(key)
        if type(value) is not int or not lo <= value <= hi:
            raise ValueError(f"Invalid practice result: {key}.")
        return value
    def identifier(key):
        value = data.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
            raise ValueError(f"Invalid result identifier: {key}.")
        return value
    def points(value, graded):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= graded or value * 2 != int(value * 2):
            raise ValueError("Invalid self-marked points.")
        return value
    def card_ids(values):
        if not isinstance(values, list) or len(values) > MAX_QUESTIONS or any(type(c) is not int or not 1 <= c < 2**53 for c in values) or len(set(values)) != len(values):
            raise ValueError("Invalid result card identifiers.")
        return list(values)
    result = {"id": identifier("id"), "exam_id": identifier("exam_id")}
    for key in ("started_at", "finished_at"):
        value = data.get(key)
        if not isinstance(value, str) or len(value) > 64:
            raise ValueError("Invalid result timestamp.")
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None:
            raise ValueError("Result timestamps must include a timezone.")
        result[key] = value
    kind = data.get("kind")
    if kind not in ("exam", "practice"):
        raise ValueError("Invalid result type.")
    result["kind"] = kind
    total = result["total"] = integer("total", 1, MAX_QUESTIONS)
    graded = result["graded"] = integer("graded", 0, total)
    result["ungraded"] = integer("ungraded", 0, total)
    if result["ungraded"] + graded != total:
        raise ValueError("Result totals do not agree.")
    result["points"] = points(data.get("points"), graded)
    result["percent"] = integer("percent", 0, 100)
    if result["percent"] != round(100 * result["points"] / total):
        raise ValueError("Result score does not agree with its points.")
    result["elapsed_seconds"] = integer("elapsed_seconds", 0, 2**53 - 1)
    for key in ("interrupted", "timed_out"):
        if type(data.get(key)) is not bool:
            raise ValueError("Invalid result status.")
        result[key] = data[key]
    rows = data.get("breakdown")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Invalid practice breakdown.")
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid practice breakdown row.")
        t = integer("total", 1, MAX_QUESTIONS, row)
        g = integer("graded", 0, t, row)
        ids = card_ids(row.get("missed_ids"))
        if len(ids) > g:
            raise ValueError("Too many missed card identifiers.")
        clean.append({"deck_id": integer("deck_id", 1, 2**53 - 1, row), "total": t, "graded": g, "points": points(row.get("points"), g), "missed_ids": ids})
    if len({row["deck_id"] for row in clean}) != len(clean) or sum(row["total"] for row in clean) != total or sum(row["graded"] for row in clean) != graded or sum(row["points"] for row in clean) != result["points"]:
        raise ValueError("Practice breakdown does not agree with its totals.")
    result["breakdown"] = clean
    result["flagged_ids"] = card_ids(data.get("flagged_ids"))
    if "items" in data:
        items = data["items"]
        if not isinstance(items, list) or len(items) != total:
            raise ValueError("Invalid session card list.")
        parsed = []
        for item in items:
            if not isinstance(item, dict): raise ValueError("Invalid session card.")
            grade = item.get("grade")
            if grade is not None and (type(grade) not in (int, float) or grade not in (0, .5, 1)):
                raise ValueError("Invalid session card grade.")
            parsed.append({"card_id": integer("card_id",1,2**53-1,item),
                           "note_id": integer("note_id",1,2**53-1,item),
                           "deck_id": integer("deck_id",1,2**53-1,item), "grade":grade})
        if len({i["card_id"] for i in parsed}) != total or sum(i["grade"] is not None for i in parsed) != graded or sum(i["grade"] or 0 for i in parsed) != result["points"]:
            raise ValueError("Session card totals disagree.")
        if any(i["deck_id"] not in {r["deck_id"] for r in clean} for i in parsed):
            raise ValueError("Session card belongs to an unknown result group.")
        # Optional v0.10 telemetry is validated independently; old results remain readable.
        for source, target in zip(items, parsed):
            for key in ("seen", "attempted", "cold", "scheduled", "render_error"):
                if key in source:
                    if type(source[key]) is not bool: raise ValueError("Invalid item status.")
                    target[key] = source[key]
            if "confidence" in source:
                target["confidence"] = integer("confidence", 0, 3, source)
            for key, maximum in (("seconds", 90*86400), ("answered_at", 9_999_999_999)):
                if key in source and source[key] is not None:
                    value = source[key]
                    if type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= maximum:
                        raise ValueError("Invalid item timing.")
                    target[key] = value
            if "error_type" in source:
                if source["error_type"] not in ("none","recall","concept","application","misread","calculation","guess"):
                    raise ValueError("Invalid error category.")
                target["error_type"] = source["error_type"]
        # Items and summary must agree PER TOPIC, not only in their grand totals.
        for row in clean:
            group = [i for i in parsed if i["deck_id"] == row["deck_id"]]
            if (len(group) != row["total"] or sum(i["grade"] is not None for i in group) != row["graded"]
                    or sum(i["grade"] or 0 for i in group) != row["points"]
                    or {i["card_id"] for i in group if i["grade"] is not None and i["grade"] < 1} != set(row["missed_ids"])):
                raise ValueError("Topic item totals disagree.")
        result["items"] = parsed
    if "sampling" in data:
        if data["sampling"] not in ("representative", "adaptive"): raise ValueError("Invalid sampling method.")
        result["sampling"] = data["sampling"]
    if "pip_study" in data:
        if type(data["pip_study"]) is not bool: raise ValueError("Invalid study mode.")
        result["pip_study"] = data["pip_study"]
    if "blind_spots" in data:
        result["blind_spots"] = integer("blind_spots",0,total)
    return result


def validate_state(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or type(data.get("schema")) is not int:
        raise ValueError("Invalid state file.")
    if data["schema"] != SCHEMA:
        raise ValueError("This data was created by a different version. It has not been overwritten.")
    exams = data.get("exams", [])
    history = data.get("history", [])
    if not isinstance(exams, list) or len(exams) > 500:
        raise ValueError("Invalid exam list.")
    parsed = [Exam.parse(e).to_dict() for e in exams]
    if len({e["id"] for e in parsed}) != len(parsed):
        raise ValueError("Duplicate exam IDs in state file.")
    if not isinstance(history, list):
        raise ValueError("Invalid practice history.")
    clean_history = [validate_result(r) for r in history[-50:]]
    return {"schema": SCHEMA, "settings": settings_from(data.get("settings", {})), "exams": parsed, "history": clean_history}


class Store:
    def __init__(self, profile_folder: str | Path):
        self.folder = Path(profile_folder) / "exam_sprout"
        self.path = self.folder / "state.json"
        self.backup = self.folder / "state.json.bak"
        self.state = {"schema": SCHEMA, "settings": dict(DEFAULT_SETTINGS), "exams": [], "history": []}
        self.warning = ""
        self.read_only = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self.state = self._read(self.path)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            # Do not silently overwrite a newer schema with an older backup.
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("schema") != SCHEMA:
                    self.read_only = True
                    self.warning = str(exc)
                    return
            except (OSError, ValueError):
                pass
            try:
                self.state = self._read(self.backup)
                self.warning = "The main exam data file could not be read. A validated backup was loaded. The original file is preserved until your next successful save."
            except (OSError, ValueError, TypeError, KeyError):
                self.read_only = True
                self.warning = "Exam data and its backup could not be read. Both are preserved. Use Export data to inspect the current in-memory state; repair or move the state files before restarting. No new state will overwrite them."

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        if path.stat().st_size > 20_000_000:
            raise ValueError("State file exceeds the supported size.")
        return validate_state(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _atomic(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".exam-sprout-", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(payload)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, path)
            # Best-effort directory sync makes the rename durable on POSIX.
            if os.name != "nt":
                try:
                    handle = os.open(str(path.parent), os.O_RDONLY)
                    try:
                        os.fsync(handle)
                    finally:
                        os.close(handle)
                except OSError:
                    pass
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def replace(self, candidate: dict[str, Any]) -> None:
        if self.read_only:
            raise ValueError(self.warning or "Exam data is read-only.")
        checked = validate_state(candidate)
        payload = json.dumps(checked, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        if len(payload)>20_000_000:
            raise ValueError("Exam history exceeds the local safety size limit; export and remove old exams before saving more.")
        if self.path.exists():
            try:
                self._read(self.path)
                previous = self.path.read_bytes()
            except (OSError, ValueError, TypeError, KeyError):
                # Preserve invalid originals for diagnosis; do not poison backup.
                previous = None
                corrupt = self.path.with_suffix(".json.unreadable")
                if not corrupt.exists():
                    self._atomic(corrupt, self.path.read_bytes())
            if previous is not None:
                self._atomic(self.backup, previous)
        self._atomic(self.path, payload)
        self.state = checked

    def exams(self) -> list[Exam]:
        return [Exam.parse(x) for x in self.state["exams"]]

    def get_exam(self, eid: str) -> Exam:
        for e in self.exams():
            if e.id == eid:
                return e
        raise ValueError("That exam no longer exists. Reopen the planner.")

    def save_exam(self, data: dict[str, Any]) -> Exam:
        exam = Exam.parse(data)
        candidate = deepcopy(self.state)
        index = next((i for i, e in enumerate(candidate["exams"]) if e["id"] == exam.id), None)
        if index is None:
            candidate["exams"].append(exam.to_dict())
        else:
            candidate["exams"][index] = exam.to_dict()
        self.replace(candidate)
        return exam

    def delete_exam(self, eid: str) -> None:
        self.get_exam(eid)
        candidate = deepcopy(self.state)
        candidate["exams"] = [e for e in candidate["exams"] if e["id"] != eid]
        candidate["history"] = [h for h in candidate["history"] if h.get("exam_id") != eid]
        self.replace(candidate)

    def save_settings(self, settings: dict[str, Any]) -> None:
        candidate = deepcopy(self.state)
        candidate["settings"] = settings_from(settings)
        self.replace(candidate)

    def add_result(self, result: dict[str, Any]) -> None:
        candidate = deepcopy(self.state)
        candidate["history"] = [r for r in candidate["history"] if r.get("id") != result["id"]]
        candidate["history"].append(result)
        candidate["history"] = candidate["history"][-50:]
        self.replace(candidate)

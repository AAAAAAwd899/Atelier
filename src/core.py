"""Atelier's framework-independent, read-only model and validation helpers."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from .native_widgets import DEFAULT_WIDGETS, widget_layout, widget_note

VERSION = "1.0.3"
THEMES = (
    "obsidian", "glacier", "rose", "bloom", "linen", "matcha",
    "midnight", "peach", "forest", "tidal", "ember", "celestial",
    "castle", "underworld", "mythic", "cabin", "sunset-beach",
)
DEFAULTS = {
    "theme": "obsidian", "mode": "workspace", "density": "comfortable",
    "motion": True, "chrome": False, "view": "grid", "sort": "name",
    "review_style": "adaptive", "review_width": "standard", "surface_revision": 1,
    "shared_theme": True, "match_sprout": True, "native_surfaces": True, "visual_owner": "ask", "ambience": True,
    "review_context": "compact", "companion_shortcuts": False, "widget_mode": "balanced",
    "acknowledged_makeovers": [], "remote": {"enabled": False, "bindings": {}},
}
DEFAULT_PROFILE = {
    "favorites": [], "folders": [], "colors": {}, "last_location": "0",
    "studies": [], "focus_enabled": False, "selected_study": "all",
    "recent_locations": [], "last_studied": "0",
    "seen_decks": [], "seen_initialized": False, "recent_added": [],
    "native_note_types": [], "surfaces_version": 0,
    "home_layout": {"enabled": False, "columns": 3, "items": []},
    "native_widgets": copy.deepcopy(DEFAULT_WIDGETS), "native_widget_note": "",
    "widget_route_version": 0,
}
COLORS = ("violet", "blue", "rose", "green", "amber", "cyan")

class ValidationError(ValueError):
    """A safe, user-facing validation failure."""

class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        self.parts.append(data)

def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join("".join(parser.parts).split())

def json_for_html(value: Any) -> str:
    # Never let a deck name close a script tag or become an HTML entity.
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

def deck_id(value: Any, *, root: bool = False) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValidationError("Please choose a valid deck.")
    text = str(value)
    if not re.fullmatch(r"[0-9]{1,19}", text):
        raise ValidationError("Please choose a valid deck.")
    number = int(text)
    if number < (0 if root else 1) or number > 2**63 - 1:
        raise ValidationError("Please choose a valid deck.")
    return str(number)

def clean_label(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("Enter a name for this folder or deck.")
    value = unicodedata.normalize("NFC", value).strip()
    if not value:
        raise ValidationError("Enter a name for this folder or deck.")
    if len(value) > 120:
        raise ValidationError("Keep the name to 120 characters or fewer.")
    if "::" in value:
        raise ValidationError("Choose a location below instead of typing :: in the name.")
    if any(unicodedata.category(c) in ("Cc", "Cs") for c in value):
        raise ValidationError("The name contains an unsupported control character.")
    # Anki strips HTML from deck names. Reject it rather than silently changing a name.
    if "<" in value or ">" in value:
        raise ValidationError("Use a name without < or > characters.")
    if value.startswith(":") or value.endswith(":"):
        raise ValidationError("A name cannot start or end with a colon.")
    return value

def settings(value: Any) -> dict[str, Any]:
    out = copy.deepcopy(DEFAULTS)
    if not isinstance(value, dict):
        return out
    choices = {"widget_mode": ("balanced","original"), "visual_owner": ("ask", "atelier", "onigiri", "external"), "theme": THEMES, "mode": ("workspace", "hybrid", "native"),
               "density": ("comfortable", "compact"), "view": ("grid", "list"),
               "sort": ("name", "due", "recent"),
               "review_style": ("adaptive", "controls", "off"),
               "review_width": ("standard", "wide"), "review_context": ("compact", "full", "hidden")}
    for key, options in choices.items():
        if isinstance(value.get(key), str) and value[key] in options:
            out[key] = value[key]
    for key in ("motion", "chrome", "shared_theme", "match_sprout", "native_surfaces", "ambience", "companion_shortcuts"):
        if type(value.get(key)) is bool:
            out[key] = value[key]
    if isinstance(value.get("acknowledged_makeovers"), list):
        out["acknowledged_makeovers"] = sorted({x for x in value["acknowledged_makeovers"][:200]
            if isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", x)})
    # A single migration retires the experimental shared-home default. Explicit
    # choices made on 0.5.1 are then respected on every later visit.
    if value.get("surface_revision") != 1:
        out["mode"] = "workspace"
    # The old hybrid layout stacked two entire homepages. Migrate it to the
    # isolated workspace; the untouched original is now a one-click view.
    if out["mode"] == "hybrid":
        out["mode"] = "workspace"
    from .remote_model import settings as remote_settings
    out["remote"] = remote_settings(value.get("remote"))
    return out

def profile_settings(value: Any) -> dict[str, Any]:
    out = copy.deepcopy(DEFAULT_PROFILE)
    if not isinstance(value, dict):
        return out
    for key in ("favorites", "folders", "native_note_types"):
        if isinstance(value.get(key), list):
            seen: set[str] = set()
            for item in value[key][:20000]:
                try:
                    did = deck_id(item)
                    if did not in seen:
                        seen.add(did)
                        out[key].append(did)
                except ValidationError:
                    pass
    if isinstance(value.get("colors"), dict):
        for key, val in list(value["colors"].items())[:20000]:
            try:
                if val in COLORS:
                    out["colors"][deck_id(key)] = val
            except (ValidationError, TypeError):
                pass
    try:
        out["last_location"] = deck_id(value.get("last_location", "0"), root=True)
    except ValidationError:
        pass
    for key in ("focus_enabled", "seen_initialized"):
        if type(value.get(key)) is bool:
            out[key] = value[key]
    for key in ("recent_locations", "seen_decks"):
        if isinstance(value.get(key), list):
            limit = 32 if key == "recent_locations" else 100000
            seen = set()
            for item in value[key][:limit]:
                try:
                    did = deck_id(item)
                    if did not in seen:
                        seen.add(did)
                        out[key].append(did)
                except ValidationError:
                    pass
    try:
        out["last_studied"] = deck_id(value.get("last_studied", "0"), root=True)
    except ValidationError:
        pass
    selected = value.get("selected_study")
    if selected == "all" or isinstance(selected, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", selected):
        out["selected_study"] = selected
    if isinstance(value.get("studies"), list):
        seen = set()
        for raw in value["studies"][:24]:
            try:
                study = validate_study(raw)
                if study["id"] not in seen:
                    out["studies"].append(study)
                    seen.add(study["id"])
            except ValidationError:
                pass
    if isinstance(value.get("recent_added"), list):
        for raw in value["recent_added"][:32]:
            try:
                if not isinstance(raw, dict):
                    continue
                did = deck_id(raw.get("id"))
                when = str(raw.get("observed", ""))
                datetime.fromisoformat(when)
                out["recent_added"].append({"id": did, "observed": when})
            except (ValidationError, ValueError, TypeError):
                pass
    if type(value.get("surfaces_version")) is int:
        out["surfaces_version"] = max(0, min(1, value["surfaces_version"]))
    out["home_layout"] = home_layout(value.get("home_layout"))
    if type(value.get("widget_route_version")) is int:
        out["widget_route_version"] = max(0, min(1, value["widget_route_version"]))
    out["native_widgets"] = widget_layout(value.get("native_widgets"))
    out["native_widget_note"] = widget_note(value.get("native_widget_note", ""))
    return unique_active_studies(out)


def study_signature(study: dict) -> tuple[str, ...]:
    """The same deck selection is the same exam regardless of its label/order."""
    return tuple(sorted(set(study.get("deck_ids", []))))


def unique_active_studies(profile: dict, preferred: str | None = None) -> dict:
    seen: set[tuple[str, ...]] = set()
    ordered = sorted(profile["studies"], key=lambda s: s["id"] != preferred)
    for study in ordered:
        if not study["active"]:
            continue
        key = study_signature(study)
        if key in seen:
            study["active"] = False
        else:
            seen.add(key)
    if profile["selected_study"] not in ["all"] + [s["id"] for s in ordered if s["active"]]:
        profile["selected_study"] = "all"
    return profile


def upsert_study(profile: dict, value: dict, catalog: dict | None = None) -> dict:
    result = profile_settings(profile)
    candidate = validate_study(value)
    if catalog is not None:
        candidate = canonical_study(candidate, catalog, require_present=True)
        result = canonical_profile(result, catalog)
    others = [s for s in result["studies"] if s["id"] != candidate["id"]]
    if candidate["active"] and any(s["active"] and study_signature(s) == study_signature(candidate) for s in others):
        raise ValidationError("That folder selection is already an active exam. Open the existing exam to edit its name or date.")
    if len(others) >= 24:
        raise ValidationError("Your study shelf has 24 setups. Remove an old setup first.")
    result["studies"] = others + [candidate]
    result["focus_enabled"] = True
    return unique_active_studies(result, candidate["id"])



def canonical_study(study: dict, catalog: dict, *, require_present: bool = False) -> dict:
    """Parent selection already includes descendants; IDs remain strings throughout."""
    result = validate_study(study)
    ids = result["deck_ids"]
    if require_present and any(did not in catalog for did in ids):
        raise ValidationError("A selected deck is no longer available. Refresh and choose its replacement.")
    roots = []
    for did in ids:
        name = catalog.get(did, {}).get("name")
        if name and any(other != did and other in catalog and
                        name.startswith(catalog[other]["name"] + "::") for other in ids):
            continue
        roots.append(did)
    result["deck_ids"] = roots
    return result


def canonical_profile(profile: dict, catalog: dict) -> dict:
    result = profile_settings(profile)
    result["studies"] = [canonical_study(s, catalog) for s in result["studies"]]
    return unique_active_studies(result)


def validate_study(raw: Any) -> dict[str, Any]:
    """Local display scope only. Never creates a deck or reschedules a card."""
    if not isinstance(raw, dict):
        raise ValidationError("Enter a study name and choose its decks.")
    sid = raw.get("id")
    if not isinstance(sid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", sid):
        raise ValidationError("Invalid study identifier.")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValidationError("Give this study a name of 1–100 characters.")
    if any(unicodedata.category(c) in ("Cc", "Cs") for c in name):
        raise ValidationError("The study name contains unsupported characters.")
    when = raw.get("date", "")
    if not isinstance(when, str):
        raise ValidationError("Choose an exam date, or leave it blank.")
    if when:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
                raise ValueError()
            date.fromisoformat(when)
        except ValueError:
            raise ValidationError("Choose a valid exam date.")
    ids = raw.get("deck_ids")
    if not isinstance(ids, list) or not ids or len(ids) > 500:
        raise ValidationError("Choose between 1 and 500 folders or decks.")
    normalized = list(dict.fromkeys(deck_id(item) for item in ids))
    active = raw.get("active", True)
    if type(active) is not bool:
        raise ValidationError("Choose whether this study is active.")
    return {"id": sid, "name": name.strip(), "date": when,
            "deck_ids": normalized, "active": active}


def exam_label(path: str) -> str:
    """Disambiguate generic exam-folder names without renaming the deck."""
    parts = str(path).split("::")
    label = parts[-1]
    if len(parts) > 1 and re.match(r"^(exam|test|quiz|assessment|midterm|final)\b", label, re.I):
        label = parts[-2] + " · " + label
    return label[:100]


def quick_study(profile: dict, did: str, name: str, active: bool) -> dict:
    """Idempotent exam pin. Deactivation keeps dates/setup for one-click restore."""
    result = profile_settings(profile)
    did = deck_id(did)
    if type(active) is not bool:
        raise ValidationError("Choose active or inactive.")
    matches = [x for x in result["studies"] if x["deck_ids"] == [did]]
    if matches:
        # Old duplicate single-root definitions are never silently deleted.
        # Activating reuses one; deactivating clears all exact duplicates.
        preferred = next((x for x in matches if x["active"]), matches[0])
        for study in matches:
            study["active"] = active and study is preferred
    elif active:
        if len(result["studies"]) >= 24:
            raise ValidationError("Your study shelf has 24 setups. Remove an old setup in Manage studies first.")
        sid = "deck-" + did
        used = {x["id"] for x in result["studies"]}
        while sid in used:
            sid += "-x"
        result["studies"].append(validate_study({"id": sid, "name": name[:100],
            "date": "", "deck_ids": [did], "active": True}))
    if active:
        result["focus_enabled"] = True
    if result["selected_study"] not in ["all"] + [x["id"] for x in result["studies"] if x["active"]]:
        result["selected_study"] = "all"
    return result


def set_study_active(profile: dict, sid: str, active: bool) -> dict:
    result = profile_settings(profile)
    if type(active) is not bool:
        raise ValidationError("Choose active or inactive.")
    study = next((x for x in result["studies"] if x["id"] == sid), None)
    if study is None:
        raise ValidationError("That exam setup no longer exists.")
    study["active"] = active
    unique_active_studies(result, sid)
    if active:
        result["focus_enabled"] = True
    if result["selected_study"] == sid and not active:
        result["selected_study"] = "all"
    return result


def focus_roots(nodes: list[dict], deck_ids: list[str]) -> list[dict]:
    """Union of selected branches. A selected ancestor already includes a child.

    Uses stable IDs, not names. Missing/deleted IDs are ignored here and reported
    separately by the UI. Iterative traversal is bounded even on malformed trees.
    """
    lookup = {n["id"]: n for n in nodes}
    selected = {str(x) for x in deck_ids if str(x) in lookup}
    roots = []
    for did in selected:
        n = lookup[did]
        p = n.get("parent", "0")
        seen = {did}
        covered = False
        while p in lookup and p not in seen:
            if p in selected:
                covered = True
                break
            seen.add(p)
            p = lookup[p].get("parent", "0")
        if not covered:
            roots.append(n)
    return sorted(roots, key=lambda n: n["path"].casefold())


def observe_decks(profile: dict, nodes: list[dict], now: str | None = None) -> dict:
    """Track decks first seen *after* baseline; never infer import time from IDs."""
    result = profile_settings(profile)
    current = [n["id"] for n in nodes]
    known = set(result["seen_decks"])
    if result["seen_initialized"]:
        added = [x for x in current if x not in known]
        stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        result["recent_added"] = ([{"id": x, "observed": stamp} for x in reversed(added)] +
                                  result["recent_added"])[:32]
    result["seen_initialized"] = True
    result["seen_decks"] = list(dict.fromkeys(result["seen_decks"] + current))[-100000:]
    return result

class ProfileStore:
    """Local shortcuts only. Atomic writes and one previous valid snapshot.

    A malformed or externally changed file is not silently replaced. Recovery
    is explicit and preserves the damaged/current bytes before restoring.
    """
    LIMIT = 4_000_000

    def __init__(self, directory: Path, profile_path: str) -> None:
        digest = hashlib.sha256(os.path.normcase(os.path.abspath(profile_path)).encode()).hexdigest()[:24]
        self.path = directory / f"profile-{digest}.json"
        self.backup_path = self.path.with_suffix(".json.bak")
        self.damaged = False

    @classmethod
    def _load(cls, path: Path) -> tuple[bytes, dict]:
        with path.open("rb") as stream:
            raw = stream.read(cls.LIMIT + 1)
        if len(raw) > cls.LIMIT:
            raise ValueError("Oversized settings")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Settings must be a JSON object")
        return raw, profile_settings(value)

    @staticmethod
    def _atomic(path: Path, raw: bytes) -> None:
        fd, temp = tempfile.mkstemp(prefix=".atelier-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def read(self) -> dict[str, Any]:
        try:
            _, value = self._load(self.path)
            self.damaged = False
            return value
        except FileNotFoundError:
            # Loss of a primary file after a valid save is not a fresh install.
            self.damaged = self.backup_path.exists()
            return copy.deepcopy(DEFAULT_PROFILE)
        except (OSError, ValueError, TypeError, RecursionError):
            self.damaged = True
            return copy.deepcopy(DEFAULT_PROFILE)

    def write(self, data: dict[str, Any]) -> None:
        if self.damaged:
            raise ValidationError("Atelier's local shortcuts could not be read. Your cards are unaffected. Use Tools → Atelier → Restore previous shortcuts, or back up user_files before manual recovery.")
        raw = (json.dumps(profile_settings(data), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(raw) > self.LIMIT:
            raise ValidationError("The local shortcut file is too large to save safely.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        previous = None
        try:
            previous, _ = self._load(self.path)
        except FileNotFoundError:
            if self.backup_path.exists():
                self.damaged = True
                raise ValidationError("The shortcut file is missing, but its backup exists. Restore previous shortcuts before saving.")
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            self.damaged = True
            raise ValidationError("The shortcut file changed or became unreadable. It has not been overwritten; use Restore previous shortcuts.") from exc
        if previous == raw:
            return
        if previous is not None:
            # If backing up fails, stop BEFORE touching the valid primary file.
            self._atomic(self.backup_path, previous)
        self._atomic(self.path, raw)

    def restore_previous(self) -> dict[str, Any]:
        try:
            raw, value = self._load(self.backup_path)
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            raise ValidationError("No readable previous shortcut snapshot is available. No files were changed.") from exc
        if self.path.exists():
            # Keep a recovery copy, even if the current primary is malformed.
            with self.path.open("rb") as stream:
                current = stream.read(self.LIMIT + 1)
            if len(current) > self.LIMIT:
                raise ValidationError("The existing shortcut file is unusually large. Back it up manually before restoring.")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            recovery = self.path.with_name(self.path.stem + ".before-restore-" + stamp + ".json")
            self._atomic(recovery, current)
        self._atomic(self.path, raw)
        self.damaged = False
        return value

def _count(node: Any, name: str) -> int:
    return max(0, int(getattr(node, name, 0)))

def flatten_tree(tree: Any, names: dict[str, str]) -> list[dict[str, Any]]:
    """Iterative traversal handles deeply nested decks without recursion errors."""
    result = []
    stack = [(child, "0", "", 0) for child in reversed(list(tree.children))]
    seen: set[str] = set()
    while stack:
        node, parent, parent_path, depth = stack.pop()
        did = deck_id(node.deck_id)
        if did in seen:
            continue
        seen.add(did)
        path = names.get(did) or (f"{parent_path}::{node.name}" if parent_path else str(node.name))
        label = path.rsplit("::", 1)[-1]
        children = list(node.children)
        result.append({"id": did, "parent": parent, "name": label, "path": path,
                       "depth": depth, "children": [deck_id(c.deck_id) for c in children],
                       "new": _count(node, "new_count"), "learn": _count(node, "learn_count"),
                       "review": _count(node, "review_count"), "filtered": bool(getattr(node, "filtered", False))})
        stack.extend((child, did, path, depth + 1) for child in reversed(children))
    return result

def collection_snapshot(col: Any) -> dict[str, Any]:
    """Call only inside QueryOp. Reuses Anki's own scheduler counts, no SQL."""
    names = {str(item.id): item.name for item in col.decks.all_names_and_ids()}
    tree = col.sched.deck_due_tree()
    nodes = flatten_tree(tree, names)
    top = [n for n in nodes if n["parent"] == "0"]
    return {"nodes": nodes, "current": str(col.decks.get_current_id()),
            "totals": {k: sum(n[k] for n in top) for k in ("new", "learn", "review")},
            "studied": plain_text(col.studied_today())}

def fresh_catalog(col: Any) -> dict[str, dict[str, Any]]:
    # Two bulk name queries; no per-deck database round trips.
    regular = {str(d.id) for d in col.decks.all_names_and_ids(include_filtered=False)}
    return {str(d.id): {"name": d.name, "filtered": str(d.id) not in regular}
            for d in col.decks.all_names_and_ids()}

def _entry(catalog: dict, did: str) -> dict:
    if did not in catalog:
        raise ValidationError("That deck is no longer here. Refresh the workspace and try again.")
    return catalog[did]

def _unique(catalog: dict, name: str, excluding: str | None = None) -> None:
    canonical = unicodedata.normalize("NFC", name).casefold()
    if any(key != excluding and unicodedata.normalize("NFC", val["name"]).casefold() == canonical
           for key, val in catalog.items()):
        raise ValidationError("A deck with that name already exists in this location. Choose a different name; Atelier never merges decks automatically.")

def creation_path(catalog: dict, name: Any, parent: Any) -> str:
    label = clean_label(name)
    parent = deck_id(parent, root=True)
    prefix = ""
    if parent != "0":
        target = _entry(catalog, parent)
        if target["filtered"]:
            raise ValidationError("A filtered deck cannot be used as a folder.")
        prefix = target["name"] + "::"
    path = prefix + label
    _unique(catalog, path)
    return path

def rename_path(catalog: dict, did: Any, name: Any, expected: str | None = None) -> str:
    did = deck_id(did)
    entry = _entry(catalog, did)
    if expected is not None and entry["name"] != expected:
        raise ValidationError("This deck changed while the dialog was open. Refresh before renaming it.")
    label = clean_label(name)
    parent = entry["name"].rsplit("::", 1)[0] + "::" if "::" in entry["name"] else ""
    path = parent + label
    _unique(catalog, path, did)
    return path

def validate_move(catalog: dict, did: Any, parent: Any, expected: str | None = None) -> tuple[str, str]:
    did, parent = deck_id(did), deck_id(parent, root=True)
    source = _entry(catalog, did)
    if expected is not None and source["name"] != expected:
        raise ValidationError("This deck changed while the dialog was open. Refresh before moving it.")
    if source["filtered"]:
        raise ValidationError("Manage filtered decks in Anki's original view.")
    prefix = ""
    if parent != "0":
        target = _entry(catalog, parent)
        if target["filtered"]:
            raise ValidationError("A filtered deck cannot be used as a folder.")
        sp, tp = source["name"].casefold(), target["name"].casefold()
        if did == parent or tp.startswith(sp + "::"):
            raise ValidationError("A folder cannot go inside itself or one of its own subfolders.")
        prefix = target["name"] + "::"
    new_path = prefix + source["name"].rsplit("::", 1)[-1]
    _unique(catalog, new_path, did)
    return did, parent


def home_layout(raw: Any, *, strict: bool = False) -> dict[str, Any]:
    """Local, reversible presentation preferences. Never store HTML or callbacks."""
    default = {"enabled": False, "columns": 3, "items": []}
    if raw is None:
        return default
    if not isinstance(raw, dict):
        if strict: raise ValidationError("Invalid home layout.")
        return default
    valid = type(raw.get("enabled", False)) is bool and type(raw.get("columns", 3)) is int and raw.get("columns", 3) in (1, 2, 3, 4)
    items = raw.get("items", [])
    valid = valid and isinstance(items, list) and len(items) <= 40
    if not valid:
        if strict: raise ValidationError("Choose 1–4 columns and up to 40 widgets.")
        return default
    result = {"enabled": raw.get("enabled", False), "columns": raw.get("columns", 3), "items": []}
    seen = set()
    for item in items:
        ok = isinstance(item, dict)
        key = item.get("id") if ok else None
        ok = ok and isinstance(key, str) and bool(re.fullmatch(r"[a-zA-Z0-9_:.~-]{1,160}", key)) and key not in seen
        ok = ok and type(item.get("visible", True)) is bool and item.get("size", "wide") in ("small", "wide", "full") and item.get("height", "auto") in ("auto", "short", "tall")
        if not ok:
            if strict: raise ValidationError("That widget layout contains an invalid or duplicate item.")
            continue
        seen.add(key)
        result["items"].append({"id": key, "visible": item.get("visible", True), "size": item.get("size", "wide"), "height": item.get("height", "auto")})
    return result

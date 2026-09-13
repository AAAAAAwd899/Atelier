"""Reversible registration and read-only duplicate-install checks.

No add-on is enabled, disabled, deleted, imported, or migrated by this module.
"""
from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

LOG = logging.getLogger("atelier.lifecycle")
PACKAGE = "daedalus_atelier"


class StartupBlocked(RuntimeError):
    """A clear, recoverable reason for not registering this copy."""


class Registration:
    def __init__(self) -> None:
        self._undo: list[Callable[[], Any]] = []

    def cleanup(self, action: Callable[[], Any]) -> None:
        self._undo.append(action)

    def hook(self, collection: Any, callback: Callable[..., Any]) -> None:
        collection.append(callback)
        self.cleanup(lambda: collection.remove(callback))

    def rollback(self) -> None:
        for action in reversed(self._undo):
            try:
                action()
            except Exception:
                LOG.warning("An Atelier registration cleanup was unavailable")
        self._undo.clear()


def check_duplicates(manager: Any, own: str) -> list[str]:
    """Recognize enabled copies by manifest identity, not just a similar title.

    This supports the private package → numeric AnkiWeb-package transition.
    The user resolves duplicates by disabling one and restarting. No content
    or settings from the other installation are loaded or changed.
    """
    duplicates: list[str] = []
    if not callable(getattr(manager, "all_addon_meta", None)) or not callable(getattr(manager, "addonsFolder", None)):
        return duplicates
    try:
        entries = list(manager.all_addon_meta())[:500]
    except Exception:
        return duplicates
    for meta in entries:
        package = str(getattr(meta, "dir_name", ""))
        if package == own or not getattr(meta, "enabled", False) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", package) or package in (".", ".."):
            continue
        try:
            root = Path(manager.addonsFolder()).resolve()
            directory = Path(manager.addonsFolder(package)).resolve()
            if directory.parent != root:
                continue
            manifest = directory / "manifest.json"
            with manifest.open("rb") as stream:
                data = stream.read(16385)
            if len(data) > 16384:
                continue
            info = json.loads(data)
            if isinstance(info, dict) and info.get("package") == PACKAGE and (directory / "__init__.py").is_file():
                duplicates.append(package)
        except (OSError, ValueError, TypeError, RecursionError):
            continue
    return sorted(set(duplicates))

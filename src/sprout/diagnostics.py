"""Bounded local diagnostics; never write add-on errors to Anki's stderr UI.

Only the exam_sprout logger is isolated. We do not replace sys.excepthook,
Qt's event dispatcher, or any other add-on's logging/error handling.
"""
from __future__ import annotations
from collections import deque
from datetime import datetime
import logging
from pathlib import Path
import platform
import threading
import time


class LocalDiagnostics(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.records: deque[str] = deque(maxlen=40)
        self.path: Path | None = None
        self._last_key = ""
        self._last_at = 0.0
        self._lock = threading.RLock()
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    def use_profile(self, folder: str | Path | None) -> None:
        with self._lock:
            self.path = Path(folder) / "exam_sprout" / "diagnostics.log" if folder else None
            self._last_key = ""
            self._last_at = 0.0
            self.records.clear()

    def emit(self, record: logging.LogRecord) -> None:
        # Handler failures must not fall back to stderr / another modal popup.
        try:
            text = self.format(record)[-18000:]
            key = record.getMessage() + (str(record.exc_info[1]) if record.exc_info else "")
            with self._lock:
                now = time.monotonic()
                if key == self._last_key and now - self._last_at < 5:
                    return
                self._last_key, self._last_at = key, now
                self.records.append(text)
                if self.path is not None:
                    try:
                        self.path.parent.mkdir(parents=True, exist_ok=True)
                        if self.path.exists() and self.path.stat().st_size > 120_000:
                            self.path.replace(self.path.with_suffix(".log.1"))
                        with self.path.open("a", encoding="utf-8") as output:
                            output.write(text + "\n\n")
                    except OSError:
                        pass  # In-memory diagnostics still work on read-only drives.
        except Exception:
            pass

    def report(self, include_earlier: bool = False) -> str:
        with self._lock:
            if include_earlier and self.path is not None:
                try:
                    with self.path.open("rb") as source:
                        source.seek(max(0, self.path.stat().st_size - 80_000))
                        return source.read(80_000).decode("utf-8", errors="replace")
                except OSError:
                    pass
            return "\n\n".join(self.records) or "No Exam Sprout errors have been recorded in this session."


DIAGNOSTICS = LocalDiagnostics()
LOG = logging.getLogger("exam_sprout")
LOG.setLevel(logging.WARNING)
LOG.propagate = False
if not any(isinstance(handler, LocalDiagnostics) for handler in LOG.handlers):
    LOG.addHandler(DIAGNOSTICS)


def show_diagnostics(parent) -> None:
    """Independent native window: no webview, no custom Qt event override."""
    import anki
    from aqt.qt import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QApplication, QCheckBox
    from .core import VERSION
    dialog = getattr(parent, "_exam_sprout_diagnostics", None)
    if dialog is not None:
        try:
            dialog.show(); dialog.raise_(); dialog.activateWindow()
            return
        except RuntimeError:
            pass
    dialog = QDialog(parent)
    dialog.setWindowTitle("Exam Sprout · Diagnostics")
    dialog.resize(760, 500)
    layout = QVBoxLayout(dialog)
    label = QLabel("Local technical details. Review before sharing: file paths may include your username.\nCard contents and typed practice answers are not collected.", dialog)
    label.setWordWrap(True)
    layout.addWidget(label)
    text = QPlainTextEdit(dialog)
    text.setReadOnly(True)
    layout.addWidget(text, 1)
    earlier = QCheckBox("Include earlier runs (may include errors from old builds)", dialog)
    layout.addWidget(earlier)
    def refresh():
        header = f"Exam Sprout {VERSION}\nAnki {getattr(anki, 'version', 'unknown')}\n{platform.system()} · Python {platform.python_version()}\nCaptured {datetime.now().isoformat(timespec='seconds')}\nCurrent-session errors unless the earlier-runs option is checked.\n\n"
        text.setPlainText(header + DIAGNOSTICS.report(earlier.isChecked()))
    earlier.toggled.connect(lambda _: refresh())
    row = QHBoxLayout()
    refresh_button = QPushButton("Refresh", dialog)
    refresh_button.clicked.connect(lambda _=False: refresh())
    copy_button = QPushButton("Copy details", dialog)
    copy_button.clicked.connect(lambda _=False: QApplication.clipboard().setText(text.toPlainText()))
    close_button = QPushButton("Close", dialog)
    close_button.clicked.connect(lambda _=False: dialog.close())
    for button in (refresh_button, copy_button, close_button):
        button.setAutoDefault(False)
    row.addWidget(refresh_button); row.addWidget(copy_button); row.addStretch(1); row.addWidget(close_button)
    layout.addLayout(row)
    refresh()
    parent._exam_sprout_diagnostics = dialog  # Keep the modeless Python wrapper alive.
    dialog.show()

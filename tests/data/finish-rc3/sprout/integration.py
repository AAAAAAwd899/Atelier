"""Anki integration through additive hooks and serialized read-only queries."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import aqt
from aqt import gui_hooks
from aqt.deckbrowser import DeckBrowser
from aqt.operations import QueryOp
from aqt.qt import QDialog, QVBoxLayout, QHBoxLayout, Qt, QAction, QFileDialog, QPushButton, QLabel, QWidget, QTimer
from aqt.utils import askUser, showWarning, tooltip
from aqt.webview import AnkiWebView
from aqt.theme import theme_manager

from .collection_reader import deck_list, read_snapshot
from .evidence import read_exam_snapshot
from .readiness import readiness
from .exam_engine import sample_exam, item_priority, note_history
from .new_learning import available as native_learning_available
from .progress import PipProgress
from .drafts import draft_summary, load_draft, discard_draft
from .core import VERSION, CardInfo, Exam, bounded_int, finite_weight, plan_exam, sample_cards, suggest_decks, MAX_QUESTIONS, MAX_SESSION_MINUTES
from .storage import Store
from .widget import countdown_html
from .session_tools import needs_focus_session, practice_weights, sampling_coverage, review_items, growth_signal, named_sample_warnings
from .answers import clean_responses, load_answers, save_answers, clear_answers, remove_answers

from .diagnostics import LOG, DIAGNOSTICS, show_diagnostics
CONTROLLER = None
PREFIX = "exam-sprout:"


class Controller:
    def __init__(self, mw, suite=None, register=None):
        self.mw = mw
        self.suite = suite
        self._register = register or (lambda hook, fn: hook.append(fn))
        self.store: Store | None = None
        self.dialog: PlannerDialog | None = None
        self.runner = None
        self.package = mw.addonManager.addonFromModule(__name__)
        self.asset_base = f"/_addons/{self.package}/" + ("sprout/web" if suite is not None else "web")
        # The original profile-local Store paths are deliberately unchanged.
        if suite is not None:
            from . import widget
            widget.SPROUT_SVG = widget.SPROUT_SVG.replace("/_addons/exam_sprout/web", self.asset_base)
        self.epoch = 0
        self._opening = False
        self.responses = {}
        self.growth_cache = {}
        self.active_exam_id = ""
        self.companion = None
        self.progress = None
        if suite is None:
            mw.addonManager.setWebExports(__name__, r"web/.*\.(css|js|svg|png|webp|json)$")
        self.menu_action = QAction("Exam Studio · plans & readiness…" if suite is not None else "Exam Sprout…", mw)
        self.menu_action.triggered.connect(lambda _checked=False: self.open())
        (suite.menu if suite is not None else mw.form.menuTools).addAction(self.menu_action)
        self.diagnostics_action = QAction("Exam Sprout diagnostics…", mw)
        self.diagnostics_action.triggered.connect(lambda _checked=False: self.diagnostics())
        (suite.menu if suite is not None else mw.form.menuTools).addAction(self.diagnostics_action)

    def profile_open(self, *args) -> None:
        self.epoch += 1
        self.responses.clear(); self.growth_cache.clear()
        self.active_exam_id = ""
        try:
            DIAGNOSTICS.use_profile(self.mw.pm.profileFolder())
            self.store = Store(self.mw.pm.profileFolder())
            self.progress = PipProgress(self.store)
        except Exception:
            LOG.exception("Cannot open profile-local Exam Sprout state")
            self.store = None
        self.menu_action.setEnabled(self.store is not None)

    def profile_close(self, *args) -> None:
        self.epoch += 1
        if self.runner is not None:
            self.runner.force_close()
            self.runner = None
        if self.dialog is not None:
            self.dialog.force_close()
            self.dialog = None
        self.store = None
        self.progress = None
        self.responses.clear(); self.growth_cache.clear()
        if self.companion is not None: self.companion.cleanup()
        self.menu_action.setEnabled(False)

    def temporary_close(self, *args) -> None:
        # Full-sync and similar operations may close the collection while the
        # profile remains open. Invalidate every in-flight callback.
        self.epoch += 1
        if self.companion is not None: self.companion.cleanup()
        if self.runner:
            self.runner.force_close()
            self.runner = None
        if self.dialog:
            self.dialog.force_close()
            self.dialog = None

    def state_changed(self, new, old="") -> None:
        if self.companion is not None: self.companion.state_changed(new, old)

    def install_companion(self) -> None:
        try:
            from .companion import ReviewerCompanion
            self.companion = ReviewerCompanion(self)
            action = QAction("Show Pip in reviewer", self.mw)
            action.triggered.connect(lambda _=False: self.show_pip())
            (self.suite.menu if self.suite is not None else self.mw.form.menuTools).addAction(action)
            self.pip_menu_action = action
            self._register(gui_hooks.state_did_change, self.state_changed)
        except Exception:
            LOG.exception("Pip companion is unavailable; study functions are unchanged")

    def pip_signal(self):
        progress = getattr(self, "progress", None)
        return progress.signal() if progress is not None else {"score":0,"stage":1,"label":"Just planted","points":0,"kind":"effort"}

    def record_effort(self, note_ids):
        try:
            if self.progress is not None:
                self.progress.record(note_ids)
                value = self.progress.signal()
                for key in list(self.growth_cache): self.growth_cache[key] = value
        except Exception:
            LOG.exception("Pip effort could not be saved; card studying is unchanged")

    def after_native_answer(self, reviewer, card, ease):
        try:
            if self.store is not None and ease in (1,2,3,4):
                self.record_effort([int(card.nid)])
                if self.dialog is not None:
                    self.dialog.pending_sample = None
        except Exception:
            LOG.exception("Pip effort hook skipped; Anki reviewing is unchanged")

    def show_pip(self) -> None:
        if self.companion is not None:
            self.companion.dismissed = False
            if self.store:
                self.store.save_settings({**self.store.state["settings"], "show_pip": True, "reviewer_pip": True})
            self.state_changed(self.mw.state)

    def diagnostics(self) -> None:
        try:
            show_diagnostics(self.dialog or self.mw)
        except Exception:
            LOG.exception("Could not open native diagnostics")

    def open(self, exam_id: str = "") -> None:
        # Reentrant clicks must not construct another half-initialized window.
        if self._opening:
            return
        self._opening = True
        try:
            self._open_planner(exam_id)
        except Exception:
            LOG.exception("Could not open the exam planner")
            if self.dialog is not None:
                try:
                    self.dialog.force_close()
                except Exception:
                    LOG.exception("Could not clean up a failed planner window")
                finally:
                    self.dialog = None
            tooltip("Exam Sprout could not open. Details are in Tools → Atelier → Exam Sprout diagnostics.", parent=self.mw)
        finally:
            self._opening = False

    def _open_planner(self, exam_id: str = "") -> None:
        if not self.mw.col:
            return
        if self.mw.state == "review":
            tooltip("Return to Decks first. Exam Sprout will not interrupt your current review.", parent=self.mw)
            return
        if self.store is None:
            self.profile_open()
        if self.store is None:
            tooltip("Exam Sprout could not open its local data folder. See Tools → Atelier → Exam Sprout diagnostics. Your collection was not changed.", parent=self.mw)
            return
        if self.runner:
            self.runner.raise_()
            self.runner.activateWindow()
            return
        if self.dialog and not self.dialog.closed:
            self.dialog.raise_()
            self.dialog.activateWindow()
            if exam_id:
                self.dialog.emit_ui_event("select", {"id": exam_id})
            return
        self.dialog = PlannerDialog(self, exam_id)
        self.dialog.show()
        if hasattr(self.dialog, "showMaximized"): self.dialog.showMaximized()
        self.dialog.load_page()

    def refresh_home(self) -> None:
        if self.mw.col and self.mw.state == "deckBrowser":
            try:
                self.mw.deckBrowser.refresh()
                self.mw.toolbar.draw()
                # Atelier attaches its toolbar palette on the redraw hook.
                self.mw.toolbar.redraw()
            except Exception:
                LOG.exception("Could not refresh the home countdown")

    def render_countdowns(self, deck_browser, content) -> None:
        try:
            if self.store is not None:
                content.stats = countdown_html(self.store) + content.stats
        except Exception:
            # A broken countdown must not break the deck list or reviewer.
            LOG.exception("Countdown rendering skipped")

    def web_assets(self, web_content, context) -> None:
        if isinstance(context, DeckBrowser):
            for target, asset in ((web_content.css, "/countdown.css"), (web_content.js, "/countdown.js")):
                path = self.asset_base + asset
                if path not in target:
                    target.append(path)

    def home_rendered(self, deck_browser) -> None:
        if self.mw.col and self.mw.state == "deckBrowser" and deck_browser is self.mw.deckBrowser:
            try:
                html = json.dumps(countdown_html(self.store) if self.store is not None else "")
                deck_browser.web.eval(
                    f"(function(){{const html={html};if(html&&!document.getElementById('es-countdowns')){{const wrap=document.createElement('div');wrap.innerHTML=html;const node=wrap.firstElementChild;if(node)(document.body||document.documentElement).appendChild(node);}}window.ExamSproutCountdown&&window.ExamSproutCountdown.mount();}})();"
                )
            except Exception:
                LOG.exception("Could not mount the home countdown")

    def web_message(self, handled, message: str, context):
        if handled[0] or not isinstance(context, DeckBrowser):
            return handled
        if context is not self.mw.deckBrowser or self.mw.state != "deckBrowser" or not self.mw.col:
            return handled
        if message.startswith(PREFIX + "open:"):
            self.open(message[len(PREFIX + "open:"):][:64])
            return (True, None)
        return handled

    def toolbar(self, links, toolbar) -> None:
        if self.store is None or self.store.state["settings"]["show_toolbar"]:
            links.append(toolbar.create_link("exam_sprout_open", "Exams", lambda: self.open(), tip="Exam countdowns and study plans", id="exam-sprout-nav"))


class PlannerDialog(QDialog):
    def __init__(self, controller: Controller, initial_exam: str):
        super().__init__(controller.mw)
        self.controller = controller
        self.mw = controller.mw
        self.store = controller.store
        self.initial_exam = initial_exam
        self.epoch = controller.epoch
        self._collection = self.mw.col
        self.closed = False
        self._closing = False
        self._load_rid = None
        self.web = None
        self.dirty = False
        self.forced = False
        self.pending_sample = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("Atelier · Exam Studio" if controller.suite is not None else "Exam Sprout")
        self.resize(1020, 780)
        self.setMinimumSize(560, 460)
        self.setWindowModality(getattr(Qt.WindowModality, "NonModal", Qt.WindowModality.WindowModal))
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(0, 0, 0, 0)
        self.layout_box.setSpacing(0)
        # These are native controls, not part of the web page. A page failure
        # cannot remove the Close or Diagnostics buttons.
        self.native_bar = QWidget(self)
        bar = QHBoxLayout(self.native_bar)
        bar.setContentsMargins(12, 7, 12, 7)
        self.status_label = QLabel("Opening your exam space…", self.native_bar)
        self.status_label.setWordWrap(True)
        bar.addWidget(self.status_label, 1)
        diagnostics = QPushButton("Diagnostics", self.native_bar)
        diagnostics.setAutoDefault(False)
        diagnostics.clicked.connect(lambda _=False: controller.diagnostics())
        close = QPushButton("Close", self.native_bar)
        close.setAutoDefault(False)
        close.clicked.connect(lambda _=False: self.close())
        bar.addWidget(diagnostics)
        bar.addWidget(close)
        self.layout_box.addWidget(self.native_bar)
        self.open_timer = QTimer(self)
        self.open_timer.setSingleShot(True)
        self.open_timer.timeout.connect(self._opening_slow)

    def load_page(self) -> None:
        if self.closed or self.web is not None:
            return
        try:
            self.web = AnkiWebView(self)
            self.layout_box.insertWidget(0, self.web, 1)
            self.web.set_bridge_command(self.bridge, self)
            self.web.loadFinished.connect(self._page_loaded)
            base = self.controller.asset_base
            self.open_timer.start(20000)
            self.web.stdHtml('<main id="es-app" aria-label="Exam Sprout"><div class="es-loading">Opening your exam space…</div></main>',
                             css=[base + "/app.css", base + "/countdown.css", base + "/pip.css"], js=[base + "/countdown.js", base + "/pip-scene.js", base + "/pip.js", base + "/app.js"], context=self)
        except Exception:
            LOG.exception("Planner page initialization failed")
            self.open_timer.stop()
            self.status_label.setText("The planner could not load. Close remains available; Diagnostics has the details.")

    def _page_loaded(self, ok: bool) -> None:
        if not self.valid():
            return
        if not ok:
            self.open_timer.stop()
            LOG.warning("Planner web page failed to load")
            self.status_label.setText("The page could not load. Close this window or open Diagnostics.")

    def _opening_slow(self) -> None:
        if self.valid():
            self.status_label.setText("Still waiting for Anki. You can close this window safely or check Diagnostics.")


    def valid(self) -> bool:
        return not self.closed and self.mw.col is self._collection and self.mw.col is not None and self.controller.epoch == self.epoch and self.controller.store is self.store

    def send(self, rid: str, payload: Any = None, error: str | None = None) -> None:
        if self.valid() and self.web is not None:
            try:
                data = json.dumps({"id": rid, "data": payload, "error": error}, ensure_ascii=True, allow_nan=False)
                self.web.eval(f"window.ExamSprout && window.ExamSprout.receive({data});")
                if rid == self._load_rid:
                    self.open_timer.stop()
                    self.status_label.setText("Could not load exam data. See Diagnostics." if error else "Focus practice leaves card schedules unchanged. Normal Study uses Anki’s reviewer.")
            except Exception:
                LOG.exception("Could not deliver a planner response")

    def emit_ui_event(self, name: str, payload: Any) -> None:
        # Never name this 'event': QDialog inherits QObject.event(QEvent).
        # An incompatible override causes a new error for every Qt window event.
        if self.valid() and self.web is not None:
            try:
                self.web.eval(f"window.ExamSprout && window.ExamSprout.event({json.dumps(name)}, {json.dumps(payload, ensure_ascii=True)});")
            except Exception:
                LOG.exception("Could not deliver a planner notification")

    def query(self, rid: str, operation, transform=lambda x: x) -> None:
        def guarded_operation(col):
            # Do not read a newly opened profile for a request from an old one.
            if (self.closed or self.controller.epoch != self.epoch
                    or col is not self._collection or self.controller.store is not self.store):
                raise ValueError("This planner was closed. Reopen it from the current profile.")
            return operation(col)
        try:
            # No progress-dialog stacking. The planner supplies inline feedback.
            # Parent the operation to mw, which outlives a dismissed planner.
            QueryOp(parent=self.mw, op=guarded_operation,
                    success=lambda result: self._query_success(rid, result, transform)).failure(
                lambda error: self._query_failure(rid, error)
            ).run_in_background()
        except Exception as exc:
            self._query_failure(rid, exc)

    def _query_failure(self, rid: str, error: Exception) -> None:
        if not self.valid():
            return
        LOG.warning("Planner query failed: %s", error)
        self.send(rid, error=str(error))

    def _query_success(self, rid: str, result, transform) -> None:
        if not self.valid():
            return
        try:
            self.send(rid, transform(result))
        except Exception as exc:
            LOG.exception("Exam Sprout result processing failed")
            self.send(rid, error=str(exc))

    def bridge(self, message: str):
        if not message.startswith(PREFIX) or not self.valid():
            return None
        if len(message) > 250_000:
            return None
        rid = ""
        try:
            request = json.loads(message[len(PREFIX):])
            rid = str(request.get("id", ""))[:80]
            action = request.get("action")
            payload = request.get("payload", {})
            if not isinstance(payload, dict):
                raise ValueError("Invalid request.")
            if action == "load":
                self._load_rid = rid
                state = deepcopy(self.store.state)
                self.query(rid, deck_list, lambda decks: {"state": state, "decks": decks, "version": VERSION, "asset_base": self.controller.asset_base, "night": bool(theme_manager.night_mode), "initial_exam": self.initial_exam, "suite": self.controller.suite is not None, "draft": draft_summary(self.store), "pip_growth": self.controller.pip_signal(), "warning": self.store.warning, "read_only": self.store.read_only, "countdown_html": countdown_html(self.store, preview=True)})
            elif action == "plan":
                exam = self.store.get_exam(str(payload["id"]))
                history = deepcopy(self.store.state["history"])
                self.query(rid, lambda col: read_exam_snapshot(col, exam, history), lambda snap: self._plan_payload(exam, snap))
            elif action == "suggest":
                topics = str(payload.get("topics", ""))[:3000]
                self.query(rid, deck_list, lambda decks: {"ids": suggest_decks(topics, decks)})
            elif action == "save_exam":
                exam = Exam.parse(payload)
                history = deepcopy(self.store.state["history"])
                # Validate search syntax and mappings before persisting.
                self.query(rid, lambda col: read_exam_snapshot(col, exam, history), lambda snap: self._save_valid_exam(exam, snap))
            elif action == "archive_exam":
                exam = self.store.get_exam(str(payload["id"]))
                archived = payload.get("archived")
                if type(archived) is not bool:
                    raise ValueError("Archived must be true or false.")
                self.store.save_exam({**exam.to_dict(), "archived": archived})
                self.pending_sample = None
                self.send(rid, {"state": self.store.state, "countdown_html": countdown_html(self.store, preview=True)})
                self.controller.refresh_home()
            elif action == "delete_exam":
                eid = str(payload["id"])
                result_ids = {r["id"] for r in self.store.state["history"] if r.get("exam_id") == eid}
                self.store.delete_exam(eid)
                try:
                    saved = load_draft(self.store)
                    if saved is not None and saved.exam_id == eid: discard_draft(self.store)
                except (ValueError, OSError, TypeError, KeyError):
                    LOG.exception("Saved draft could not be removed; use Discard saved exam to remove it explicitly")
                for result_id in result_ids:
                    self.controller.responses.pop(result_id, None)
                try:
                    remove_answers(self.store, result_ids)
                except OSError:
                    LOG.exception("Deleted exam but could not erase its optional saved answers")
                    self.emit_ui_event("error", {"message": "Exam deleted. Saved written answers could not be removed; check folder permissions."})
                self.controller.growth_cache.pop(eid, None)
                if self.controller.active_exam_id == eid:
                    self.controller.active_exam_id = ""
                self.pending_sample = None
                self.send(rid, {"state": self.store.state, "countdown_html": countdown_html(self.store, preview=True)})
                self.controller.refresh_home()
            elif action == "settings":
                self.store.save_settings(payload)
                if not self.store.state["settings"].get("remember_answers"): clear_answers(self.store)
                self.controller.state_changed(self.mw.state)
                self.send(rid, {"state": self.store.state, "countdown_html": countdown_html(self.store, preview=True)})
                self.controller.refresh_home()
            elif action == "suite_theme":
                suite = self.controller.suite
                if suite is None or suite.get_config().get("visual_owner") != "atelier":
                    raise ValueError("The current visual owner controls the appearance.")
                from ..core import THEMES
                theme = payload.get("theme")
                if theme not in THEMES:
                    raise ValueError("Choose a valid world.")
                cfg = suite.save_config({"theme": theme})
                self.send(rid, {"theme": cfg["theme"]})
            elif action == "suite_native":
                if self.controller.suite is None:
                    raise ValueError("This action requires the unified suite.")
                from ..native_tools import dispatch as native_dispatch
                native_dispatch(self.mw, payload.get("command"))
                self.send(rid, {"opened": True})
            elif action == "suite_focus":
                if self.controller.suite is None:
                    raise ValueError("This action requires the unified suite.")
                from ..suite import focus_exam
                result = focus_exam(self.controller.suite, str(payload.get("id", "")))
                self.send(rid, result)
                self.controller.refresh_home()
            elif action == "dirty":
                self.dirty = bool(payload.get("value", False))
                self.send(rid, {})
            elif action == "prepare":
                self._prepare(rid, payload)
            elif action == "start":
                self._start(rid, payload)
            elif action == "pip_study":
                self._pip_study(rid, payload)
            elif action == "resume_exam":
                self._resume_exam(rid)
            elif action == "discard_draft":
                discard_draft(self.store); self.send(rid, {"discarded": True})
            elif action == "export_result":
                self._export_result(rid, payload)
            elif action == "study":
                self._study(rid, payload)
            elif action == "focus":
                self._focus(rid, payload)
            elif action == "review_misses":
                self._review_misses(rid, payload)
            elif action == "back_to_anki":
                self.send(rid, {})
                if self.close() and self.controller.suite is not None and self.mw.col:
                    self.controller.suite._ui_state = {"page": "desk"}
                    self.controller.suite.open()
            elif action == "browse":
                self._browse(rid, payload)
            elif action == "export":
                self._export(rid)
            else:
                raise ValueError("Unsupported Exam Sprout action.")
        except Exception as exc:
            LOG.exception("Exam Sprout request failed")
            self.send(rid, error=str(exc))
        return None

    def _plan_payload(self, exam, snapshot):
        growth = self.controller.pip_signal()
        self.controller.growth_cache[exam.id] = growth
        self.controller.active_exam_id = exam.id
        estimate = readiness(exam, snapshot)
        return {"plan": {**plan_exam(exam, snapshot.stats), "growth": growth, "readiness": estimate},
                "warnings": snapshot.warnings, "draft": draft_summary(self.store)}

    def _save_valid_exam(self, exam, snapshot):
        missing = [s.name for s in snapshot.stats.values() if s.missing]
        if missing:
            raise ValueError("Remove or re-select missing decks before saving: " + ", ".join(missing))
        self.store.save_exam(exam.to_dict())
        self.dirty = False
        self.pending_sample = None
        self.controller.refresh_home()
        return {"state": self.store.state, "countdown_html": countdown_html(self.store, preview=True), "exam_id": exam.id, **self._plan_payload(exam, snapshot)}

    def _prepare(self, rid, payload):
        exam = self.store.get_exam(str(payload["id"]))
        size = bounded_int(payload.get("size", 50), 1, MAX_QUESTIONS, "Practice cards")
        minutes = bounded_int(payload.get("minutes", 0), 0, MAX_SESSION_MINUTES, "Time limit")
        kind = payload.get("kind", "exam")
        weighting = payload.get("weighting", "emphasis")
        if kind not in ("exam", "practice") or weighting not in ("emphasis", "equal", "size", "custom"):
            raise ValueError("Choose a supported practice mode and weighting.")
        options = {k: payload.get(k, default) for k, default in (("one_per_note", True), ("ensure_coverage", True), ("include_new", True), ("include_suspended", False), ("include_buried", False), ("cold_only", False))}
        if any(type(v) is not bool for v in options.values()):
            raise ValueError("Practice options must be true or false.")
        raw_weights = payload.get("weights", {})
        if not isinstance(raw_weights, dict):
            raise ValueError("Invalid practice weights.")
        custom = {s.deck_id: finite_weight(raw_weights.get(str(s.deck_id), s.weight)) for s in exam.scopes}
        self.pending_sample = None
        strategy = payload.get("strategy", "representative")

        def finish(snap):
            cards = [c for c in snap.cards if options["include_new"] or not c.is_new]
            result, cards = sample_exam(exam, snap, size, weighting=weighting, custom=custom,
                strategy=strategy, include_new=options["include_new"], one_per_note=options["one_per_note"],
                ensure_coverage=options["ensure_coverage"], cold_only=options["cold_only"])
            if not result.cards:
                raise ValueError("No eligible cards match these settings. Check the deck selections, filter, zero weights, and inclusion options.")
            token = uuid4().hex
            self.pending_sample = (token, exam, result, kind, minutes)
            self._pending_options = self._session_options(result.cards, snap, strategy)
            names = {s.deck_id: s.name for s in snap.stats.values()}
            return {"token": token, "requested": size, "actual": len(result.cards), "available": result.available,
                    "kind": kind, "minutes": minutes, "strategy": strategy, "warnings": snap.warnings + named_sample_warnings(result.warnings, snap.stats),
                    "coverage": sampling_coverage(exam, snap, cards, result.counts),
                    "counts": [{"name": names.get(k, str(k)), "count": v} for k, v in result.counts.items()]}
        self.query(rid, lambda col: read_exam_snapshot(col, exam, deepcopy(self.store.state["history"]), options["include_suspended"], options["include_buried"]), finish)

    def _start(self, rid, payload):
        if not self.pending_sample or payload.get("token") != self.pending_sample[0]:
            raise ValueError("This practice preview expired. Build a fresh one.")
        if self.controller.runner:
            raise ValueError("A practice session is already open.")
        if self.mw.state == "review":
            raise ValueError("Return to Decks before starting a separate practice session.")
        from .runner import ExamRunner
        _, exam, sample, kind, minutes = self.pending_sample
        self.pending_sample = None
        runner = ExamRunner(self.controller, exam, sample.cards, kind, minutes, self._runner_finished)
        self._configure_runner(runner, getattr(self, "_pending_options", {}))
        self.controller.runner = runner
        try:
            runner.open()
        except Exception:
            self.controller.runner = None
            runner.force_close()
            raise
        self.hide()
        self.send(rid, {"started": True})

    def _runner_finished(self, result):
        self.controller.runner = None
        if result.get("_draft_saved"):
            if self.valid():
                self.show(); self.raise_(); self.activateWindow()
                self.emit_ui_event("draft_saved", {"draft":draft_summary(self.store)})
            return
        try: discard_draft(self.store, result["id"])
        except Exception: LOG.exception("Completed exam's draft could not be removed")
        self.controller.record_effort([i["note_id"] for i in result.get("items", []) if i.get("grade") is not None]) if self.valid() else None
        responses = clean_responses(result.pop("_responses", {}))
        # Never cache an old profile's written answers in the new profile.
        if self.valid():
            self.controller.responses[result["id"]] = responses
            self.controller.responses = dict(list(self.controller.responses.items())[-10:])
        try:
            self.store.add_result(result)
        except Exception as exc:
            LOG.exception("Local practice result could not be saved")
            if self.valid():
                showWarning(f"The session finished, but its local result could not be saved: {exc}\nYour Anki scheduling was not changed.", parent=self)
        try:
            save_answers(self.store, result["id"], responses)
        except Exception:
            # A disk error saving optional prose must not discard scores/card IDs.
            LOG.exception("Optional written-answer saving failed; the result was handled independently")
            if self.valid():
                tooltip("Written answers could not be saved to disk. They remain available in this profile session.", parent=self)
        if not self.valid():
            return
        self.emit_ui_event("result", {"result": result, "state": self.store.state})
        self.show()
        self.raise_()
        self.activateWindow()

    def _study(self, rid, payload):
        if self.controller.runner or self.mw.state == "review":
            raise ValueError("Finish the current review before starting a different study session.")
        exam = self.store.get_exam(str(payload["id"]))
        did = bounded_int(payload.get("deck_id"), 1, 2**53-1, "Deck ID")
        if getattr(self, "_study_pending", False): raise ValueError("Study is already opening.")
        def finish(snap):
            names = {d["id"]: d["name"] for d in snap.decks}
            if needs_focus_session(exam, did, names):
                return self._launch_focus(exam, snap, did, payload)
            from aqt.operations import CollectionOp
            self._study_pending = True
            def select(col):
                if not self.valid() or col is not self._collection:
                    raise ValueError("The profile changed before study could start.")
                return col.decks.set_current(did)
            def selected(_):
                self._study_pending = False
                if not self.valid(): return
                self.controller.active_exam_id = exam.id
                self.forced = True; self.close()
                self.mw.moveToState("review")
            def failed(error):
                self._study_pending = False
                LOG.warning("Scheduled study could not open: %s", error)
                if self.valid():
                    self.emit_ui_event("error", {"message": str(error)})
            CollectionOp(parent=self.mw, op=select).success(selected).failure(failed).run_in_background()
            return {"launching": True, "scheduled": True}
        self.query(rid, lambda col: read_snapshot(col, exam), finish)

    def _launch_focus(self, exam, snap, did, payload):
        if self.mw.state == "review": raise ValueError("A scheduled review started while the cards were loading. Return to Decks first.")
        if self.controller.runner: raise ValueError("A card session is already open.")
        if did not in {s.deck_id for s in exam.scopes}: raise ValueError("That deck is outside this exam.")
        cards = [c for c in snap.cards if c.owner == did]
        if not cards: raise ValueError("No eligible cards remain in this exact group. Check its subdecks and filters.")
        size = bounded_int(payload.get("size", 20), 1, MAX_QUESTIONS, "Focus cards")
        sampled = sample_cards(cards, min(size, len(cards)), {did: 1}, True, True)
        from .runner import ExamRunner
        runner = ExamRunner(self.controller, exam, sampled.cards, "practice", 0, self._runner_finished)
        self.controller.runner = runner
        try: runner.open()
        except Exception:
            self.controller.runner = None
            runner.force_close()
            raise
        self.hide()
        return {"started": True, "scheduled": False, "actual": len(sampled.cards)}

    def _focus(self, rid, payload):
        if self.mw.state == "review": raise ValueError("Return to Decks before opening focus practice.")
        exam = self.store.get_exam(str(payload["id"]))
        did = bounded_int(payload.get("deck_id"), 1, 2**53-1, "Deck ID")
        self.query(rid, lambda col: read_snapshot(col, exam), lambda snap: self._launch_focus(exam, snap, did, payload))

    def _session_options(self, cards, snap, strategy="representative"):
        import time
        last = snap.evidence.get("last_seen", {})
        indexed = note_history(snap)
        return {"sampling": strategy,
                "cold": {c.id for c in cards if not c.is_new and last.get(c.note_id,0)>0 and time.time()-last[c.note_id]>=86400},
                "prompts": {c.id:item_priority(c,snap,indexed=indexed)[1] for c in cards}}

    @staticmethod
    def _configure_runner(runner, options):
        if not hasattr(runner, "session"): return
        runner.session.sampling = options.get("sampling", "representative")
        runner.session.cold = set(options.get("cold", []))
        runner.session.pip_study = bool(options.get("pip_study", False))
        runner.session.allow_new_learning = bool(options.get("teach_new", False))
        runner.item_prompts = options.get("prompts", {})

    def _pip_study(self, rid, payload):
        if self.controller.runner or self.mw.state == "review": raise ValueError("Finish your current review first.")
        if type(payload.get("teach_new", False)) is not bool: raise ValueError("Choose whether to introduce new cards.")
        if payload.get("teach_new",False) and not native_learning_available(self.mw.col):
            raise ValueError("Anki’s Grade Now API is unavailable. Turn off Introduce new cards for rehearsal, or use normal Study to advance learning.")
        exam = self.store.get_exam(str(payload["id"]))
        size = bounded_int(payload.get("size",30),1,MAX_QUESTIONS,"Pip Study cards")
        def finish(snap):
            if self.controller.runner or self.mw.state=="review": raise ValueError("Another study session opened while these cards were loading.")
            result,_ = sample_exam(exam,snap,size,strategy="adaptive",one_per_note=True)
            if not result.cards: raise ValueError("No eligible cards remain in this exam.")
            from .runner import ExamRunner
            runner=ExamRunner(self.controller,exam,result.cards,"practice",0,self._runner_finished)
            options=self._session_options(result.cards,snap,"adaptive")
            options.update(pip_study=True,teach_new=payload.get("teach_new",False))
            self._configure_runner(runner,options)
            self.controller.runner=runner
            try: runner.open()
            except Exception:
                self.controller.runner=None;runner.force_close();raise
            self.hide()
            return {"started":True,"questions":len(result.cards)}
        history=deepcopy(self.store.state["history"])
        self.query(rid,lambda col:read_exam_snapshot(col,exam,history),finish)

    def _resume_exam(self, rid):
        if self.controller.runner or self.mw.state=="review": raise ValueError("Finish your current review before resuming.")
        session=load_draft(self.store)
        if session is None: raise ValueError("There is no saved exam to resume.")
        exam=self.store.get_exam(session.exam_id)
        ids=[c.id for c in session.cards]
        def check(col): return set(int(i) for i in col.find_cards("cid:"+",".join(map(str,ids))))
        def finish(found):
            if self.controller.runner or self.mw.state=="review": raise ValueError("Another session has started.")
            if found!=set(ids): raise ValueError("Some saved exam cards were deleted. The saved draft is preserved; discard it and build a new exam.")
            from .runner import ExamRunner
            runner=ExamRunner(self.controller,exam,session.cards,session.kind,session.minutes,self._runner_finished)
            runner.session=session
            self.controller.runner=runner
            try:runner.open()
            except Exception:
                self.controller.runner=None;runner.force_close();raise
            self.hide();return {"started":True,"resumed":True}
        self.query(rid,check,finish)

    def _export_result(self, rid, payload):
        result=next((r for r in self.store.state["history"] if r["id"]==payload.get("result_id")),None)
        if result is None: raise ValueError("That result is no longer stored.")
        filename,_=QFileDialog.getSaveFileName(self,"Export exam result (no written answers)","Exam Sprout Result.json","JSON files (*.json)")
        if filename:
            Store._atomic(Path(filename),json.dumps(result,ensure_ascii=False,indent=2).encode("utf8"))
        self.send(rid,{"saved":bool(filename)})

    def _review_misses(self, rid, payload):
        if self.controller.runner or self.mw.state == "review": raise ValueError("Finish the current card session first.")
        exam = self.store.get_exam(str(payload["id"]))
        result = next((r for r in self.store.state["history"] if r["id"] == payload.get("result_id") and r["exam_id"] == exam.id), None)
        if result is None: raise ValueError("That practice result is no longer available.")
        if payload.get("filter", "misses") not in ("misses", "all"): raise ValueError("Invalid result review filter.")
        items = list(result.get("items", [])) if payload.get("filter") == "all" else review_items(result)
        if not items:
            self.send(rid, {"empty": True, "message": "No missed cards were recorded. Older results cannot recover unanswered card IDs." if "items" not in result else "No misses or unanswered cards in this session."})
            return
        # This read checks existence without loading card fields or altering cards.
        def existing(col):
            return set(int(cid) for cid in col.find_cards("cid:" + ",".join(str(x["card_id"]) for x in items)))
        def finish(ids):
            if self.controller.runner or self.mw.state == "review":
                raise ValueError("Another card session opened while the missed cards were loading.")
            available = [x for x in items if x["card_id"] in ids]
            if not available: raise ValueError("The recorded cards have been deleted; no replacement cards were selected.")
            answers = self.controller.responses.get(result["id"])
            if answers is None: answers = load_answers(self.store).get(result["id"], {})
            from .runner import MistakeReview
            def done():
                self.controller.runner = None
                if self.valid(): self.show(); self.raise_(); self.activateWindow()
            runner = MistakeReview(self.controller, exam, available, answers, done)
            self.controller.runner = runner
            try: runner.open()
            except Exception:
                self.controller.runner = None
                runner.force_close()
                raise
            self.hide()
            return {"started": True, "missing_cards": len(items)-len(available)}
        self.query(rid, existing, finish)

    def _browse(self, rid, payload):
        if payload.get("missed_result"):
            self._review_misses(rid, {"id": payload["id"], "result_id": payload["missed_result"]})
            return
        # Read-only browser launch. This deliberately does not start reviewing,
        # change the selected deck, create a filtered deck, or reschedule cards.
        # Anki exports a DialogManager instance from aqt; it is not a
        # separately importable aqt.dialogs module.
        from aqt import dialogs as dialogs_mod
        exam = self.store.get_exam(str(payload["id"]))
        did = int(payload["deck_id"])
        if did not in {s.deck_id for s in exam.scopes}:
            raise ValueError("That deck is outside this exam.")
        # Resolve current name without creating a deck on lookup.
        deck = self.mw.col.decks.get(did, default=False)
        if not deck:
            raise ValueError("This deck no longer exists.")
        escaped = deck["name"].replace("\\", "\\\\").replace('"', '\\"')
        search = f'deck:"{escaped}" -is:suspended -is:buried'
        # A separately selected child has its own plan row. Exclude that
        # child's subtree so this browser query matches the parent row.
        for scope in exam.scopes:
            child = self.mw.col.decks.get(scope.deck_id, default=False)
            if child and scope.deck_id != did and child["name"].startswith(deck["name"] + "::"):
                name = child["name"].replace("\\", "\\\\").replace('"', '\\"')
                search += f' -deck:"{name}"'
        if exam.query:
            search += f" ({exam.query})"
        # Resolve/open first. If native Browser construction fails, the bridge
        # can still report it in this live planner instead of closing silently.
        dialogs_mod.open("Browser", self.mw, search=(search,))
        self.send(rid, {})
        self.forced = True
        self.close()

    def _export(self, rid):
        filename, _ = QFileDialog.getSaveFileName(self, "Export exam plans", "Exam Sprout Plans.json", "JSON files (*.json)")
        if filename:
            payload = json.dumps(self.store.state, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
            Store._atomic(Path(filename), payload)
        self.send(rid, {"saved": bool(filename)})

    def hideEvent(self, event) -> None:
        if self.web is not None:
            self.web.eval("window.PipCompanion && window.PipCompanion.pause();")
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.web is not None:
            self.web.eval("window.PipCompanion && window.PipCompanion.resume();")

    def reject(self) -> None:
        self.close()

    def force_close(self) -> None:
        self.forced = True
        self.close()

    def closeEvent(self, event) -> None:
        if self.closed:
            event.accept()
            return
        if self._closing:
            event.ignore()
            return
        self._closing = True
        try:
            if self.controller.runner and not self.forced:
                self.controller.runner.raise_()
                event.ignore()
                return
            if self.dirty and not self.forced and not askUser("Discard your unsaved exam changes?", parent=self):
                event.ignore()
                return
            self.closed = True
            self.pending_sample = None
            self.open_timer.stop()
            if self.controller.dialog is self:
                self.controller.dialog = None
            web, self.web = self.web, None
            if web is not None:
                try:
                    web.set_bridge_command(lambda _message: None, self)
                    web.cleanup()
                except Exception:
                    LOG.exception("Planner webview cleanup failed; window will still close")
            event.accept()
        finally:
            self._closing = False


def install(suite=None, register=None):
    """Register the bundled engine once, under the outer suite's transaction."""
    global CONTROLLER
    if CONTROLLER is not None or aqt.mw is None:
        return CONTROLLER
    existing = getattr(aqt.mw, "_exam_sprout_controller", None)
    if existing is not None:
        if suite is not None and getattr(existing, "suite", None) is not suite:
            raise RuntimeError("A standalone Exam Sprout is already running. Disable its standalone entry, keep Atelier enabled, then fully restart Anki. Do not delete your profile's exam_sprout folder.")
        CONTROLLER = existing
        return existing
    add = register or (lambda hook, fn: hook.append(fn))
    controller = Controller(aqt.mw, suite=suite, register=add)
    CONTROLLER = controller
    aqt.mw._exam_sprout_controller = controller
    for name, callback in (
        ("profile_did_open", controller.profile_open),
        ("profile_will_close", controller.profile_close),
        ("collection_will_temporarily_close", controller.temporary_close),
        ("deck_browser_will_render_content", controller.render_countdowns),
        ("deck_browser_did_render", controller.home_rendered),
        ("webview_will_set_content", controller.web_assets),
        ("webview_did_receive_js_message", controller.web_message),
        ("top_toolbar_did_init_links", controller.toolbar),
        ("reviewer_did_answer_card", controller.after_native_answer),
    ):
        add(getattr(gui_hooks, name), callback)
    controller.install_companion()
    if aqt.mw.col:
        controller.profile_open()
    return controller

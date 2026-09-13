"""Independent exam previewer plus explicitly authorized NEW learning in Pip Study.

The native Previewer renders templates, media, cloze, and MathJax. It uses
preview contexts, not review contexts. Anki's back-side preference is neither
read nor changed. Exam answers are self-marked, not automatically assessed.
"""
from __future__ import annotations
import logging
import math
import time

from aqt import gui_hooks
from aqt.browser.previewer import Previewer
from aqt.qt import (
    QSplitter, QComboBox,
    Qt, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QProgressBar,
    QPlainTextEdit, QTimer, QShortcut, QKeySequence,
)
from aqt.sound import av_player
from aqt.utils import askUser
from aqt.webview import AnkiWebView, AnkiWebViewKind
from aqt.theme import theme_manager

from .core import PracticeSession, CardInfo
from .exam_session import ExamSession, ERROR_TYPES
from .new_learning import fingerprint, available, introduce_new
from .drafts import save_draft, draft_summary

LOG = logging.getLogger("exam_sprout")


class ExamRunner(Previewer):
    def __init__(self, controller, exam, cards, kind, minutes, finished):
        self.controller = controller
        self.exam = exam
        self.session = ExamSession(exam.id, cards, kind, minutes)
        self._collection = controller.mw.col
        self._learning_busy = False
        self._draft_saved = False
        self.item_prompts = {}
        self.callback = finished
        self.forced = False
        self.finished_once = False
        self._ui_ready = False
        self._last_cid = None
        self._cached_card = None
        self._render_error = False
        self._web = None
        self.epoch = controller.epoch
        super().__init__(parent=None, mw=controller.mw, on_close=lambda: None)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def open(self) -> None:
        self._state = "question"
        self._last_state = None
        self._show_both_sides = False
        self._create_gui()
        self._setup_web_view()
        self._ui_ready = True
        self.resize(1180, 820)
        self.setMinimumSize(620, 500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.tick = QTimer(self)
        self.tick.setInterval(1000)
        self.tick.timeout.connect(self._tick)
        self.tick.start()
        self._show_current()
        self.showMaximized()
        self.activateWindow()
        if self._pip_badge is not None:
            badge = self._pip_badge
            self._web.evalWithCallback("matchMedia('(prefers-reduced-motion: reduce)').matches",
                lambda value: badge.set_reduced_motion(value is not False) if self._open and self._pip_badge is badge else None)

    def _create_gui(self) -> None:
        self.setWindowTitle(f"{self.exam.name} · {'Atelier Exam Studio' if getattr(self.controller, 'suite', None) is not None else 'Exam Sprout'}")
        dark = bool(theme_manager.night_mode)
        fg, muted, bg, line, accent = ("#ecf0ed", "#b2bab5", "#242925", "#424b45", "#a0bea6") if dark else ("#26392e", "#68736d", "#f6f8f5", "#dce4dc", "#53755b")
        palette_fn = getattr(self.controller, "suite_palette", None)
        palette = palette_fn() if callable(palette_fn) else None
        if palette:
            fg, muted, bg, line, accent = (palette[k] for k in ("text", "muted", "panel", "line", "accent"))
        self.setStyleSheet(f"QWidget#esChrome {{ background: {bg}; color: {fg}; }} QWidget#esChrome QLabel {{ color: {fg}; }} QWidget#esChrome QPushButton {{ padding: 8px 13px; border: 1px solid {line}; border-radius: 8px; background: transparent; color: {fg}; }} QWidget#esChrome QPushButton:hover {{ border-color: {accent}; }} QWidget#esChrome QPushButton:disabled {{ color: {muted}; }} QWidget#esChrome QComboBox {{ padding: 6px; color: {fg}; background: {bg}; border: 1px solid {line}; border-radius: 7px; }} QWidget#esChrome QPlainTextEdit {{ border: 1px solid {line}; border-radius: 8px; padding: 10px; color: {fg}; background: {bg}; }} QProgressBar {{ border: 0; background: {line}; max-height: 3px; }} QProgressBar::chunk {{ background: {accent}; }}")
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(0)
        top = QWidget(self)
        top.setObjectName("esChrome")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(24, 17, 24, 14)
        top_row = QHBoxLayout()
        self.heading = QLabel(top)
        self.heading.setTextFormat(Qt.TextFormat.PlainText)
        self.heading.setWordWrap(True)
        self.heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        self.clock = QLabel(top)
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.clock.setStyleSheet("font-size: 16px; font-weight: 600;")
        top_row.addWidget(self.heading, 1)
        self.navigator = QComboBox(top)
        self.navigator.setAccessibleName("Jump to an exam question")
        self.navigator.setMinimumWidth(118)
        self.navigator.setMaximumWidth(190)
        self.navigator.activated.connect(self._jump)
        top_row.addWidget(self.navigator)
        top_row.addWidget(self.clock)
        top_layout.addLayout(top_row)
        self.explainer = QLabel(top)
        self.explainer.setWordWrap(True)
        self.explainer.setStyleSheet(f"font-size: 12px; color: {muted};")
        top_layout.addWidget(self.explainer)
        checks = QHBoxLayout()
        self.attempt_button = self._button("Mark answered", self._attempt, top)
        checks.addWidget(self.attempt_button)
        self.confidence_control = QComboBox(top)
        self.confidence_control.setAccessibleName("Confidence before seeing the answer")
        for label in ("Confidence: not set", "Guessing", "Unsure", "Confident"):
            self.confidence_control.addItem(label)
        self.confidence_control.activated.connect(self._confidence)
        checks.addWidget(self.confidence_control)
        self.error_control = QComboBox(top)
        self.error_control.setAccessibleName("Why was this answer difficult?")
        for label in ("Error type (optional)", "Recall", "Concept", "Application", "Misread", "Calculation", "Guess"):
            self.error_control.addItem(label)
        self.error_control.activated.connect(self._error_category)
        checks.addWidget(self.error_control)
        checks.addStretch(1)
        top_layout.addLayout(checks)
        session_actions = QHBoxLayout()
        session_actions.addStretch(1)
        self.save_close = self._button("Save & close", self._save_close, top)
        session_actions.addWidget(self.save_close)
        self.submit_now = self._button("Submit exam", self._submit_now, top)
        session_actions.addWidget(self.submit_now)
        top_layout.addLayout(session_actions)
        self.vbox.addWidget(top)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, len(self.session.cards))
        self.progress_bar.setTextVisible(False)
        self.vbox.addWidget(self.progress_bar)
        self._web = AnkiWebView(self, kind=AnkiWebViewKind.PREVIEWER)
        self.split = QSplitter(Qt.Orientation.Horizontal, self)
        self.split.addWidget(self._web)
        self.side = QWidget(self)
        self.side.setObjectName("esChrome")
        self.side.setMinimumWidth(225); self.side.setMaximumWidth(340)
        self.side_layout = QVBoxLayout(self.side)
        self.side_layout.setContentsMargins(18, 20, 18, 16)
        self.split.addWidget(self.side)
        self.split.setStretchFactor(0, 1); self.split.setStretchFactor(1, 0)
        self.split.setSizes([900, 270])
        self.vbox.addWidget(self.split, 1)
        gui_hooks.card_review_webview_did_init(self._web, AnkiWebViewKind.PREVIEWER)
        bottom = QWidget(self)
        bottom.setObjectName("esChrome")
        controls = QVBoxLayout(bottom)
        controls.setContentsMargins(24, 14, 24, 18)
        self.response_label = QLabel("Your answer / reasoning (optional)", bottom)
        self.response_label.setStyleSheet(f"font-size: 12px; color: {muted};")
        self.response = QPlainTextEdit(bottom)
        self.response.setPlaceholderText("Recall it first. A few words are enough…")
        self.response.setMaximumHeight(16777215)
        self.response.setMinimumHeight(100)
        self.side_layout.addWidget(self.response_label)
        self.side_layout.addWidget(self.response, 1)
        # Pip never owns a response/sidebar webview. It is a 46px native
        # button in the control strip, independent of written-answer visibility.
        self._pip_web = None
        self._pip_badge = None
        self._side_open = False
        self.side.hide()
        self.side_hint = QLabel("Typed answers stay here until you leave the profile, unless local response saving is enabled.", self.side)
        self.side_hint.setWordWrap(True); self.side_hint.setStyleSheet(f"font-size:10px;color:{muted};")
        self.side_layout.addWidget(self.side_hint)
        self.response.textChanged.connect(self._save_response)
        tools = QHBoxLayout()
        row = QHBoxLayout()
        self.replay = self._button("Replay audio", self._replay_audio, bottom)
        self.flag = self._button("Flag", self._flag, bottom)
        self.previous = self._button("Back", self._previous, bottom)
        tools.addWidget(self.replay)
        tools.addWidget(self.flag)
        row.addWidget(self.previous)
        self.fit_button = self._button("Fit card", self._fit_card, bottom)
        tools.addWidget(self.fit_button)
        self.notes_button = self._button("Write answer", self._toggle_side, bottom)
        tools.addWidget(self.notes_button)
        tools.addStretch(1)
        controls.addLayout(tools)
        row.addStretch(1)
        self.skip_button = self._button("Skip", self._skip, bottom)
        self.primary = self._button("Next", self._primary, bottom)
        row.addWidget(self.skip_button)
        row.addWidget(self.primary)
        if (self.controller.store.state["settings"].get("show_pip", True)
                and self.controller.store.state["settings"].get("reviewer_pip", True)):
            try:
                from .companion import TinyPip
                badge = TinyPip(self.controller, bottom)
                growth = self.controller.growth_cache.get(self.exam.id, {"stage": 1})
                badge.configure(growth.get("stage", 1), self.controller.store.state["settings"].get("animate_pip", True))
                self._pip_badge = badge
                row.addWidget(badge)
            except Exception:
                LOG.exception("Tiny Pip is unavailable in practice; card session is unchanged")
        controls.addLayout(row)
        grading = QHBoxLayout()
        grading.addStretch(1)
        self.grade_buttons = []
        for label, score in (("Missed", 0), ("Partly right", .5), ("Correct", 1)):
            button = self._button(label, lambda _checked=False, score=score: self._grade(score), bottom)
            grading.addWidget(button)
            self.grade_buttons.append(button)
        controls.addLayout(grading)
        learning = QHBoxLayout()
        learning.addStretch(1)
        self.learning_buttons = []
        for rating, label in enumerate(("Again · Anki", "Hard · Anki", "Good · Anki", "Easy · Anki"), 1):
            button = self._button(label, lambda _=False, r=rating: self._schedule_rating(r), bottom)
            learning.addWidget(button); self.learning_buttons.append(button)
            button.hide()
        controls.addLayout(learning)
        self.safety = QLabel("Separate self-assessment · No due dates, ease, or review history are changed.", bottom)
        self.safety.setWordWrap(True)
        self.safety.setStyleSheet(f"font-size: 11px; color: {muted}; margin-top: 6px;")
        controls.addWidget(self.safety)
        self.vbox.addWidget(bottom)
        # This shortcut exists only on this dialog; never on the main reviewer.
        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.shortcut.activated.connect(self._primary)

    @staticmethod
    def _button(label, handler, parent):
        button = QPushButton(label, parent)
        button.setAutoDefault(False)
        button.clicked.connect(handler)
        return button

    def card(self):
        if not self.mw.col or self.controller.epoch != self.epoch:
            return None
        cid = self.session.current.id
        if self._cached_card is None or self._cached_card.id != cid:
            self._cached_card = self.mw.col.get_card(cid)
        return self._cached_card

    def card_changed(self) -> bool:
        cid = self.session.current.id
        changed = cid != self._last_cid
        self._last_cid = cid
        return changed

    def _show_current(self) -> None:
        s = self.session
        if s.phase == "finished":
            self.close()
            return
        self._render_error = s.current.id in getattr(s, 'render_errors', set())
        self._allow_grade_at = time.monotonic() + .30
        self._cached_card = None
        self._state = "answer" if s.revealed else "question"
        # Previewer resets to the question when the card changes. A grading pass
        # intentionally shows the answer; mark this card as already selected.
        self._last_cid = s.current.id
        self._card_changed = False
        self._last_state = None
        self._last_render = 0
        self.heading.setText(f"{'Check' if s.phase == 'grading' else 'Question'} {s.index + 1} of {len(s.cards)}  ·  {self.exam.name}")
        self.explainer.setText("Mark your own recall honestly. Partial credit is ½ point; ungraded items receive no points." if s.phase == "grading" else "Answers stay hidden until you submit the entire exam. Flag anything to revisit before submitting." if s.kind == "exam" else "Recall the answer, reveal it, then mark yourself. This is not a scheduled Anki review.")
        self.progress_bar.setValue(s.index)
        self._update_navigator()
        self.response.blockSignals(True)
        self.response.setPlainText(s.responses.get(s.current.id, ""))
        self.response.setReadOnly(s.phase == "grading" or s.revealed)
        self.response.blockSignals(False)
        self.response_label.setText("Your recorded answer" if s.phase == "grading" else "Your answer / reasoning (optional)")
        if not self._side_open:
            self.notes_button.setText("Write answer")
        self.previous.setVisible(s.phase == "answering")
        self.previous.setEnabled(s.index > 0)
        self.flag.setText("Flagged ✓" if s.current.id in s.flags else "Flag")
        self.primary.setVisible(s.phase == "answering" or not s.revealed)
        self.primary.setText("Submit exam" if s.phase == "answering" and s.index == len(s.cards) - 1 else "Next →" if s.phase == "answering" else "Reveal answer")
        for b in self.grade_buttons:
            b.setVisible(s.phase in ("practice", "grading") and s.revealed)
            b.setEnabled(True)
        self.skip_button.setText("Leave ungraded" if s.phase == "grading" else "Skip")
        if self._web is not None: self._web.setZoomFactor(1.0)
        try:
            import re
            if re.search(r"\[\[type:[^]]+\]\]", self.card().question()):
                self.response_label.setText("Typed-answer card · enter your answer here")
                if not self._side_open:
                    self.notes_button.setText("Type answer")
        except Exception:
            pass
        self._update_exam_controls()
        if hasattr(s, "enter"): s.enter()
        self.render_card()
        self._tick()

    def _update_navigator(self):
        nav = self.navigator
        s = self.session
        nav.blockSignals(True)
        nav.clear()
        for i, card in enumerate(s.cards):
            label = f"Question {i + 1}"
            label += " · answered" if card.id in getattr(s, "attempted", set()) else " · unanswered"
            if card.id in s.flags:
                label += " · flagged"
            nav.addItem(label)
        nav.setCurrentIndex(s.index)
        nav.setVisible(s.phase == "answering")
        nav.blockSignals(False)

    def _jump(self, index):
        s = self.session
        if s.phase != "answering" or not isinstance(index, int) or not 0 <= index < len(s.cards):
            return
        self._save_response()
        s.go(index - s.index)
        self._show_current()

    def _toggle_side(self, *args):
        self._side_open = not self._side_open
        self.side.setVisible(self._side_open)
        self.notes_button.setText("Hide answer notes" if self._side_open else "Write answer")
        if self._side_open:
            self.response.setFocus()

    def _fit_card(self, *args):
        if self._web is None: return
        web = self._web
        cid = self.session.current.id
        def fit(measurement):
            if self._web is not web or not self._open or self.session.current.id != cid: return
            if not isinstance(measurement,list) or len(measurement)!=4:return
            if any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or v <= 0 for v in measurement):
                return
            width,height,vw,vh=measurement
            factor = max(.25,min(1.,web.zoomFactor() * min(vw/width,vh/height) * .95))
            web.setZoomFactor(factor)
        # Scale the complete document, preserving image/mask coordinate alignment.
        web.evalWithCallback("(()=>{const q=document.getElementById('qa')||document.body;return [Math.max(q.scrollWidth,q.getBoundingClientRect().width),q.scrollHeight,innerWidth,innerHeight];})()", fit)

    def _render_scheduled(self) -> None:
        try:
            super()._render_scheduled()
        except Exception:
            LOG.exception("A practice card could not be rendered")
            self._render_error = True
            if hasattr(self.session, "render_errors"): self.session.render_errors.add(self.session.current.id)
            for button in getattr(self, "learning_buttons", []): button.setEnabled(False)
            self.explainer.setText("This card could not be rendered. Skip it and check its template in Anki’s browser; it will not count as graded.")
            for button in self.grade_buttons:
                button.setEnabled(False)
            if self._web is not None:
                self._web.eval("document.getElementById('qa') && (document.getElementById('qa').textContent = 'This card could not be rendered.');")

    def _save_response(self) -> None:
        self.session.save_response(self.response.toPlainText())

    def _primary(self, *args) -> None:
        s = self.session
        if s.phase == "answering":
            self._save_response()
            if s.index == len(s.cards) - 1:
                self._submit_now()
                return
            else:
                s.go(1)
            self._show_current()
        elif s.phase == "practice" and not s.revealed:
            self._save_response()
            s.reveal()
            self._show_current()

    def _previous(self, *args) -> None:
        self._save_response()
        self.session.go(-1)
        self._show_current()

    def _skip(self, *args) -> None:
        if getattr(self, "_learning_busy", False): return
        if self.session.phase == "answering" and self.session.index == len(self.session.cards) - 1:
            self._primary()
            return
        self._save_response()
        self.session.skip()
        self._show_current()

    def _grade(self, score) -> None:
        if getattr(self, "_learning_busy", False): return
        if getattr(self, "_native_new_card", False): return
        if self._render_error or self.session.phase == "finished" or time.monotonic() < getattr(self, "_allow_grade_at", 0):
            return
        try: self.session.grade(score)
        except ValueError as error:
            self.explainer.setText(str(error)); return
        self._show_current()

    def _flag(self, *args) -> None:
        cid = self.session.current.id
        if cid in self.session.flags:
            self.session.flags.remove(cid)
        else:
            self.session.flags.add(cid)
        self.flag.setText("Flagged ✓" if cid in self.session.flags else "Flag")
        self._update_navigator()

    def _update_exam_controls(self):
        s = self.session
        front = s.phase in ("answering", "practice") and not s.revealed
        self.attempt_button.setVisible(front)
        self.attempt_button.setText("Answered ✓" if s.current.id in s.attempted else "Mark answered")
        self.confidence_control.setVisible(front)
        self.confidence_control.blockSignals(True)
        self.confidence_control.setCurrentIndex(s.confidence.get(s.current.id, 0))
        self.confidence_control.blockSignals(False)
        self.error_control.setVisible(s.revealed)
        self.error_control.blockSignals(True)
        self.error_control.setCurrentIndex(ERROR_TYPES.index(s.errors.get(s.current.id, "none")))
        self.error_control.blockSignals(False)
        self.submit_now.setVisible(s.phase == "answering")
        self.save_close.setEnabled(not self._learning_busy)
        self._native_new_card = False; self._learning_expected = None
        if s.pip_study:
            prompt = self.item_prompts.get(s.current.id, "Cold recall: explain why, give an example, or contrast a similar concept before revealing.")
            self.explainer.setText("Pip Study · " + prompt)
            try:
                card = self.card()
                self._native_new_card = bool(s.allow_new_learning and s.current.is_new and s.current.id not in s.scheduled)
                if self._native_new_card: self._learning_expected = fingerprint(card)
            except Exception: pass
        for button in self.learning_buttons:
            button.setVisible(self._native_new_card and s.revealed)
            button.setEnabled(not self._learning_busy and not self._render_error)
        if self._native_new_card:
            for button in self.grade_buttons: button.hide()
            self.safety.setText("NEW learning is enabled. After reveal, an Anki rating changes THIS new card's normal learning schedule. This is not a retrospective exam mark.")
        else:
            self.safety.setText("Exam rehearsal: this card's Anki schedule is unchanged. Self-mark honestly; your readiness estimate is not a grade guarantee.")
        if self._render_error:
            self.explainer.setText('This card had a rendering failure in this session. Review it or skip; it cannot receive a score or native learning rating here.')
            for button in self.grade_buttons:button.setEnabled(False)
        if s.phase == "grading" and s.current.id not in s.attempted:
            self.explainer.setText("Unanswered before submission · no score credit. Review the answer, then mark Missed or leave ungraded.")
            for button in self.grade_buttons[1:]: button.setEnabled(False)

    def _attempt(self, *args):
        self.session.mark_attempted(self.session.current.id not in self.session.attempted)
        self._update_exam_controls(); self._update_navigator()

    def _confidence(self, index):
        self.session.set_confidence(index)
        self._update_exam_controls(); self._update_navigator()

    def _error_category(self, index):
        if type(index) is int and 0 <= index < len(ERROR_TYPES): self.session.set_error(ERROR_TYPES[index])

    def _submit_now(self, *args):
        s = self.session
        if s.phase != "answering": return
        self._save_response()
        answered = len(getattr(s, "attempted", s.responses))
        if not askUser(f"Submit {len(s.cards)} questions?\n{answered} marked answered · {len(s.cards)-answered} unanswered · {len(s.flags)} flagged.\nAnswers will be locked. Unanswered items receive no score credit.", parent=self): return
        s.submit(); self._show_current()

    def _save_close(self, *args):
        if self._learning_busy or self.session.phase == "finished": return
        existing = draft_summary(self.controller.store)
        replace = " This replaces your other saved exam." if existing and existing.get("id") != self.session.id else ""
        if not askUser("Save this session and its written answers locally on this computer?"+replace+"\nTimed exams keep counting while closed. You can resume or discard the saved exam in Exam Sprout.", parent=self): return
        self._save_response()
        try: save_draft(self.controller.store, self.session)
        except Exception as error:
            LOG.exception("Exam draft could not be saved")
            self.explainer.setText("Could not save this exam: " + str(error)); self.session.enter(); return
        self._draft_saved = True; self.forced = True; self.close()

    def _schedule_rating(self, rating):
        s = self.session
        if (self._learning_busy or self._render_error or self.finished_once or not s.revealed
                or s.kind != "practice" or not s.pip_study or not s.allow_new_learning
                or not s.current.is_new or s.current.id in s.render_errors or s.current.id in s.scheduled
                or not getattr(self, "_learning_expected", None)):
            return
        if type(rating) is not int or rating not in (1,2,3,4): return
        self._learning_busy = True
        cid = s.current.id; expected = self._learning_expected
        col_ref = self._collection; epoch = self.epoch; store_ref = self.controller.store
        for button in self.learning_buttons: button.setEnabled(False)
        self.save_close.setEnabled(False); self.skip_button.setEnabled(False); self.primary.setEnabled(False)
        from aqt.operations import CollectionOp
        def op(col):
            if (col is not col_ref or self.controller.epoch != epoch or self.controller.store is not store_ref
                    or self.finished_once or self.mw.state == "review"):
                raise ValueError("The collection or session changed before the rating; nothing was saved.")
            return introduce_new(col,card_id=cid,expected=expected,exam=self.exam,rating=rating,authorized=True)
        def done(_):
            self._learning_busy = False
            if self.finished_once or self.controller.epoch != epoch or self.controller.store is not store_ref: return
            s.scheduled.add(cid); s.mark_attempted(True)
            s.grade(0 if rating==1 else 1)
            self.skip_button.setEnabled(True); self.primary.setEnabled(True); self._show_current()
        def failed(error):
            self._learning_busy = False
            LOG.warning("New learning rating was not completed: %s", error)
            if self.finished_once or self.controller.epoch != epoch: return
            self._update_exam_controls()
            self.skip_button.setEnabled(True); self.primary.setEnabled(True)
            self.explainer.setText(str(error))
        try: CollectionOp(parent=self.mw,op=op).success(done).failure(failed).run_in_background(initiator=self)
        except Exception as error: failed(error)

    def _replay_audio(self, *args) -> None:
        try:
            if not self._render_error:
                self._on_replay_audio()
        except Exception:
            LOG.exception("Practice audio could not be replayed")

    def _tick(self) -> None:
        if not self._open or self.finished_once or getattr(self,"_learning_busy",False):
            return
        if self.controller.epoch != self.epoch or not self.mw.col:
            self.force_close()
            return
        seconds = self.session.remaining_seconds()
        if seconds == 0:
            self._save_response()
            self.session.submit(timed_out=True)
            self._show_current()
            return
        self.clock.setText(f"{seconds // 60:02d}:{seconds % 60:02d}" if seconds is not None else "Self-marking" if self.session.phase == "grading" else "Untimed")

    def reject(self) -> None:
        self.close()

    def force_close(self) -> None:
        self.forced = True
        self.close()

    def closeEvent(self, event) -> None:
        if getattr(self, "_learning_busy", False) and not self.forced:
            event.ignore(); return
        if self.finished_once:
            event.accept()
            return
        complete = self.session.phase == "finished"
        if not complete and not self.forced and not askUser("End this session? Completed self-marks and unanswered card IDs will be kept as a partial result. Written responses follow your local retention setting.", parent=self):
            event.ignore()
            return
        self.finished_once = True
        self._open = False
        try:self.cancel_timer()
        except Exception:LOG.exception("Practice render timer cleanup failed")
        if hasattr(self, "tick"):
            self.tick.stop()
        try:av_player.stop_and_clear_queue()
        except Exception:LOG.exception("Practice audio cleanup failed")
        badge = getattr(self, "_pip_badge", None)
        if badge is not None:
            try: badge.dispose()
            except Exception: LOG.exception("Tiny Pip cleanup failed; closing card session anyway")
            self._pip_badge = None
        for key in ("_web", "_pip_web"):
            web=getattr(self,key,None)
            if web is not None:
                try:web.cleanup()
                except Exception:LOG.exception("Practice webview cleanup failed")
                setattr(self,key,None)
        event.accept()
        if self._ui_ready:
            if getattr(self, "_draft_saved", False):
                try: self.callback({"_draft_saved": True})
                except Exception: LOG.exception("Saved exam close callback failed")
                self.session.responses.clear()
                return
            result = self.session.result(interrupted=not complete)
            result["_responses"] = dict(self.session.responses)
            try:self.callback(result)
            except Exception:LOG.exception("Practice result callback failed after closing")
        self.session.responses.clear()


class MistakeReview(ExamRunner):
    """Read-only reinspection of original questions and retained written answers.

    This never saves a second practice result, changes grades, or opens Browser.
    """
    def __init__(self, controller, exam, items, answers, finished):
        cards = [CardInfo(x["card_id"], x["note_id"], x["deck_id"]) for x in items]
        super().__init__(controller, exam, cards, "practice", 0, lambda _: None)
        self.items = items
        self.saved_answers = answers
        self.review_finished = finished
        self.answer_visible = False

    def _show_current(self):
        s = self.session
        self._render_error = False
        self._cached_card = None
        self._last_cid = s.current.id
        self._card_changed = False
        self._last_state = None
        self._last_render = 0
        self._state = "answer" if self.answer_visible else "question"
        self.heading.setText(f"Review {s.index + 1} of {len(s.cards)} · {self.exam.name}")
        grade = self.items[s.index].get("grade")
        status = "Unanswered / not graded" if grade is None else "Partly right" if grade == .5 else "Correct" if grade == 1 else "Missed"
        self.explainer.setText(status + " · Compare your original response with the answer. This does not change the result or your Anki schedule.")
        self.clock.setText("Read-only")
        for widget in (self.attempt_button,self.confidence_control,self.error_control,self.submit_now,self.save_close): widget.hide()
        for button in self.learning_buttons: button.hide()
        self.navigator.hide()
        self.progress_bar.setValue(s.index + 1)
        self.response.blockSignals(True)
        answer = self.saved_answers.get(str(s.current.id), self.saved_answers.get(s.current.id, ""))
        self.response.setPlainText(answer or "No written response was retained for this card.")
        self.response.setReadOnly(True); self.response.blockSignals(False)
        self.response_label.setText("Your original written answer")
        self.previous.show(); self.previous.setEnabled(s.index > 0)
        self.flag.hide()
        self.primary.show(); self.primary.setText("Hide answer" if self.answer_visible else "Reveal answer")
        self.skip_button.setText("Finish review" if s.index + 1 == len(s.cards) else "Next card →")
        for b in self.grade_buttons:b.hide()
        # Opening mistake review is an explicit request to compare the original
        # response. Keep its notes pane separate from the tiny mascot.
        if not hasattr(self, "_review_notes_initialized"):
            self._side_open = True
            self._review_notes_initialized = True
        self.side.setVisible(self._side_open)
        self.notes_button.setText("Hide answer notes" if self._side_open else "Original answer")
        if self._web is not None:self._web.setZoomFactor(1.)
        self.render_card()

    def _primary(self, *args):
        self.answer_visible = not self.answer_visible
        self._show_current()

    def _previous(self, *args):
        self.session.index = max(0,self.session.index-1)
        self.answer_visible = False; self._show_current()

    def _skip(self, *args):
        if self.session.index+1 == len(self.session.cards):self.close();return
        self.session.index += 1; self.answer_visible = False; self._show_current()

    def _save_response(self):pass
    def _grade(self, score):pass

    def _tick(self):
        if self.controller.epoch != self.epoch or not self.mw.col:self.force_close()

    def closeEvent(self, event):
        if self.finished_once:event.accept();return
        self.finished_once=True;self._open=False
        try:self.cancel_timer()
        except Exception:LOG.exception('Mistake review timer cleanup failed')
        if hasattr(self,'tick'):self.tick.stop()
        try:av_player.stop_and_clear_queue()
        except Exception:LOG.exception('Mistake review audio cleanup failed')
        badge = getattr(self, "_pip_badge", None)
        if badge is not None:
            try: badge.dispose()
            except Exception: LOG.exception("Tiny Pip cleanup failed; closing card session anyway")
            self._pip_badge = None
        for key in ('_web','_pip_web'):
            web=getattr(self,key,None)
            if web is not None:
                try:web.cleanup()
                except Exception:LOG.exception('Mistake review cleanup failed')
                setattr(self,key,None)
        event.accept()
        try:self.review_finished()
        except Exception:LOG.exception('Mistake review callback failed after closing')

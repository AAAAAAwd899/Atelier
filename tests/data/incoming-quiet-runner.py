"""Independent exam previewer plus explicitly authorized NEW learning in Pip Study.

The native Previewer renders templates, media, cloze, and MathJax. It uses
preview contexts, not review contexts. Anki's back-side preference is neither
read nor changed. Exam answers are self-marked, not automatically assessed.
"""
from __future__ import annotations
import logging
import json
from pathlib import Path
from uuid import uuid4
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
        self._layout_answer_panel()
        self.activateWindow()
        if self._pip_badge is not None:
            badge = self._pip_badge
            self._web.evalWithCallback("matchMedia('(prefers-reduced-motion: reduce)').matches",
                lambda value: badge.set_reduced_motion(value is not False) if self._open and self._pip_badge is badge else None)

    def _create_gui(self) -> None:
        from .review_ui import build_review_ui
        build_review_ui(self)
        self._side_open = False
        self.side.hide()
        self._key_token = ""
        self._key_actions = {}

    def _setup_web_view(self) -> None:
        super()._setup_web_view()
        self._key_script = (Path(__file__).parent / "web" / "review_keys.js").read_text(encoding="utf-8")
        if self._web is not None:
            self._web.eval(self._key_script)

    def _refresh_quiet(self) -> None:
        if not getattr(self, "_review_ui_ready", False):
            return
        from .review_ui import review_view, keyboard_actions
        s = self.session
        mistake = isinstance(self, MistakeReview)
        native = bool(getattr(self, "_native_new_card", False)) and not mistake
        view = review_view(s, native_new=native, mistake=mistake,
                          answer_visible=getattr(self, "answer_visible", False), render_error=self._render_error)
        self.heading.setText(f"{s.index + 1} / {len(s.cards)}")
        self.heading.setToolTip(self.exam.name)
        self.mode_label.setText("Saving Anki rating…" if self._learning_busy else view.mode)
        self.mode_label.setToolTip(view.mode_help)
        self.mode_label.setAccessibleName(view.mode_help)
        self.safety.setText(view.mode_help)
        self.primary.setText(view.primary)
        self.primary.setToolTip(view.primary_help)
        self.primary.setVisible(mistake or s.phase == "answering" or (not s.revealed and not self._render_error))
        self.previous.setVisible(view.previous)
        self.previous.setEnabled(s.index > 0 and not self._learning_busy)
        self.previous_tool.setVisible(mistake or s.phase == "answering")
        self.previous_tool.setEnabled(s.index > 0 and not self._learning_busy)
        self.skip_button.setVisible(view.skip or self._render_error)
        self.skip_button.setEnabled(not self._learning_busy)
        self.skip_tool.setText("Continue without a mark" if s.phase == "grading" else "Skip this question")
        self.skip_tool.setEnabled(not self._learning_busy)
        for b in self.grade_buttons:
            b.setVisible(view.grades == "practice")
        for b in self.learning_buttons:
            b.setVisible(view.grades == "learning")
        self.key_hint.setText(view.hint)
        self.flag.setText("Remove bookmark" if s.current.id in s.flags else "Bookmark question")
        self.flag.setToolTip("Only bookmarks this practice question; does not change Anki card flags.")
        self.tools_button.setText("Tools •" if s.current.id in s.flags else "Tools")
        self.tools_button.setEnabled(not self._learning_busy)
        self.attempt_button.setVisible(s.phase == "answering" and not mistake)
        self.attempt_button.setText("Mark as unanswered" if s.current.id in getattr(s, "attempted", set()) else "I answered without typing")
        self.save_close.setText("Save and close")
        self.submit_now.setText("Finish exam…")
        self.notes_button.setText("Close my answer" if self._side_open else "View my answer" if mistake or s.phase == "grading" else "Write an answer")
        self.progress_bar.hide()
        self.clock.setVisible(s.minutes > 0 and s.phase in ("answering", "practice"))
        self._key_actions = keyboard_actions(s, native_new=native, mistake=mistake,
                                            answer_visible=getattr(self,"answer_visible",False),
                                            render_error=self._render_error, busy=self._learning_busy)
        self._publish_keys()

    def _publish_keys(self) -> None:
        if self._web is None or not getattr(self, "_key_script", None):
            return
        payload = json.dumps({"token": self._key_token, "actions": self._key_actions}, ensure_ascii=True)
        try:
            self._web.eval(self._key_script + "\nwindow.AtelierReviewKeys.update(" + payload + ");")
        except RuntimeError:
            # A delayed rendering callback may arrive during Qt destruction.
            LOG.debug("Keyboard update skipped for a closing card view")

    def _on_bridge_cmd(self, cmd):
        if isinstance(cmd, str) and cmd.startswith("atelier-review-key:"):
            if len(cmd) > 512:
                return
            try:
                data = json.loads(cmd.split(":", 1)[1])
            except (ValueError, TypeError):
                return
            if not isinstance(data, dict) or not self._key_token or data.get("token") != self._key_token:
                return
            self._dispatch_review_key(data.get("key"))
            return
        return super()._on_bridge_cmd(cmd)

    def _dispatch_review_key(self, key):
        if (not isinstance(key, str) or not getattr(self, "_open", False) or self.finished_once
                or self._learning_busy or self.controller.epoch != self.epoch
                or self.mw.col is not self._collection):
            return
        if getattr(self, "tools_panel", None) is not None and self.tools_panel.isVisible():
            return
        action = self._key_actions.get(key)
        if not action:
            return
        if action == "tools": self._toggle_tools()
        elif action == "primary": self._advance_primary()
        elif action == "previous":
            if self.session.index > 0: self._previous()
        elif action == "skip": self._skip()
        elif action.startswith("grade:"): self._grade(float(action.split(":")[1]))
        elif action.startswith("learn:"): self._schedule_rating(int(action.split(":")[1]))

    def keyPressEvent(self, event):
        # The web document handles its own keys, checking editable and interactive
        # targets first. Native text boxes/comboboxes retain their ordinary keys.
        from aqt.qt import QApplication, QLineEdit, QAbstractSpinBox
        focus = QApplication.focusWidget()
        blocked = isinstance(focus, (QPlainTextEdit, QLineEdit, QComboBox, QAbstractSpinBox))
        in_web = self._web is not None and (focus is self._web or (focus is not None and self._web.isAncestorOf(focus)))
        if (not blocked and not in_web and not event.isAutoRepeat()
                and not event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)):
            key = {Qt.Key.Key_Space:" ", Qt.Key.Key_Return:"Enter", Qt.Key.Key_Enter:"Enter",
                   Qt.Key.Key_Left:"ArrowLeft",Qt.Key.Key_Right:"ArrowRight"}.get(event.key(),event.text().lower())
            if key in self._key_actions:
                self._dispatch_review_key(key); event.accept(); return
        super().keyPressEvent(event)

    def _toggle_tools(self, *args):
        if self._learning_busy or self.finished_once:
            return
        if self.tools_panel.isVisible():
            self._close_tools(); return
        from aqt.qt import QPoint
        self._refresh_quiet()
        self._tools_token = self._key_token
        rect = self.screen().availableGeometry()
        width = min(390, rect.width() - 28)
        height = min(610, rect.height() - 36, max(360, self.height() - 28))
        self.tools_panel.resize(width, height)
        origin = self.tools_button.mapToGlobal(QPoint(0, 0))
        x = max(rect.left() + 8, min(origin.x(), rect.right() - width - 8))
        y = max(rect.top() + 8, min(origin.y() - height - 8, rect.bottom() - height - 8))
        self.tools_panel.move(x, y)
        self.tools_panel.show(); self.tools_panel.raise_()
        self.tools_button.setChecked(True)
        self.notes_button.setFocus()

    def _close_tools(self, *args):
        panel = getattr(self, "tools_panel", None)
        if panel is not None:
            panel.hide()
        if getattr(self, "tools_button", None) is not None:
            self.tools_button.setChecked(False)
        if self._web is not None and getattr(self, "_open", False):
            self._web.setFocus()

    def _run_tool(self, handler):
        if (self.finished_once or self._learning_busy or self.controller.epoch != self.epoch
                or self.mw.col is not self._collection):
            return
        if getattr(self, "_tools_token", None) != self._key_token:
            self._close_tools(); return
        self._close_tools()
        handler()

    def _jump_from_tools(self, index):
        self._run_tool(lambda: self._jump(index))

    def _reset_zoom(self, *args):
        if self._web is not None:
            self._web.setZoomFactor(1.0)

    def _notice(self, text):
        # Ordinary tips remain behind Tools, but failures cannot be hidden there.
        self.explainer.setText(text)
        notice = getattr(self, "notice", None)
        if notice is not None:
            notice.setText(text); notice.setVisible(bool(text))

    def _advance_primary(self, *args):
        s = self.session
        if getattr(self, "_learning_busy", False) or self.finished_once:
            return
        if isinstance(self, MistakeReview):
            self._primary(); return
        if s.phase == "answering":
            self._save_response()
            if s.index + 1 == len(s.cards):
                self._submit_now(mark_current=True)
            else:
                s.mark_attempted(True)
                self._primary()
        else:
            self._primary()

    def _layout_answer_panel(self):
        if not getattr(self, "_review_ui_ready", False):
            return
        narrow = self.width() < 860
        if narrow == self._side_axis:
            return
        self._side_axis = narrow
        self.side.setMinimumWidth(0 if narrow else 230)
        self.side.setMaximumWidth(16777215 if narrow else 340)
        self.side.setMaximumHeight(220 if narrow else 16777215)
        self.split.setOrientation(Qt.Orientation.Vertical if narrow else Qt.Orientation.Horizontal)
        self.split.setSizes([max(200, self.height()-260),180] if narrow else [max(350,self.width()-290),290])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_answer_panel()

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
        if getattr(self, "_review_ui_ready", False):
            self._close_tools()
            self.notice.hide()
        self._key_token = uuid4().hex
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
        self._refresh_quiet()
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
                label += " · bookmarked"
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
            self._layout_answer_panel()
            self.response.setFocus()
        elif self._web is not None:
            self._web.setFocus()
        self._refresh_quiet()

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
            self._publish_keys()
        except Exception:
            LOG.exception("A practice card could not be rendered")
            self._render_error = True
            if hasattr(self.session, "render_errors"): self.session.render_errors.add(self.session.current.id)
            for button in getattr(self, "learning_buttons", []): button.setEnabled(False)
            self._notice("This card could not be displayed. Use Skip, then check its template in Browse. It will not receive a grade.")
            for button in self.grade_buttons:
                button.setEnabled(False)
            if self._web is not None:
                self._web.eval("document.getElementById('qa') && (document.getElementById('qa').textContent = 'This card could not be rendered.');")
            self._refresh_quiet()

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
            self._notice(str(error)); return
        self._show_current()

    def _flag(self, *args) -> None:
        cid = self.session.current.id
        if cid in self.session.flags:
            self.session.flags.remove(cid)
        else:
            self.session.flags.add(cid)
        self.flag.setText("Remove bookmark" if cid in self.session.flags else "Bookmark question")
        self._update_navigator()
        self._refresh_quiet()

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
            self._notice("This card could not be displayed correctly. Skip it; grading is disabled for this card.")
            for button in self.grade_buttons:button.setEnabled(False)
        if s.phase == "grading" and s.current.id not in s.attempted:
            self._notice("You left this question unanswered. It cannot earn points after the answer is shown; mark Missed or use Tools to skip the mark.")
            for button in self.grade_buttons[1:]: button.setEnabled(False)
        self._refresh_quiet()

    def _attempt(self, *args):
        if getattr(self, "_review_ui_ready", False) and (not self.tools_panel.isVisible() or self._tools_token != self._key_token): return
        self.session.mark_attempted(self.session.current.id not in self.session.attempted)
        self._update_exam_controls(); self._update_navigator()

    def _confidence(self, index):
        if getattr(self, "_review_ui_ready", False) and (not self.tools_panel.isVisible() or self._tools_token != self._key_token): return
        self.session.set_confidence(index)
        self._update_exam_controls(); self._update_navigator()

    def _error_category(self, index):
        if getattr(self, "_review_ui_ready", False) and (not self.tools_panel.isVisible() or self._tools_token != self._key_token): return
        if type(index) is int and 0 <= index < len(ERROR_TYPES): self.session.set_error(ERROR_TYPES[index])

    def _submit_now(self, *args, mark_current=False):
        s = self.session
        if s.phase != "answering": return
        self._save_response()
        answered = len(getattr(s, "attempted", s.responses))
        if mark_current and s.current.id not in s.attempted:
            answered += 1
        if not askUser(f"Finish this exam and check your answers?\n{answered} answered · {len(s.cards)-answered} unanswered · {len(s.flags)} bookmarked.\nYou cannot change your original answers after finishing. Unanswered questions receive no points.", parent=self): return
        if mark_current:
            s.mark_attempted(True)
        s.submit(); self._show_current()

    def _save_close(self, *args):
        if self._learning_busy or self.session.phase == "finished": return
        existing = draft_summary(self.controller.store)
        replace = " This replaces your other saved exam." if existing and existing.get("id") != self.session.id else ""
        if not askUser("Save this session and its written answers locally on this computer?"+replace+"\nTimed exams keep counting while closed. Resume or discard it from your exam planner.", parent=self): return
        self._save_response()
        try: save_draft(self.controller.store, self.session)
        except Exception as error:
            LOG.exception("Exam draft could not be saved")
            self._notice("Could not save this exam: " + str(error)); self.session.enter(); return
        self._draft_saved = True; self.forced = True; self.close()

    def _schedule_rating(self, rating):
        s = self.session
        if (self._learning_busy or self._render_error or self.finished_once or not s.revealed
                or s.kind != "practice" or not s.pip_study or not s.allow_new_learning
                or not s.current.is_new or s.current.id in s.render_errors or s.current.id in s.scheduled
                or not getattr(self, "_learning_expected", None)):
            return
        if type(rating) is not int or rating not in (1,2,3,4): return
        if time.monotonic() < getattr(self, "_allow_grade_at", 0): return
        self._learning_busy = True
        self._refresh_quiet()
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
            self._notice(str(error))
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
        self.clock.setText(f"{seconds // 60:02d}:{seconds % 60:02d}" if seconds is not None else "")
        self.clock.setVisible(seconds is not None)

    def reject(self) -> None:
        panel = getattr(self, "tools_panel", None)
        if panel is not None and panel.isVisible():
            self._close_tools(); return
        if getattr(self, "_side_open", False):
            self._toggle_side(); return
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
        panel = getattr(self, "tools_panel", None)
        if panel is not None: panel.hide()
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
        if getattr(self, "_review_ui_ready", False):
            self._close_tools()
            self.notice.hide()
        self._key_token = uuid4().hex
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
            self._side_open = False
            self._review_notes_initialized = True
        self.side.setVisible(self._side_open)
        self.notes_button.setText("Hide answer notes" if self._side_open else "Original answer")
        if self._web is not None:self._web.setZoomFactor(1.)
        self._refresh_quiet()
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
        panel = getattr(self, "tools_panel", None)
        if panel is not None: panel.hide()
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

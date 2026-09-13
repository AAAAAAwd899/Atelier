"""Quiet review presentation. No collection, scheduler or persistence access.

The normal view has one compact status row, the untouched native card webview,
and one answer row. Optional controls live in a click-open, dismissible popup.
Qt imports are lazy so the presentation policy can be tested without Qt.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewView:
    mode: str
    mode_help: str
    primary: str
    primary_help: str
    hint: str
    grades: str  # none, practice or learning
    previous: bool = False
    skip: bool = False


def review_view(session, *, native_new: bool = False, mistake: bool = False,
                answer_visible: bool = False, render_error: bool = False) -> ReviewView:
    """Labels describe actual per-card behavior, never a predicted grade."""
    if mistake:
        return ReviewView(
            "Mistake review · no changes",
            "Compare the original card and any saved response. This does not change your result or card schedule.",
            "Hide answer" if answer_visible else "Show answer",
            "Show or hide the original answer; no grade is recorded.",
            "Space: flip card · Tools: your saved answer", "none", True, True)
    if session.phase == "answering":
        last = session.index + 1 == len(session.cards)
        return ReviewView(
            "Mock exam · answers hidden",
            "Answers stay hidden until you finish. Answered records a mental answer, not a correct answer. Skip leaves it for later.",
            "Answered · finish" if last else "Answered · next",
            "Record that you answered without typing, then " + ("review the submission summary." if last else "go to the next question."),
            "Answered records an attempt, not correctness · Tools: type or revisit",
            "none", False, True)
    if native_new:
        return ReviewView(
            "New card · updates Anki",
            "You enabled new-card learning. After showing the answer, Again / Hard / Good / Easy changes this new card's Anki learning schedule.",
            "Show answer", "Show the answer. No Anki rating is saved until you choose one.",
            "1–4: rate in Anki" if session.revealed else "Space: show answer · ratings update Anki",
            "learning" if session.revealed and not render_error else "none")
    if session.phase == "grading":
        return ReviewView(
            "Check answers · no rescheduling",
            "Mark the answer you gave before submission. These marks affect this practice result, not Anki's schedule. They do not predict your exam grade.",
            "Show answer", "Show the original answer.",
            "1: Missed · 2: Partial · 3: Correct", "practice" if not render_error else "none")
    return ReviewView(
        "Practice · no rescheduling",
        "Recall first, then show the answer and mark yourself. Previously learned cards are independent rehearsal: their Anki schedules do not change.",
        "Show answer", "Show the answer, then mark what you recalled.",
        "1: Missed · 2: Partial · 3: Correct" if session.revealed else "Space: show answer · Tools: optional study aids",
        "practice" if session.revealed and not render_error else "none")


def keyboard_actions(session, *, native_new=False, mistake=False,
                     answer_visible=False, render_error=False, busy=False) -> dict[str, str]:
    """Allow only currently meaningful keys. Space never guesses a grade."""
    if busy or session.phase == "finished":
        return {}
    actions = {"t": "tools"}
    if mistake:
        return {**actions, " ": "primary", "ArrowLeft": "previous", "ArrowRight": "skip"}
    if session.phase == "answering":
        return {**actions, " ": "primary", "Enter": "primary"}
    if not session.revealed:
        if not render_error:
            actions[" "] = "primary"
            actions["Enter"] = "primary"
        return actions
    if render_error:
        return actions
    if native_new:
        return {**actions, **{str(n): "learn:" + str(n) for n in range(1, 5)}}
    values = ("0", "0.5", "1")
    if session.phase == "grading" and session.current.id not in getattr(session, "attempted", set()):
        values = ("0",)
    return {**actions, **{str(i + 1): "grade:" + value for i, value in enumerate(values)}}


def build_review_ui(runner) -> None:
    from aqt import gui_hooks
    from aqt.qt import (Qt, QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                        QPushButton, QProgressBar, QComboBox, QSplitter,
                        QPlainTextEdit, QScrollArea, QFrame, QSizePolicy)
    from aqt.webview import AnkiWebView, AnkiWebViewKind
    from aqt.theme import theme_manager

    r = runner
    dark = bool(theme_manager.night_mode)
    # Neutral Anki-like chrome, not the world's large decorative panels. The
    # actual card document keeps its own CSS, including third-party masks/media.
    bg, raised, fg, muted, line, accent, on_accent = (
        ("#292929", "#343434", "#eeeeee", "#b4b4b4", "#454545", "#bfd2b2", "#1d2c18") if dark else
        ("#f5f5f4", "#ffffff", "#262c29", "#626b66", "#dadfda", "#426547", "#ffffff"))
    palette = getattr(r.controller, 'suite_palette', lambda: None)()
    if palette:
        bg,raised,fg,muted,line,accent,on_accent = [palette[k] for k in ('side','panel','text','muted','line','accent','on-accent')]
    r.setStyleSheet(f"""
    QWidget#esReviewHeader, QWidget#esReviewFooter, QDialog#esReviewTools,
    QWidget#esToolsContent, QWidget#esAnswerNotes {{ background:{bg}; color:{fg}; }}
    QWidget#esReviewHeader QLabel, QWidget#esReviewFooter QLabel,
    QDialog#esReviewTools QLabel, QWidget#esAnswerNotes QLabel {{ color:{fg}; }}
    QWidget#esReviewHeader QLabel#esMode, QWidget#esReviewFooter QLabel#esKeyHint {{ color:{muted}; font-size:11px; }}
    QWidget#esReviewHeader {{ border-bottom:1px solid {line}; }}
    QWidget#esReviewFooter {{ border-top:1px solid {line}; }}
    QPushButton#esReviewAction, QDialog#esReviewTools QPushButton,
    QWidget#esAnswerNotes QPushButton {{ background:{raised}; color:{fg}; border:1px solid {line}; border-radius:6px; padding:6px 12px; min-height:20px; font-size:13px; }}
    QPushButton#esReviewAction:hover, QDialog#esReviewTools QPushButton:hover {{ border-color:{accent}; }}
    QPushButton#esReviewAction:focus, QDialog#esReviewTools QPushButton:focus {{ border:2px solid {accent}; padding:5px 11px; }}
    QPushButton#esReviewAction:disabled, QDialog#esReviewTools QPushButton:disabled {{ color:{muted}; }}
    QPushButton#esReviewAction[primary="true"] {{ background:{accent}; color:{on_accent}; border-color:{accent}; }}
    QDialog#esReviewTools QComboBox {{ background:{raised}; color:{fg}; border:1px solid {line}; border-radius:5px; padding:7px; min-height:20px; }}
    QDialog#esReviewTools QComboBox QAbstractItemView {{ background:{raised}; color:{fg}; selection-background-color:{accent}; selection-color:{on_accent}; }}
    QPlainTextEdit#esResponse {{ border:1px solid {line}; border-radius:6px; padding:9px; background:{raised}; color:{fg}; font-size:14px; }}
    QScrollArea#esToolsScroll {{ border:0; background:{bg}; }}
    QLabel#esReviewNotice {{ background:{raised}; color:{fg}; padding:8px 16px; border-bottom:1px solid {line}; font-size:12px; }}
    """)
    r.setWindowTitle(f"{r.exam.name} · {'Atelier Exam Studio' if getattr(r.controller, 'suite', None) is not None else 'Exam Sprout'}")
    r.vbox = QVBoxLayout(r)
    r.vbox.setContentsMargins(0, 0, 0, 0); r.vbox.setSpacing(0)
    r.top = QWidget(r); r.top.setObjectName("esReviewHeader")
    top = QHBoxLayout(r.top); top.setContentsMargins(16, 8, 16, 8); top.setSpacing(12)
    r.mode_label = QLabel(r.top); r.mode_label.setObjectName("esMode")
    r.mode_label.setTextFormat(Qt.TextFormat.PlainText)
    top.addWidget(r.mode_label); top.addStretch(1)
    r.heading = QLabel(r.top); r.heading.setTextFormat(Qt.TextFormat.PlainText)
    r.heading.setStyleSheet("font-size:12px;font-weight:600;")
    top.addWidget(r.heading)
    r.clock = QLabel(r.top); r.clock.setStyleSheet("font-size:12px;font-weight:600;")
    r.clock.setAccessibleName("Time remaining")
    top.addWidget(r.clock); r.vbox.addWidget(r.top)
    r.notice = QLabel(r); r.notice.setObjectName("esReviewNotice")
    r.notice.setWordWrap(True); r.notice.setTextFormat(Qt.TextFormat.PlainText); r.notice.hide()
    r.vbox.addWidget(r.notice)
    # Kept for the existing session contract, hidden instead of consuming a row.
    r.progress_bar = QProgressBar(r); r.progress_bar.setRange(0, len(r.session.cards))
    r.progress_bar.setTextVisible(False); r.progress_bar.hide()
    r._web = AnkiWebView(r, kind=AnkiWebViewKind.PREVIEWER)
    r.split = QSplitter(Qt.Orientation.Horizontal, r)
    r.split.addWidget(r._web)
    r.side = QWidget(r); r.side.setObjectName("esAnswerNotes")
    r.side_layout = QVBoxLayout(r.side); r.side_layout.setContentsMargins(12, 12, 12, 12)
    label_row = QHBoxLayout()
    r.response_label = QLabel("Your answer", r.side)
    r.response_label.setTextFormat(Qt.TextFormat.PlainText); r.response_label.setWordWrap(True)
    label_row.addWidget(r.response_label, 1)
    close_notes = r._button("Close", r._toggle_side, r.side)
    close_notes.setAccessibleName("Close written-answer panel")
    label_row.addWidget(close_notes); r.side_layout.addLayout(label_row)
    r.response = QPlainTextEdit(r.side); r.response.setObjectName("esResponse")
    r.response.setAccessibleName("Your written answer")
    r.response.setPlaceholderText("Recall it in your own words…")
    r.response.setMinimumHeight(82)
    r.side_layout.addWidget(r.response, 1)
    r.side_hint = QLabel("Optional. Kept while this session is open. Save and close stores unfinished answers locally (up to 10,000 characters per response).", r.side)
    r.side_hint.setWordWrap(True); r.side_hint.setStyleSheet(f"font-size:11px;color:{muted};")
    r.side_layout.addWidget(r.side_hint)
    r.split.addWidget(r.side); r.split.setStretchFactor(0, 1); r.split.setStretchFactor(1, 0)
    r.split.setSizes([900, 290]); r.side.hide()
    r._side_open = False; r._side_axis = None
    r.vbox.addWidget(r.split, 1)
    r.response.textChanged.connect(r._save_response)
    gui_hooks.card_review_webview_did_init(r._web, AnkiWebViewKind.PREVIEWER)

    # Native popup: no hover-open, no extra webview, no permanent sidebar. Qt
    # Popup closes on outside click/Escape and returns to the underlying card.
    class ToolsPopup(QDialog):
        def hideEvent(self, event):
            super().hideEvent(event)
            if getattr(r, "_open", False) and r._web is not None:
                r.tools_button.setChecked(False)
        def reject(self):
            self.hide()
    r.tools_panel = ToolsPopup(r, Qt.WindowType.Popup)
    r.tools_panel.setObjectName("esReviewTools")
    r.tools_panel.setWindowTitle("Study tools")
    outer = QVBoxLayout(r.tools_panel); outer.setContentsMargins(14, 12, 14, 12); outer.setSpacing(8)
    title_row = QHBoxLayout(); title = QLabel("Study tools", r.tools_panel)
    title.setStyleSheet("font-weight:600;font-size:14px;"); title_row.addWidget(title, 1)
    close_tools = r._button("Done", r._close_tools, r.tools_panel)
    close_tools.setAccessibleName("Close study tools"); title_row.addWidget(close_tools); outer.addLayout(title_row)
    r.tools_scroll = QScrollArea(r.tools_panel); r.tools_scroll.setObjectName("esToolsScroll")
    r.tools_scroll.setWidgetResizable(True); r.tools_scroll.setFrameShape(QFrame.Shape.NoFrame)
    contents = QWidget(); contents.setObjectName("esToolsContent")
    body = QVBoxLayout(contents); body.setContentsMargins(0, 0, 7, 0); body.setSpacing(8)
    r.tools_scroll.setWidget(contents); outer.addWidget(r.tools_scroll, 1)
    def section(label):
        w = QLabel(label, contents); w.setStyleSheet(f"font-size:11px;color:{muted};margin-top:8px;")
        body.addWidget(w)
    def tool(label, handler):
        return r._button(label, lambda checked=False: r._run_tool(handler), contents)
    def pair(*widgets):
        row=QHBoxLayout();row.setSpacing(8)
        for w in widgets:row.addWidget(w, 1)
        body.addLayout(row)
    section("THIS QUESTION")
    r.notes_button = tool("Write an answer", r._toggle_side)
    r.flag = tool("Bookmark question", r._flag); pair(r.notes_button, r.flag)
    r.attempt_button = r._button("I answered without typing", r._attempt, contents)
    body.addWidget(r.attempt_button)
    r.confidence_control = QComboBox(contents)
    r.confidence_control.setAccessibleName("How sure are you? Optional; recorded before showing the answer")
    for text in ("How sure are you? (optional)", "Guessing", "Somewhat sure", "Very sure"):
        r.confidence_control.addItem(text)
    r.confidence_control.activated.connect(r._confidence); body.addWidget(r.confidence_control)
    r.error_control = QComboBox(contents)
    r.error_control.setAccessibleName("What went wrong? Optional")
    for text in ("What went wrong? (optional)", "Forgot the fact", "Did not understand", "Could not apply it", "Misread the question", "Calculation mistake", "Guessed"):
        r.error_control.addItem(text)
    r.error_control.activated.connect(r._error_category); body.addWidget(r.error_control)
    section("CARD DISPLAY")
    r.replay = tool("Replay audio", r._replay_audio)
    r.fit_button = tool("Fit to window", r._fit_card); pair(r.replay, r.fit_button)
    r.reset_zoom_button = tool("Original size", r._reset_zoom); body.addWidget(r.reset_zoom_button)
    section("THIS SESSION")
    r.navigator = QComboBox(contents); r.navigator.setAccessibleName("Go to question")
    r.navigator.activated.connect(r._jump_from_tools); body.addWidget(r.navigator)
    factory = getattr(r.controller, 'suite_navigation_factory', None)
    r._suite_navigation = factory(r, contents, body) if callable(factory) else None
    r.previous_tool = tool("Previous question", r._previous)
    r.skip_tool = tool("Skip this question", r._skip); pair(r.previous_tool, r.skip_tool)
    r.save_close = tool("Save and close", r._save_close)
    r.submit_now = tool("Finish exam…", r._submit_now); pair(r.save_close, r.submit_now)
    r.explainer = QLabel(contents); r.explainer.setWordWrap(True); r.explainer.setTextFormat(Qt.TextFormat.PlainText)
    r.explainer.setStyleSheet(f"font-size:11px;color:{muted};margin-top:8px;"); body.addWidget(r.explainer)
    r.safety = QLabel(contents); r.safety.setWordWrap(True); r.safety.setTextFormat(Qt.TextFormat.PlainText)
    r.safety.setStyleSheet(f"font-size:11px;color:{muted};"); body.addWidget(r.safety)
    body.addStretch(1)

    r.bottom = QWidget(r); r.bottom.setObjectName("esReviewFooter")
    controls = QVBoxLayout(r.bottom); controls.setContentsMargins(14, 8, 14, 7); controls.setSpacing(4)
    row = QHBoxLayout(); row.setSpacing(8)
    left = QWidget(r.bottom); left.setFixedWidth(78); ll = QHBoxLayout(left);ll.setContentsMargins(0,0,0,0)
    r.tools_button = r._button("Tools", r._toggle_tools, left)
    r.tools_button.setObjectName("esReviewAction");r.tools_button.setCheckable(True)
    r.tools_button.setToolTip("Optional notes, bookmarks, confidence, card display and session actions (T)")
    ll.addWidget(r.tools_button);row.addWidget(left);row.addStretch(1)
    r.previous = r._button("Previous", r._previous, r.bottom)
    r.skip_button = r._button("Skip", r._skip, r.bottom)
    r.primary = r._button("Show answer", r._advance_primary, r.bottom)
    r.primary.setProperty("primary", True)
    r.primary.setMinimumWidth(128)
    row.addWidget(r.previous);row.addWidget(r.primary);row.addWidget(r.skip_button)
    r.grade_buttons=[]
    for label,score in (("Missed",0),("Partial",.5),("Correct",1)):
        b=r._button(label,lambda checked=False,score=score:r._grade(score),r.bottom)
        b.setMinimumWidth(76);b.setToolTip("Self-mark this practice answer; no Anki rescheduling.")
        r.grade_buttons.append(b);row.addWidget(b)
    r.learning_buttons=[]
    for rating,label in enumerate(("Again","Hard","Good","Easy"),1):
        b=r._button(label,lambda checked=False,rating=rating:r._schedule_rating(rating),r.bottom)
        b.setMinimumWidth(66);b.setToolTip("Record this rating in Anki for this new card.")
        r.learning_buttons.append(b);row.addWidget(b);b.hide()
    for b in [r.previous,r.skip_button,r.primary,*r.grade_buttons,*r.learning_buttons]:
        b.setObjectName("esReviewAction")
        # Mouse clicks keep the card focused; Tab still reaches every control.
        b.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    row.addStretch(1)
    right=QWidget(r.bottom);right.setFixedWidth(78);rr=QHBoxLayout(right);rr.setContentsMargins(0,0,0,0);rr.addStretch(1)
    r._pip_web=None;r._pip_badge=None
    if (r.controller.store.state["settings"].get("show_pip",True)
            and r.controller.store.state["settings"].get("reviewer_pip",True)):
        try:
            from .companion import TinyPip
            badge=TinyPip(r.controller,right)
            growth=r.controller.growth_cache.get(r.exam.id,{"stage":1})
            badge.configure(growth.get("stage",1),r.controller.store.state["settings"].get("animate_pip",True))
            r._pip_badge=badge;rr.addWidget(badge)
        except Exception:
            from .runner import LOG
            LOG.exception("Tiny Pip is unavailable; the card session is unchanged")
    row.addWidget(right);controls.addLayout(row)
    r.key_hint=QLabel(r.bottom);r.key_hint.setObjectName("esKeyHint")
    r.key_hint.setTextFormat(Qt.TextFormat.PlainText);r.key_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    r.key_hint.setWordWrap(True);controls.addWidget(r.key_hint)
    r.vbox.addWidget(r.bottom)
    r._review_ui_ready=True

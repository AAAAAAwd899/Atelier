"""Responsive Qt chrome around the original Sprout Previewer.

Reuses every existing control, signal, native card webview, notes editor and Pip
badge. No HTML wrapper/stylesheet/JavaScript is injected into a practice card.
Only Atelier's own integrated runner is adapted, never a foreign review window.
"""
from __future__ import annotations
import logging
from aqt.qt import (QObject, QEvent, Qt, QWidget, QLabel, QFrame, QVBoxLayout,
                    QHBoxLayout, QGridLayout, QPushButton, QComboBox, QTimer)
from .session_model import PAGE_SIZE, question_page, next_question, presentation
LOG = logging.getLogger('atelier.session')

class SessionChrome(QObject):
    def __init__(self, runner):
        super().__init__(runner)
        self.r = runner
        self.filter = 'all'
        self.page = 0
        self.last_layout = None
        self.last_map = None
        self.notes_orientation = None
        self.last_stage = None
        self.relayout = QTimer(self)
        self.relayout.setSingleShot(True)
        self.relayout.timeout.connect(self.adapt)
        self.build()
        runner.installEventFilter(self)

    @staticmethod
    def label(text='', name=''):
        w = QLabel(text)
        w.setTextFormat(Qt.TextFormat.PlainText)
        w.setObjectName(name)
        return w

    def button(self, text, handler):
        b = QPushButton(text)
        b.setAutoDefault(False)
        b.clicked.connect(handler)
        b.setMinimumHeight(32)
        return b

    def build(self):
        r = self.r
        # Retain original containers until all their live children have moved.
        old_top = r.vbox.itemAt(0).widget()
        old_bottom = r.vbox.itemAt(r.vbox.count() - 1).widget()
        r.vbox.removeWidget(old_top); r.vbox.removeWidget(old_bottom)
        self.top = QFrame(r); self.top.setObjectName('esSessionTop')
        v = QVBoxLayout(self.top); v.setContentsMargins(18, 12, 18, 10); v.setSpacing(8)
        line = QHBoxLayout()
        self.phase = self.label('', 'esSessionPhase'); self.phase.setWordWrap(True)
        self.status = self.label('', 'esSessionStatus')
        line.addWidget(self.phase); line.addWidget(self.status, 1); line.addWidget(r.clock)
        v.addLayout(line)
        self.heading_row = QGridLayout(); self.heading_row.setColumnStretch(0, 1)
        r.heading.setStyleSheet(''); r.heading.setObjectName('esSessionHeading')
        r.heading.setMinimumWidth(0); r.clock.setStyleSheet(''); r.clock.setObjectName('esSessionClock')
        self.heading_row.addWidget(r.heading, 0, 0)
        self.heading_row.addWidget(r.save_close, 0, 1)
        v.addLayout(self.heading_row)
        self.mode_note = self.label('', 'esSessionMode'); self.mode_note.setWordWrap(True)
        v.addWidget(self.mode_note)
        self.navrow = QWidget(self.top); nl = QHBoxLayout(self.navrow); nl.setContentsMargins(0, 0, 0, 0); nl.setSpacing(8)
        self.map_toggle = self.button('Question map', self.toggle_map)
        self.map_toggle.setCheckable(True)
        self.next_flagged = self.button('Next flagged', lambda: self.jump_next('flagged'))
        self.next_unanswered = self.button('Next unanswered', lambda: self.jump_next('unanswered'))
        nl.addWidget(r.navigator, 1); nl.addWidget(self.next_unanswered); nl.addWidget(self.next_flagged); nl.addWidget(self.map_toggle)
        v.addWidget(self.navrow)
        self.mapbox = QFrame(self.top); self.mapbox.setObjectName('esQuestionMap')
        mv = QVBoxLayout(self.mapbox); mv.setContentsMargins(12, 10, 12, 10); mv.setSpacing(8)
        filters = QHBoxLayout(); self.map_filter = QComboBox(self.mapbox)
        self.map_filter.setAccessibleName('Filter question map')
        for label, value in [('All questions', 'all'), ('Unanswered', 'unanswered'), ('Flagged', 'flagged')]: self.map_filter.addItem(label, value)
        self.map_filter.activated.connect(self.change_filter)
        self.map_label = self.label('', 'esMapLabel')
        self.prev_page = self.button('Previous page', lambda: self.move_page(-1))
        self.next_page = self.button('Next page', lambda: self.move_page(1))
        filters.addWidget(self.map_filter); filters.addWidget(self.map_label, 1); filters.addWidget(self.prev_page); filters.addWidget(self.next_page)
        mv.addLayout(filters)
        grid = QGridLayout(); grid.setSpacing(5); self.map_buttons = []
        for i in range(PAGE_SIZE):
            b = self.button('', lambda _=False, slot=i: self.jump_slot(slot))
            b.setCheckable(True); b._target_index = None; b.setMinimumWidth(38)
            self.map_buttons.append(b); grid.addWidget(b, i // 8, i % 8)
        mv.addLayout(grid); self.mapbox.hide(); v.addWidget(self.mapbox)
        r.vbox.insertWidget(0, self.top)
        self.bottom = QFrame(r); self.bottom.setObjectName('esSessionBottom')
        b = QVBoxLayout(self.bottom); b.setContentsMargins(18, 10, 18, 12); b.setSpacing(8)
        self.response_controls = QWidget(self.bottom); checks = QHBoxLayout(self.response_controls); checks.setContentsMargins(0, 0, 0, 0)
        checks.addWidget(r.attempt_button); checks.addWidget(r.confidence_control); checks.addWidget(r.error_control); checks.addStretch(1)
        b.addWidget(self.response_controls)
        self.tools = QWidget(self.bottom); tools = QHBoxLayout(self.tools); tools.setContentsMargins(0, 0, 0, 0); tools.setSpacing(8)
        for w in (r.replay, r.fit_button, r.notes_button, r.flag): tools.addWidget(w)
        self.detail_toggle = self.button('Guidance', self.toggle_guidance); self.detail_toggle.setCheckable(True)
        tools.addStretch(1); tools.addWidget(self.detail_toggle)
        if r._pip_badge is not None: tools.addWidget(r._pip_badge)
        b.addWidget(self.tools)
        self.guidance = QFrame(self.bottom); self.guidance.setObjectName('esSessionGuidance')
        gv = QVBoxLayout(self.guidance); gv.setContentsMargins(10, 6, 10, 6); gv.addWidget(r.explainer)
        r.explainer.setStyleSheet(''); self.guidance.hide(); b.addWidget(self.guidance)
        self.action_grid = QGridLayout(); self.action_grid.setSpacing(8)
        self.back_group = QWidget(self.bottom); bg = QHBoxLayout(self.back_group); bg.setContentsMargins(0, 0, 0, 0)
        bg.addWidget(r.previous); bg.addWidget(r.skip_button)
        self.rating_group = QWidget(self.bottom); self.rating_grid = QGridLayout(self.rating_group); self.rating_grid.setContentsMargins(0, 0, 0, 0); self.rating_grid.setSpacing(8)
        for w in (r.primary, *r.grade_buttons, *r.learning_buttons): w.setMinimumHeight(40)
        r.primary.setObjectName('esSessionPrimary')
        for w in r.learning_buttons: w.setObjectName('esNativeRating')
        r.submit_now.setObjectName('esSessionSubmit')
        self.action_grid.addWidget(self.back_group, 0, 0); self.action_grid.addWidget(self.rating_group, 0, 1)
        self.action_grid.setColumnStretch(1, 1); b.addLayout(self.action_grid)
        r.safety.setStyleSheet(''); r.safety.setObjectName('esSessionSafety'); b.addWidget(r.safety)
        r.vbox.addWidget(self.bottom)
        # The legacy top-right submit action is retained in the compact header.
        self.heading_row.addWidget(r.submit_now, 0, 2)
        r.side.setObjectName('esSessionNotes'); r.side_hint.setStyleSheet('')
        r.response_label.setStyleSheet(''); r.response_label.setWordWrap(True)
        self.note_count = self.label('', 'esNoteCount'); r.side_layout.insertWidget(1, self.note_count)
        r.side_hint.setText('In memory while this session is open. Save & close stores an unfinished session locally, including these answers. Completed-answer retention follows your privacy setting.')
        r.response_label.setBuddy(r.response); r.response.setAccessibleName('Your written response')
        old_top.hide(); old_bottom.hide()
        self.retired_containers = (old_top, old_bottom)
        self.style()
        self.refresh()

    def style(self):
        p = self.r.controller.suite_palette() or {}
        if not p:
            from aqt.theme import theme_manager
            p = ({'bg':'#242925','text':'#ecf0ed','muted':'#b2bab5','panel':'#2a302c','raised':'#343c36','line':'#424b45','accent':'#a0bea6','on-accent':'#18251c'} if theme_manager.night_mode else {'bg':'#f6f8f5','text':'#26392e','muted':'#58685d','panel':'#ffffff','raised':'#edf1eb','line':'#cad5cc','accent':'#53755b','on-accent':'#ffffff'})
        fg=p.get('text','#e8eee9'); muted=p.get('muted','#b6c3b9'); panel=p.get('panel','#15241d')
        bg=p.get('bg',panel); raised=p.get('raised',panel); line=p.get('line','#3c5144'); accent=p.get('accent','#c4d493'); on=p.get('on-accent','#152419')
        q = f'''
QFrame#esSessionTop, QFrame#esSessionBottom {{ background:{bg};color:{fg};border:0; }}
QFrame#esSessionTop {{border-bottom:1px solid {line};}} QFrame#esSessionBottom {{border-top:1px solid {line};}}
QFrame#esSessionTop QLabel, QFrame#esSessionBottom QLabel, QWidget#esSessionNotes QLabel {{ color:{fg};background:transparent; }}
QLabel#esSessionHeading {{font-size:16px;font-weight:600;}} QLabel#esSessionClock {{font-size:16px;font-weight:600;}}
QLabel#esSessionPhase {{font-size:12px;font-weight:600;background:{raised};border:1px solid {line};border-radius:8px;padding:5px 9px;color:{accent};}}
QLabel#esSessionStatus, QLabel#esSessionMode, QLabel#esSessionSafety, QLabel#esNoteCount, QLabel#esMapLabel {{font-size:11px;color:{muted};}}
QFrame#esSessionTop QPushButton, QFrame#esSessionBottom QPushButton {{padding:7px 11px;border:1px solid {line};border-radius:9px;background:{panel};color:{fg};font-size:12px;}}
QFrame#esSessionTop QPushButton:hover, QFrame#esSessionBottom QPushButton:hover {{border-color:{accent};}}
QFrame#esSessionTop QPushButton:focus, QFrame#esSessionBottom QPushButton:focus {{border:2px solid {accent};}}
QFrame#esSessionTop QPushButton:disabled, QFrame#esSessionBottom QPushButton:disabled {{color:{muted};}}
QFrame#esSessionBottom QPushButton#esSessionPrimary, QFrame#esSessionBottom QPushButton#esNativeRating {{background:{accent};color:{on};font-weight:600;}}
QFrame#esSessionTop QPushButton:checked {{border:2px solid {accent};}}
QFrame#esQuestionMap, QFrame#esSessionGuidance {{background:{panel};border:1px solid {line};border-radius:10px;}}
QWidget#esSessionNotes {{background:{panel};border-left:1px solid {line};}}
QWidget#esSessionNotes QPlainTextEdit {{background:{bg};color:{fg};border:1px solid {line};border-radius:10px;padding:12px;font-size:14px;selection-background-color:{accent};selection-color:{on};}}
QFrame#esSessionTop QComboBox, QFrame#esSessionBottom QComboBox {{padding:7px;background:{panel};color:{fg};border:1px solid {line};border-radius:8px;}}
QFrame#esSessionTop QComboBox QAbstractItemView, QFrame#esSessionBottom QComboBox QAbstractItemView {{background:{panel};color:{fg};selection-background-color:{accent};selection-color:{on};}}
QProgressBar {{background:{line};border:0;max-height:3px;}} QProgressBar::chunk {{background:{accent};}}
'''
        # One style on this owned dialog; never QApplication or the main reviewer.
        self.r.setStyleSheet(q)

    def eventFilter(self, obj, event):
        if obj is self.r and event.type() == QEvent.Type.Resize:
            self.relayout.start(0)
        return False

    def adapt(self):
        if getattr(self.r, 'finished_once', False): return
        r=self.r
        compact_notes = r.width() < 1040 or r.height() < 650
        # A narrow stage switches between card and notes. Do not shrink a card
        # into a tiny box above a tall editor, or rescale an occlusion image.
        orientation = Qt.Orientation.Horizontal
        if self.notes_orientation != compact_notes:
            self.notes_orientation = compact_notes
            r.side.setMinimumWidth(0); r.side.setMaximumWidth(16777215)
            r.split.setOrientation(orientation)
            if not compact_notes:
                r.side.setMinimumWidth(240); r.side.setMaximumWidth(380); r.split.setSizes([850,300])
        if compact_notes:
            showing_notes = bool(r._side_open)
            if r._web is not None: r._web.setVisible(not showing_notes)
            r.side.setVisible(showing_notes)
            r.notes_button.setText('Show card' if showing_notes else 'Original answer' if hasattr(r,'saved_answers') else 'Write answer')
            r.fit_button.setEnabled(not showing_notes)
            r.side_hint.setVisible(r.height() >= 650)
        else:
            if r._web is not None:r._web.show()
            r.side.setVisible(r._side_open); r.fit_button.setEnabled(True); r.side_hint.show()
            r.notes_button.setText('Hide answer notes' if r._side_open else 'Original answer' if hasattr(r,'saved_answers') else 'Write answer')
        narrow=r.width()<850
        visible=[w for w in (r.primary,*r.grade_buttons,*r.learning_buttons) if not w.isHidden()]
        key=(narrow,tuple(id(w) for w in visible))
        if key != self.last_layout:
            self.last_layout=key
            # Remove layout items only, keeping original widgets/signals/focus.
            while self.rating_grid.count(): self.rating_grid.takeAt(0)
            for col in range(4): self.rating_grid.setColumnStretch(col,0)
            cols=2 if narrow and len(visible)>2 else max(1,len(visible))
            for i,w in enumerate(visible): self.rating_grid.addWidget(w,i//cols,i%cols);self.rating_grid.setColumnStretch(i%cols,1)
        # In a short window the map temporarily occupies the card stage rather
        # than forcing the native card/response editor into a clipped sliver.
        # Hiding the splitter does not rebuild it or discard a response.
        map_open = not self.mapbox.isHidden()
        r.split.setVisible(not (map_open and r.height() < 740))
        self.map_toggle.setText('Close map' if map_open else 'Question map')
        # Decorative guidance is collapsed by default; render errors surface it.
        self.status.setVisible(r.width()>=750)

    def toggle_map(self):
        self.mapbox.setVisible(self.map_toggle.isChecked())
        self.refresh_map()
        self.adapt()

    def toggle_guidance(self):
        self.guidance.setVisible(self.detail_toggle.isChecked())

    def change_filter(self, index):
        self.filter=self.map_filter.itemData(index) or 'all';self.page=0;self.refresh_map()

    def move_page(self, delta):
        self.page=max(0,self.page+delta);self.refresh_map()

    def jump_slot(self, slot):
        i=self.map_buttons[slot]._target_index
        if type(i) is int and self.r.session.phase=='answering':
            self.r._jump(i)
            self.map_toggle.setChecked(False); self.mapbox.hide(); self.adapt()
            self.map_toggle.setFocus()

    def jump_next(self, view):
        index=next_question(self.r.session,view)
        if index is not None:self.r._jump(index)

    def refresh_map(self):
        data=question_page(self.r.session,self.filter,self.page);self.page=data['page']
        self.map_label.setText(data['label']);self.prev_page.setEnabled(self.page>0);self.next_page.setEnabled(self.page+1<data['pages'])
        for slot,b in enumerate(self.map_buttons):
            if slot>=len(data['rows']):b.hide();b._target_index=None;continue
            row=data['rows'][slot];b._target_index=row['index'];b.setText(str(row['number'])+(' •' if row['flagged'] else ' ✓' if row['answered'] else ''))
            b.setAccessibleName(row['label']);b.setToolTip(row['label']);b.setChecked(row['current']);b.show()

    def refresh(self):
        r=self.r
        if getattr(r,'finished_once',False):return
        readonly=hasattr(r,'saved_answers')
        stage=(r.session.current.id, r._state)
        compact_notes=r.width()<1040 or r.height()<650
        if compact_notes and ((self.last_stage is not None and stage[1]=='answer' and self.last_stage[1]!='answer') or (readonly and self.last_stage is None)):
            r._side_open=False
        self.last_stage=stage
        state=presentation(r.session,read_only=readonly,current_new=getattr(r,'_native_new_card',False),render_error=getattr(r,'_render_error',False))
        self.phase.setText(state['title']);self.phase.setAccessibleName(state['title']);self.mode_note.setText(state['note'])
        self.status.setText(state['summary']);r.progress_bar.setValue(state['progress'])
        self.navrow.setVisible(state['navigation']);self.mapbox.setVisible(state['navigation'] and self.map_toggle.isChecked())
        self.next_flagged.setEnabled(next_question(r.session,'flagged') is not None)
        self.next_unanswered.setEnabled(next_question(r.session,'unanswered') is not None)
        self.response_controls.setVisible(not readonly)
        r.safety.setText(state['note'])
        if state['render_error']:
            self.detail_toggle.setChecked(True);self.guidance.show()
        self.note_count.setText(('Read-only response' if r.response.isReadOnly() else 'Not automatically saved')+f' · {len(r.response.toPlainText()):,} / 10,000 characters')
        if not r.response.isReadOnly() and len(r.response.toPlainText())>10000:
            self.note_count.setText('Only the first 10,000 characters are retained by this session.')
        if self.map_toggle.isChecked():self.refresh_map()
        self.adapt()

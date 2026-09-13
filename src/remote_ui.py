"""Native, scrollable remote setup. Opened deliberately; never added to review chrome."""
from __future__ import annotations
import platform
from .remote_model import ACTIONS, valid_key, key_name
from .review_model import PALETTES

def create_dialog(controller,mw):
    from aqt.qt import (QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,
                        QCheckBox,QScrollArea,QWidget,Qt,QEvent)
    class RemoteDialog(QDialog):
        def __init__(self):
            super().__init__(mw)
            self.setWindowTitle('Atelier · Remote controls');self.resize(800,690);self.setMinimumSize(520,420)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
            self.binding=dict(controller.config()['bindings']);self.waiting=None;self.testing=False;self.changed=False
            layout=QVBoxLayout(self);layout.setContentsMargins(20,18,20,18)
            title=QLabel('Remote controls',self);title.setObjectName('remoteTitle');layout.addWidget(title)
            hint=QLabel('Pair once. Test safely. Keep the reviewer clear.',self);layout.addWidget(hint)
            scroll=QScrollArea(self);scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            content=QWidget();box=QVBoxLayout(content);box.setSpacing(14);box.setContentsMargins(0,12,8,12)
            def text(value):
                label=QLabel(value,content);label.setWordWrap(True);box.addWidget(label);return label
            text('1  Connect your remote in your computer’s Bluetooth settings, or plug in its USB receiver. Select Keyboard / Key mode on the remote when available.')
            text('macOS: System Settings → Bluetooth.' if platform.system()=='Darwin' else 'Windows: Settings → Bluetooth & devices → Add device → Bluetooth.' if platform.system()=='Windows' else 'Use your system Bluetooth settings to pair the remote.')
            text('2  Standard Anki keys already work: Space / Return shows the answer; 1–4 choose a rating on the answer side. Anki’s own settings control their exact behavior. No custom mapping is required for a remote that already sends your Anki shortcuts.')
            self.test=QPushButton('Test remote buttons — no cards affected',content);box.addWidget(self.test)
            self.status=text('Ready to test. Click Test, then press a remote button. Escape stops testing.')
            self.status.setObjectName('remoteStatus');self.test.clicked.connect(self.start_test)
            self.enabled=QCheckBox('Use custom buttons during scheduled review',content)
            self.enabled.setChecked(controller.config()['enabled']);box.addWidget(self.enabled)
            self.enabled.toggled.connect(lambda *_:setattr(self,'changed',True))
            text('Optional: choose Assign, then press the desired button. Changes apply only after Save. Custom buttons also affect those same keys on your keyboard during review; text fields, other windows and practice sessions keep their own controls.')
            grid=QGridLayout();grid.setHorizontalSpacing(10);grid.setVerticalSpacing(8);self.labels={}
            for i,(action,label) in enumerate(ACTIONS.items()):
                grid.addWidget(QLabel(label,content),i,0)
                badge=QLabel(key_name(self.binding.get(action)),content);self.labels[action]=badge;grid.addWidget(badge,i,1)
                learn=QPushButton('Assign',content);learn.setAccessibleName('Assign remote button for '+label);grid.addWidget(learn,i,2)
                clear=QPushButton('Clear',content);clear.setAccessibleName('Clear remote button for '+label);grid.addWidget(clear,i,3)
                learn.clicked.connect(lambda checked=False,a=action:self.learn(a))
                clear.clicked.connect(lambda checked=False,a=action:self.clear(a))
            box.addLayout(grid)
            text('Show answer never also grades a card in the custom mapping. Rating buttons work only after reveal. Hold/repeat signals are ignored. No remote banner is added to your cards.')
            text('Already using Contanki or the manufacturer’s add-on? Leave custom buttons off here to avoid two mappings. Gamepad-only, mouse-only and proprietary Bluetooth devices are not handled by this keyboard-mode adapter. A device name or battery status cannot be inferred reliably from keystrokes.')
            box.addStretch();scroll.setWidget(content);layout.addWidget(scroll,1)
            row=QHBoxLayout();reset=QPushButton('Use original Anki controls',self);row.addWidget(reset);row.addStretch()
            cancel=QPushButton('Cancel',self);save=QPushButton('Save',self);row.addWidget(cancel);row.addWidget(save);layout.addLayout(row)
            reset.clicked.connect(lambda:self.enabled.setChecked(False));cancel.clicked.connect(self.reject);save.clicked.connect(self.save)
            # Dialog-local event filter. No typing is recorded outside this dialog.
            from aqt.qt import QApplication
            QApplication.instance().installEventFilter(self)
            self.finished.connect(lambda *_:QApplication.instance().removeEventFilter(self))
            self.finished.connect(lambda *_:setattr(controller,'window',None))
            cfg=controller.owner.get_config();p=PALETTES.get(cfg['theme'],PALETTES['obsidian'])
            if cfg.get('visual_owner')=='atelier':
                self.setStyleSheet('QDialog,QScrollArea,QWidget{background:'+p['bg']+';color:'+p['text']+';} QLabel{font-size:14px;} QLabel#remoteTitle{font-size:25px;font-weight:600;} QLabel#remoteStatus{background:'+p['panel']+';border:1px solid '+p['line']+';border-radius:8px;padding:12px;} QPushButton{background:'+p['raised']+';color:'+p['text']+';border:1px solid '+p['line']+';border-radius:8px;padding:9px 12px;} QPushButton:focus{border:2px solid '+p['accent']+';} QCheckBox{font-size:14px;spacing:10px;}')
        def start_test(self):
            self.waiting=None;self.testing=not self.testing
            self.test.setText('Stop test' if self.testing else 'Test remote buttons — no cards affected')
            self.status.setText('Press a button. Testing never reveals, rates or changes a card.' if self.testing else 'Test stopped. Nothing changed.')
        def learn(self,action):
            self.testing=False;self.waiting=action;self.test.setText('Test remote buttons — no cards affected')
            self.status.setText('Press the remote button for '+ACTIONS[action]+'. Escape cancels this assignment.')
        def clear(self,action):
            self.binding.pop(action,None);self.labels[action].setText('Not assigned');self.changed=True
        def eventFilter(self,watched,event):
            if not (self.testing or self.waiting) or not self.isActiveWindow():return False
            if not (watched is self or isinstance(watched,QWidget) and self.isAncestorOf(watched)):return False
            if event.type() not in (QEvent.Type.ShortcutOverride,QEvent.Type.KeyPress):return False
            key=int(event.key())
            modified=event.modifiers() & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier|Qt.KeyboardModifier.MetaModifier|Qt.KeyboardModifier.ShiftModifier)
            if modified:return False  # Keep normal app/OS shortcuts while testing.
            if event.type()==QEvent.Type.ShortcutOverride:
                if valid_key(key) or key==int(Qt.Key.Key_Escape):event.accept();return True
                return False
            if event.isAutoRepeat():return True
            if key==int(Qt.Key.Key_Escape):self.testing=False;self.waiting=None;self.test.setText('Test remote buttons — no cards affected');self.status.setText('Stopped. No action was sent.');return True
            if event.modifiers() & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier|Qt.KeyboardModifier.MetaModifier|Qt.KeyboardModifier.ShiftModifier) or not valid_key(key):
                self.status.setText('This sends a modified or unsupported key. Use an unmodified letter, number, arrow, Page key, Space, Enter or function key.');return True
            if self.waiting:
                other=next((a for a,k in self.binding.items() if k==key and a!=self.waiting),None)
                if other:self.status.setText(key_name(key)+' is assigned to '+ACTIONS[other]+'. Clear that assignment first.');return True
                self.binding[self.waiting]=key;self.labels[self.waiting].setText(key_name(key));self.waiting=None;self.changed=True
                self.status.setText('Assigned '+key_name(key)+'. Choose Save to keep this mapping.')
            else:
                action=next((a for a,k in self.binding.items() if k==key),None)
                self.status.setText('Received: '+key_name(key)+(' → '+ACTIONS[action] if action else ' · no custom action assigned')+'. Test only; no card affected.')
            return True
        def save(self):
            self.testing=False;self.waiting=None
            try:controller.save({'enabled':self.enabled.isChecked(),'bindings':self.binding})
            except Exception as exc:
                self.status.setText(str(exc) if isinstance(exc,ValueError) else 'Could not save. Your previous controls remain; try again.');return
            self.accept()
    return RemoteDialog()

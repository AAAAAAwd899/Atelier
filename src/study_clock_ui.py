"""Small non-modal native study clock; styles stay inside its own window."""
from pathlib import Path
import time
from aqt.qt import (QApplication,QButtonGroup,QCheckBox,QDialog,QHBoxLayout,QLabel,
    QProgressBar,QPushButton,QScrollArea,QSpinBox,Qt,QTimer,QVBoxLayout,QWidget,QPixmap)
from .study_clock import ClockStore,ClockError
from .review_model import PALETTES
from .worlds import CATALOG

class ClockWindow(QDialog):
    def __init__(self,owner,parent,path):
        super().__init__(parent,Qt.WindowType.Window)
        self.owner=owner;self.store=ClockStore(path);self.clock=self.store.read();self.last_save=time.monotonic();self.last_display=None
        self.setWindowTitle('Atelier · Study clock');self.setObjectName('atelierStudyClock');self.setMinimumSize(300,320)
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        scroll=QScrollArea(self);scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame);outer.addWidget(scroll)
        content=QWidget();box=QVBoxLayout(content);box.setContentsMargins(18,14,18,14);box.setSpacing(10);scroll.setWidget(content)
        self.scene=QLabel();self.scene.setFixedHeight(60);self.scene.setObjectName('clockScene');box.addWidget(self.scene)
        self.title=QLabel('Study clock');self.title.setObjectName('clockTitle');box.addWidget(self.title)
        self.mode_row=QHBoxLayout();self.group=QButtonGroup(self);self.modes={}
        for key,label in [('countdown','Countdown'),('stopwatch','Stopwatch')]:
            b=QPushButton(label);b.setCheckable(True);self.group.addButton(b);self.modes[key]=b;self.mode_row.addWidget(b);b.clicked.connect(lambda _,m=key:self.change_mode(m))
        box.addLayout(self.mode_row)
        row=QHBoxLayout();self.length_label=QLabel('Study for');row.addWidget(self.length_label)
        self.length=QSpinBox();self.length.setRange(1,480);self.length.setSuffix(' min');self.length.setAccessibleName('Countdown length in minutes');self.length.setValue(self.clock.minutes);row.addWidget(self.length,1);box.addLayout(row)
        self.length.valueChanged.connect(self.change_length)
        self.digits=QLabel();self.digits.setAlignment(Qt.AlignmentFlag.AlignCenter);self.digits.setObjectName('clockDigits');self.digits.setAccessibleName('Study clock time');box.addWidget(self.digits)
        self.progress=QProgressBar();self.progress.setRange(0,1000);self.progress.setTextVisible(False);self.progress.setFixedHeight(5);self.progress.setAccessibleName('Countdown progress');box.addWidget(self.progress)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setAlignment(Qt.AlignmentFlag.AlignCenter);self.status.setObjectName('clockStatus');box.addWidget(self.status)
        row=QHBoxLayout();self.toggle=QPushButton();self.toggle.setObjectName('clockStart');self.reset=QPushButton('Reset');row.addWidget(self.toggle,2);row.addWidget(self.reset,1);box.addLayout(row)
        self.toggle.clicked.connect(self.toggle_clock);self.reset.clicked.connect(self.reset_clock)
        row=QHBoxLayout();self.sound=QCheckBox('Sound at finish');self.sound.setChecked(self.clock.sound);row.addWidget(self.sound);self.pin=QCheckBox('Keep on top');self.pin.setChecked(self.clock.pin);row.addWidget(self.pin);box.addLayout(row)
        self.sound.toggled.connect(self.set_sound);self.pin.toggled.connect(self.set_pin)
        self.hint=QLabel('Elapsed time includes breaks unless paused. Closing this window keeps it running; quitting Anki pauses it.');self.hint.setWordWrap(True);self.hint.setObjectName('clockHint');box.addWidget(self.hint)
        self.notice=QLabel();self.notice.setWordWrap(True);self.notice.setObjectName('clockNotice');box.addWidget(self.notice)
        if self.store.blocked:self.notice.setText('Saved clock settings could not be read and were kept. This clock works for this visit.')
        if self.clock.pin:self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True)
        self.timer=QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self.tick);self.timer.start()
        self.refresh();self.paint_state()
        available=self.screen().availableGeometry();self.resize(min(350,available.width()-24),min(450,available.height()-32))

    def refresh(self):
        cfg=self.owner.get_config();self.palette_tokens=PALETTES.get(cfg['theme'],PALETTES['obsidian'])
        themed=cfg.get('visual_owner')=='atelier';p=self.palette_tokens
        self.setStyleSheet(('QDialog#atelierStudyClock,QScrollArea,QWidget{background:'+p['bg']+';color:'+p['text']+';font-family:Segoe UI;font-size:14px;} QLabel#clockTitle{font-size:22px;font-weight:600;} QLabel#clockDigits{font-size:46px;font-weight:600;padding:4px;} QLabel#clockStatus{color:'+p['accent']+';} QLabel#clockHint,QLabel#clockNotice{color:'+p['quiet']+';font-size:13px;} QPushButton,QSpinBox{background:'+p['raised']+';color:'+p['text']+';border:1px solid '+p['line']+';border-radius:9px;padding:8px;} QPushButton:checked{background:'+p['accent-soft']+';border-color:'+p['accent']+';} QPushButton#clockStart{background:'+p['accent']+';color:'+p['on-accent']+';font-weight:600;} QPushButton:disabled{color:'+p['quiet']+';} QPushButton:focus,QSpinBox:focus{border:2px solid '+p['accent']+';} QProgressBar{background:'+p['line']+';border:0;border-radius:2px;} QProgressBar::chunk{background:'+p['accent']+';} QCheckBox{spacing:6px;font-size:13px;}') if themed else '')
        self.scene.setVisible(themed)
        world=next((w for w in CATALOG if w['id']==cfg['theme']),CATALOG[0]);self.scene_path=Path(__file__).parent/'web'/world['scene'];self.title.setToolTip(world['name']+' · '+world['title']);self.paint_scene()

    def paint_scene(self):
        if not self.scene.isVisible():return
        pix=QPixmap(str(self.scene_path));size=self.scene.size()
        scaled=pix.scaled(size,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
        self.scene.setPixmap(scaled.copy(max(0,(scaled.width()-size.width())//2),max(0,(scaled.height()-size.height())//2),size.width(),size.height()))
    def resizeEvent(self,event):super().resizeEvent(event);self.paint_scene()
    def showEvent(self,event):super().showEvent(event);self.paint_scene()
    def save(self):
        try:self.store.write(self.clock);self.last_save=time.monotonic()
        except ClockError as exc:self.notice.setText(str(exc))
    def paint_state(self):
        c=self.clock;display=c.display()
        if display!=self.last_display:self.digits.setText(display);self.last_display=display
        active=c.elapsed()>0 or c.running
        for key,b in self.modes.items():b.setChecked(c.mode==key);b.setEnabled(not active or c.mode==key);b.setToolTip('Reset to change clock mode.' if active else '')
        self.length.setVisible(c.mode=='countdown');self.length_label.setVisible(c.mode=='countdown');self.length.setEnabled(not active)
        self.progress.setVisible(c.mode=='countdown');self.progress.setValue(round(1000*c.elapsed()/(c.minutes*60)))
        self.status.setText('Time’s up. Take a moment, or start again.' if c.complete else ('Counting down' if c.mode=='countdown' else 'Stopwatch')+' · '+('running' if c.running else 'paused' if c.elapsed()>0 else 'ready'))
        self.toggle.setText('Pause' if c.running else 'Start again' if c.complete else 'Resume' if c.elapsed()>0 else 'Start')
        self.reset.setEnabled(active);self.sound.setVisible(c.mode=='countdown')
    def tick(self):
        if self.clock.tick():
            if self.clock.sound:QApplication.beep()
            self.save()
        self.paint_state()
        if self.clock.running and time.monotonic()-self.last_save>=30:self.save()
    def toggle_clock(self):
        self.clock.pause() if self.clock.running else self.clock.start();self.save();self.paint_state()
    def reset_clock(self):self.clock.reset();self.save();self.paint_state()
    def change_mode(self,mode):
        if self.clock.elapsed()>0 or self.clock.running:self.paint_state();return
        self.clock.configure(mode,self.length.value());self.save();self.paint_state()
    def change_length(self,minutes):
        if self.clock.elapsed()==0 and not self.clock.running:self.clock.configure(self.clock.mode,minutes);self.save();self.paint_state()
    def set_sound(self,value):self.clock.sound=value;self.save()
    def set_pin(self,value):
        self.clock.pin=value;self.save();self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,value);self.show()
    def closeEvent(self,event):self.save();self.hide();event.ignore()
    def shutdown(self):self.clock.pause();self.save();self.timer.stop();self.hide();self.deleteLater()

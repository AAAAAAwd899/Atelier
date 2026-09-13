"""0.9.5 regressions. These Qt doubles are NOT native Anki installation tests."""
import ast
import importlib.util
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from addon.companion_layout import BADGE_SIZE, footer_position
from addon.storage import Store, settings_from
from test_window_contract import integration, Signal

ROOT=Path(__file__).resolve().parents[1]


def measure(width=1200,height=64,rects=None):
    return {'ready':True,'width':width,'height':height,'rects':rects if rects is not None else [[12,12,70,36],[360,10,480,40],[1100,12,86,36]],'reduce':False}


def test_pip_is_tiny():
    assert BADGE_SIZE == 46


def test_badge_uses_spare_footer_space_not_more_or_grading_buttons():
    x,y=footer_position(measure(),1200,64)
    assert 848<=x and x+46<=1092 and y==9


def test_crowded_footer_hides_instead_of_covering_controls():
    assert footer_position(measure(700,64,[[0,0,700,64]]),700,64) is None


@pytest.mark.parametrize('width,height',[(1200,30),(260,64),(1200,0)])
def test_small_footer_hides(width,height):
    assert footer_position(measure(),width,height) is None


@pytest.mark.parametrize('value',[None,{},[],{'ready':False},measure(rects=[[0,0,float('inf'),1]]),measure(rects=[[0,0,-1,1]]),measure(rects=[['bad']]),{'ready':True,'width':float('nan'),'height':64,'rects':[]}])
def test_unknown_layout_fails_closed(value):
    assert footer_position(value,1200,64) is None


def test_high_dpi_measurements_respect_logical_size():
    m=measure(2400,128,[[24,24,140,72],[720,20,960,80],[2200,24,172,72]])
    assert footer_position(m,1200,64)==footer_position(measure(),1200,64)


def test_randomized_placement_never_intersects_reported_controls():
    rng=random.Random(951)
    for _ in range(1000):
        width=rng.randint(400,2000);height=rng.randint(48,160)
        rects=[[rng.randint(0,width-1),0,rng.randint(10,200),height] for __ in range(rng.randint(1,15))]
        out=footer_position(measure(width,height,rects),width,height)
        if out:
            x,y=out
            assert x>=width//2 and x+46<=width-6 and y>=0 and y+46<=height
            assert all(x+46<=r[0]-8 or x>=r[0]+r[2]+8 for r in rects)


def test_old_settings_migrate_without_touching_exams_or_history(tmp_path):
    store=Store(tmp_path)
    assert store.state['settings']['reviewer_pip'] is True
    before=json.loads(json.dumps(store.state))
    store.save_settings({**store.state['settings'],'reviewer_pip':False})
    again=Store(tmp_path)
    assert again.state['settings']['reviewer_pip'] is False
    assert again.state['exams']==before['exams'] and again.state['history']==before['history']
    assert settings_from({'show_pip':False})['show_pip'] is False


def test_no_dock_or_reviewer_monkeypatch_or_extra_pip_webview():
    src=(ROOT/'addon/companion.py').read_text()
    tree=ast.parse(src)
    imported={a.name for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) for a in n.names}
    assert 'QDockWidget' not in imported and 'AnkiWebView' not in imported
    assert 'addDockWidget(' not in src and '.setFixedSize(BADGE_SIZE, BADGE_SIZE)' in src
    assert 'setFocusPolicy(Qt.FocusPolicy.NoFocus)' in src
    assert 'QShortcut' not in src and 'setStateShortcuts' not in src


def test_practice_starts_with_notes_closed_and_never_opens_them_for_pip():
    src=(ROOT/'addon/runner.py').read_text()
    assert 'self._side_open = False' in src and 'self.side.hide()' in src
    assert 'companion_markup' not in src and 'AnkiWebView(self.side)' not in src
    tree=ast.parse(src);runner=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='ExamRunner')
    show=next(m for m in runner.body if isinstance(m,ast.FunctionDef) and m.name=='_show_current')
    assert 'self.side.show()' not in ast.get_source_segment(src,show)
    # rc4 moves the same optional action into a native Tools popup.
    ui=(ROOT/'addon/review_ui.py').read_text()
    assert 'tool("Write an answer", r._toggle_side)' in ui
    assert 'r.tools_panel = ToolsPopup(r, Qt.WindowType.Popup)' in ui


def test_full_study_exam_and_mistake_routes_present():
    src=(ROOT/'addon/integration.py').read_text();ui=(ROOT/'addon/web/app.js').read_text()
    for route in ['study','focus','prepare','start','review_misses','browse']:
        assert f'action == "{route}"' in src
    assert 'self.mw.moveToState("review")' in src
    assert 'import aqt.dialogs' not in src
    assert 'data-action="study"' in ui and "request(a," in ui
    assert 'data-action="focus"' in ui and "request(a," in ui
    assert 'data-action="browse"' in ui and "request('browse'" in ui


class Sig(Signal):
    def disconnect(self,fn):self.functions.remove(fn)


class Widget:
    def __init__(self,parent=None):
        self.parent=parent;self.visible=False;self.clicked=Sig();self.customContextMenuRequested=Sig();self.calls=[]
    def setObjectName(self,n):self.name=n
    def setFixedSize(self,w,h):self.size=(w,h)
    def setFocusPolicy(self,value):self.focus_policy=value
    def setAttribute(self,*args):pass
    def setAutoFillBackground(self,value):pass
    def setCursor(self,value):pass
    def setAccessibleName(self,value):pass
    def setToolTip(self,value):pass
    def setContextMenuPolicy(self,value):pass
    def update(self):pass
    def isVisible(self):return self.visible
    def show(self):self.visible=True
    def hide(self):self.visible=False
    def move(self,x,y):self.position=(x,y)
    def raise_(self):pass
    def deleteLater(self):self.deleted=True


class Pixmap:
    def __init__(self,*args):self.path=args[0] if args else None
    def isNull(self):return not self.path


class Buffer:
    """Strict QBuffer stand-in: bytes cannot change while Qt is reading."""
    def __init__(self,parent):
        self.parent=parent; self.payload=b''; self.opened=False
        self.calls=[]
    def setData(self,value):
        assert not self.opened, 'QBuffer must close before setData'
        assert getattr(self.parent, '_device', None) is not self, 'detach decoder first'
        self.payload=bytes(value);self.calls.append(('data',len(self.payload)))
    def open(self,mode):
        assert mode==1
        self.opened=True;self.calls.append(('open',mode));return True
    def close(self):
        assert getattr(self.parent, '_device', None) is not self, 'detach decoder first'
        self.opened=False;self.calls.append(('close',))
    def isOpen(self):return self.opened
    def data(self):return self.payload


class Movie:
    CacheMode=SimpleNamespace(CacheAll=1)
    def __init__(self,parent):
        self.frameChanged=Sig();self.running=False;self._device=None;self.path=None
        self.device_calls=[]
    def setCacheMode(self,value):pass
    def setFileName(self,name):raise AssertionError('File-backed QMovie would lock updates')
    def setDevice(self,device):
        if device is not None:assert device.opened and device.payload
        self._device=device;self.device_calls.append(device)
        self.path='memory.webp' if device else None
    def device(self):return self._device
    def fileName(self):return ''
    def setFormat(self,value):self.format=bytes(value)
    def isValid(self):return self._device is not None and self._device.opened
    def start(self):
        assert self.isValid()
        self.running=True
    def stop(self):self.running=False
    def setPaused(self,value):self.running=not value
    def currentPixmap(self):return Pixmap(self.path)


class Timer:
    def __init__(self,parent):self.timeout=Sig();self.running=False
    def setSingleShot(self,value):pass
    def start(self,*args):self.running=True
    def stop(self):self.running=False
    def isActive(self):return self.running
    def remainingTime(self):return 1700


@pytest.fixture
def companion(integration,monkeypatch):
    app=SimpleNamespace(applicationStateChanged=Sig(),applicationState=lambda:1)
    qt=sys.modules['aqt.qt']
    constants=SimpleNamespace(FocusPolicy=SimpleNamespace(NoFocus=0),WidgetAttribute=SimpleNamespace(WA_TranslucentBackground=1),CursorShape=SimpleNamespace(PointingHandCursor=1),ContextMenuPolicy=SimpleNamespace(CustomContextMenu=1),ApplicationState=SimpleNamespace(ApplicationActive=1))
    for name,value in {'QAbstractButton':Widget,'QApplication':SimpleNamespace(instance=lambda:app),'QEvent':SimpleNamespace(Type=SimpleNamespace(Resize=1,Show=2,Hide=3)),'QMenu':Widget,'QMovie':Movie,'QBuffer':Buffer,'QByteArray':bytes,'QIODevice':SimpleNamespace(OpenModeFlag=SimpleNamespace(ReadOnly=1)),'QObject':Widget,'QPainter':object,'QPixmap':Pixmap,'QRect':object,'Qt':constants,'QTimer':Timer}.items():monkeypatch.setattr(qt,name,value,raising=False)
    hooks=sys.modules['aqt'].gui_hooks
    for name in ['reviewer_did_answer_card','reviewer_did_show_question','reviewer_did_show_answer']:monkeypatch.setattr(hooks,name,[],raising=False)
    spec=importlib.util.spec_from_file_location('addon.companion_test095',ROOT/'addon/companion.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m,integration.c,app


def test_tiny_widget_is_not_focusable_or_initially_expanded(companion):
    m,c,app=companion;badge=m.TinyPip(c,None)
    assert badge.size==(46,46) and badge.focus_policy==0 and not badge.visible
    assert not badge.movie.running
    assert not hasattr(badge,'dock') and not hasattr(badge,'web')


def test_petting_uses_animation_without_changing_store(companion):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show();before=json.dumps(c.store.state)
    badge.play('pet')
    assert badge.movie.running and badge.movie.fileName() == '' and badge.return_timer.running
    assert bytes(badge._movie_buffer.data()) == (m.ASSETS/'tiny-stage1-pet.webp').read_bytes()
    assert before==json.dumps(c.store.state)
    badge.play('water');assert b'WEBP' == bytes(badge._movie_buffer.data())[8:12]
    assert bytes(badge._movie_buffer.data()) == (m.ASSETS/'tiny-stage1-water.webp').read_bytes()


def test_disabled_animation_and_reduced_motion_stay_static(companion):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show();badge.configure(4,False);badge.play('water')
    assert not badge.movie.running and badge._pixmap.path.endswith('stage4.png')
    badge.configure(4,True);badge.set_reduced_motion(True)
    assert not badge.movie.running


def test_stale_measurement_cannot_resurrect_hidden_companion(companion):
    m,c,app=companion;co=m.ReviewerCompanion(c);c.mw.state='review';callbacks=[]
    host=SimpleNamespace(width=lambda:1200,height=lambda:64,evalWithCallback=lambda js,fn:callbacks.append(fn))
    co.host=host;co.badge=m.TinyPip(c,None);co._measure();co.hide();callbacks.pop()(measure())
    assert not co.badge.visible


def test_visible_only_after_verified_free_footer_space(companion):
    m,c,app=companion;co=m.ReviewerCompanion(c);c.mw.state='review';callbacks=[]
    co.host=SimpleNamespace(width=lambda:1200,height=lambda:64,evalWithCallback=lambda js,fn:callbacks.append(fn))
    co.badge=m.TinyPip(c,None);co._measure();assert not co.badge.visible
    callbacks.pop()(measure());assert co.badge.visible and co.badge.position[0]+46<1100


def test_hide_is_persistent_and_does_not_hide_planner_pip(companion):
    m,c,app=companion;co=m.ReviewerCompanion(c);c.mw.state='review';co.badge=m.TinyPip(c,None);co.badge.show();co.dismiss()
    assert not co.badge.visible and co.dismissed and not c.store.state['settings']['reviewer_pip']
    assert c.store.state['settings']['show_pip']


def test_profile_switch_invalidates_pending_footer_callback(companion):
    m,c,app=companion;co=m.ReviewerCompanion(c);c.mw.state='review';callbacks=[]
    co.host=SimpleNamespace(width=lambda:1200,height=lambda:64,evalWithCallback=lambda js,fn:callbacks.append(fn));co.badge=m.TinyPip(c,None)
    co._measure();c.epoch+=1;callbacks.pop()(measure());assert not co.badge.visible


def test_reenable_command_sets_both_required_settings(integration,monkeypatch):
    c=integration.c;co=SimpleNamespace(dismissed=True,cleanup=lambda:None);c.companion=co;calls=[]
    monkeypatch.setattr(c,'state_changed',lambda *args:calls.append(args))
    c.store.save_settings({**c.store.state['settings'],'reviewer_pip':False})
    c.show_pip();assert not co.dismissed and c.store.state['settings']['reviewer_pip'] and calls


def test_remaining_shortfall_notices_use_names_not_opaque_deck_ids():
    from addon.session_tools import named_sample_warnings
    from addon.core import DeckStats
    warning='Deck 1234 has no eligible cards after filters and sibling deduplication.'
    output=named_sample_warnings([warning,'Only 2 eligible notes are available; no cards will be repeated.'],{1234:DeckStats(1234,'Exam::Cardio')})
    assert output[0].startswith('“Exam::Cardio” has no eligible cards')
    assert '1234' not in output[0] and output[1].startswith('Only 2 eligible')


def test_all_asset_frames_fit_the_native_source_rectangle():
    from PIL import Image, ImageSequence
    for path in (ROOT/'addon/web/pip').glob('*.webp'):
        with Image.open(path) as image:
            assert image.n_frames==(180 if '-idle.' in path.name else 96)
            for frame in ImageSequence.Iterator(image):
                left,top,right,bottom=frame.convert('RGBA').getchannel('A').getbbox()
                assert left >= 0 and top >= 0 and right <= image.width and bottom <= image.height
                assert image.size == ((96, 96) if path.name.startswith('tiny-') else (480, 480))

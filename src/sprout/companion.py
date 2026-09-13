"""Tiny native mascot in spare footer space. No dock, card HTML, or shortcuts.

The existing pre-rendered 3D art is played by Qt, not an extra webview. Only
explicit right-click opens controls. Pet/Water never call grading or scheduling.
"""
from __future__ import annotations
from pathlib import Path
import time
from aqt import gui_hooks
from aqt.qt import (
    QAbstractButton, QApplication, QBuffer, QByteArray, QEvent, QIODevice,
    QMenu, QMovie, QObject, QPainter,
    QPixmap, QRect, Qt, QTimer,
)
from .companion_layout import BADGE_SIZE, footer_position
from .diagnostics import LOG

ASSETS = Path(__file__).resolve().parent / 'web' / 'pip'
# Only one compressed native animation is retained per badge. Largest bundled
# tiny animation is under 1.5 MB; never read an unbounded replacement asset.
MAX_MOVIE_BYTES = 4 * 1024 * 1024

# Read-only measurements. No selectors, classes, CSS, or attributes are changed.
FOOTER_MEASURE = r"""(()=>{
 const box = el => {const r=el.getBoundingClientRect();return [r.x,r.y,r.width,r.height]};
 const controls=[...document.querySelectorAll('button,a,input,select,textarea,[role="button"],[onclick]')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');
 const rects=controls.map(box);
 const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node,n=0;
 while((node=walk.nextNode())&&n++<300){
  if(!node.textContent.trim()||node.parentElement?.closest('script,style,noscript'))continue;
  const range=document.createRange();range.selectNodeContents(node);
  for(const r of range.getClientRects())if(r.width&&r.height)rects.push([r.x,r.y,r.width,r.height]);
 }
 return {ready:controls.length>0,width:innerWidth,height:innerHeight,rects:rects.slice(0,512),reduce:matchMedia('(prefers-reduced-motion: reduce)').matches};
})()"""


class TinyPip(QAbstractButton):
    """46px non-focus-taking button. Native popup is opened only by the user."""
    def __init__(self, controller, parent, on_hide=None):
        super().__init__(parent)
        self.controller = controller
        self.on_hide = on_hide or self._hide_reviewers
        self.stage = 1
        self.animated = True
        self.reduced = False
        self.user_paused = False
        self._playing = None
        self._disposed = False
        self._failed_movies = set()
        self._remaining_action_ms = 0
        self._pixmap = QPixmap()
        self.setObjectName('exam_sprout_tiny_pip')
        self.setFixedSize(BADGE_SIZE, BADGE_SIZE)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Pip. Click to pet. Right-click for water, pause, or hide.')
        self.setToolTip('Pip · Click to pet\nRight-click for water, pause or hide')
        self.movie = QMovie(self)
        # QMovie(filename) / setFileName keeps a QFile open on Windows even
        # while paused. Anki deletes the old add-on directory BEFORE extracting
        # an update. Play from an owned in-memory device instead of that file.
        # Both the Python reference and Qt parenting retain the device until
        # the movie has detached; setData owns the QByteArray contents.
        self._movie_buffer = QBuffer(self.movie)
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.frameChanged.connect(self._frame)
        self.return_timer = QTimer(self)
        self.return_timer.setSingleShot(True)
        self.return_timer.timeout.connect(lambda: self.play('idle'))
        self.clicked.connect(lambda _=False: self.play('pet'))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self._app = QApplication.instance()
        if self._app:
            self._app.applicationStateChanged.connect(self._activity)
        self.configure(1, True)

    def configure(self, stage=1, animated=True):
        if self._disposed: return
        stage = max(1, min(4, int(stage)))
        changed = (stage, bool(animated)) != (self.stage, self.animated)
        self.stage, self.animated = stage, bool(animated)
        if changed or self._pixmap.isNull():
            self._release_movie()
            self.return_timer.stop()
            self._remaining_action_ms = 0
            self._pixmap = QPixmap(str(ASSETS / f'tiny-stage{stage}.png'))
            self._playing = None
        if changed or self._playing is None:
            self.play('idle')
        else:
            self._resume_movie()

    def set_reduced_motion(self, reduced):
        if self.reduced != bool(reduced):
            self.reduced = bool(reduced)
            self.play('idle')

    def _can_move(self):
        return (not self._disposed and self.animated and not self.reduced and not self.user_paused
                and self.isVisible() and (self._app is None or
                self._app.applicationState() == Qt.ApplicationState.ApplicationActive))

    def _resume_movie(self):
        if self._disposed: return
        if not self._can_move():
            self._pause_movie()
            return
        if self._playing is None:
            self.play('idle')
            return
        self.movie.setPaused(False)
        if self._playing[1] != 'idle' and self._remaining_action_ms:
            self.return_timer.start(self._remaining_action_ms)
            self._remaining_action_ms = 0

    def _pause_movie(self):
        if self.return_timer.isActive():
            self._remaining_action_ms = max(1, self.return_timer.remainingTime())
        self.return_timer.stop()
        # Preserve the displayed frame across question/answer footer remounts.
        # stop() rewinds QMovie and made each new card restart the idle cycle.
        if self._playing is not None:
            self.movie.setPaused(True)

    def play(self, action='idle'):
        if self._disposed or action not in ('idle', 'pet', 'water'):
            return
        key = (self.stage, action)
        if not self._can_move():
            self._pause_movie()
            self.update()
            return
        if self._playing == key:
            self._resume_movie()
            return
        if key in self._failed_movies:
            return  # Missing/unsupported art must not retry on every card.
        self.return_timer.stop()
        self._remaining_action_ms = 0
        self._release_movie()
        try:
            path = ASSETS / f'tiny-stage{self.stage}-{action}.webp'
            # The OS file is CLOSED before Qt receives any of the bytes. A
            # paused/active movie therefore never pins an installed asset file.
            with path.open('rb') as source:
                payload = source.read(MAX_MOVIE_BYTES + 1)
            if not 12 <= len(payload) <= MAX_MOVIE_BYTES:
                raise ValueError('Pip animation is empty, truncated, or too large')
            if payload[:4] != b'RIFF' or payload[8:12] != b'WEBP':
                raise ValueError('Pip animation is not a WebP image')
            self._movie_buffer.setData(QByteArray(payload))
            if not self._movie_buffer.open(QIODevice.OpenModeFlag.ReadOnly):
                raise RuntimeError('Pip animation memory buffer could not open')
            self.movie.setDevice(self._movie_buffer)
            self.movie.setFormat(QByteArray(b'webp'))
            if not self.movie.isValid():
                raise ValueError('Pip animation decoder is unavailable or the image is invalid')
            self._playing = key
            self.movie.start()
            if action != 'idle':
                self.return_timer.start(3200)
        except (OSError, ValueError, RuntimeError):
            # An interrupted update or unsupported decoder affects only Pip.
            # Retain still art and the review controls; never open an error modal.
            self._release_movie()
            self._failed_movies.add(key)
            still = QPixmap(str(ASSETS / f'tiny-stage{self.stage}.png'))
            if not still.isNull(): self._pixmap = still
            LOG.warning('Pip animation unavailable (stage %s, %s); using still art.', *key)
            self.update()

    def _release_movie(self):
        """Detach the decoder before clearing its buffer, without deferred I/O."""
        self._playing = None
        self.movie.stop()
        self.movie.setDevice(None)
        self._movie_buffer.close()
        self._movie_buffer.setData(QByteArray())

    def _frame(self, _index):
        if self._disposed or self._playing is None: return
        pixmap = self.movie.currentPixmap()
        if not pixmap.isNull(): self._pixmap = pixmap
        self.update()

    def paintEvent(self, _event):
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # The 96px frames include margin around the sculpted character. A fixed
        # source rectangle retains all growth/interaction frames without jitter.
        source = QRect(0, 0, 96, 96)
        dest = QRect(0, 0, BADGE_SIZE, BADGE_SIZE)
        painter.drawPixmap(dest, self._pixmap, source)
        painter.end()

    def _menu(self, position):
        menu = QMenu(self)
        pet = menu.addAction('Pet Pip')
        water = menu.addAction('Water Pip')
        pause = menu.addAction('Resume motion' if self.user_paused else 'Pause motion')
        menu.addSeparator()
        hide = menu.addAction('Hide Pip while reviewing')
        try:
            choice = menu.exec(self.mapToGlobal(position))
            if choice is pet: self.play('pet')
            elif choice is water: self.play('water')
            elif choice is pause:
                self.user_paused = not self.user_paused
                self.play('idle')
            elif choice is hide: self.on_hide()
        except Exception:
            LOG.exception('Pip menu failed; card controls are unchanged')
        finally:
            try: menu.deleteLater()
            except RuntimeError: pass

    def _hide_reviewers(self):
        self.hide()
        c = self.controller
        if c.store:
            try: c.store.save_settings({**c.store.state['settings'], 'reviewer_pip': False})
            except Exception: LOG.exception('Could not persist hiding Pip')
        companion = getattr(c, 'companion', None)
        if companion is not None: companion.hide()

    def _activity(self, _state):
        self._resume_movie()

    def showEvent(self, event):
        super().showEvent(event)
        self._resume_movie()

    def hideEvent(self, event):
        self._pause_movie()
        super().hideEvent(event)

    def dispose(self):
        if getattr(self, '_disposed', False): return
        self._disposed = True
        self.return_timer.stop()
        self._remaining_action_ms = 0
        self._release_movie()  # Release bytes now, not only after deleteLater.
        self._failed_movies.clear()
        if self._app:
            try: self._app.applicationStateChanged.disconnect(self._activity)
            except (RuntimeError, TypeError): pass
        self.hide()
        self.deleteLater()


class ReviewerCompanion(QObject):
    def __init__(self, controller):
        super().__init__(controller.mw)
        self.controller = controller
        self.badge = self.host = None
        self.dismissed = False
        self.refresh_pending = False
        self.last_refresh = 0.
        self.answer_count = 0
        self._generation = 0
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.timeout.connect(self._measure)
        gui_hooks.reviewer_did_answer_card.append(self.after_answer)
        gui_hooks.reviewer_did_show_question.append(self.schedule_layout)
        gui_hooks.reviewer_did_show_answer.append(self.schedule_layout)

    def enabled(self):
        c = self.controller
        return bool(c.store and c.mw.col and c.mw.state == 'review' and not self.dismissed
                    and c.store.state['settings'].get('show_pip', True)
                    and c.store.state['settings'].get('reviewer_pip', True))

    def state_changed(self, new, old=''):
        try:
            if new != 'review' or not self.enabled():
                self.hide(); return
            host = getattr(self.controller.mw, 'bottomWeb', None)
            if host is None: return  # No fallback over the card surface.
            if self.host is not host:
                self.cleanup()
                self.host = host
                self.badge = TinyPip(self.controller, host, self.dismiss)
                self.badge.hide()
                host.installEventFilter(self)
                host.loadFinished.connect(self.schedule_layout)
            self.refresh()
            self.schedule_layout()
            if new != old: self.refresh_signal()
        except Exception:
            LOG.exception('Tiny Pip could not load; reviewer layout is unchanged')
            self.hide()

    def eventFilter(self, obj, event):
        if obj is self.host:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                self.schedule_layout()
            elif event.type() == QEvent.Type.Hide:
                self.hide()
        return False  # Never consume a native event or keyboard shortcut.

    def schedule_layout(self, *args):
        self._generation += 1
        if self.badge: self.badge.hide()
        if self.enabled() and self.host is not None:
            self.layout_timer.start(90)

    def _measure(self):
        if not self.enabled() or self.host is None or self.badge is None: return
        generation, epoch = self._generation, self.controller.epoch
        host, badge = self.host, self.badge
        def place(data):
            if (generation != self._generation or epoch != self.controller.epoch
                    or self.host is not host or self.badge is not badge or not self.enabled()): return
            position = footer_position(data, host.width(), host.height())
            if position is None:
                badge.hide(); return
            badge.set_reduced_motion(bool(data.get('reduce')))
            badge.move(*position)
            badge.show()
            badge.raise_()
        try: host.evalWithCallback(FOOTER_MEASURE, place)
        except Exception:
            LOG.exception('Footer measurement failed; Pip stays hidden')
            badge.hide()

    def dismiss(self):
        self.dismissed = True
        self.hide()
        c = self.controller
        if c.store:
            try: c.store.save_settings({**c.store.state['settings'], 'reviewer_pip': False})
            except Exception: LOG.exception('Could not persist hiding Pip')

    def refresh(self):
        if self.badge is None or self.controller.store is None: return
        c = self.controller
        growth = c.pip_signal() if hasattr(c, 'pip_signal') else c.growth_cache.get(c.active_exam_id, {'stage': 1})
        self.badge.configure(growth.get('stage', 1), c.store.state['settings'].get('animate_pip', True))

    def after_answer(self, reviewer, card, ease):
        self.answer_count += 1
        if self.answer_count % 5 == 0 and time.monotonic() - self.last_refresh > 20:
            self.refresh_signal()

    def refresh_signal(self):
        # Lifetime effort is profile-local and already updated by answer hooks.
        # Never query card mastery to decide how tall Pip should be.
        c = self.controller
        if c.store is None: return
        self.last_refresh = time.monotonic()
        if hasattr(c, "pip_signal"):
            c.growth_cache[c.active_exam_id] = c.pip_signal()
        if self.enabled(): self.refresh()

    def hide(self):
        self._generation += 1
        self.layout_timer.stop()
        if self.badge: self.badge.hide()

    def cleanup(self):
        self.hide()
        if self.host is not None:
            try:
                self.host.removeEventFilter(self)
                self.host.loadFinished.disconnect(self.schedule_layout)
            except (TypeError, RuntimeError): pass
        if self.badge is not None: self.badge.dispose()
        self.badge = self.host = None
        self.dismissed = False
        self.refresh_pending = False
        self.answer_count = 0

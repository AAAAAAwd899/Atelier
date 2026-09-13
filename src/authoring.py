"""Suite-owned authoring entry points; never a scheduler or mask-format override.

Native EditCurrent keeps Anki's save/return behavior. Only recognized IO Enhanced
notes are sent to their already-registered owning editor. Native IO stays native.
"""
from __future__ import annotations
import logging
import weakref

LOG = logging.getLogger('atelier.authoring')


def mask_kind(editor):
    """Conservative classification: native metadata or the actual IOE schema."""
    note = getattr(editor, 'note', None)
    if note is None:
        return 'fields'
    native = getattr(editor, 'current_notetype_is_image_occlusion', None)
    if callable(native):
        try:
            if native():
                return 'native'
        except Exception:
            return 'fields'
    try:
        model = note.note_type()
        names = {f['name'].casefold() for f in model.get('flds', [])}
        if model.get('originalStockKind') == 6:
            return 'native'
        required = {'image', 'question mask', 'answer mask', 'original mask'}
        # Exact owning schema, not a vague name/substring match.
        if required <= names and any(n.startswith('id (') or n == 'id' for n in names):
            return 'ioe'
    except (AttributeError, KeyError, TypeError):
        pass
    return 'fields'


class AuthoringRoutes:
    def __init__(self, owner, controller, registration):
        self.owner = owner
        self.controller = controller
        self.mw = controller.mw
        self.native_add = getattr(self.mw, 'onAddCard', None)
        self.alive = True
        self.opening = False
        self._editors = weakref.WeakKeyDictionary()
        self._shortcuts = []
        self._add_wrapper = lambda *args: self.create()
        registration.cleanup(self.dispose)

    def create(self):
        if not self.alive or self.opening or not getattr(self.mw, 'col', None):
            return
        self.opening = True
        try:
            engine = getattr(self.mw, '_exam_sprout_controller', None)
            if getattr(engine, 'runner', None) is not None:
                self._notice('Save and close or finish your practice session before creating cards. Your answers are still open.')
                return
            # Deliberate action only. Opening during scheduled review is modal,
            # preventing input in the editor from grading the card behind it.
            self.controller.preferred_deck = None
            self.controller.open('studio', allow_review=True)
        finally:
            self.opening = False

    def open_page(self, view="studio", note_id=None, deck_id=None):
        from .core import ValidationError
        if view not in ("library", "studio", "drafts", "import", "find", "improve", "media", "settings"):
            raise ValidationError("Choose a valid Card Studio page.")
        if not self.alive or not getattr(self.mw, "col", None):
            raise ValidationError("Open an Anki profile first.")
        if getattr(getattr(self.mw, "_exam_sprout_controller", None), "runner", None) is not None:
            raise ValidationError("Save and close or finish the current practice session before opening Card Studio.")
        if deck_id is not None:
            from .core import deck_id as valid_id, fresh_catalog
            did = valid_id(deck_id)
            if did not in fresh_catalog(self.mw.col):
                raise ValidationError("This deck no longer exists. Choose another destination.")
            self.controller.preferred_deck = int(did)
        else:
            # A contextual deck belongs to that request, not every later entry.
            # An already-open draft keeps its explicitly displayed destination.
            self.controller.preferred_deck = None
        self.controller.open(view, note_id=note_id, allow_review=True)

    def _notice(self, message):
        from aqt.utils import tooltip
        tooltip(message, parent=self.mw)

    def original_add(self):
        import aqt
        # Do not call the redirected onAddCard from this explicit escape hatch.
        return aqt.dialogs.open('AddCards', self.mw)

    def message(self, handled, message, context):
        if handled[0] or not self.alive:
            return handled
        if message == 'add' and context is getattr(self.mw, 'toolbar', None):
            self.create()
            return (True, None)
        return handled

    def bind(self, *_):
        """Change our instance route; rebind only the exact native A callback.

        Unknown/foreign shortcuts are left alone. We never disconnect all signals.
        """
        if not self.alive:
            return
        if getattr(self.mw, 'onAddCard', None) in (self.native_add, self._add_wrapper):
            self.mw.onAddCard = self._add_wrapper
        try:
            from aqt.qt import QShortcut
            for shortcut in self.mw.findChildren(QShortcut):
                if shortcut in self._shortcuts or shortcut.key().toString().casefold() != 'a':
                    continue
                try:
                    shortcut.activated.disconnect(self.native_add)
                except (TypeError, RuntimeError):
                    continue
                shortcut.activated.connect(self._add_wrapper)
                self._shortcuts.append(shortcut)
        except (ImportError, AttributeError, RuntimeError):
            pass

    def editor_loaded(self, editor):
        """Enhance the *existing* bottom-left Edit route, never Browser selection."""
        if not self.alive or getattr(editor, 'addMode', False):
            return
        parent = getattr(editor, 'parentWindow', None)
        try:
            from aqt.editcurrent import EditCurrent
            recognized = isinstance(parent, EditCurrent)
        except ImportError:
            return
        if not recognized:
            return
        note = getattr(editor, 'note', None)
        card = getattr(getattr(self.mw, 'reviewer', None), 'card', None)
        if (not getattr(self.mw, 'col', None) or self.mw.state != 'review'
                or note is None or card is None or int(note.id) != int(card.nid)):
            return
        kind = mask_kind(editor)
        key = (id(self.mw.col), int(note.id))
        if self._editors.get(editor) == key:
            return
        self._editors[editor] = key
        # Anki's loadNote() already opens its mask canvas for native IO. Running
        # setupMaskEditor a second time could reset an in-progress native edit.
        if kind != 'ioe':
            return
        link = getattr(editor, '_links', {}).get('I/O')
        if not callable(link):
            self._notice('This card uses Image Occlusion Enhanced. Enable its owning add-on to edit masks; the field editor remains available.')
            return
        col = self.mw.col
        epoch = self.controller.epoch
        reference = weakref.ref(editor)
        def launch():
            e = reference()
            if (not self.alive or self.mw.col is not col or self.controller.epoch != epoch
                    or e is None or getattr(e, 'note', None) is None or int(e.note.id) != key[1]):
                return
            try:
                # The registered owner callback itself calls call_after_note_saved.
                link(e)
            except Exception as exc:
                self.controller.record('open_owning_mask_editor', exc)
                self._notice('The owning mask editor could not open. Your note has not been converted; use its Image Occlusion button in Edit.')
        from aqt.qt import QTimer
        QTimer.singleShot(0, launch)

    def dispose(self):
        if not self.alive:
            return
        self.alive = False
        if getattr(self.mw, 'onAddCard', None) is self._add_wrapper:
            self.mw.onAddCard = self.native_add
        for shortcut in self._shortcuts:
            try:
                shortcut.activated.disconnect(self._add_wrapper)
                shortcut.activated.connect(self.native_add)
            except (RuntimeError, TypeError):
                pass
        self._shortcuts.clear()
        self._editors.clear()
        if getattr(self.mw, '_atelier_authoring_routes', None) is self:
            delattr(self.mw, '_atelier_authoring_routes')


def install_authoring(owner, registration):
    from aqt import mw, gui_hooks
    from .workshop.integration import install
    existing = getattr(mw, '_daedalus_workshop_controller', None)
    if existing is not None:
        # No two independent writers to a project database. Keep the suite usable
        # with a clear migration error rather than overwriting a running controller.
        from .lifecycle import StartupBlocked
        raise StartupBlocked('Standalone Workshop is still running. Disable the separate Workshop add-on and fully restart Anki. Its projects and drafts stay in your profile; do not delete them.')
    controller = install(suite=owner, registration=registration)
    if controller is None:
        raise RuntimeError('Card Studio could not initialize.')
    owner.workshop = controller
    routes = AuthoringRoutes(owner, controller, registration)
    mw._atelier_authoring_routes = routes
    for name, callback in [('webview_did_receive_js_message', routes.message),
                           ('profile_did_open', routes.bind),
                           ('editor_did_load_note', routes.editor_loaded)]:
        hook = getattr(gui_hooks, name, None)
        if hook is not None:
            registration.hook(hook, callback)
    from aqt.qt import QAction
    native = QAction('Add cards in native Anki…', mw)
    native.triggered.connect(lambda _=False: routes.original_add())
    controller.menu.addAction(native)
    routes.bind()
    from .card_studio import install_suite_authoring
    install_suite_authoring(owner, controller, routes, registration)

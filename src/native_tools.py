"""Native Anki access and scoped tool-window presentation.

No replacement editor/browser, forced note save, global palette, scheduler patch,
or filesystem mutation. Commands delegate to Anki's existing actions/dialogs.
"""
from __future__ import annotations
from typing import Any
import logging
import weakref
from .core import ValidationError, json_for_html
from .review_model import PALETTES

LOG = logging.getLogger('atelier.native')
COMMANDS = {
    'add': ('Add cards', ('onAddCard',)),
    'browse': ('Browse cards', ('onBrowse',)),
    'stats': ('Statistics', ('onStats',)),
    'sync': ('Sync', ('on_sync_button_clicked', 'onSync')),
    'import': ('Import', ('onImport',)),
    'export': ('Export', ('onExport',)),
    'preferences': ('Anki preferences', ('onPrefs',)),
    'note_types': ('Note types', ('onNoteTypes',)),
    'undo': ('Undo', ('undo', 'onUndo')),
    'redo': ('Redo', ('redo',)),
    'help': ('Anki manual', ('onDocumentation',)),
}
FORM_ACTIONS = {
    'addons': ('actionAdd_ons', 'actionAddons'),
    'check_media': ('actionCheckMediaDatabase', 'actionCheckMedia', 'actionCheck_Media'),
    'check_database': ('actionFullDatabaseCheck', 'actionCheckDB', 'actionCheck_Database'),
    'profiles': ('actionSwitchProfile', 'actionSwitch_Profile'),
    'filtered_deck': ('actionCreateFiltered',),
    'empty_cards': ('actionEmptyCards',),
    'fullscreen': ('actionFullScreen',),
    'check_updates': ('action_check_for_updates',),
}


def capabilities(mw: Any) -> dict[str, bool]:
    out = {key: any(callable(getattr(mw, name, None)) for name in funcs)
           for key, (_, funcs) in COMMANDS.items()}
    for key, names in FORM_ACTIONS.items():
        out[key] = any(callable(getattr(getattr(getattr(mw, 'form', None), name, None), 'trigger', None)) for name in names)
    return out


def dispatch(mw: Any, action: Any) -> None:
    """Called only after the calling home/planner bridge verifies its context."""
    if not isinstance(action, str) or action not in COMMANDS and action not in FORM_ACTIONS:
        raise ValidationError('That is not an available Anki tool.')
    if not getattr(mw, 'col', None):
        raise ValidationError('Open an Anki profile first.')
    engine = getattr(mw, '_exam_sprout_controller', None)
    studio = getattr(getattr(mw, '_daedalus_workshop_controller', None), 'window', None)
    if action in ('sync', 'profiles', 'check_database') and studio is not None and (getattr(studio, 'dirty', False) or getattr(studio, 'busy', False)):
        raise ValidationError('Save your Card Studio draft and wait for publishing to finish before this operation.')
    if action in ('sync', 'profiles', 'check_database') and engine is not None:
        if getattr(engine, 'runner', None) is not None:
            raise ValidationError('Save & close or finish the current practice session before this operation.')
        if getattr(getattr(engine, 'dialog', None), 'dirty', False):
            raise ValidationError('Save or cancel the unfinished exam setup before this operation; its contents have been kept.')
    routes = getattr(mw, '_atelier_authoring_routes', None)
    if action == 'add' and routes is not None:
        routes.create()
        return
    if action in COMMANDS:
        for name in COMMANDS[action][1]:
            fn = getattr(mw, name, None)
            if callable(fn):
                fn()
                return
    else:
        for name in FORM_ACTIONS[action]:
            native_action = getattr(getattr(mw, 'form', None), name, None)
            if callable(getattr(native_action, 'trigger', None)):
                if callable(getattr(native_action, 'isEnabled', None)) and not native_action.isEnabled():
                    raise ValidationError('Anki has temporarily disabled this action. Finish the current operation first.')
                native_action.trigger()
                return
    raise ValidationError('This Anki version does not expose this shortcut. Use the original File or Tools menu; it has not been hidden.')


DIALOGS = frozenset(('AddCards', 'NewAddCards', 'Browser', 'EditCurrent', 'NewEditCurrent',
                    'Preferences', 'DeckStats', 'NewDeckStats', 'DeckOptionsDialog'))
BEGIN = '/* atelier-native-start */'
END = '/* atelier-native-end */'


def remove_owned(sheet: str) -> str:
    start = sheet.find(BEGIN)
    if start >= 0:
        end = sheet.find(END, start)
        if end >= 0:
            return (sheet[:start] + sheet[end+len(END):]).rstrip()
    return sheet


def qt_css(p: dict) -> str:
    """A per-window stylesheet. No field HTML, note styles or chart colors."""
    root = 'QWidget[atelier_surface="true"]'
    return BEGIN + '\n' + f'''
{root} {{ background-color:{p['bg']}; color:{p['text']}; }}
{root} QLabel, {root} QCheckBox, {root} QRadioButton {{color:{p['text']};}}
{root} QToolBar, {root} QStatusBar, {root} QTabWidget::pane {{background:{p['side']};border:1px solid {p['line']};}}
{root} QPushButton, {root} QToolButton {{background:{p['raised']};color:{p['text']};border:1px solid {p['line']};border-radius:6px;padding:5px 9px;}}
{root} QPushButton:hover, {root} QToolButton:hover {{background:{p['hover']};border-color:{p['accent']};}}
{root} QPushButton:focus, {root} QToolButton:focus {{border-color:{p['accent']};}}
{root} QPushButton:disabled, {root} QToolButton:disabled {{color:{p['quiet']};}}
{root} QLineEdit, {root} QComboBox, {root} QSpinBox, {root} QDoubleSpinBox {{background:{p['panel']};color:{p['text']};border:1px solid {p['line']};border-radius:5px;padding:4px;selection-background-color:{p['accent-soft']};selection-color:{p['text']};}}
{root} QTreeView, {root} QTableView, {root} QListView {{background:{p['panel']};alternate-background-color:{p['side']};color:{p['text']};border:1px solid {p['line']};selection-background-color:{p['accent-soft']};selection-color:{p['text']};}}
{root} QHeaderView::section {{background:{p['side']};color:{p['muted']};border:0;border-bottom:1px solid {p['line']};padding:7px;}}
{root} QTabBar::tab {{background:{p['side']};color:{p['muted']};padding:7px 11px;border-bottom:2px solid transparent;}}
{root} QTabBar::tab:selected {{color:{p['text']};border-bottom-color:{p['accent']};}}
{root} QGroupBox {{color:{p['text']};border:1px solid {p['line']};border-radius:7px;margin-top:12px;padding-top:12px;}}
{root} QGroupBox::title {{subcontrol-origin:margin;left:10px;}}
''' + END


def web_css(p: dict) -> str:
    vars_ = {'canvas':'bg', 'canvas-inset':'side', 'canvas-elevated':'panel',
             'canvas-overlay':'panel', 'fg':'text', 'fg-default':'text',
             'fg-subtle':'muted', 'fg-muted':'muted', 'border':'line',
             'border-subtle':'line-soft', 'link':'accent', 'button-bg':'raised'}
    return ':root{' + ''.join(f'--{k}:{p[v]}!important;' for k,v in vars_.items()) + '}'


class NativeSurfaces:
    """Keep original native controls, dimensions, data and dialog close guards."""
    def __init__(self, owner: Any):
        self.owner = owner
        self.windows = weakref.WeakKeyDictionary()
        self.webs = weakref.WeakSet()

    def enabled(self) -> bool:
        cfg = self.owner.get_config()
        return cfg.get('visual_owner') == 'atelier' and cfg.get('native_surfaces', True)

    def apply(self, dialog: Any) -> None:
        if not callable(getattr(dialog, 'setStyleSheet', None)):
            return
        try:
            before = dialog.styleSheet()
            if dialog not in self.windows:
                self.windows[dialog] = {'property':dialog.property('atelier_surface')}
            if self.enabled():
                p = PALETTES[self.owner.get_config()['theme']]
                dialog.setProperty('atelier_surface', True)
                clean = remove_owned(before)
                dialog.setStyleSheet(clean + '\n' + qt_css(p))
            else:
                dialog.setProperty('atelier_surface', self.windows[dialog]['property'])
                dialog.setStyleSheet(remove_owned(before))
        except (RuntimeError, AttributeError, TypeError):
            LOG.warning('Anki window theme unavailable; original tool controls remain.')

    def opened(self, manager: Any, name: str, instance: Any) -> None:
        if name in DIALOGS:
            self.apply(instance)

    def parent_dialog(self, web: Any):
        obj=web
        for _ in range(9):
            if obj is None: break
            if type(obj).__name__ in DIALOGS and type(obj).__module__.startswith('aqt.'):
                return obj
            parent = getattr(obj,'parent',None)
            obj = parent() if callable(parent) else None
        return None

    def inject(self, web: Any) -> None:
        # Stats/options use external TS pages; do not touch any card Previewer.
        dialog = self.parent_dialog(web)
        if dialog is None: return
        self.webs.add(web)
        self.apply(dialog)
        self._web(web)

    def _web(self, web: Any) -> None:
        enabled = self.enabled()
        css = web_css(PALETTES[self.owner.get_config()['theme']]) if enabled else ''
        script = '(function(){let s=document.getElementById("atelier-native-tool-tokens");'
        script += 'if(!s){s=document.createElement("style");s.id="atelier-native-tool-tokens";document.head.append(s);}s.textContent='+json_for_html(css)+';})();'
        try: web.eval(script)
        except (RuntimeError, AttributeError): pass

    def refresh(self) -> None:
        for dialog in list(self.windows): self.apply(dialog)
        for web in list(self.webs): self._web(web)

    def dispose(self) -> None:
        for dialog,state in list(self.windows.items()):
            try:
                dialog.setProperty('atelier_surface', state['property'])
                dialog.setStyleSheet(remove_owned(dialog.styleSheet()))
            except (RuntimeError, AttributeError): pass
        for web in list(self.webs):
            try: web.eval('document.getElementById("atelier-native-tool-tokens")?.remove();')
            except (RuntimeError, AttributeError): pass
        self.windows.clear();self.webs.clear()

    def install(self, registration: Any):
        from aqt import gui_hooks
        for name,fn in [('dialog_manager_did_open_dialog',self.opened),('webview_did_inject_style_into_page',self.inject)]:
            hook=getattr(gui_hooks,name,None)
            if callable(getattr(hook,'append',None)): registration.hook(hook,fn)
        registration.cleanup(self.dispose)

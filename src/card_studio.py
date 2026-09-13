"""One suite-owned presentation/navigation contract for the embedded Card Studio.

The project database, native-note publisher, assessment engine and their approval
protocols stay with their original owners. This module only projects summaries,
coordinates appearance, and opens existing guarded routes.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from .core import VERSION, ValidationError, json_for_html, fresh_catalog
from .review_model import PALETTES
from .worlds import CATALOG

LOG = logging.getLogger('atelier.card-studio')
ROOT = Path(__file__).resolve().parent


def appearance(owner: Any) -> dict:
    cfg = owner.get_config()
    enabled = cfg.get('visual_owner') == 'atelier'
    key = cfg.get('theme', 'obsidian')
    p = dict(PALETTES.get(key, PALETTES['obsidian']))
    world = next((w for w in CATALOG if w['id'] == key), CATALOG[0])
    return {'version': VERSION, 'enabled': enabled, 'theme': key,
            'motion': cfg.get('motion', True), 'ambience': cfg.get('ambience', True),
            'palette': p if enabled else {},
            'world': {k: world.get(k, '') for k in ('id','name','title','font','radius','material')},
            'worlds': [{'id': w['id'], 'name': w['name'], 'kind': w['kind']} for w in CATALOG]}


def head(owner: Any) -> str:
    cfg = appearance(owner)
    sheet = (ROOT/'web'/'card-studio-shell.css').read_text(encoding='utf8')
    return ('<style id="atelier-card-studio-shell">'+sheet+'</style><script>'
            'window.AtelierCardStudioBootstrap='+json_for_html(cfg)+';'
            'document.documentElement.dataset.atelierCardStudio="true";'
            '</script>')


def native_chrome(window: Any, value: dict) -> None:
    """Theme this owned window's native status/Close controls, not application globals."""
    from .native_tools import qt_css, remove_owned
    if not all(callable(getattr(window,k,None)) for k in ('styleSheet','setStyleSheet','setProperty')):
        return
    sheet=remove_owned(window.styleSheet())
    if value.get('enabled') and value.get('palette'):
        window.setProperty('atelier_surface',True)
        window.setStyleSheet(sheet+'\n'+qt_css(value['palette']))
    else:
        window.setProperty('atelier_surface',False)
        window.setStyleSheet(sheet)


def summary(controller: Any) -> dict:
    store = getattr(controller, 'store', None)
    if store is None:
        return {'available': False, 'message': 'Card Studio will be available when this profile is ready.'}
    # Local read-only projection; never persist a competing project list in Atelier.
    projects = store.list('project', limit=10000)
    drafts = store.list('draft', limit=10000)
    repairs = store.list('repair', limit=10000)
    return {'available': True, 'version': '1.1.0-rc.1',
            'projects': sum(not p.get('archived') for p in projects),
            'drafts': sum(d.get('status') != 'committed' for d in drafts),
            'repairs': sum(r.get('status') == 'open' for r in repairs)}


def refresh_home(owner: Any) -> None:
    mw = getattr(owner, 'workshop', None)
    if mw is None:
        return
    mw = mw.mw
    if getattr(mw, 'state', None) != 'deckBrowser' or not getattr(owner, 'nonce', ''):
        return
    try:
        payload = {'token': owner.nonce, 'authoring': summary(owner.workshop)}
        mw.web.eval('window.AtelierMakeover&&window.AtelierMakeover.updateAuthoring&&'
                    'window.AtelierMakeover.updateAuthoring('+json_for_html(payload)+');')
    except (RuntimeError, AttributeError):
        LOG.debug('Closed home ignored while refreshing authoring summary')


def install_suite_authoring(owner: Any, controller: Any, routes: Any, registration: Any) -> None:
    owner.authoring_summary = lambda: summary(controller)
    def refresh() -> None:
        dialog = getattr(controller, 'window', None)
        if dialog is not None and not getattr(dialog, 'closed', False):
            # Do not reload the webview or alter any editor input / mask state.
            value = appearance(owner)
            dialog.suite_palette = value['palette']
            try:
                native_chrome(dialog,value)
                dialog.emit('appearance', value)
            except (RuntimeError, AttributeError):
                pass
    owner.authoring_refresh = refresh
    unsubscribe = controller.api.subscribe(lambda _event: refresh_home(owner))
    registration.cleanup(unsubscribe)
    def cleanup() -> None:
        for key in ('authoring_summary', 'authoring_refresh', 'workshop'):
            if hasattr(owner, key):
                delattr(owner, key)
    registration.cleanup(cleanup)


def _ready(window: Any, *, clean: bool = False) -> Any:
    if not window.valid() or window.controller.suite is None:
        raise ValidationError('The Card Studio profile changed. Reopen it before continuing.')
    if window.busy:
        raise ValidationError('Wait for the current Card Studio operation to finish.')
    if clean and window.dirty:
        raise ValidationError('Save your current draft before leaving Card Studio.')
    if getattr(getattr(window.mw, '_exam_sprout_controller', None), 'runner', None) is not None:
        raise ValidationError('Save and close or finish the current practice session first.')
    return window.controller.suite


def command(window: Any, action: str, payload: dict) -> dict:
    owner = _ready(window, clean=action in ('suite_home', 'suite_open'))
    if action == 'suite_appearance':
        cfg = owner.get_config()
        if cfg.get('visual_owner') != 'atelier':
            raise ValidationError('The original appearance owner is active. Change ownership from Atelier Appearance first.')
        allowed = {'theme', 'motion', 'ambience'}
        if not payload or not set(payload) <= allowed:
            raise ValidationError('Only the shared world and comfort settings can change here.')
        if 'theme' in payload and payload['theme'] not in PALETTES:
            raise ValidationError('Choose a world from the shared catalogue.')
        for k in ('motion','ambience'):
            if k in payload and type(payload[k]) is not bool:
                raise ValidationError('Choose an enabled or disabled comfort setting.')
        owner.save_config(payload)
        return appearance(owner)
    if action == 'suite_decks':
        from .focus_context import active_deck_ids
        cat=fresh_catalog(window.col);owner.ensure_store()
        active=active_deck_ids(owner.profile,cat)
        return {'decks':[{'id':i,'name':d['name'],'active':i in active} for i,d in cat.items() if not d.get('filtered')]}
    if action == 'suite_native':
        from .native_tools import dispatch
        action_id = payload.get('command')
        if action_id not in ('browse','sync','stats','check_media','note_types'):
            raise ValidationError('This native tool is not available through Card Studio.')
        dispatch(window.mw, action_id)
        return {'opened': action_id}
    if action == 'suite_home':
        # Caller flushes its original draft first. Closing uses the normal close guard.
        window.mw.moveToState('deckBrowser')
        window.close()
        return {'opened': 'study-desk'}
    if action == 'suite_open':
        view = payload.get('view','overview')
        if view not in ('overview','practice','pip'):
            raise ValidationError('Choose an existing study destination.')
        window.mw.moveToState('deckBrowser')
        owner.sprout_link.open_target(view)
        window.hide()  # original window and draft remain; no second controller
        return {'opened': view}
    raise ValidationError('Unknown suite action.')


def project_to_plan(window: Any, payload: dict) -> dict:
    owner = _ready(window, clean=True)
    from .workshop.core import identifier
    project = window.store.get('project', identifier(payload.get('project_id')))
    linked = {int(link['note_id']) for link in window.store.list('link',project['id'])}
    # Read original note/card IDs. Do not tag notes or broaden to whole decks.
    existing = []
    decks = set()
    for nid in sorted(linked):
        try:
            ids = list(window.col.card_ids_of_note(nid))
            if not ids:
                continue
            current = set()
            for cid in ids:
                card = window.col.get_card(cid)
                did = int(getattr(card,'odid',0) or card.did)
                current.add(str(did))
            if not current:
                continue
            existing.append(nid)
            decks.update(current)
        except (KeyError, LookupError):
            continue
    if not existing:
        raise ValidationError('Add or link cards to this project before creating an exam plan.')
    query = 'nid:' + ','.join(map(str,existing))
    if len(query) > 2000:
        raise ValidationError('This project exceeds the exam search limit. Use a smaller project or an explicitly chosen deck/tag scope; no notes were retagged.')
    catalogue = fresh_catalog(window.col)
    if not 1 <= len(decks) <= 100 or any(d not in catalogue for d in decks):
        raise ValidationError('The project’s deck scope is unavailable or too large. No exam was created.')
    setup = {'name': str(project['title'])[:120], 'deck_ids': sorted(decks, key=int), 'query': query}
    window.mw.moveToState('deckBrowser')
    owner.sprout_link.open_target('new', setup=setup)
    window.hide()
    return {'opened': 'exam-setup', 'notes':len(existing), 'query':query,
            'message':'Exam setup uses only this project’s linked notes. Choose the date and routine, then save the plan. No exam was automatically saved.'}

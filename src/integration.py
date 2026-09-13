"""Public Anki hooks, context-restricted bridge and undo-aware deck operations.

No scheduler patches, SQL writes, card-template modifications,
network requests, card-template edits, or global Qt stylesheets.
"""
from __future__ import annotations

import json
import logging
import re
import secrets
from pathlib import Path
from typing import Any

import aqt
from aqt import gui_hooks, mw
from aqt.deckbrowser import DeckBrowser, DeckBrowserBottomBar
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import QAction, QApplication, QEvent, QObject, Qt, QWidget
from aqt.utils import showInfo

from .core import (VERSION, COLORS, ProfileStore, ValidationError, collection_snapshot,
                   creation_path, deck_id, fresh_catalog, json_for_html, profile_settings,
                   rename_path, settings, validate_move, validate_study, observe_decks, quick_study, set_study_active, exam_label, home_layout, upsert_study, canonical_profile)

log = logging.getLogger("atelier")
ROOT = Path(__file__).resolve().parent
from .review_model import PALETTES as REVIEW_PALETTES
PALETTES = {k: (p["bg"], p["text"], p["accent"], p["line"]) for k, p in REVIEW_PALETTES.items()}

class InputShortcutGuard(QObject):
    """Protect only Atelier's focused form/modal from plain-key Qt shortcuts.

    QWebEngine receives ShortcutOverride before JavaScript keydown. Accepting
    that event keeps letters such as D/B/A in the input, without disabling or
    unregistering any of Anki's or another add-on's QShortcuts.
    """
    def __init__(self, controller: "Atelier") -> None:
        super().__init__(mw)
        self.controller = controller

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (event.type() != QEvent.Type.ShortcutOverride
                or not self.controller.capture_keys
                or not self.controller.nonce
                or mw.state != "deckBrowser"):
            return False
        web = getattr(mw, "web", None)
        if web is None or not (watched is web or
                isinstance(watched, QWidget) and web.isAncestorOf(watched)):
            return False
        # Keep platform menu, copy/paste, zoom and other modified shortcuts.
        modifiers = event.modifiers()
        if modifiers & (Qt.KeyboardModifier.ControlModifier |
                        Qt.KeyboardModifier.AltModifier |
                        Qt.KeyboardModifier.MetaModifier):
            return False
        event.accept()
        return True

class Atelier:
    def __init__(self, module: str) -> None:
        self.module = module
        self.package = mw.addonManager.addonFromModule(module)
        self.nonce = ""
        self.open_settings_next = False
        self.store: ProfileStore | None = None
        self.profile: dict[str, Any] = profile_settings({})
        self.busy = False
        self.operation_ticket = None
        self.capture_keys = False
        self._ui_state: dict[str, Any] = {}
        from .sprout_link import SproutLink
        self.sprout_link = SproutLink(self, mw)
        from .ownership import Ownership
        self.ownership = Ownership(self)

    def addon_manager(self) -> Any:
        return mw.addonManager

    def get_config(self) -> dict[str, Any]:
        from .ownership import resolve_config
        return resolve_config(settings(mw.addonManager.getConfig(self.module)), self.ownership.report())

    def current_state(self) -> str:
        return getattr(mw, 'state', '')

    def sprout_config(self) -> dict:
        cfg = self.get_config()
        if cfg['visual_owner'] != 'atelier':
            # Native ownership means native Sprout appearance too. Companion
            # colors are used ONLY in our own shadow-root organizer/launcher.
            cfg['match_sprout'] = False
        return cfg

    def save_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        config = self.get_config()
        config.update({k: v for k, v in patch.items() if k in config})
        config = settings(config)
        mw.addonManager.writeConfig(self.module, config)
        self.ownership.install()
        self.apply_chrome()
        if hasattr(self, "native_surfaces"): self.native_surfaces.refresh()
        self.sprout_link.refresh()
        if hasattr(self, "authoring_refresh"):
            self.authoring_refresh()
        if hasattr(self, "review_theme"):
            self.review_theme.refresh()
        # A planner can change worlds while the home remains open behind it.
        # Deliver the current appearance to that same page without reloading its
        # form or deck tree. The page token rejects stale navigation callbacks.
        web = getattr(mw, "web", None)
        if self.nonce and getattr(mw, "state", "") == "deckBrowser" and getattr(mw, "col", None) is not None and web is not None:
            try:
                web.eval("window.AtelierMakeover?.applyAppearance(" + json_for_html({"token": self.nonce, "settings": config}) + ");")
            except (AttributeError, RuntimeError):
                log.debug("Appearance delivery skipped: home webview closed")
        return config

    def ensure_store(self) -> None:
        if self.store is None:
            self.store = ProfileStore(ROOT / "user_files", str(mw.pm.profileFolder()))
            self.profile = self.store.read()
            if self.profile.get("surfaces_version", 0) < 1:
                # Reset only the first 0.5.1-or-later launch to the isolated study desk.
                # Keep saved widgets and studies; the original home is one click away.
                # A per-profile marker works even when Anki merges new config defaults.
                cfg = self.get_config()
                cfg.update(mode="workspace", surface_revision=1)
                mw.addonManager.writeConfig(self.module, cfg)
                migrated = dict(self.profile, surfaces_version=1)
                try:
                    self.store.write(migrated)
                    self.profile = migrated
                except (OSError, ValidationError):
                    log.warning("Atelier could not save the one-time surface migration")
            from .native_widgets import widget_route_upgrade
            current_config = self.get_config()
            route_config, route_profile, recovered = widget_route_upgrade(current_config, self.profile)
            if route_profile != self.profile:
                try:
                    # Persist config before consuming the upgrade marker. A failed
                    # write leaves the marker eligible for a later retry.
                    if recovered:
                        mw.addonManager.writeConfig(self.module, route_config)
                    self.store.write(route_profile)
                    self.profile = route_profile
                except (OSError, ValidationError):
                    log.warning("Widget navigation upgrade could not be saved; existing data retained")
                if recovered:
                    self._ui_state = {"page": "widgets", "location": "0", "query": "", "filter": "all"}

    def closed(self) -> None:
        self.capture_keys = False
        self.busy = False
        self.nonce = ""
        self.store = None
        self.profile = profile_settings({})
        self._ui_state = {}
        self.operation_ticket = None
        self.ownership.dispose()
        if hasattr(self, "review_theme"):
            self.review_theme.layout_token = ""
            self.review_theme.layout_pending = False
        self.sprout_link.cancel_pending()

    def add_content(self, content: Any, context: Any) -> None:
        # Screen allow-list. Card/preview/editor/stats content is never touched.
        self.ownership.install()
        config = self.get_config()
        self.sprout_link.add_content(content, context)
        if isinstance(context, DeckBrowserBottomBar):
            if config["visual_owner"] == "atelier" and config["chrome"] and config["mode"] != "native":
                bg, fg, accent, line = PALETTES[config["theme"]]
                content.head += f'<style id="atelier-bottom-chrome">body{{background:{bg};color:{fg}}}button{{border-color:{line};color:{fg};background:{bg};border-radius:8px}}</style>'
            return
        if not isinstance(context, DeckBrowser):
            return
        try:
            self.ensure_store()
            config = self.get_config()
            nonce = secrets.token_urlsafe(24)
            from .worlds import CATALOG
            from .native_tools import capabilities
            boot = {"version": VERSION, "token": nonce, "settings": config,
                    "profile": self.profile, "ui": self._ui_state,
                    "openSettings": self.open_settings_next, "preview": False,
                    "worlds": CATALOG, "authoring": self.authoring_summary() if hasattr(self, "authoring_summary") else {}, "suite": self.sprout_link.summary(), "nativeTools": capabilities(mw), "suiteAssets": f"/_addons/{self.package}/sprout/web",
                    "integrations": {"bundled": True, "exam_sprout": self.sprout_link.available(), "onigiri": self.ownership.available(), **self.ownership.report()}}
            # Read CSS as text and mount it *inside* a shadow root. Other add-ons'
            # body/button/card selectors cannot reach Atelier's interface.
            css = (ROOT / "web" / "atelier.css").read_text(encoding="utf-8")
            from .worlds import home_css
            css += "\n" + home_css(self.package)
            addition = ('<div id="atelier-root"></div>'
                        '<script type="application/json" id="atelier-bootstrap">'
                        + json_for_html(boot) + '</script>'
                        '<template id="atelier-style"><style>' + css + '</style></template>')
            from .surfaces import home_guard
            content.head = home_guard(config) + content.head
            content.body = addition + content.body  # Preserve all original nodes/content.
            content.js.append(f"/_addons/{self.package}/web/widget-registry.js?v={VERSION}")
            content.js.append(f"/_addons/{self.package}/web/native-widgets.js?v={VERSION}")
            content.js.append(f"/_addons/{self.package}/web/ownership.js?v={VERSION}")
            content.js.append(f"/_addons/{self.package}/web/model.js?v={VERSION}")
            content.js.append(f"/_addons/{self.package}/web/cohesion.js?v={VERSION}")
            content.js.append(f"/_addons/{self.package}/web/home.js?v={VERSION}")
            content.js.append(f"/_addons/{self.package}/web/atelier.js?v={VERSION}")
            self.capture_keys = False
            self.nonce = nonce
            self.open_settings_next = False
        except Exception:
            log.exception("Atelier could not render; keeping the original home screen")

    def reply(self, nonce: str, request_id: str, *, result: Any = None, error: str | None = None) -> None:
        if self.nonce != nonce or mw.state != "deckBrowser" or not mw.col:
            return
        payload = {"id": request_id, "token": nonce, "result": result, "error": error}
        mw.web.eval("window.AtelierMakeover && window.AtelierMakeover.receive(" + json_for_html(payload) + ");")

    def receive(self, handled: tuple[bool, Any], message: str, context: Any) -> tuple[bool, Any]:
        if handled[0] or not message.startswith("atelier:v1:"):
            return handled
        # Messages from a reviewer, editor, different page, or old profile are ignored.
        if (not isinstance(context, DeckBrowser) or context is not mw.deckBrowser
                or mw.state != "deckBrowser" or not mw.col):
            return (True, None)
        request_id = ""
        nonce = ""
        try:
            if len(message) > 16384:
                raise ValidationError("That request is too large.")
            _, _, nonce, raw = message.split(":", 3)
            if not self.nonce or not secrets.compare_digest(nonce, self.nonce):
                return (True, None)
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValidationError("Invalid request.")
            request_id = str(request.get("id", ""))
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", request_id):
                raise ValidationError("Invalid request identifier.")
            data = request.get("data", {})
            if not isinstance(data, dict):
                raise ValidationError("Invalid request data.")
            self.dispatch(nonce, request_id, request.get("action"), data)
        except Exception as exc:
            log.warning("Atelier command rejected: %s", type(exc).__name__)
            self.reply(nonce, request_id, error=str(exc) if isinstance(exc, ValidationError)
                       else "This action could not be completed. Refresh and try again; the original Anki interface remains available.")
        return (True, None)

    def dispatch(self, nonce: str, rid: str, action: str, data: dict[str, Any]) -> None:
        self.ensure_store()
        if action == "load":
            store = self.store
            def complete(snapshot: dict) -> None:
                if self.nonce != nonce or self.store is not store or not mw.col:
                    return
                observed = observe_decks(self.profile, snapshot["nodes"])
                if observed != self.profile:
                    try:
                        assert store is not None
                        store.write(observed)
                        self.profile = observed
                    except Exception:
                        snapshot["notice"] = "Recent-deck tracking could not be saved. Your collection is unchanged."
                snapshot.update(settings=self.get_config(), profile=self.profile, suite=self.sprout_link.summary(), authoring=self.authoring_summary() if hasattr(self, "authoring_summary") else {})
                self.reply(nonce, rid, result=snapshot)
            QueryOp(parent=mw, op=collection_snapshot, success=complete).failure(
                lambda exc: self.reply(nonce, rid, error="Anki's deck information is not available right now. Your original home remains available. Try Refresh after Anki finishes its current operation.")
            ).run_in_background()
        elif action == "study_progress":
            from .study_progress import read_progress
            from copy import deepcopy
            profile=deepcopy(self.profile);col=mw.col;store=self.store
            def ready_progress(result):
                if mw.col is col and self.store is store and self.nonce==nonce:
                    self.reply(nonce,rid,result=result)
            QueryOp(parent=mw,op=lambda c:read_progress(c,profile,str(data.get('scope','active')),data.get('days',7)),success=ready_progress).failure(lambda e:self.reply(nonce,rid,error=str(e) if isinstance(e,ValidationError) else 'Study history could not load. Your collection is unchanged.')).run_in_background()
        elif action == "export_deck":
            from .study_progress import export_deck
            self._export_dialog=export_deck(mw,data.get('id'))
            self.reply(nonce,rid,result={"opened":True})
        elif action == "remote_setup":
            self.remotes.open()
            self.reply(nonce, rid, result={"opened": True})
        elif action == "native_tool":
            from .native_tools import dispatch as native_dispatch
            native_dispatch(mw, data.get("command"))
            self.reply(nonce, rid, result={"opened": True})
        elif action == "authoring_open":
            routes = getattr(mw, "_atelier_authoring_routes", None)
            if routes is None:
                raise ValidationError("Card Studio is not ready. Use Tools → Atelier → Diagnostics.")
            routes.open_page(data.get("view", "studio"), data.get("note_id"), data.get("deck_id"))
            self.reply(nonce, rid, result={"opened": True})
        elif action == "suite_open":
            self.sprout_link.open_target(data.get("view", "overview"), str(data.get("id", "")), data.get("setup"))
            self.reply(nonce, rid, result={"opened": True})
        elif action == "suite_focus":
            from .suite import focus_exam
            result = focus_exam(self, str(data.get("id", "")))
            self.reply(nonce, rid, result={**result, "profile": self.profile})
        elif action == "visual_owner":
            value = data.get('owner')
            if value not in ('atelier', 'onigiri', 'external'):
                raise ValidationError('Choose Atelier, Onigiri, or Original / other makeover.')
            if value == 'onigiri' and not self.ownership.available():
                raise ValidationError('Onigiri is not loaded. Enable it and restart before choosing Companion.')
            cfg = self.save_config({'visual_owner': value, 'mode': 'workspace' if value == 'atelier' else 'native',
                                    'acknowledged_makeovers': [x['id'] for x in self.ownership.report()['makeovers']]})
            self.ownership.companion_palette.clear()
            self.reply(nonce, rid, result=cfg)
            # Deliver the response before replacing its bridge/web document.
            collection = mw.col
            def reload_owner() -> None:
                if mw.col is collection and self.nonce == nonce and mw.state == 'deckBrowser':
                    mw.moveToState('deckBrowser')
            mw.progress.single_shot(150, reload_owner)
        elif action == 'rescan_makeovers':
            report = self.ownership.report(refresh=True)
            self.reply(nonce, rid, result=report)
        elif action == 'companion_palette':
            if self.get_config()['visual_owner'] in ('onigiri', 'external'):
                from .ownership import validate_palette
                try:
                    self.ownership.companion_palette = validate_palette(data)
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc
                self.sprout_link.refresh()
            self.reply(nonce, rid, result=True)
        elif action == 'sprout_practice':
            if not self.sprout_link.open_practice():
                raise ValidationError('Exam Studio could not open Practice. See Tools → Atelier → Exam Sprout diagnostics.')
            self.reply(nonce, rid, result=True)
        elif action == "sprout_open":
            if not self.sprout_link.open():
                raise ValidationError("Exam Studio is not ready in this profile. See Tools → Atelier → Exam Sprout diagnostics.")
            self.reply(nonce, rid, result=True)
        elif action == "focus":
            if type(data.get("active")) is not bool:
                raise ValidationError("Invalid focus state.")
            self.capture_keys = data["active"]
            self.reply(nonce, rid, result=True)
        elif action == "settings":
            if "visual_owner" in data or "acknowledged_makeovers" in data:
                raise ValidationError("Change visual ownership through the owner picker.")
            self.reply(nonce, rid, result=self.save_config(data))
        elif action == "preference":
            updated = profile_settings(self.profile)
            key = data.get("key")
            if key in ("favorites", "folders"):
                did = deck_id(data.get("id"))
                selected = data.get("value")
                if type(selected) is not bool:
                    raise ValidationError("Choose on or off.")
                updated[key] = [x for x in updated[key] if x != did]
                if selected:
                    updated[key].append(did)
            elif key == "color":
                did = deck_id(data.get("id"))
                value = data.get("value")
                if value not in COLORS:
                    raise ValidationError("Choose one of the folder colors.")
                updated["colors"][did] = value
            elif key == "last_location":
                updated[key] = deck_id(data.get("value"), root=True)
                if updated[key] != "0":
                    updated["recent_locations"] = ([updated[key]] +
                        [x for x in updated["recent_locations"] if x != updated[key]])[:32]
            elif key == "focus_enabled":
                if type(data.get("value")) is not bool:
                    raise ValidationError("Choose on or off.")
                updated[key] = data["value"]
            elif key == "selected_study":
                selected = data.get("value")
                if selected != "all" and selected not in [x["id"] for x in updated["studies"] if x["active"]]:
                    raise ValidationError("Choose an active study.")
                updated[key] = selected
            elif key in ("native_widgets", "native_widget_note"):
                from .native_widgets import widget_layout, widget_note
                updated[key] = (widget_layout if key == "native_widgets" else widget_note)(data.get("value"), strict=True)
            elif key == "home_layout":
                updated[key] = home_layout(data.get("value"), strict=True)
            elif key == "study":
                updated = upsert_study(updated, data.get("value"), fresh_catalog(mw.col))
            elif key == "quick_study":
                did = deck_id(data.get("id"))
                deck = mw.col.decks.get(int(did), default=False)
                if not deck:
                    raise ValidationError("That folder is no longer here. Refresh your library.")
                updated = quick_study(canonical_profile(updated, fresh_catalog(mw.col)), did, exam_label(deck["name"]), data.get("value"))
            elif key == "study_active":
                updated = set_study_active(canonical_profile(updated, fresh_catalog(mw.col)), data.get("id"), data.get("value"))
            elif key == "remove_study":
                sid = data.get("value")
                if not isinstance(sid, str):
                    raise ValidationError("Choose a study.")
                updated["studies"] = [x for x in updated["studies"] if x["id"] != sid]
                if updated["selected_study"] == sid:
                    updated["selected_study"] = "all"
            else:
                raise ValidationError("Unknown preference.")
            assert self.store is not None
            self.store.write(updated)
            self.profile = updated
            self.reply(nonce, rid, result=updated)
        elif action == "ui":
            # Ephemeral navigation survives Anki's own home redraws; no disk I/O.
            self._ui_state = {"location": deck_id(data.get("location", "0"), root=True),
                              "filter": data.get("filter") if data.get("filter") in ("all", "due", "favorites") else "all",
                              "query": str(data.get("query", ""))[:200],
                              "page": data.get("page") if data.get("page") in ("desk", "library", "recent", "favorites", "due", "tools", "widgets") else "desk"}
            self.reply(nonce, rid, result=True)
        elif action in ("create", "rename", "move"):
            if self.busy:
                raise ValidationError("Anki is already finishing an organization change.")
            self.mutate(nonce, rid, action, data)
        elif action in ("study", "study_now", "study_folder"):
            if self.busy:
                raise ValidationError("Anki is already opening a lecture or finishing an organization change.")
            did = deck_id(data.get("id"))
            collection, store = mw.col, self.store
            ticket = object()
            self.operation_ticket, self.busy = ticket, True
            def select(col: Any) -> Any:
                if col is not collection or self.store is not store or self.nonce != nonce:
                    raise ValidationError("The profile or screen changed. Choose the lecture again.")
                if not col.decks.get(int(did), default=False):
                    raise ValidationError("That deck is no longer here. Refresh and choose another.")
                if action == "study_folder":
                    from .folder_study import select_folder
                    return select_folder(col, did, data.get("expected"), data.get("order"))
                if action == 'study_now':
                    current_name = col.decks.get(int(did), default=False)['name']
                    if any(entry['name'].startswith(current_name + '::') for entry in fresh_catalog(col).values()):
                        raise ValidationError('Choose an individual lecture. Quick study does not start a whole parent folder.')
                return col.decks.set_current(int(did))
            def open_overview(_: Any) -> None:
                if self.operation_ticket is ticket:
                    self.operation_ticket, self.busy = None, False
                if self.nonce != nonce or self.store is not store or mw.col is not collection:
                    return
                if self.nonce == nonce and self.store is not None:
                    try:
                        updated = profile_settings(self.profile)
                        updated["last_studied"] = did
                        self.store.write(updated)
                        self.profile = updated
                    except Exception:
                        log.warning("Could not save last-study shortcut")
                self.reply(nonce, rid, result=True)
                if self.nonce == nonce and mw.state == "deckBrowser":
                    if action == 'study_now':
                        mw.col.startTimebox()
                        mw.moveToState('review')
                    else:
                        mw.onOverview()  # Native overview/reviewer/scheduler.
            def study_failure(exc: Exception) -> None:
                if self.operation_ticket is ticket:
                    self.operation_ticket, self.busy = None, False
                self.reply(nonce, rid, error=str(exc) if isinstance(exc, ValidationError)
                           else "Anki could not open that lecture. Refresh and try again.")
            try:
                CollectionOp(mw, select).success(open_overview).failure(study_failure).run_in_background()
            except Exception:
                if self.operation_ticket is ticket:
                    self.operation_ticket, self.busy = None, False
                raise
        elif action == "browse":
            did = deck_id(data["id"]) if data.get("id") else None
            # Native onBrowse/save flow: never search an open editor without saving it.
            if did:
                aqt.dialogs.open("Browser", mw, search=(f"did:{did}",))
            else:
                mw.onBrowse()
            self.reply(nonce, rid, result=True)
        elif action == "options":
            from aqt.deckoptions import display_options_for_deck_id
            display_options_for_deck_id(int(deck_id(data.get("id"))))
            self.reply(nonce, rid, result=True)
        elif action in ("add", "import", "stats"):
            self.reply(nonce, rid, result=True)
            {"add": mw.onAddCard, "import": mw.onImport, "stats": mw.onStats}[action]()
        elif action == "external_layout":
            api = getattr(mw, "onigiri_api", None)
            callback = api.get("open_settings") if isinstance(api, dict) else None
            if not callable(callback):
                raise ValidationError("This Onigiri version does not expose its settings shortcut. Open its Settings from the Onigiri menu. Your widgets and layout are unchanged.")
            self.reply(nonce, rid, result=True)
            callback()
        elif action == "website":
            from aqt.utils import openLink
            openLink("https://daedalusworks.net")
            self.reply(nonce, rid, result=True)
        else:
            raise ValidationError("That action is not supported.")

    def mutate(self, nonce: str, rid: str, action: str, data: dict[str, Any]) -> None:
        # Validate IDs/shape before queueing. Recheck actual names/parents inside the
        # serialized operation, so stale dialogs cannot accidentally rename a new path.
        if action == "create":
            parent = deck_id(data.get("parent", "0"), root=True)
            if data.get("kind") not in ("folder", "deck"):
                raise ValidationError("Choose a folder or a deck.")
        else:
            did = deck_id(data.get("id"))
            if not isinstance(data.get("expected"), str):
                raise ValidationError("Refresh before organizing this deck.")
        self.busy = True
        ticket = self.operation_ticket = object()
        store, collection = self.store, mw.col
        def op(col: Any) -> Any:
            if col is not collection or self.store is not store or self.nonce != nonce:
                raise ValidationError("The profile or screen changed. Reopen the organization dialog.")
            catalog = fresh_catalog(col)
            if action == "create":
                path = creation_path(catalog, data.get("name"), parent)
                return col.decks.add_normal_deck_with_name(path)
            if action == "rename":
                path = rename_path(catalog, did, data.get("name"), data["expected"])
                return col.decks.rename(int(did), path)
            source, target = validate_move(catalog, did, data.get("parent", "0"), data["expected"])
            return col.decks.reparent(deck_ids=[int(source)], new_parent=int(target))
        def success(out: Any) -> None:
            if self.operation_ticket is ticket:
                self.operation_ticket, self.busy = None, False
            warning = None
            if action == "create" and data["kind"] == "folder" and store:
                try:
                    prefs = store.read()
                    created = str(out.id)
                    if created not in prefs["folders"]:
                        prefs["folders"].append(created)
                    store.write(prefs)
                    if self.store is store:
                        self.profile = prefs
                except Exception:
                    warning = "The deck was created, but its local folder icon could not be saved. The actual deck is safe."
                    log.exception("Could not save local folder marker")
            self.reply(nonce, rid, result={"ok": True, "id": str(getattr(out, "id", "")), "warning": warning})
        def failure(exc: Exception) -> None:
            if self.operation_ticket is ticket:
                self.operation_ticket, self.busy = None, False
            self.reply(nonce, rid, error=str(exc) if isinstance(exc, ValidationError)
                       else "Anki did not complete the change. Refresh to check the current structure, then try again.")
        try:
            CollectionOp(mw, op).success(success).failure(failure).run_in_background()
        except Exception:
            if self.operation_ticket is ticket:
                self.operation_ticket, self.busy = None, False
            raise

    def chrome_css(self) -> str:
        config = self.get_config()
        if config["visual_owner"] != "atelier":
            return ""
        home = mw.state == "deckBrowser" and config["chrome"] and config["mode"] != "native"
        review = mw.state in ("review", "overview") and config["review_style"] != "off"
        if not (home or review):
            return ""
        bg, fg, accent, line = PALETTES[config["theme"]]
        return (f"body{{background:{bg};color:{fg}}}.header{{background:{bg};border-color:{line}}}"
                f".hitem{{color:{fg};border-radius:7px;padding:5px 11px}}"
                f".hitem:hover{{color:{accent};background:{line}}}"
                f"#decks{{color:{accent}}}")

    def apply_chrome(self) -> None:
        if not getattr(mw, "toolbarWeb", None):
            return
        css = self.chrome_css()
        js = ("(()=>{let s=document.getElementById('atelier-toolbar-chrome');"
              + ("if(!s){s=document.createElement('style');s.id='atelier-toolbar-chrome';document.head.append(s)}s.textContent=" + json.dumps(css) + ";" if css else "if(s)s.remove();") + "})();")
        mw.toolbarWeb.eval(js)
        # Bottom toolbar is not used by the reviewer while this callback is at home.
        if mw.state == "deckBrowser" and getattr(mw, "bottomWeb", None):
            config = self.get_config()
            bg, fg, _, line = PALETTES[config["theme"]]
            bottom = f"body{{background:{bg};color:{fg}}}button{{background:{bg};color:{fg};border-color:{line};border-radius:8px}}" if css else ""
            mw.bottomWeb.eval("(()=>{let s=document.getElementById('atelier-bottom-chrome');if(!s){s=document.createElement('style');s.id='atelier-bottom-chrome';document.head.append(s)}s.textContent=" + json.dumps(bottom) + ";})();")

    def state_changed(self, new: str, old: str) -> None:
        self.ownership.install()
        if new != "deckBrowser":
            self.capture_keys = False
            self.nonce = ""  # Late responses cannot write into a review page.
            if getattr(mw, "bottomWeb", None):
                mw.bottomWeb.eval("document.getElementById('atelier-bottom-chrome')?.remove();")
        self.apply_chrome()

    def open(self, *, appearance: bool = False) -> None:
        if not mw.col:
            showInfo("Open an Anki profile first.")
            return
        self.open_settings_next = appearance
        config = self.get_config()
        if config["mode"] == "native":
            self.save_config({"mode": "workspace"})
        mw.moveToState("deckBrowser")

    def open_widgets(self) -> None:
        """Open the built-in widget page, not the separate legacy provider page."""
        if not mw.col:
            showInfo("Open an Anki profile first.")
            return
        self._ui_state = {"page": "widgets", "location": "0", "query": "", "filter": "all"}
        self.open()

    def restore_home_layout(self) -> None:
        if not mw.col:
            return
        self.ensure_store()
        updated = profile_settings(self.profile)
        updated["home_layout"]["enabled"] = False
        try:
            assert self.store is not None
            self.store.write(updated)
            self.profile = updated
            mw.web.eval("window.AtelierMakeover&&window.AtelierMakeover.reload();")
        except Exception:
            showInfo("The layout preference could not be saved. Disable Atelier and restart to recover the original interface.")

    def restore_shortcuts(self) -> None:
        from aqt.utils import askUser
        if not mw.col:
            showInfo("Open an Anki profile first.")
            return
        self.ensure_store()
        if not askUser("Restore this profile's previous Atelier shortcut snapshot?\n\nThis replaces local active exams, favorites and folder display choices. Cards, decks, scheduling and other add-ons are not changed. The current shortcut file is kept as a recovery copy."):
            return
        try:
            assert self.store is not None
            self.profile = self.store.restore_previous()
            self._ui_state = {}
            self.open()
            showInfo("Previous Atelier shortcuts restored. Your card collection was not changed.")
        except (OSError, ValidationError) as exc:
            showInfo(str(exc) if isinstance(exc, ValidationError) else "The shortcut snapshot could not be restored. No card data was changed.")

    def original(self) -> None:
        self.save_config({"visual_owner": "onigiri" if self.ownership.available() else "external", "mode": "native", "shared_theme": False, "match_sprout": False, "review_style": "off", "chrome": False})
        if mw.col:
            mw.moveToState("deckBrowser")


def install(module: str) -> Atelier:
    from .lifecycle import Registration, StartupBlocked, check_duplicates
    package = mw.addonManager.addonFromModule(module)
    existing = getattr(mw, "_daedalus_atelier_runtime", None)
    if existing is not None:
        if getattr(existing, "module", None) == module:
            return existing
        raise StartupBlocked("Another Atelier copy is already active. Keep one Atelier installation enabled in Tools → Add-ons, then restart. Do not delete user_files.")
    duplicates = check_duplicates(mw.addonManager, package)
    if duplicates:
        raise StartupBlocked("More than one enabled Atelier package was found: " + ", ".join([package] + duplicates) + ". Keep one enabled and restart; this copy has not registered its hooks. No add-on or settings file was disabled, deleted or migrated.")
    required = ("webview_will_set_content", "webview_did_receive_js_message", "state_did_change",
                "profile_will_close", "top_toolbar_did_redraw", "reviewer_did_show_question", "reviewer_did_show_answer")
    if not all(callable(getattr(getattr(gui_hooks, hook, None), "append", None)) and
               callable(getattr(getattr(gui_hooks, hook, None), "remove", None)) for hook in required):
        raise StartupBlocked("This Anki build does not expose the hooks Atelier requires. Atelier has not changed the interface. Use the supported Anki desktop version listed in the release guide.")
    addon = Atelier(module)
    from .review_theme import ReviewTheme
    addon.review_theme = ReviewTheme(addon)
    registration = Registration()
    addon._registration = registration
    registration.cleanup(addon.ownership.dispose)
    try:
        if hasattr(gui_hooks, "profile_did_open"):
            registration.hook(gui_hooks.profile_did_open, addon.ownership.profile_opened)
        registration.hook(gui_hooks.webview_will_set_content, addon.add_content)
        registration.hook(gui_hooks.webview_did_receive_js_message, addon.receive)
        registration.hook(gui_hooks.state_did_change, addon.state_changed)
        registration.hook(gui_hooks.profile_will_close, addon.closed)
        if hasattr(gui_hooks, "state_will_change"):
            registration.hook(gui_hooks.state_will_change, addon.review_theme.before_state)
        registration.hook(gui_hooks.state_did_change, addon.review_theme.after_state)
        addon.review_theme.install(register=registration.hook)
        registration.hook(gui_hooks.top_toolbar_did_redraw, lambda toolbar: (addon.apply_chrome(), addon.review_theme._top_surface(mw.state)))
        addon.input_guard = InputShortcutGuard(addon)
        app = QApplication.instance()
        if app:
            app.installEventFilter(addon.input_guard)
            registration.cleanup(lambda: app.removeEventFilter(addon.input_guard))
        menu = mw.form.menuTools.addMenu("Atelier · " + VERSION)
        addon.menu = menu
        def remove_menu() -> None:
            mw.form.menuTools.removeAction(menu.menuAction())
            menu.deleteLater()
        registration.cleanup(remove_menu)
        for name, callback in (("Open workspace", addon.open),
                              ("Open Atelier widgets", addon.open_widgets),
                              ("Appearance & compatibility…", lambda: addon.open(appearance=True)),
                              ("Use original Anki home", addon.original),
                              ("Restore original widget layout", addon.restore_home_layout),
                              ("Restore previous shortcuts…", addon.restore_shortcuts),
                              ("Use original reviewer styling", addon.review_theme.disable),
                              ("Copy display diagnostics", addon.review_theme.copy_diagnostics),
                              ("Use original design for this note type", addon.review_theme.preserve_current),
                              ("Allow adaptive styling for this note type", addon.review_theme.restore_current)):
            action = QAction(name, mw)
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            menu.addAction(action)
        manager = mw.addonManager
        old_exports = manager.getWebExports(module) if callable(getattr(manager, "getWebExports", None)) else None
        registration.cleanup(lambda: manager.setWebExports(module, old_exports or r"(?!)"))
        manager.setWebExports(module, r"(?:web|sprout/web|workshop/web)/.*\.(js|css|svg|png|webp|json)$")
        previous_action = manager.configAction(package) if callable(getattr(manager, "configAction", None)) else None
        registration.cleanup(lambda: manager.setConfigAction(module, previous_action))
        manager.setConfigAction(module, lambda: addon.open(appearance=True))
        from .native_tools import NativeSurfaces
        addon.native_surfaces = NativeSurfaces(addon)
        addon.native_surfaces.install(registration)
        from .remotes import RemoteControls
        addon.remotes = RemoteControls(addon)
        addon.remotes.install(registration, app)
        remote_action = QAction("Remote controls…", mw)
        remote_action.triggered.connect(lambda checked=False: addon.remotes.open())
        menu.addAction(remote_action)
        from .suite import install_engine
        install_engine(addon, registration)
        from .authoring import install_authoring
        install_authoring(addon, registration)
        addon.ownership.install()
        mw._daedalus_atelier_runtime = addon
        return addon
    except Exception:
        registration.rollback()
        raise

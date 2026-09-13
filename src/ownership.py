"""One visual owner. Runtime-only adapters for positively identified Onigiri.

No saved Onigiri settings are changed. Reward/event hooks remain registered.
Only named presentation functions on the already-loaded patcher are wrapped.
Unsupported functions are left alone and reported in diagnostics.
"""
from __future__ import annotations
import functools
import logging
import re
import sys
from typing import Any

LOG = logging.getLogger('atelier.ownership')
# Intentionally conservative *possible* conflict detector, not a compatibility guarantee.
MAKEOVER_NAME = re.compile(r"(?:\b(?:recolor|recolour|redesign|makeover|beautify|beautification|beautified|synapsepro)\b|custom\s+background|advanced\s+(?:review|answer)\s+(?:bottom\s+)?bar|(?:anki|reviewer|interface|ui)\s+themes?|background.*gear.*icon)", re.I)
EXCLUDED_NAME = re.compile(r"(?:exam[ _-]*sprout|image[ _-]*occlusion|review[ _-]*heatmap)", re.I)


def detect_makeovers(manager: Any, own_package: str = "daedalus_atelier") -> dict:
    """Read enabled add-on metadata. A renamed/unknown makeover may be missed.

    Returns no directories, paths, card text, deck names, or user settings.
    Does not assume every enabled add-on has completed loading yet.
    """
    found = []
    onigiri = False
    complete = False
    try:
        if callable(getattr(manager, "all_addon_meta", None)):
            metas = list(manager.all_addon_meta())
            entries = [(m.dir_name, m.human_name(), bool(m.enabled), str(getattr(m, "human_version", "") or "")) for m in metas]
        elif callable(getattr(manager, "allAddons", None)):
            entries = []
            for package in manager.allAddons():
                meta = manager.addonMeta(package)
                entries.append((package, manager.addonName(package), not meta.get("disabled", False), str(meta.get("human_version", ""))))
        else:
            entries = []
        complete = callable(getattr(manager, "all_addon_meta", None)) or callable(getattr(manager, "allAddons", None))
        for package, name, enabled, version in entries[:500]:
            if not enabled or package == own_package:
                continue
            name = str(name)[:200]
            if re.search(r"\bonigiri\b", name, re.I) or str(package).lower() == "onigiri":
                onigiri = True
            elif MAKEOVER_NAME.search(name) and not EXCLUDED_NAME.search(name):
                found.append({"id":str(package), "name":name, "version":version[:40], "reason":"May change page colors or review controls"})
    except Exception:
        LOG.warning("Could not finish the read-only makeover metadata check")
    return {"onigiri":onigiri, "makeovers":found, "metadata_checked":complete}


def resolve_config(config: dict, report: dict) -> dict:
    cfg = dict(config)
    others = {m["id"] for m in report.get("makeovers", [])}
    acknowledged = set(cfg.get("acknowledged_makeovers", []))
    selected = cfg.get("visual_owner", "ask")
    # A new potential global makeover requires an explicit choice. We do not
    # suppress a foreign add-on or silently choose Atelier in that situation.
    if others - acknowledged and selected != "external":
        cfg.update(visual_owner="ask", mode="workspace")
    elif selected == "ask":
        if report.get("metadata_checked") is False:
            # A failed metadata scan is not evidence that no other theme exists.
            cfg["mode"] = "workspace"
        elif report.get("onigiri") or others:
            cfg["mode"] = "workspace"
        else:
            cfg.update(visual_owner="atelier", mode="workspace")
    elif selected == "onigiri" and not report.get("onigiri"):
        cfg.update(visual_owner="external" if others else "atelier", mode="native" if others else "workspace")
    return cfg

# Return contracts inspected in the published Onigiri source. These functions
# return CSS strings or perform a presentation-only background/height update.
CSS_FUNCTIONS = (
    'generate_deck_browser_backgrounds', 'generate_reviewer_background_css',
    'generate_overview_background_css', 'generate_toolbar_background_css',
    'generate_reviewer_bottom_bar_background_css', 'generate_reviewer_buttons_css',
)
VOID_FUNCTIONS = ('set_main_webview_background_color', 'apply_reviewer_bottom_bar_height')


def find_patcher() -> Any:
    for name, module in tuple(sys.modules.items()):
        if not name.endswith('.patcher') or module is None:
            continue
        parent = sys.modules.get(name.rsplit('.', 1)[0])
        if (getattr(parent, 'patcher', None) is module
                and getattr(parent, 'onigiri_renderer', None) is not None
                and callable(getattr(module, 'generate_reviewer_background_css', None))
                and callable(getattr(module, 'generate_deck_browser_backgrounds', None))):
            return module
    return None


def validate_palette(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError('Invalid companion palette.')
    colors = ('bg', 'side', 'panel', 'raised', 'hover', 'text', 'muted', 'quiet',
              'line', 'line-soft', 'accent', 'accent-strong', 'accent-soft',
              'on-accent', 'blue', 'green', 'pink', 'amber', 'hero', 'hero-end')
    out = {}
    for name in colors:
        color = value.get(name)
        if isinstance(color, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            out[name] = color.lower()
    if not all(k in out for k in ('bg', 'panel', 'text', 'accent')):
        raise ValueError('The companion palette is incomplete.')
    out['scheme'] = 'light' if value.get('scheme') == 'light' else 'dark'
    return out


class Ownership:
    def __init__(self, owner: Any):
        self.owner = owner
        self._wrapped: list[tuple[Any, str, Any, Any]] = []
        self.companion_palette: dict[str, str] = {}
        self._report: dict | None = None

    def report(self, refresh: bool = False) -> dict:
        if self._report is None or refresh:
            manager = getattr(self.owner, "addon_manager", lambda: None)()
            self._report = detect_makeovers(manager, getattr(self.owner, "package", "daedalus_atelier"))
        out = {**self._report, "makeovers":list(self._report["makeovers"])}
        out["onigiri_loaded"] = find_patcher() is not None
        out["onigiri"] = bool(out["onigiri"] or out["onigiri_loaded"])
        return out

    def available(self) -> bool:
        return bool(self.report()["onigiri"])

    def reset_scan(self) -> None:
        self._report = None

    def profile_opened(self, *_args: Any) -> None:
        self.reset_scan()
        self.install()

    def install(self, *_args: Any) -> None:
        cfg = self.owner.get_config()
        if cfg.get("visual_owner") != "atelier":
            self.release()
            return
        patcher = find_patcher()
        if patcher is None:
            return
        for name in CSS_FUNCTIONS + VOID_FUNCTIONS:
            original = getattr(patcher, name, None)
            if not callable(original) or getattr(original, '_atelier_visual_gate', False):
                continue
            @functools.wraps(original)
            def gate(*args: Any, __fn=original, __name=name, **kwargs: Any) -> Any:
                cfg = self.owner.get_config()
                # Recovery: native reviewer/overview also regains its own native
                # presentation when the reviewer styling is explicitly switched off.
                owned = cfg.get('visual_owner') == 'atelier'
                state = getattr(self.owner, 'current_state', lambda: '')()
                if state in ('review', 'overview') and cfg.get('review_style') == 'off':
                    owned = False
                if owned:
                    return '' if __name in CSS_FUNCTIONS else None
                return __fn(*args, **kwargs)
            gate._atelier_visual_gate = True
            setattr(patcher, name, gate)
            self._wrapped.append((patcher, name, original, gate))

    def release(self) -> None:
        for module, name, original, gate in reversed(self._wrapped):
            if getattr(module, name, None) is gate:
                setattr(module, name, original)
        self._wrapped.clear()

    def dispose(self) -> None:
        self.release()
        self.companion_palette.clear()
        self.reset_scan()

    def diagnostics(self) -> dict:
        return {'available': self.available(), 'detection': self.report(),
                'owner': self.owner.get_config().get('visual_owner'),
                'presentation_adapters': [n for _, n, _, _ in self._wrapped],
                'saved_onigiri_settings_modified': False,
                'reward_hooks_removed': False}

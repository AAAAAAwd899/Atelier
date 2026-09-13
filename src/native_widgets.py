"""Profile-local widget preferences. No provider code, collection writes or new store.

Unknown installed providers can be absent temporarily: their ids stay saved so a
profile does not lose layout when an optional add-on is disabled.
"""
from __future__ import annotations
import copy
import re

BUILTIN_IDS = ('today', 'focus', 'plans', 'work', 'recent', 'saved', 'notes', 'onigiri')
DEFAULT_WIDGETS = {'items': [
    {'id': 'today', 'size': 'wide', 'home': False},
    {'id': 'focus', 'size': 'normal', 'home': False},
    {'id': 'plans', 'size': 'normal', 'home': False},
    {'id': 'work', 'size': 'wide', 'home': False},
]}
MAX_WIDGETS = 24
MAX_NOTE = 4000

def widget_id(value):
    return isinstance(value, str) and (value in BUILTIN_IDS or
        re.fullmatch(r'addon\.[a-z0-9][a-z0-9_.-]{1,75}', value) is not None)

def widget_layout(value, *, strict=False):
    from .core import ValidationError
    if not isinstance(value, dict) or not isinstance(value.get('items'), list):
        if strict: raise ValidationError('Choose the widgets you want to show.')
        return copy.deepcopy(DEFAULT_WIDGETS)
    if strict and len(value['items']) > MAX_WIDGETS:
        raise ValidationError('Use up to 24 widgets on this page.')
    out, seen = [], set()
    for item in value['items'][:MAX_WIDGETS]:
        valid = (isinstance(item, dict) and widget_id(item.get('id')) and
                 item.get('size') in ('normal', 'wide') and type(item.get('home')) is bool)
        if not valid:
            if strict: raise ValidationError('One widget setting is not valid. Open Arrange widgets again.')
            continue
        if item['id'] in seen:
            if strict: raise ValidationError('Each widget can appear once. Remove the duplicate.')
            continue
        seen.add(item['id'])
        out.append({'id': item['id'], 'size': item['size'], 'home': item['home']})
    return {'items': out}

def widget_note(value, *, strict=False):
    from .core import ValidationError
    if not isinstance(value, str) or len(value) > MAX_NOTE or '\x00' in value:
        if strict: raise ValidationError('Keep the note to 4,000 characters, without null characters.')
        return ''
    return value


WIDGET_ROUTE_VERSION = 1

def widget_route_upgrade(config, profile):
    """Retire only the legacy Atelier-led provider start page, once per profile.

    Mode used to be persisted as "native" by the general widgets link. Do not
    confuse that old view with an explicit Onigiri/external appearance owner.
    Return independent copies; the caller owns atomic preference persistence.
    No exam/source/widget records are migrated or deleted.
    """
    cfg, updated = copy.deepcopy(config), copy.deepcopy(profile)
    if updated.get("widget_route_version") == WIDGET_ROUTE_VERSION:
        return cfg, updated, False
    recover = cfg.get("visual_owner") == "atelier" and cfg.get("mode") == "native"
    if recover:
        cfg["mode"] = "workspace"
    updated["widget_route_version"] = WIDGET_ROUTE_VERSION
    return cfg, updated, recover

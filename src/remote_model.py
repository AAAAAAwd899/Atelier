"""Keyboard-mode remote bindings and a bounded press gate; no OS/network hooks."""
from __future__ import annotations
import time
from typing import Any

ACTIONS = {
    'reveal': 'Show answer', 'again': 'Again', 'hard': 'Hard',
    'good': 'Good', 'easy': 'Easy', 'replay': 'Replay audio',
    'scroll_up': 'Scroll up', 'scroll_down': 'Scroll down',
}
# Plain keys only. Keep OS shortcuts, text-editing keys and menu navigation native.
SPECIAL = {0x01000004: 'Return', 0x01000005: 'Enter', 0x01000012: 'Left',
           0x01000013: 'Up', 0x01000014: 'Right', 0x01000015: 'Down',
           0x01000016: 'Page Up', 0x01000017: 'Page Down'}
SPECIAL.update({0x01000030+i: f'F{i+1}' for i in range(24)})

def valid_key(key: Any) -> bool:
    return type(key) is int and (key == 32 or 48 <= key <= 57 or 65 <= key <= 90 or key in SPECIAL)

def key_name(key: Any) -> str:
    if key == 32: return 'Space'
    if key in SPECIAL: return SPECIAL[key]
    return chr(key) if valid_key(key) else 'Not assigned'

def validate_settings(value: Any) -> dict:
    if not isinstance(value, dict) or type(value.get('enabled', False)) is not bool:
        raise ValueError('Choose whether to use custom remote buttons.')
    bindings = value.get('bindings', {})
    if not isinstance(bindings, dict) or len(bindings) > len(ACTIONS):
        raise ValueError('The remote button list is invalid.')
    clean = {}; seen = set()
    for action, key in bindings.items():
        if action not in ACTIONS or not valid_key(key):
            raise ValueError('Use a letter, number, arrow, Page key, Space, Enter or function key without modifiers.')
        if key in seen:
            raise ValueError('A button cannot control two actions. Clear its previous assignment first.')
        seen.add(key); clean[action] = key
    if value.get('enabled', False) and not clean:
        raise ValueError('Assign at least one button before enabling custom controls.')
    return {'enabled': value.get('enabled', False), 'bindings': clean}

def settings(value: Any) -> dict:
    try: return validate_settings(value)
    except (ValueError, TypeError): return {'enabled': False, 'bindings': {}}

class PressGate:
    """One physical press, never autorepeat, with cross-card bounce suppression."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock; self.down = set(); self.last = float('-inf')
    def press(self, key: int, repeat=False) -> bool:
        if repeat or key in self.down: return False
        self.down.add(key)
        now=self.clock()
        if now-self.last < .22: return False
        self.last=now; return True
    def release(self, key: int, repeat=False) -> None:
        if not repeat: self.down.discard(key)
    def reset(self) -> None:
        self.down.clear()  # Do not erase the bounce window across a new card.

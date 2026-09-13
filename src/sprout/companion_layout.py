"""Placement arithmetic only. A mascot must never displace or cover card controls."""
from __future__ import annotations
import math

BADGE_SIZE = 46  # Qt logical pixels; fixed, independent of card zoom.


def footer_position(measurement, width: int, height: int, size: int = BADGE_SIZE):
    """Find empty space in the existing footer, or return None (hide).

    measurement is read from the footer DOM, not the card DOM. CSS-pixel rects
    are converted to Qt logical pixels so high-DPI/card zoom cannot move Pip
    over a button. Unknown/invalid layouts fail closed.
    """
    if not isinstance(measurement, dict) or not measurement.get('ready'):
        return None
    if width < 300 or height < size + 4:
        return None
    try:
        vw, vh = float(measurement['width']), float(measurement['height'])
        if not all(math.isfinite(v) and v > 0 for v in (vw, vh)):
            return None
        rects = measurement['rects']
        if not isinstance(rects, list) or len(rects) > 512:
            return None
        sx, sy = width / vw, height / vh
        y = (height - size) // 2
        blocked = []
        for rect in rects:
            if not isinstance(rect, (list, tuple)) or len(rect) != 4:
                return None
            x, top, w, h = map(float, rect)
            if not all(math.isfinite(v) for v in (x, top, w, h)) or w < 0 or h < 0:
                return None
            left, right = x * sx - 8, (x + w) * sx + 8
            top, bottom = top * sy, (top + h) * sy
            if bottom > y - 3 and top < y + size + 3:
                blocked.append((max(6, left), min(width - 6, right)))
        # Use only the right half of the footer. Never cross the central review
        # controls just to make the mascot visible.
        start = max(6, width // 2)
        gaps = []
        for left, right in sorted(blocked):
            if right <= start or left >= width - 6:
                continue
            if left - start >= size:
                gaps.append((start, left))
            start = max(start, right)
        if width - 6 - start >= size:
            gaps.append((start, width - 6))
        if not gaps:
            return None
        left, right = gaps[-1]
        return int(right - size), int(y)
    except (ValueError, TypeError, KeyError, OverflowError):
        return None

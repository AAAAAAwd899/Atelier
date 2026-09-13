"""A cached, scoped countdown. No collection queries or scheduling calls."""
from __future__ import annotations
from datetime import datetime
from html import escape
from .core import due_local

SPROUT_SVG = '<img src="/_addons/exam_sprout/web/pip/stage1.png" alt="" width="30" height="30" draggable="false">'

ARROW_SVG = '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h11m-4-4 4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def countdown_html(store, *, preview: bool = False) -> str:
    """Settings previews use the identical markup, but are inert (not controls)."""
    settings = store.state["settings"]
    if (not settings["show_countdown"] and not preview) or store.read_only:
        return ""
    now = datetime.now()
    exams = sorted((e for e in store.exams() if not e.archived and due_local(e.due) > now), key=lambda e: e.due)
    theme = escape(settings["theme"])
    compact = "true" if settings["compact"] else "false"
    items = []
    for e in exams[:settings["max_countdowns"]]:
        due = due_local(e.due)
        minutes = max(0, int((due.timestamp() - now.timestamp()) / 60))
        initial = f"{minutes // 1440}d {(minutes % 1440) // 60}h" if minutes >= 1440 else f"{minutes // 60}h {minutes % 60}m" if minutes >= 60 else f"{minutes}m" if minutes else "Exam time"
        subtitle = due.strftime('%a, %b ') + str(due.day) + ' · Open study plan'
        items.append(
            f'<button type="button" class="es-chip" data-exam-id="{escape(e.id)}" title="Open study plan: {escape(e.name)}">'
            f'<span class="es-mark">{SPROUT_SVG}</span><span class="es-chip-copy"><span class="es-chip-title">{escape(e.name)}</span>'
            f'<span class="es-chip-sub">{escape(subtitle)}</span></span>'
            f'<span class="es-time" data-deadline="{escape(e.due)}">{initial}</span>'
            f'<span class="es-chip-arrow">{ARROW_SVG}</span></button>'
        )
    if not exams:
        items.append(f'<button type="button" class="es-chip es-chip-empty" data-exam-id=""><span class="es-mark">{SPROUT_SVG}</span><span class="es-chip-copy"><span class="es-chip-title">A little less last-minute.</span><span class="es-chip-sub">Add your first exam countdown</span></span><span class="es-plus" aria-hidden="true">+</span></button>')
    elif len(exams) > settings["max_countdowns"]:
        items.append(f'<button type="button" class="es-more" data-exam-id="">+{len(exams) - settings["max_countdowns"]} more</button>')
    attrs = ' data-preview="true" inert' if preview else ''
    return f'<section id="es-countdowns" data-theme="{theme}" data-compact="{compact}" aria-label="Exam countdowns"{attrs}>' + "".join(items) + '</section>'

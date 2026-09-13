"""Read-only reviewer presentation decisions. No Anki or Qt dependency."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

PALETTES = json.loads((Path(__file__).parent / "web" / "palettes.json").read_text(encoding="utf8"))


def theme_tokens(theme: str) -> str:
    p = PALETTES.get(theme, PALETTES["obsidian"])
    return ":root{" + "".join(f"--at-{k}:{v};" for k, v in p.items()) + "}"


def plain_template(model: Any) -> bool:
    """Fail closed: only the small stock Basic/Cloze stylesheet is eligible.

    Translated model names are irrelevant. Custom CSS, scripts, occlusion,
    complex layouts and third-party note types retain their native card surface.
    Empty CSS is *not* assumed to mean safe: templates may depend on inheritance.
    """
    if not isinstance(model, dict):
        return False
    css = model.get("css", "")
    if not isinstance(css, str) or not css.strip():
        return False
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if "@" in css:
        return False
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    if not rules or re.sub(r"[^{}]+\{[^{}]*\}", "", css).strip():
        return False
    allowed = {
        ".card": {"font-family": {"arial", "arial, sans-serif"}, "font-size": {"20px"},
                  "text-align": {"center"}, "color": {"black", "#000", "#000000"},
                  "background-color": {"white", "#fff", "#ffffff"}},
        ".cloze": {"font-weight": {"bold"}, "color": {"blue", "#00f", "#0000ff"}},
        ".nightMode .cloze": {"color": {"lightblue"}},
        ".night_mode .cloze": {"color": {"lightblue"}},
    }
    seen_card = False
    for selector, body in rules:
        selector = " ".join(selector.split())
        if selector not in allowed:
            return False
        seen_card |= selector == ".card"
        for decl in body.split(";"):
            if not decl.strip():
                continue
            if ":" not in decl:
                return False
            prop, value = decl.split(":", 1)
            prop, value = prop.strip().lower(), " ".join(value.strip().lower().split())
            if value not in allowed[selector].get(prop, set()):
                return False
    templates = model.get("tmpls", [])
    if not isinstance(templates, list) or not templates:
        return False
    for tmpl in templates:
        if not isinstance(tmpl, dict):
            return False
        text = str(tmpl.get("qfmt", "")) + str(tmpl.get("afmt", ""))
        if re.search(r"<(?:script|style|canvas|svg|iframe|object|embed)\b|image.occlusion|io-overlay|io-wrapper", text, re.I):
            return False
    return seen_card


def static_text_template(model: Any) -> bool:
    """Eligible static custom text without touching scripted/positioned designs.

    The previous exact-stock CSS allow-list rejected ordinary formatted notes.
    This separate classifier allows headings, typography, lists, tables, cloze
    and typed-answer fields, but rejects positioning and interactive templates.
    Runtime media detection is an additional guard, not a substitute for this.
    """
    if not isinstance(model, dict) or not isinstance(model.get('tmpls'), list) or not model['tmpls']:
        return False
    text = ''.join(str(t.get('qfmt',''))+str(t.get('afmt','')) for t in model['tmpls'] if isinstance(t,dict))
    css = re.sub(r'/\*.*?\*/', '', str(model.get('css','')), flags=re.S)
    if not text.strip():
        return False
    if re.search(r'<(?:script|iframe|canvas|svg|object|embed|video|audio)\b|\bon[a-z]+\s*=|javascript:|image.?occlusion|io[-_]overlay|io[-_]wrapper', text, re.I):
        return False
    if re.search(r'(?:position\s*:\s*(?:absolute|fixed|sticky)|transform\s*:|zoom\s*:|@import|@keyframes|display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\D|$))', css+' '+text, re.I):
        return False
    return True


# Geometry-sensitive content must never receive the text-card layout. This is a
# conservative presentation classifier, not a change to card or note templates.
def geometry_sensitive(model: Any) -> bool:
    if not isinstance(model, dict):
        return True
    templates = model.get("tmpls")
    if not isinstance(templates, list) or not templates or any(not isinstance(t, dict) for t in templates):
        return True
    value = str(model.get("css", "")) + " " + " ".join(str(t.get(k, "")) for t in templates for k in ("qfmt", "afmt"))
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.S)
    return bool(re.search(
        r"image[-_ .]?occlusion|(?:id|class)\s*=\s*[\"']?[^>]*?\bio[-_](?:wrapper|overlay|container|image|original|qmask|amask)|"
        r"\{\{(?:cloze:)?(?:Occlusion|Question Mask|Answer Mask)\}\}|"
        r"(?:position\s*:\s*(?:absolute|fixed|sticky)|transform\s*:|zoom\s*:|"
        r"(?:min-|max-)?height\s*:[^;}]*\b(?:[0-9.]+)(?:dvh|svh|lvh|vh)|overflow(?:-y)?\s*:\s*(?:hidden|clip))",
        value, re.I))

def reading_template(model: Any) -> bool:
    return not geometry_sensitive(model) and (plain_template(model) or static_text_template(model))

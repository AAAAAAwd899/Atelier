"""Theme Anki's *existing* reviewer/overview. Never replace its renderer.

All answers, intervals, keys, media, IO canvases and notifications remain native.
Only supported web-content/show hooks are used; failures leave native rendering.
"""
from __future__ import annotations
import json
import logging
import secrets
import math
from pathlib import Path
from typing import Any
from .core import json_for_html, profile_settings
from .review_model import reading_template, theme_tokens
from .io_view import recognized as recognized_io

log = logging.getLogger("atelier.review")
ROOT = Path(__file__).resolve().parent


class ReviewTheme:
    def __init__(self, owner: Any) -> None:
        self.owner = owner
        self.layout_token = ""
        self.layout_pending = False

    def install(self, register=None) -> None:
        from aqt import gui_hooks
        add = register or (lambda hook, callback: hook.append(callback))
        add(gui_hooks.webview_will_set_content, self.add_content)
        add(gui_hooks.reviewer_did_show_question, self.question)
        add(gui_hooks.reviewer_did_show_answer, self.answer)
        add(gui_hooks.webview_did_receive_js_message, self.receive_layout)
        if hasattr(gui_hooks, "card_will_show"):
            add(gui_hooks.card_will_show, self.prepare_card)
        # Do not subscribe to answer-card/scheduler hooks or replace webview HTML.

    def options(self, screen: str) -> dict:
        cfg = self.owner.get_config()
        return {"version": "1.0.4", "theme": cfg["theme"], "style": cfg["review_style"] if cfg.get("visual_owner", "atelier") == "atelier" else "off",
                "width": cfg["review_width"], "motion": cfg["motion"], "ambience": cfg.get("ambience", True), "context": cfg.get("review_context", "compact"),
                "screen": screen, "layoutToken": self.layout_token if screen == "review-bottom" else ""}

    def add_content(self, content: Any, context: Any) -> None:
        from aqt.reviewer import Reviewer, ReviewerBottomBar
        from aqt.overview import Overview, OverviewBottomBar
        screen = ("review" if isinstance(context, Reviewer) else
                  "review-bottom" if isinstance(context, ReviewerBottomBar) else
                  "overview" if isinstance(context, Overview) else
                  "overview-bottom" if isinstance(context, OverviewBottomBar) else None)
        if not screen or self.owner.get_config().get("visual_owner", "atelier") != "atelier":
            return
        try:
            if screen == "review-bottom":
                self.layout_token = secrets.token_urlsafe(18)
            options = self.options(screen)
            # Also install a dormant stylesheet when off, allowing native menu
            # toggles without changing the current card or advancing the queue.
            boot = '<script id="atelier-review-boot" type="application/json">' + json_for_html(options) + '</script>'
            tokens = '<style id="atelier-review-tokens">' + theme_tokens(options["theme"]) + '</style>'
            early = '<script>(()=>{const r=document.documentElement,c='+json_for_html(options)+';if(c.style!=="off"){r.dataset.atelierScreen=c.screen;r.dataset.atelierWidth=c.width;r.dataset.atelierWorld=c.theme;if(c.screen==="review-bottom")r.dataset.atelierToolbar="stock";}})();</script>'
            from .worlds import reviewer_css
            addition = boot + tokens + '<style id="atelier-review-css">' + (ROOT/'web'/'reviewer.css').read_text(encoding='utf8') + '\n' + reviewer_css() + '</style>' + early
            content.head += addition
            content.js.append(f"/_addons/{self.owner.package}/web/reviewer.js?v=1.0.4")
        except Exception:
            log.exception("Reviewer styling skipped; native card rendering preserved")

    def receive_layout(self, handled: tuple[bool, Any], message: str, context: Any) -> tuple[bool, Any]:
        """Safely fit the native webview; never execute a card/answer command."""
        from aqt import mw
        from aqt.reviewer import ReviewerBottomBar
        prefix = "atelier:review-layout:"
        if handled[0] or not message.startswith(prefix):
            return handled
        if (not isinstance(context, ReviewerBottomBar) or mw.state != "review"
                or getattr(context, "reviewer", None) is not getattr(mw, "reviewer", None)
                or not self.layout_token or len(message) > 128
                or not secrets.compare_digest(message[len(prefix):], self.layout_token)):
            return (True, None)
        if self.layout_pending:
            return (True, None)
        token = self.layout_token
        self.layout_pending = True
        def fit() -> None:
            self.layout_pending = False
            if token != self.layout_token or mw.state != "review":
                return
            web = getattr(mw, "bottomWeb", None)
            # Preserve native auto-hide/fullscreen choices. Do not force a hidden
            # toolbar visible or resize a different screen after a navigation.
            if web is None or getattr(web, "hidden", False):
                return
            def apply(measurement: Any) -> None:
                # QWebEngine calls a callback with None when it destroys a page.
                # Do NOT delegate this to _onHeight: its None fallback resets
                # the main window and can flash the previous home screen.
                if token != self.layout_token or mw.state != "review" or getattr(mw, "bottomWeb", None) is not web:
                    return
                if getattr(web, "hidden", False) or self.options("review-bottom")["style"] == "off":
                    return
                if not isinstance(measurement, dict) or measurement.get("token") != token:
                    return
                h = measurement.get("height")
                if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(h) or not 36 <= h <= 600:
                    return
                try:
                    target = math.ceil(h)
                    # Finish a stale expand animation before applying the measured
                    # natural height. Never change auto-hide settings or show().
                    animation = getattr(web, "animation", None)
                    if animation is not None:
                        animation.stop()
                    web.web_height = target
                    if web.height() != target:
                        web.setFixedHeight(target)
                except (RuntimeError, AttributeError):
                    pass
            try:
                web.evalWithCallback("window.AtelierReview ? window.AtelierReview.measureFooter() : null", apply)
            except (RuntimeError, AttributeError):
                pass
        mw.progress.single_shot(40, fit)
        return (True, None)

    def card_info(self, card: Any, stage: str) -> dict:
        from aqt import mw
        try:
            self.owner.ensure_store()
            model = card.note_type()
            model_id = str(model.get("id", ""))
            did = card.current_deck_id()
            deck = mw.col.decks.get(did, default=False)
            path = str(deck["name"]) if deck else ""
            io = any("image-occlusion" in str(t.get("qfmt", "")).lower() or "io-wrapper" in str(t.get("qfmt", "")).lower() for t in model.get("tmpls", []) if isinstance(t, dict))
            safe = model_id not in self.owner.profile.get("native_note_types", []) and reading_template(model)
            return {"id": str(card.id), "stage": stage, "path": path.split("::"),
                    "eligible": safe, "protected": model_id in self.owner.profile.get("native_note_types", []), "imageOcclusion": io and model_id not in self.owner.profile.get("native_note_types", []),
                    "ioFit": recognized_io(model) and model_id not in self.owner.profile.get("native_note_types", [])}
        except Exception:
            # Unknown templates or metadata failures never receive card overrides.
            return {"stage": stage, "eligible": False, "protected": True, "path": []}

    def prepare_card(self, html: str, card: Any, context: str) -> str:
        """Run after Anki inserts the new card, not against the previous DOM.

        Appends a presentation-only script to eligible text cards in the native
        reviewer. No template mutation, preview injection, or IO script changes.
        """
        if context not in ("reviewQuestion", "reviewAnswer"):
            return html
        cfg = self.owner.get_config()
        if cfg.get("visual_owner") != "atelier" or cfg.get("review_style") != "adaptive":
            return html
        info = self.card_info(card, "question" if context == "reviewQuestion" else "answer")
        if not (info.get("eligible") or info.get("ioFit")) or info.get("protected"):
            return html
        data = json_for_html(info)
        return html + ('<script data-atelier-presentation="1">(()=>{const value=' + data + ';'
                       'const update=()=>window.AtelierReview?.painted(value);'
                       'if(typeof onUpdateHook!=="undefined")onUpdateHook.push(update);else update();'
                       'if(typeof onShownHook!=="undefined")onShownHook.push(()=>window.AtelierReview?.settled(value));'
                       '})();</script>')

    def show(self, card: Any, stage: str) -> None:
        from aqt import mw
        if mw.state != "review":
            return
        try:
            data = json_for_html(self.card_info(card, stage))
            mw.web.eval("window.__atelierReviewCard=" + data + ";window.AtelierReview&&window.AtelierReview.setCard(window.__atelierReviewCard);")
        except Exception:
            log.exception("Reviewer decoration update skipped")

    def before_state(self, new: str, old: str) -> None:
        """Invalidates pending footer callbacks before Anki changes the page."""
        if new != "review":
            self.layout_token = ""
            self.layout_pending = False
        self._top_surface(new)

    def after_state(self, new: str, old: str) -> None:
        self._top_surface(new)

    def _top_surface(self, screen: str) -> None:
        from aqt import mw
        web = getattr(mw, "toolbarWeb", None)
        if web is None:
            return
        cfg = self.owner.get_config()
        enabled = cfg.get("visual_owner", "atelier") == "atelier" and screen in ("review", "overview") and cfg["review_style"] != "off"
        css = ""
        if enabled:
            css = theme_tokens(cfg["theme"]) + (ROOT/"web"/"top.css").read_text(encoding="utf8")
        script = "(()=>{let s=document.getElementById('atelier-top-surface');if(!s){s=document.createElement('style');s.id='atelier-top-surface';document.head.append(s);}s.textContent="+json.dumps(css)+";})();"
        try:
            web.eval(script)
        except (RuntimeError, AttributeError):
            pass

    def copy_diagnostics(self) -> None:
        """Copy runtime geometry, not card HTML, names, or study content."""
        from aqt import mw
        from aqt.qt import QApplication
        from aqt.utils import tooltip
        import platform
        report = {"atelier":"1.0.4", "os":platform.system(), "screen":mw.state,
                  "settings":self.owner.get_config(), "ownership":self.owner.ownership.diagnostics(), "webviews":{}}
        try:
            import anki
            report["anki"] = getattr(anki, "version", "unknown")
        except Exception:
            pass
        targets = [(k,getattr(mw,k,None)) for k in ("web","bottomWeb","toolbarWeb")]
        remaining = len(targets)
        def done(key: str, data: Any) -> None:
            nonlocal remaining
            if key in report["webviews"]:
                return
            report["webviews"][key] = data
            remaining -= 1
            if not remaining:
                QApplication.clipboard().setText(json.dumps(report, indent=2, default=str))
                tooltip("Atelier display diagnostics copied. No card text included.")
        for key, web in targets:
            if web is None:
                done(key,None)
            else:
                try:
                    web.evalWithCallback("window.AtelierReview ? window.AtelierReview.diagnostics() : {cohesion:window.AtelierCohesion?.diagnostics(),home:document.documentElement.dataset.atelierHome||'original',mounted:!!document.documentElement.dataset.atelierMounted,background:getComputedStyle(document.body).backgroundColor,viewportWidth:innerWidth,viewportHeight:innerHeight,deviceScale:devicePixelRatio}", lambda data,k=key:done(k,data))
                except (RuntimeError, AttributeError):
                    done(key,{"unavailable":True})
        mw.progress.single_shot(3000, lambda: [done(k,{"timeout":True}) for k,_ in targets if k not in report["webviews"]])

    def question(self, card: Any) -> None:
        self.show(card, "question")

    def answer(self, card: Any) -> None:
        self.show(card, "answer")

    def refresh(self) -> None:
        from aqt import mw
        if mw.state not in ("review", "overview"):
            return
        cfg = self.owner.get_config()
        self._top_surface(mw.state)
        for attr, screen in (("web", mw.state), ("bottomWeb", mw.state + "-bottom")):
            web = getattr(mw, attr, None)
            if web is not None:
                web.eval("(()=>{let s=document.getElementById('atelier-review-tokens');if(s)s.textContent=" + json.dumps(theme_tokens(cfg["theme"])) + ";window.AtelierReview&&window.AtelierReview.configure(" + json_for_html(self.options(screen)) + ");})();")
        card = getattr(getattr(mw, "reviewer", None), "card", None)
        if mw.state == "review" and card:
            self.show(card, getattr(mw.reviewer, "state", "question"))

    def disable(self) -> None:
        self.owner.save_config({"review_style": "off"})

    def preserve_current(self) -> None:
        self._set_current_native(True)

    def restore_current(self) -> None:
        """Remove a local exception; unsafe templates still fail closed."""
        self._set_current_native(False)

    def _set_current_native(self, native: bool) -> None:
        from aqt import mw
        from aqt.utils import showInfo
        card = getattr(getattr(mw, "reviewer", None), "card", None)
        if mw.state != "review" or card is None:
            showInfo("Open a card in the reviewer first.")
            return
        try:
            self.owner.ensure_store()
            mid = str(card.note_type()["id"])
            updated = profile_settings(self.owner.profile)
            updated["native_note_types"] = [x for x in updated["native_note_types"] if x != mid]
            if native:
                updated["native_note_types"].append(mid)
            self.owner.store.write(updated)
            self.owner.profile = updated
            self.refresh()
        except Exception:
            showInfo("The preference could not be saved. Use ‘Use original reviewer styling’ instead.")

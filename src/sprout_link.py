"""Narrow navigation/presentation bridge to the bundled Sprout 0.10.1 engine.

The engine owns the SAME profile-local exams, assessment, drafts, practice runner
and Pip. This adapter never recreates those algorithms or migrates their files.
"""
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from typing import Any
from .core import json_for_html
from .review_model import PALETTES

LOG = logging.getLogger('atelier.sprout')
ROOT = Path(__file__).resolve().parent


def controller(mw: Any) -> Any:
    from .suite import active_engine
    bundled = active_engine(mw)
    if bundled is not None and getattr(bundled, 'suite', None) is not None:
        return bundled
    module = sys.modules.get('exam_sprout.integration')
    candidate = getattr(module, 'CONTROLLER', None)
    if (candidate is not None and getattr(candidate, 'mw', None) is mw
            and callable(getattr(candidate, 'open', None))):
        return candidate
    return None


def is_planner(context: Any, mw: Any) -> bool:
    c = controller(mw)
    # Identity, not a fuzzy class-name match. Never touch runner or preview.
    return bool(c is not None and context is getattr(c, 'dialog', None)
                and context is not None and type(context).__name__ == 'PlannerDialog')


def tokens_css(config: dict) -> str:
    p = {**PALETTES.get(config.get('theme'), PALETTES['obsidian']), **config.get('_companion_tokens', {})}
    return ':root{' + ''.join(f'--ats-{k}:{v};' for k, v in p.items()) + '}'


class SproutLink:
    def __init__(self, owner: Any, mw: Any):
        self.owner, self.mw = owner, mw
        self._bar = None
        self._bar_original = None
        self._bar_applied = None

    def cancel_pending(self) -> None:
        self._practice_serial = getattr(self, "_practice_serial", 0) + 1
        self._bar = self._bar_original = self._bar_applied = None

    def available(self) -> bool:
        return controller(self.mw) is not None

    def open(self) -> bool:
        c = controller(self.mw)
        if c is None or not self.mw.col or self.mw.state != 'deckBrowser':
            return False
        c.open()  # Sprout's own reentrant/single-dialog guard and lifecycle.
        return True

    def open_practice(self) -> bool:
        if not self.open():
            return False
        c = controller(self.mw)
        if c is None or getattr(c, 'runner', None) is not None:
            # Existing practice is raised by Sprout, never replaced.
            return True
        serial = getattr(self, '_practice_serial', 0) + 1
        self._practice_serial = serial
        collection = self.mw.col
        def attempt(count=0):
            if serial != self._practice_serial or self.mw.col is not collection:
                return
            dialog = getattr(c, 'dialog', None)
            if dialog is None or getattr(dialog, 'closed', False):
                return
            web = getattr(dialog, 'web', None)
            if web is None:
                if count < 40:
                    self.mw.progress.single_shot(100, lambda: attempt(count+1))
                return
            def result(ok):
                if ok is False and count < 40 and self._practice_serial == serial:
                    self.mw.progress.single_shot(100, lambda: attempt(count+1))
            # Use Sprout's existing tab action. Its draft-discard confirmation is
            # retained. Do not set S.view, dispatch a Start, or reset its form.
            script = """(()=>{const b=document.querySelector('#es-app .es-top-nav button[data-action="nav"][data-view="practice"]');if(!b||b.disabled)return false;b.click();return true;})();"""
            try:
                web.evalWithCallback(script, result)
            except (AttributeError, RuntimeError):
                LOG.warning('Practice shortcut unavailable; use Sprout Practice tab.')
        self.mw.progress.single_shot(80, attempt)
        return True

    def summary(self) -> dict:
        from .suite import summary
        return summary(self.mw)

    def open_target(self, view='overview', exam_id='', setup=None) -> bool:
        from .core import ValidationError
        if view not in ('overview','practice','settings','pip','new'):
            raise ValidationError('Choose a valid exam page.')
        c = controller(self.mw)
        if c is None or not self.mw.col or self.mw.state != 'deckBrowser':
            raise ValidationError('Return to the study desk before opening Exam Studio.')
        if exam_id:
            if c.store is None:
                raise ValidationError('The exam profile is not ready.')
            c.store.get_exam(exam_id)  # validates the live record, not a stale tile
        payload = {'view':view, 'id':exam_id}
        if setup is not None:
            if not isinstance(setup,dict):
                raise ValidationError('Invalid plan setup.')
            from .core import deck_id, fresh_catalog
            catalog=fresh_catalog(self.mw.col)
            ids=setup.get('deck_ids',[])
            if not isinstance(ids,list) or not 1 <= len(ids) <= 100:
                raise ValidationError('Choose 1–100 folders for a plan.')
            ids=list(dict.fromkeys(deck_id(d) for d in ids))
            if any(d not in catalog for d in ids):
                raise ValidationError('One of these folders is no longer available.')
            payload['setup']={'name':str(setup.get('name',''))[:120], 'deck_ids':ids}
            if setup.get('query'):
                import re
                query=setup['query']
                if not isinstance(query,str) or len(query)>2000 or not re.fullmatch(r'nid:[1-9][0-9]*(?:,[1-9][0-9]*)*',query):
                    raise ValidationError('The exact-note project scope is invalid or too large.')
                if not self.mw.col.find_notes(query):
                    raise ValidationError('These project notes are no longer in this collection.')
                payload['setup']['query']=query
        c.open()  # preserve active runner and dirty form; do not preselect prematurely
        if getattr(c,'runner',None) is not None:
            return True
        if getattr(c,'dialog',None) is None:
            raise ValidationError('Exam Studio could not open. See Tools → Atelier → Exam Sprout diagnostics.')
        serial=getattr(self,'_practice_serial',0)+1; self._practice_serial=serial
        col=self.mw.col;epoch=getattr(c,'epoch',None)
        def attempt(count=0):
            if serial!=self._practice_serial or col is not self.mw.col or epoch!=getattr(c,'epoch',None):return
            dialog=getattr(c,'dialog',None)
            if dialog is None or getattr(dialog,'closed',False):return
            web=getattr(dialog,'web',None)
            if web is None:
                if count<50:self.mw.progress.single_shot(100,lambda:attempt(count+1))
                return
            def ready(ok):
                if serial!=self._practice_serial or col is not self.mw.col or epoch!=getattr(c,'epoch',None) or dialog is not getattr(c,'dialog',None):return
                if ok is not True:
                    if count<50:self.mw.progress.single_shot(100,lambda:attempt(count+1))
                    return
                dialog.emit_ui_event('suite-navigate',payload)
            web.evalWithCallback('!!(window.ExamSprout && window.ExamSprout.suiteReady && window.ExamSprout.suiteReady())',ready)
        self.mw.progress.single_shot(80,attempt)
        return True

    def add_content(self, content: Any, context: Any) -> None:
        if not is_planner(context, self.mw):
            return
        cfg = self.owner.sprout_config() if hasattr(self.owner, "sprout_config") else self.owner.get_config()
        enabled = cfg.get('match_sprout', True)
        css = (ROOT / 'web' / 'sprout.css').read_text(encoding='utf-8')
        from .worlds import planner_head
        content.head += planner_head(cfg, self.owner.package)
        content.head += ('<style id="atelier-sprout-tokens">' + tokens_css(cfg) + '</style>'
                         '<style id="atelier-sprout-css">' + css + '</style>'
                         '<script>document.documentElement.dataset.atelierSprout='
                         + json.dumps(str(enabled).lower()) + ';</script>')
        self._native_bar(context, cfg)

    def _native_bar(self, dialog: Any, config: dict) -> None:
        bar = getattr(dialog, 'native_bar', None)
        if bar is None:
            return
        try:
            if self._bar is not bar:
                self._bar, self._bar_original, self._bar_applied = bar, bar.styleSheet(), None
            if not config.get('match_sprout', True):
                if self._bar_applied is not None and bar.styleSheet() == self._bar_applied:
                    bar.setStyleSheet(self._bar_original or '')
                self._bar_applied = None
                return
            p = {**PALETTES[config['theme']], **config.get('_companion_tokens', {})}
            # This applies only within Sprout's dedicated header widget.
            sheet = (f'QWidget {{background:{p["side"]};color:{p["text"]};}}'
                     f'QLabel {{color:{p["muted"]};}}'
                     f'QPushButton {{background:{p["raised"]};color:{p["text"]};'
                     f'border:1px solid {p["line"]};border-radius:6px;padding:5px 12px;}}'
                     f'QPushButton:hover {{background:{p["hover"]};}}')
            if bar.styleSheet() != sheet:
                if self._bar_applied is not None and bar.styleSheet() != self._bar_applied:
                    self._bar_original = bar.styleSheet()
                bar.setStyleSheet(sheet)
            self._bar_applied = sheet
        except (RuntimeError, AttributeError):
            self._bar = None

    def refresh(self) -> None:
        c = controller(self.mw)
        dialog = getattr(c, 'dialog', None)
        if not is_planner(dialog, self.mw) or getattr(dialog, 'closed', False):
            return
        cfg = self.owner.sprout_config() if hasattr(self.owner, "sprout_config") else self.owner.get_config()
        web = getattr(dialog, 'web', None)
        if web is not None:
            try:
                from .worlds import runtime_config
                web.eval("window.AtelierWorlds&&window.AtelierWorlds.configure("+json_for_html(runtime_config(cfg))+ ");")
                web.eval("(()=>{const s=document.getElementById('atelier-sprout-tokens');"
                         "if(s)s.textContent=" + json_for_html(tokens_css(cfg)) + ';'
                         'document.documentElement.dataset.atelierSprout='
                         + json.dumps(str(cfg.get('match_sprout', True)).lower()) + ';})();')
            except (RuntimeError, AttributeError):
                pass
        self._native_bar(dialog, cfg)

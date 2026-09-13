"""Shared presentation catalog for the home, planner and native reviewer.

World selection is owned by Atelier, never stored in card templates or exam records.
"""
from __future__ import annotations
import json
from pathlib import Path
from .core import json_for_html
ROOT = Path(__file__).parent / 'web'
CATALOG = json.loads((ROOT / 'worlds.json').read_text(encoding='utf8'))

def runtime_config(config: dict) -> dict:
    return {'theme':config['theme'], 'enabled':config.get('match_sprout',True) and config.get('visual_owner')=='atelier',
            'ambience':config.get('ambience',True), 'motion':config.get('motion',True)}

def home_css() -> str:
    return '\n'.join((ROOT/n).read_text(encoding='utf8') for n in ('worlds-tokens.css','worlds-home.css','studio-home.css','home-shell.css','world-finishes.css','interaction-finish.css','native-widgets.css'))

def planner_head(config: dict, package: str) -> str:
    css = '\n'.join((ROOT/n).read_text(encoding='utf8') for n in ('worlds-planner-tokens.css','worlds-planner.css','studio-shell.css','session-shell.css','world-finishes.css','interaction-finish.css'))
    boot = {'catalog':CATALOG,'config':runtime_config(config)}
    return ('<style id="atelier-world-style">'+css+'</style>'
            '<script>window.AtelierSuiteAssets='+json_for_html('/_addons/'+package+'/sprout/web')+';'
            'window.AtelierWorldBootstrap='+json_for_html(boot)+';'
            'document.documentElement.dataset.atelierWorld='+json_for_html(config['theme'])+';</script>'
            '<script>'+(ROOT/'worlds.js').read_text(encoding='utf8')+'</script>'
            '<script>'+(ROOT/'session-model.js').read_text(encoding='utf8')+'</script>')

def reviewer_css() -> str:
    return (ROOT/'worlds-review-tokens.css').read_text(encoding='utf8')+'\n'+(ROOT/'worlds-review.css').read_text(encoding='utf8')+'\n'+(ROOT/'review-finish.css').read_text(encoding='utf8')

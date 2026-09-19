"""Unified planner fixtures run the bundled frontend and original assessment engine.
Only host commands/data are fixtures; no native Anki review is claimed.
"""
from fixtures import *
from bs4 import BeautifulSoup
import copy
sys.path[:0]=[str(ROOT/'vendor_tests'),str(ROOT/'vendor_tests/tools')]
import test_ui_0100 as assessment
import test_ui_096 as motion
import test_ui as original
worlds=importlib.import_module('atelier_testing.worlds')
link=importlib.import_module('atelier_testing.sprout_link')
BASE_COMMAND=assessment.command
CALLS=[]
ACTIVE_THEME='forest'

def command(action,p):
    CALLS.append((action,p))
    if action=='load':
        out=copy.deepcopy(BASE_COMMAND(action,p));out['state']['settings']['theme']=ACTIVE_THEME
        return {**out,'suite':True,'asset_base':'/_addons/daedalus_atelier/sprout/web'}
    if action=='suite_groups':return []
    if action=='suite_theme':
        if p.get('theme') not in core.THEMES:raise ValueError('Unknown world')
        return {'theme':p['theme']}
    if action in ('suite_native','suite_focus'):return {'opened':True,'focused':True,'native_mock':True}
    return BASE_COMMAND(action,p)
original.command=command

def html(theme='forest',enabled=True):
    global ACTIVE_THEME
    ACTIVE_THEME=theme
    cfg=core.settings({'visual_owner':'atelier' if enabled else 'onigiri','theme':theme,'ambience':True,'match_sprout':enabled,'motion':False})
    web=SRC/'sprout/web'
    css='\n'.join((web/name).read_text(encoding='utf8') for name in ('app.css','countdown.css','pip.css'))
    js=';\n'.join((web/name).read_text(encoding='utf8') for name in ('countdown.js','pip-scene.js','pip.js','app.js'))
    head=worlds.planner_head(cfg,'daedalus_atelier')
    head+='<style id="atelier-sprout-tokens">'+link.tokens_css(cfg)+'</style><style id="atelier-sprout-css">'+(SRC/'web/sprout.css').read_text()+'</style>'
    head+='<script>document.documentElement.dataset.atelierSprout="'+str(enabled).lower()+'";</script>'
    return ('<!doctype html><html lang="en"><head><base href="http://sprout.test/">'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            +head+'<style>'+css+'</style></head><body><main id="es-app"></main>'
            '<script>window.pycmd=m=>window.fixtureCommand(JSON.parse(m.slice(12))).then(window.ExamSprout.receive);</script>'
            '<script>'+js+'</script></body></html>')

def route(req):
    url=req.request.url
    if '/_addons/daedalus_atelier/sprout/web/' not in url and '/_addons/exam_sprout/web/' not in url:
        return req.fulfill(status=403,body='Blocked unexpected request')
    rel=url.split('/web/',1)[1].split('?',1)[0]
    target=(SRC/'sprout/web'/rel).resolve()
    if (SRC/'sprout/web').resolve() not in target.parents or not target.is_file():return req.fulfill(status=404,body='Missing packaged asset')
    return req.fulfill(path=str(target))

def expose(page):
    page.route('**/*',route);page.expose_function('fixtureCommand',original.bridge)
    # Native suite.save_config updates both palette and world properties. Emulate the
    # same delivery for suite_theme without replacing the form or its inputs.
    page.add_init_script('window.__suiteFixture=true')

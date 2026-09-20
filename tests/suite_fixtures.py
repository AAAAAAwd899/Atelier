"""Current suite production assets; fictional collection only, never a native Anki claim."""
from fixtures import *
from preview_071 import home071
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import base64
worlds=importlib.import_module('atelier_testing.worlds')

def suite_state():
    future=lambda n:(datetime.now()+timedelta(days=n)).replace(hour=9,minute=0,second=0,microsecond=0).isoformat()
    return {'available':True,'engine':'0.10.1','warning':'','read_only':False,'history_count':3,'draft':None,
            'plans':[{'id':'pharm3','name':'Cardiology · Exam 3','due':future(12),'archived':False,'deck_ids':['22'],'filtered':False,'mode':'steady','format':'mixed'},
                     {'id':'micro','name':'Microbiology · Written quiz','due':future(18),'archived':False,'deck_ids':['24'],'filtered':False,'mode':'steady','format':'written'}]}

def home_suite(theme='forest',owner='atelier',page='desk',with_sprout=False):
    soup=BeautifulSoup(home071(owner=owner,onigiri=True),'html.parser')
    boot=json.loads(soup.find(id='atelier-bootstrap').string)
    boot['worlds']=worlds.CATALOG;boot['suite']=suite_state();boot['demo']['suite']=suite_state()
    boot['authoring']={'available':True,'projects':6,'drafts':3,'repairs':1};boot['demo']['authoring']=dict(boot['authoring'])
    boot['assetBase']='/_addons/daedalus_atelier/web'
    mark=(ROOT/'src'/'web'/'atelier-mark-1.0.3.png').read_bytes()
    boot['brandAsset']='data:image/png;base64,'+base64.b64encode(mark).decode('ascii')
    boot['suiteAssets']='/_addons/daedalus_atelier/sprout/web'
    boot['nativeTools']={key:True for key in ('add','browse','sync','stats','import','export','preferences','addons','note_types','profiles','help','undo','redo','check_media','check_database','filtered_deck','empty_cards','fullscreen','check_updates')}
    boot['settings'].update(theme=theme,native_surfaces=True,motion=False,ambience=True)
    boot['demo']['settings']=dict(boot['settings']);boot['ui']={'page':page}
    boot['integrations'].update(bundled=True,exam_sprout=True)
    soup.find(id='atelier-bootstrap').string=core.json_for_html(boot)
    # Regenerate early palette for the chosen world too.
    soup.find(id='atelier-paint-style').decompose()
    scr=next(s for s in soup.find_all('script') if 'const c={' in (s.string or ''));scr.decompose()
    early=BeautifulSoup(guard.home_guard(boot['settings']),'html.parser')
    old=soup.find(id='atelier-shared-style')
    if old:old.decompose()
    for n in list(early.contents):soup.head.append(n.extract())
    return str(soup)

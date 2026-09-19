from patch_preservation import before_patch
"""Final world/interaction pass contracts. No native-Anki claims."""
from pathlib import Path
import hashlib,json,re,importlib,types,sys
import pytest
R=Path(__file__).resolve().parents[1];S=R/'src'
BASE=json.loads((R/'world-pass-baseline.json').read_text())
CAT=json.loads((S/'web/worlds.json').read_text())
PALETTES=json.loads((S/'web/palettes.json').read_text())

@pytest.mark.parametrize('world',CAT,ids=lambda w:w['id'])
def test_each_world_has_matching_lighting_material_and_explicit_frame(world):
 assert world['lighting']==PALETTES[world['id']]['scheme']
 assert len(world['material'])>=15
 css=(S/'web/world-finishes.css').read_text()
 assert f'.mini-screen[data-theme="{world["id"]}"]' in css
 assert f'.theme-tile[data-theme-choice="{world["id"]}"] .theme-title' in css
 assert (S/'web'/world['art']).is_file()

@pytest.mark.parametrize('file',[n for n in BASE if n.startswith('sprout/') and n not in ('sprout/runner.py','sprout/web/app.js','sprout/web/pip.css','sprout/web/pip.js','sprout/integration.py')])
def test_entire_integrated_sprout_runtime_is_byte_identical_to_rc5(file):
 assert hashlib.sha256((S/file).read_bytes()).hexdigest()==BASE[file]

@pytest.mark.parametrize('file',['session_model.py','ownership.py','lifecycle.py','review_model.py','review_theme.py','web/reviewer.js','web/reviewer.css','web/studio-shell.css','web/session-shell.css','web/model.js'])
def test_accepted_behaviour_unchanged_except_version(file):
 data=before_patch(file).replace(b'0.9.0-rc4',b'0.8.0-rc5').replace(b'0.9.0-rc5',b'0.8.0-rc5').replace(b'1.0.0',b'0.9.0-rc6').replace(b'0.9.0-rc6',b'0.8.0-rc5')
 assert hashlib.sha256(data).hexdigest()==BASE[file]

def test_finishes_do_not_add_assets_or_card_content_rules():
 css=(S/'web/world-finishes.css').read_text()
 assert '#qa' not in css and 'http' not in css and '@import' not in css
 assert css.count('--finish-aperture:')==len(CAT)
 assert len({w['material'] for w in CAT})==len(CAT)
 from upgrade_preservation import before_upgrade
 css=before_upgrade('web/review-finish.css').decode('utf8')
 assert '#qa' not in css and not re.search(r'(?<![-\w])(width|height|padding|margin|display)\s*:',css)

def test_final_layers_loaded_in_all_intended_surfaces():
 spec=types.ModuleType('world_finish_test');spec.__path__=[str(S)];sys.modules['world_finish_test']=spec
 w=importlib.import_module('world_finish_test.worlds');c=importlib.import_module('world_finish_test.core')
 assert 'Final world finishes' in w.home_css()
 assert 'Interaction finish' in w.planner_head(c.settings({'visual_owner':'atelier'}),'daedalus_atelier')
 assert 'Reader-first finish' in w.reviewer_css()

def test_no_external_requests_or_new_preferences_for_world_filter():
 s=(S/'web/atelier.js').read_text()
 f=s[s.index('    function filterWorlds('):s.index('    function parentOptions(')]
 assert 'request(' not in f and 'localStorage' not in f
 assert 'worldFilter' in f and 'tile.hidden=' in f
 assert "!event.target.closest?.('.context-menu')" in s

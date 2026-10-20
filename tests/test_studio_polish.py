"""Release-facing contracts for the Studio composition pass."""
import hashlib,json,sys,types,importlib
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1];SRC=R/'src'
pkg=types.ModuleType('atelier_studio_contract');pkg.__path__=[str(SRC)];sys.modules.setdefault('atelier_studio_contract',pkg)
worlds=importlib.import_module('atelier_studio_contract.worlds')
core=importlib.import_module('atelier_studio_contract.core')
BASELINE=json.loads((R/'vendor-baseline.json').read_text())['sha256']

@pytest.mark.parametrize('name',['core.py','exam_engine.py','exam_session.py','collection_reader.py','storage.py','drafts.py','answers.py','evidence.py','readiness.py','progress.py','session_tools.py','new_learning.py','companion.py','companion_layout.py','widget.py','web/app.css','web/pip/asset_manifest.json','web/pip-scene.js'])
def test_engine_and_original_presentation_assets_unchanged(name):
 assert hashlib.sha256((SRC/'sprout'/name).read_bytes()).hexdigest()==BASELINE[name]

@pytest.mark.parametrize('theme',core.THEMES)
def test_layout_assets_shipped_with_each_world(theme):
 cfg=core.settings({'visual_owner':'atelier','theme':theme})
 head=worlds.planner_head(cfg,'daedalus_atelier')
 assert 'atelier-world-style' in head
 assert 'grid-template-rows:auto minmax(0,1fr)' in head
 assert 'suite-setup-scroll' in head
 assert 'suite-practice-summary' in (SRC/'sprout/web/app.js').read_text()
 assert 'WorldBootstrap' in head and theme in head

def test_no_new_assessment_schema_or_network_dependency():
 manifest=json.loads((SRC/'manifest.json').read_text())
 assert manifest['package']=='daedalus_atelier'
 assert manifest['human_version']=='1.0.5'
 css=(SRC/'web/studio-shell.css').read_text()
 assert 'http://' not in css and 'https://' not in css
 assert '#qa' not in css and 'ease1' not in css
 assert 'Not saved yet' in (SRC/'sprout/web/app.js').read_text()
 assert 'Autosaved' not in (SRC/'sprout/web/app.js').read_text()

def test_bundled_original_css_not_edited_and_studio_css_is_scoped():
 css=(SRC/'web/studio-shell.css').read_text()
 assert '#es-app[data-suite="true"]' in css
 assert '[data-page="setup"] .es-main' in css
 assert 'prefers-reduced-motion:reduce' in css
 assert 'forced-colors:active' in css
 assert 'position:fixed' not in css

def test_reading_surfaces_untouched_by_new_shell():
 css=worlds.reviewer_css()
 assert 'suite-setup-scroll' not in css and 'Studio shell · rc3' not in css

def test_summary_has_no_fake_autosave_or_parallel_store():
 text=(SRC/'sprout/web/app.js').read_text()
 summary=text.split('function updateSetupSummary()',1)[1].split('function renderDeckList()',1)[0]
 assert 'request(' not in summary
 assert 'localStorage' not in summary and 'sessionStorage' not in summary
 assert 'suite-summary-note' in summary

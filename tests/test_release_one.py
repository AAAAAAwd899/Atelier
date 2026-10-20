"""1.0 release freeze: reviewed copy/version changes, not a hidden redesign."""
import ast,hashlib,json,re
from pathlib import Path
import pytest
from release_copy import before_release_copy
R=Path(__file__).resolve().parents[1];S=R/'src'
BASE=json.loads((R/'release-1-baseline.json').read_text())
COPY=json.loads((R/'release-copy-changes.json').read_text())['files']
RUNTIME={'.py','.js','.css','.json','.svg','.png','.webp'}

@pytest.mark.parametrize('name',list(COPY))
def test_reviewed_copy_can_be_reconstructed_exactly(name):
    if name in ('sprout/web/app.js','sprout/web/pip.css','sprout/web/pip.js','workshop/web/app.js','workshop/web/app.css'):
        patch=json.loads((R/'patch-106-changes.json').read_text())['changed']
        assert hashlib.sha256((S/name).read_bytes()).hexdigest()==patch[name]
        return
    assert hashlib.sha256(before_release_copy(name)).hexdigest()==BASE[name]

@pytest.mark.parametrize('group',['sprout/','workshop/','web/'])
def test_no_hidden_logic_or_asset_changes(group):
    for name,h in BASE.items():
        if name.startswith(group) and Path(name).suffix in RUNTIME and name not in ('sprout/web/app.js','sprout/web/pip.css','sprout/web/pip.js','workshop/web/app.js','workshop/web/app.css'):
            assert hashlib.sha256(before_release_copy(name)).hexdigest()==h,name

def test_final_layout_icons_and_scene_art_unchanged():
    paths=[n for n in BASE if Path(n).suffix in {'.css','.svg','.png','.webp'} and n != 'sprout/web/pip.css']
    assert len(paths)>50
    assert all(hashlib.sha256(before_release_copy(n)).hexdigest()==BASE[n] for n in paths)

def test_version_identity_and_default_preferences():
    manifest=json.loads((S/'manifest.json').read_text());assert manifest['human_version']=='1.0.6'
    assert manifest['package']=='daedalus_atelier'
    tree=ast.parse((S/'core.py').read_text())
    assert next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))=='1.0.6'
    for n in ['config.json','config.schema.json','native_widgets.py','figure_cache.py','focus_context.py','study_progress.py','quiet_navigation.py','ownership.py','native_tools.py','suite.py','card_studio.py']:
        assert hashlib.sha256(before_release_copy(n)).hexdigest()==BASE[n],n

def test_no_old_release_markers_in_live_core_assets():
    for name in COPY:
        text=(S/name).read_text(encoding='utf8')
        assert 'Preview release' not in text
        assert 'engineering candidate' not in text
        if name not in ['sprout/web/app.js','workshop/web/app.js']:
            assert '0.9.0-rc6' not in text

def test_public_copy_does_not_claim_total_privacy_or_automatic_backup():
    privacy=(S/'PRIVACY.md').read_text(encoding='utf8')
    assert 'Anki Sync does not include' in privacy
    assert 'permission' in privacy and 'API key' in privacy
    assert 'not encrypted' in privacy

def test_user_guidance_preserves_saving_and_scheduler_distinctions():
    guide=(S/'USER-GUIDE.md').read_text(encoding='utf8')
    for phrase in ['Save & close','Introduce new cards','Review & add','Widgets','workshop','exam_sprout']:
        assert phrase in guide
    assert 'timed' in guide.lower() and 'continues' in guide.lower()

def test_release_is_not_an_ankiweb_publication_claim():
    record=json.loads((R/'RELEASE-ACCEPTANCE.json').read_text())
    assert record['user_reported']['visual_and_primary_testing']=='passed'
    assert record['independent_native_windows_test_performed'] is False
    assert record['external_publication_performed'] is False
    assert record['target_anki']=='26.08.1'

def test_all_shipped_own_text_decodes_utf8_without_replacement_glyph():
    for p in S.rglob('*'):
        if not p.is_file() or 'vendor' in p.parts or p.suffix not in {'.js','.py','.json','.css','.md','.txt','.svg'}:continue
        text=p.read_text(encoding='utf8')
        assert '\ufffd' not in text,str(p)

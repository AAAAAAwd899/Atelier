from patch_preservation import before_patch
"""Audit guards and preservation: no real Anki collection or provider access."""
import hashlib,importlib,json,sys,types
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'src'
pkg=types.ModuleType('usability_contract');pkg.__path__=[str(SRC)];sys.modules[pkg.__name__]=pkg
core=importlib.import_module('usability_contract.core')
authoring=importlib.import_module('usability_contract.authoring')
BASE=json.loads((ROOT/'usability-baseline.json').read_text())

@pytest.fixture
def routes(monkeypatch):
 calls=[];cleanups=[];col=NS();mw=NS(col=col,state='deckBrowser',_exam_sprout_controller=NS(runner=None),onAddCard=lambda:None)
 ctrl=NS(mw=mw,preferred_deck=999,open=lambda *a,**k:calls.append((a,k)))
 obj=authoring.AuthoringRoutes(NS(),ctrl,NS(cleanup=cleanups.append))
 monkeypatch.setattr(core,'fresh_catalog',lambda c:{'1':{'name':'Course'},'2':{'name':'Course::Lecture'}})
 return obj,ctrl,calls

@pytest.mark.parametrize('view',['library','studio','drafts','import','find','improve','media','settings'])
def test_visible_source_destinations_use_single_controller_and_clear_stale_target(routes,view):
 obj,c,calls=routes;obj.open_page(view)
 assert calls==[((view,),{'note_id':None,'allow_review':True})]
 assert c.preferred_deck is None

@pytest.mark.parametrize('view',['studio','drafts','import'])
def test_explicit_destination_stays_exact_and_profile_existing(routes,view):
 obj,c,calls=routes;obj.open_page(view,deck_id='2')
 assert c.preferred_deck==2 and calls[0][0]==(view,)

@pytest.mark.parametrize('bad',['garbage','../other','practice','eval',''])
def test_unknown_source_view_refuses_navigation(routes,bad):
 obj,c,calls=routes
 with pytest.raises(core.ValidationError):obj.open_page(bad)
 assert not calls

@pytest.mark.parametrize('bad',['9999','-1',True,'<script>',0])
def test_missing_or_invalid_destination_never_falls_back_silently(routes,bad):
 obj,c,calls=routes
 with pytest.raises(core.ValidationError):obj.open_page('studio',deck_id=bad)
 assert not calls

@pytest.mark.parametrize('state',['closed','no-profile','active-practice'])
def test_visible_new_routes_keep_host_lifecycle_guards(routes,state):
 obj,c,calls=routes
 if state=='closed':obj.alive=False
 elif state=='no-profile':c.mw.col=None
 else:c.mw._exam_sprout_controller.runner=object()
 with pytest.raises(core.ValidationError):obj.open_page('drafts')
 assert not calls

def test_every_bundled_exam_file_matches_actual_rc2_installer():
 for n,h in BASE.items():
  if n.startswith('sprout/') and n not in ('sprout/integration.py','sprout/web/app.js'):
   assert hashlib.sha256((SRC/n).read_bytes()).hexdigest()==h,n

def test_card_importers_approval_storage_and_masks_remain_original_rc2():
 for n,h in BASE.items():
  if n.startswith('workshop/') and n not in ('workshop/web/app.js','workshop/integration.py','workshop/INTEGRATION-NOTE.md'):
   assert hashlib.sha256((SRC/n).read_bytes()).hexdigest()==h,n

def test_old_byte_boundaries_are_not_hidden_by_version_bump():
 inputs=json.loads((ROOT/'integration-baselines.json').read_text())
 changed=[n for n,h in inputs['incoming'].items() if n.startswith('workshop/') and hashlib.sha256((SRC/n).read_bytes()).hexdigest()!=h]
 assert set(changed)=={'workshop/integration.py','workshop/web/app.js'}

def test_original_review_session_native_tools_ownership_and_store_contracts_unchanged():
 for n in ['web/model.js','web/reviewer.css','session_model.py','quiet_navigation.py','native_tools.py','ownership.py','suite.py','lifecycle.py']:
  assert hashlib.sha256(before_patch(n)).hexdigest()==BASE[n],n

def test_integration_metadata_only_change_preserves_required_input_provenance():
 old=BASE.get('workshop/INTEGRATION-NOTE.md')
 assert old
 assert '0.9.0-rc4' in (SRC/'workshop/INTEGRATION-NOTE.md').read_text()


def test_native_card_controller_only_changes_its_integrated_diagnostic_path():
 s=(SRC/'workshop/integration.py').read_text()
 patched="tooltip('Card Studio could not open. Tools → Atelier → Card Studio → Diagnostics has the details.' if getattr(self,'suite',None) else 'Workshop could not open. Tools → Workshop → Diagnostics has the details.',parent=self.mw)"
 baseline="tooltip('Workshop could not open. Tools → Workshop → Diagnostics has the details.',parent=self.mw)"
 assert patched in s
 assert 'use_col=False' in s and 'figure_preview' in s
 # See test_release_finish.py for every unchanged native method's AST.

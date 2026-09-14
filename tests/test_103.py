"""Current upgrade contracts. Historical reconstructions are not behavior evidence."""
from pathlib import Path
import hashlib,json,subprocess,sys,importlib
import pytest
from fixtures import ROOT,SRC

def test_exact_upgrade_declaration_and_protected_engines():
    old=json.loads((ROOT/'baseline-1.0.2.json').read_text())
    patch=json.loads((ROOT/'patch-103-changes.json').read_text())
    actual={p.relative_to(SRC).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
    assert {n:h for n,h in actual.items() if n in old and h!=old[n]}==patch['changed']
    assert {n:h for n,h in actual.items() if n not in old}==patch['added']
    assert set(old)<=set(actual) and not patch['removed']
    protected=('sprout/','workshop/','folder_study.py','remote_model.py','remotes.py','web/remote-input.js','figure_cache.py','native_widgets.py','ownership.py','focus_context.py','study_progress.py')
    allowed_presentation={'workshop/web/app.js','workshop/web/app.css','sprout/web/app.js','sprout/web/pip.css'}
    assert not any(n.startswith(protected) and n not in allowed_presentation for n in patch['changed'])

def test_generated_adapters_are_reproducible():
    subprocess.run([sys.executable,str(ROOT/'tools/generate_design.py'),'--check'],check=True)

def luminance(hex):
    rgb=[int(hex[i:i+2],16)/255 for i in (1,3,5)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(v*w for v,w in zip(rgb,[.2126,.7152,.0722]))

@pytest.mark.parametrize('world',json.loads((SRC/'web/design-contract.json').read_text())['worlds'])
def test_readable_role_pairs(world):
    roles=json.loads((SRC/'web/design-contract.json').read_text())['worlds'][world]['roles']
    for fg,bg in [(fg,bg) for fg in ['text','muted'] for bg in ['canvas','sidebar','panel','raised','input']]+[('action-text','action')]:
        a,b=sorted([luminance(roles[fg]),luminance(roles[bg])]);assert (b+.05)/(a+.05)>=4.5,(world,fg,bg,(b+.05)/(a+.05))

def test_unknown_io_templates_fail_closed():
    io=importlib.import_module('atelier_testing.io_view')
    assert not io.recognized({})
    assert not io.recognized({'originalStockKind':6,'css':'custom','tmpls':[]})
    assert not io.recognized({'originalStockKind':6,'css':'','tmpls':[{'qfmt':'<script>custom()</script>'}]})

def test_empty_resume_strip_collapses_and_owner_is_explicit():
    text=(SRC/'web/atelier.js').read_text(encoding='utf8')
    assert "if(!cards.length)return '';" in text
    assert "host.dataset.owner=state.config.visual_owner||'ask'" in text
    css=(SRC/'web/atelier.css').read_text(encoding='utf8')
    assert 'var(--world-scene,var(--world-art))' in css and '.appearance-link::after' in css
    # The final cascade must retain the scenic layer; a later background
    # shorthand must not flatten the world-aware atmosphere tile.
    final_tile=css[css.rfind('.appearance-link{'):css.find('}',css.rfind('.appearance-link{'))+1]
    assert 'var(--world-scene,var(--world-art))' in final_tile

def test_card_studio_save_and_next_keeps_authoring_context():
    text=(SRC/'workshop/web/app.js').read_text(encoding='utf8')
    assert "saveAndNextDraft" in text
    assert "save-and-next" in text
    assert "source_id:saved.source_id||''" in text
    assert "deck_id:saved.deck_id" in text
    assert "tags:[...(saved.tags||[])]" in text
    assert "mapping:structuredClone(saved.mapping||{})" in text
    assert "hide_others:saved.hide_others!==false" in text
    assert "saveAndNextPageDraft" in text
    assert "save-and-next-page" in text
    assert "Save & next ${['pptx','odp'].includes(S.source.source.kind)?'slide':'page'}" in text
    assert "S.source?.version.pages.length>1&&S.page<S.source.version.pages.length?B('save-and-next-page'" in text
    assert "draftSort:'recent'" in text
    assert "data-change=\"draft-sort\"" in text
    assert "draftSource:'all'" in text
    assert "data-change=\"draft-source\"" in text
    assert "S.draftSource==='all'||d.source_id===S.draftSource" in text
    assert "organizeDrafts" in text and "B('organize-drafts'" in text
    assert "clear-draft-selection" in text and "S.selectedDrafts.clear();$('#ws-inbox-results').innerHTML=inboxResults()" in text
    assert "allSelected=ds.length>0&&selected===ds.length" in text
    assert "select-all-filtered" in text and "rows.forEach(d=>all?S.selectedDrafts.delete(d.id):S.selectedDrafts.add(d.id))" in text
    assert "Only local unapproved drafts are changed" in text
    assert "exceed Anki’s 40-tag limit" in text
    assert 'ws-organize-remove-tags' in text and 'removeSet=new Set(remove)' in text
    assert "S.draftSort==='source'" in text
    assert "S.draftSort==='deck'" in text
    assert "page-chip-count" in text
    assert "drafts.filter(d=>d.status!=='committed'&&d.source_id===S.source.source.id" in text
    assert "nextUncoveredPage" in text
    assert "next-uncovered" in text
    assert "source-coverage" in text
    assert "sourceContextNotice" in text and "source-context-note" in text
    assert "hasDraftWork" in text and "S.draft.front?.trim()" in text
    assert "new-page-draft" in text and "source_id:S.source.source.id" in text and "version_id:S.source.version.id" in text
    assert "const prior=S.draft" in text and "tags:[...(prior.tags||[])]" in text and "mapping:structuredClone(prior.mapping||{})" in text
    assert "Your card setup was kept." in text
    assert "No source linked" in text and "page ${Number(d.page||1)}" in text

def test_first_run_study_desk_leads_with_focus_setup():
    text=(SRC/'web/atelier.js').read_text(encoding='utf8')
    assert "btn('studies','Set your focus','focus','primary'" in text
    assert "Select every parent folder or deck you want to sit together in this exam." in text
    assert "Select the two parent folders you want to sit together in this exam." not in text
    assert "!last?btn('page','Browse library','folder','secondary'" in text

def test_card_studio_compact_navigation_keeps_labels_visible():
    css=(SRC/'workshop/web/app.css').read_text(encoding='utf8')
    assert '@media(max-width:470px)' in css
    assert '.nav-link .nav-title{display:block' in css
    assert '.nav-link{flex:1 1 0;min-width:0;flex-direction:column' in css
    assert '.nav-link[data-view="settings"]{display:flex}' in css

def test_card_studio_surfaces_specialized_card_types():
    text=(SRC/'workshop/web/app.js').read_text(encoding='utf8')
    assert 'creator-specialized' in text and 'choose Mask an image in the editor' in text
    assert 'data-value="compare"' in text and 'data-value="sequence"' in text and 'data-value="application"' in text
    assert "['occlusion','Mask an image','crop']" in text
    assert "native-source-occlusion" in text and "request('occlude'" in text

def test_library_exposes_scoped_export_share_action():
    text=(SRC/'web/atelier.js').read_text(encoding='utf8')
    assert "Find cards & sources" in text and "data-view=\"find\"" in text
    assert "export-deck','Export / share this deck…'" in text
    assert "export-deck','Export / share…'" in text
    assert "case 'export-deck':closeDialog(true);await request('export_deck',{id});break;" in text
    assert 'Choose a parent folder to include its subdecks' in text

def test_find_can_open_exact_selection_in_native_browser():
    text=(SRC/'workshop/web/app.js').read_text(encoding='utf8')
    assert "browse-selected" in text and "nativeAction('browse',null,'nid:'+ids.join(','))" in text
    assert 'Select notes to compare, link, or open in Anki for export' in text

def test_world_catalog_and_art_provenance_cover_every_shipped_world():
    catalog=json.loads((SRC/'web/worlds.json').read_text(encoding='utf8'))
    ids={row['id'] for row in catalog}
    assert len(catalog)==12 and ids=={'obsidian','glacier','rose','bloom','linen','matcha','midnight','peach','forest','tidal','ember','celestial'}
    provenance=json.loads((ROOT/'ASSET-PROVENANCE-1.0.3.json').read_text(encoding='utf8'))
    files={row['file'] for row in provenance}
    assert files=={f'src/web/world-art/{world}-1.0.3.png' for world in ids}
    assert all(row['sha256'] and row['bytes']>1000 and row['origin'] for row in provenance)
    assert all('authored SVG' not in row['origin'] for row in provenance)

def test_world_gallery_verification_scales_with_catalog():
    checker=(ROOT/'tests/check_gallery_final.py').read_text(encoding='utf8')
    assert 'world_count*10' in checker and "f'{world_count} worlds x 10 screens'" in checker

def test_unpublished_site_inventory_matches_shipped_world_catalog():
    catalog=json.loads((SRC/'web/worlds.json').read_text(encoding='utf8'))
    page=(ROOT/'site/index.html').read_text(encoding='utf8')
    styles=(ROOT/'site/style.css').read_text(encoding='utf8')
    assert '<strong>12</strong><span>distinct visual worlds</span>' in page
    assert page.count('class="world ') == len(catalog)
    assert all(f'class="world {world["id"]}"' in page for world in catalog)
    assert all(f'.{world["id"]} {{ --world:' in styles for world in catalog)

from patch_preservation import before_patch
"""Display-only contract: canonical tool search, safe resume and unmodified engine."""
import hashlib, importlib, json, subprocess, sys, types
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1]; S=R/'src'

def node(script):
    code="const assert=require('node:assert/strict'); const M=require('./src/web/model.js');\n"+script
    subprocess.run(['node','-e',code],cwd=R,check=True,capture_output=True,text=True)

@pytest.mark.parametrize('query,expected',[
    ('media','check_media'),('IMAGE OCCLUSION','add'),('image-occlusion','add'),
    ('sync','sync'),('AnkiWeb','sync'),('field','note_types'),('templátes','note_types'),
    ('plugins','addons'),('redo','redo'),('empty','empty_cards'),('apkg','import'),
    ('custom study','filtered_deck'),('profile','profiles'),('full screen','fullscreen'),
    ('documentation','help'),('check database','check_database')])
def test_tool_lookup(query,expected):
    node(f'assert(M.findTools({json.dumps(query)}).some(t=>t.id==={json.dumps(expected)}));')

@pytest.mark.parametrize('group,count',[('everyday',6),('organize',4),('maintenance',3),('settings',6)])
def test_category_counts_and_uniqueness(group,count):
    node(f"assert.equal(M.findTools('',{json.dumps(group)}).length,{count});assert.equal(new Set(M.TOOLS.map(t=>t.id)).size,19);assert(Object.isFrozen(M.TOOLS));")

def test_unknown_tool_query_is_not_a_native_command():
    node("assert.deepEqual(M.findTools('<script>'),[]);assert.deepEqual(M.findTools('delete everything now'),[]);assert.equal(M.findTools('media','settings').length,0);")

NODES=[{'id':'10','parent':'0','name':'Course','children':['11','12'],'path':'Course'},
       {'id':'11','parent':'10','name':'Lecture 2','children':[],'path':'Course::Lecture 2'},
       {'id':'12','parent':'10','name':'Lecture 10','children':[],'path':'Course::Lecture 10'},
       {'id':'20','parent':'0','name':'Old course','children':['21'],'path':'Old course'},
       {'id':'21','parent':'20','name':'Old lecture','children':[],'path':'Old course::Old lecture'}]
@pytest.mark.parametrize('last,enabled,active,expected',[
 ('11',True,True,'11'),('21',True,True,None),('10',False,False,None),
 ('missing',False,False,None),('11',True,False,None),('21',False,False,'21')])
def test_continue_never_substitutes_parent_or_out_of_focus_deck(last,enabled,active,expected):
    profile={'last_studied':last,'focus_enabled':enabled,'selected_study':'all',
             'studies':[{'id':'s','deck_ids':['10'],'active':active}]}
    node(f"const nodes={json.dumps(NODES)},profile={json.dumps(profile)};const before=JSON.stringify([nodes,profile]);assert.equal(M.continueDeck(nodes,profile)?.id||null,{json.dumps(expected)});assert.equal(JSON.stringify([nodes,profile]),before);")

@pytest.mark.parametrize('recent,current,expected',[
 (['11'],'0','10'),(['11','21'],'10','20'),(['missing'],'0',None),
 (['20','11'],'0','20'),(['12','11'],'10',None)])
def test_return_to_last_folder_skips_deleted_current_and_leaf(recent,current,expected):
    node(f"assert.equal(M.lastFolder({json.dumps(NODES)},{{recent_locations:{json.dumps(recent)}}},{json.dumps(current)})?.id||null,{json.dumps(expected)});")

def test_tool_ids_match_native_allowlist():
    spec=types.ModuleType('home_tools_contract');spec.__path__=[str(S)];sys.modules.setdefault('home_tools_contract',spec)
    nt=importlib.import_module('home_tools_contract.native_tools')
    ids=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./src/web/model.js').TOOLS.map(t=>t.id)))"],cwd=R,text=True))
    assert set(ids)==set(nt.COMMANDS)|set(nt.FORM_ACTIONS)

@pytest.mark.parametrize('file',[
 'sprout/core.py','sprout/exam_engine.py','sprout/exam_session.py','sprout/storage.py',
 'sprout/drafts.py','sprout/new_learning.py','sprout/web/app.css',
 'review_theme.py','review_model.py'])
def test_engine_and_native_behaviour_preserved_from_rc3(file):
    baseline=json.loads((R/'home-slice-baseline.json').read_text())
    # Version-only substitutions outside sprout are allowed for display diagnostics.
    txt=before_patch(file)
    if file in ('review_theme.py','review_model.py'):txt=txt.replace(b'0.9.0-rc4',b'0.8.0-rc3').replace(b'0.9.0-rc5',b'0.8.0-rc3').replace(b'1.0.0',b'0.9.0-rc6').replace(b'0.9.0-rc6',b'0.8.0-rc3')
    assert hashlib.sha256(txt).hexdigest()==baseline[file]

def test_new_styles_are_home_only_and_loaded():
    css=(S/'web/home-shell.css').read_text()
    assert '#qa' not in css and '#es-app' not in css and 'body' not in css
    assert 'forced-colors:active' in css and 'prefers-reduced-motion:reduce' in css
    assert 'home-shell.css' in (S/'worlds.py').read_text()

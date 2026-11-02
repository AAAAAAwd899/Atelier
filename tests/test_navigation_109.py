"""Additive presentation preferences; never a collection or schedule migration."""
import copy,json
from fixtures import core,ROOT

def test_folder_icons_are_bounded_tokens_with_valid_deck_ids():
    raw={'folder_icons':{'123':'bow','456':'books','0':'cat','-1':'cat','bad':'cat','9':'<svg onload=bad>','10':{'url':'https://example.invalid'},'11':['bow']}}
    original=copy.deepcopy(raw)
    assert core.profile_settings(raw)['folder_icons']=={'123':'bow','456':'books'}
    assert raw==original

def test_old_profile_receives_only_empty_icon_metadata():
    old={'colors':{'123':'rose'},'favorites':['123'],'folders':['123']}
    parsed=core.profile_settings(old)
    assert parsed['folder_icons']=={} and parsed['colors']==old['colors'] and parsed['favorites']==old['favorites']

def test_all_icon_tokens_roundtrip_without_html_or_urls():
    value={'folder_icons':{str(i+1):icon for i,icon in enumerate(core.FOLDER_ICONS)}}
    assert core.profile_settings(value)['folder_icons']==value['folder_icons']
    assert len(set(core.FOLDER_ICONS))==len(core.FOLDER_ICONS)

def test_outline_is_additive_and_schema_matches():
    schema=json.loads((ROOT/'src/config.schema.json').read_text())
    for view in ['grid','list','outline']:
        assert core.settings({'view':view})['view']==view and view in schema['properties']['view']['enum']
    assert core.settings({'view':'unknown'})['view']=='grid'

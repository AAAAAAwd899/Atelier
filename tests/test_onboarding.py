"""Local tour preferences and context-restricted bridge; Anki objects are doubles."""
import copy
import json
import pytest
from fixtures import core, SRC
from test_release import app, onigiri


@pytest.mark.parametrize('status', ['offered', 'skipped', 'completed'])
def test_tour_marker_roundtrips_without_changing_existing_work(tmp_path, status):
    store=core.ProfileStore(tmp_path, 'course-profile')
    before=core.profile_settings({'favorites':['2'], 'folders':['3'], 'native_widget_note':'Keep this note',
        'studies':[{'id':'one','name':'Final','date':'2026-12-01','deck_ids':['2','3'],'active':True}]})
    store.write(before)
    updated=copy.deepcopy(before);updated['onboarding']={'version':1,'status':status}
    store.write(updated)
    actual=store.read()
    assert actual.pop('onboarding')=={'version':1,'status':status}
    before.pop('onboarding');assert actual==before
    assert core.ProfileStore(tmp_path,'other-profile').read()['onboarding']['version']==0


@pytest.mark.parametrize('bad', [None, [], {'version':True,'status':'completed'}, {'version':99,'status':'completed'},
    {'version':1,'status':'<script>'}, {'version':0,'status':'completed'}, {'version':1,'status':[]}])
def test_invalid_marker_never_becomes_an_acknowledgement(bad):
    with pytest.raises(core.ValidationError):core.onboarding_state(bad)
    assert core.profile_settings({'onboarding':bad})['onboarding']=={'version':0,'status':'new'}


def test_bridge_updates_only_tour_preference(app):
    a,mw,*_=app
    before=copy.deepcopy(a.profile)
    a.dispatch('test','tour','preference',{'key':'onboarding','value':{'version':1,'status':'completed'}})
    assert a.profile['onboarding']=={'version':1,'status':'completed'}
    before.pop('onboarding');after=copy.deepcopy(a.profile);after.pop('onboarding')
    assert before==after
    with pytest.raises(core.ValidationError):
        a.dispatch('test','tour','preference',{'key':'onboarding','value':{'version':2,'status':'completed'}})


def test_all_stored_worlds_are_available_in_native_config_schema():
    schema=json.loads((SRC/'config.schema.json').read_text())
    assert tuple(schema['properties']['theme']['enum'])==core.THEMES


def test_manifest_enforces_documented_minimum_host():
    manifest=json.loads((SRC/'manifest.json').read_text())
    assert manifest['package']=='daedalus_atelier' and manifest['min_point_version']==250905

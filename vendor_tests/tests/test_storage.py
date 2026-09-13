from copy import deepcopy
import json
from pathlib import Path
import pytest
from addon.storage import Store, validate_state, settings_from
from addon.core import Exam, PracticeSession, CardInfo


def data():
    return {'id':'demo','name':'Exam','due':'2026-09-20T09:00','scopes':[{'deck_id':1,'name':'Deck'}]}

def test_roundtrip_profiles_and_update(tmp_path):
    s=Store(tmp_path/'a');s.save_exam(data())
    assert Store(tmp_path/'a').get_exam('demo').name=='Exam'
    assert not Store(tmp_path/'b').exams()
    s.save_exam({**data(),'name':'Changed'})
    assert len(s.exams())==1 and s.get_exam('demo').name=='Changed'
    assert s.backup.exists()

def test_bad_primary_recovers_valid_backup(tmp_path):
    s=Store(tmp_path);s.save_exam(data());s.save_exam({**data(),'name':'New'})
    s.path.write_text('bad json')
    repaired=Store(tmp_path)
    assert repaired.warning and not repaired.read_only
    assert repaired.get_exam('demo').name=='Exam'
    repaired.save_exam({**data(),'name':'Recovered'})
    assert s.path.with_suffix('.json.unreadable').read_text()=='bad json'
    assert Store(tmp_path).get_exam('demo').name=='Recovered'

def test_both_bad_never_overwritten(tmp_path):
    s=Store(tmp_path);s.folder.mkdir();s.path.write_text('bad');s.backup.write_text('also bad')
    broken=Store(tmp_path)
    assert broken.read_only
    with pytest.raises(ValueError):broken.save_exam(data())
    assert s.path.read_text()=='bad'

def test_future_schema_not_downgraded(tmp_path):
    s=Store(tmp_path);s.save_exam(data());s.save_exam(data())
    raw=json.loads(s.path.read_text());raw['schema']=2;s.path.write_text(json.dumps(raw))
    old=Store(tmp_path);assert old.read_only
    with pytest.raises(ValueError):old.save_exam(data())
    assert json.loads(s.path.read_text())['schema']==2

def test_failure_does_not_change_memory_or_primary(tmp_path,monkeypatch):
    s=Store(tmp_path);s.save_exam(data());old=deepcopy(s.state);original=s.path.read_bytes()
    def fail(*args):raise OSError('disk full')
    monkeypatch.setattr(s,'_atomic',fail)
    with pytest.raises(OSError):s.save_exam({**data(),'name':'lost'})
    assert s.state==old and s.path.read_bytes()==original

def test_settings_validated(tmp_path):
    s=Store(tmp_path)
    for settings in [{'theme':'evil'},{'show_countdown':'true'},{'max_countdowns':9}]:
        with pytest.raises(ValueError):s.save_settings(settings)
    s.save_settings({'theme':'midnight','show_countdown':False})
    assert Store(tmp_path).state['settings']['theme']=='midnight'

def test_history_bounded_and_no_duplicate_session(tmp_path):
    s=Store(tmp_path);s.save_exam(data())
    for _ in range(55):
        session=PracticeSession('demo',[CardInfo(1,1,1)])
        result=session.result();s.add_result(result);s.add_result(result)
    assert len(Store(tmp_path).state['history'])==50
    s.delete_exam('demo')
    assert s.state['exams']==s.state['history']==[]

def test_atomic_leaves_no_temp_files(tmp_path):
    s=Store(tmp_path);s.save_exam(data())
    assert not list(s.folder.glob('*.tmp'))

def test_malformed_scope_fails_cleanly(tmp_path):
    s=Store(tmp_path);s.folder.mkdir()
    bad={**s.state,'exams':[{**data(),'scopes':[None]}]}
    s.path.write_text(json.dumps(bad));loaded=Store(tmp_path)
    assert loaded.read_only


@pytest.mark.parametrize("field,value", [("percent", "<script>"), ("points", float('nan')), ("graded", 101), ("interrupted", "true"), ("total", 0), ("flagged_ids", ["x"]), ("finished_at", "bad")])
def test_corrupt_history_rejected(tmp_path, field, value):
    s=Store(tmp_path);s.save_exam(data())
    result=PracticeSession('demo',[CardInfo(1,1,1)]).result()
    result[field]=value
    with pytest.raises(ValueError):s.add_result(result)
    assert s.state['history']==[]

def test_history_does_not_accept_extra_response_text(tmp_path):
    s=Store(tmp_path);s.save_exam(data())
    result=PracticeSession('demo',[CardInfo(1,1,1)]).result()
    result['responses']={'1':'private text'}
    s.add_result(result)
    assert 'responses' not in s.path.read_text()

def test_inconsistent_breakdown_rejected(tmp_path):
    s=Store(tmp_path)
    result=PracticeSession('demo',[CardInfo(1,1,1)]).result()
    result['breakdown'][0]['total']=2
    with pytest.raises(ValueError):s.add_result(result)

import importlib,json,math
import pytest
from fixtures import SRC
mod=importlib.import_module('atelier_testing.study_clock')

def clock():
    now=[100.0];return mod.StudyClock(now=lambda:now[0]),now

def test_stopwatch_pause_resume_uses_elapsed_time_not_tick_count():
    c,n=clock();c.configure('stopwatch',25);c.start();n[0]+=61.9
    assert c.display()=='01:01';c.pause();n[0]+=300;assert c.display()=='01:01'
    c.start();n[0]+=1.2;assert c.display()=='01:03';c.reset();assert c.display()=='00:00' and not c.running

def test_countdown_catches_up_after_sleep_and_completes_only_once():
    c,n=clock();c.configure('countdown',1);c.start();n[0]+=59.1;assert c.display()=='00:01'
    n[0]+=900;assert c.tick() and not c.running and c.display()=='00:00'
    assert not c.tick();c.start();assert c.display()=='01:00' and c.running

def test_reopen_is_paused_and_never_counts_closed_anki_as_study_time():
    c,n=clock();c.configure('stopwatch',25);c.start();n[0]+=42
    restored=mod.StudyClock(c.snapshot(),now=lambda:999999)
    assert not restored.running and restored.display()=='00:42'

@pytest.mark.parametrize('value',[0,481,True,'25',None,math.nan,math.inf])
def test_invalid_duration_is_rejected(value):
    with pytest.raises(mod.ClockError):mod.StudyClock().configure('countdown',value)

@pytest.mark.parametrize('patch',[{'version':True},{'elapsed':-1},{'elapsed':math.inf},{'elapsed':True},{'mode':'<script>'},{'sound':1},{'pin':'yes'}])
def test_untrusted_saved_state_cannot_start_or_configure_a_clock(patch):
    data=mod.StudyClock().snapshot();data.update(patch)
    with pytest.raises(mod.ClockError):mod.StudyClock(data)

def test_store_preserves_external_edits_and_corrupt_files(tmp_path):
    path=tmp_path/'clock.json';store=mod.ClockStore(path);c=store.read();store.write(c)
    path.write_bytes(b'OWNER EDIT');assert not mod.ClockStore(path).read().running
    with pytest.raises(mod.ClockError):store.write(c)
    assert path.read_bytes()==b'OWNER EDIT'
    damaged=mod.ClockStore(path);damaged.read()
    with pytest.raises(mod.ClockError):damaged.write(c)
    assert path.read_bytes()==b'OWNER EDIT'

def test_two_profile_clocks_and_other_saved_work_are_independent(tmp_path):
    marker=tmp_path/'other-project.json';marker.write_bytes(b'KEEP SAVED WORK')
    one=mod.ClockStore(tmp_path/'clock-one.json');c=one.read();c.configure('stopwatch',30);c.base=99;one.write(c)
    two=mod.ClockStore(tmp_path/'clock-two.json');assert two.read().elapsed()==0
    assert one.read().elapsed()==99 and marker.read_bytes()==b'KEEP SAVED WORK'

def test_clock_routes_remain_native_and_do_not_touch_engines():
    text=(SRC/'integration.py').read_text(encoding='utf8')
    assert 'elif action == "study_clock"' in text and 'self.study_clock.shutdown()' in text
    help=importlib.import_module('atelier_testing.getting_started') if False else (SRC/'getting_started.py').read_text(encoding='utf8')
    assert all(v in help for v in ['.apkg','Image Occlusion','Shuffle between lectures','Study clock','Sync'])

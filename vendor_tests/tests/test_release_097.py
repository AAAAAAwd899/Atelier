"""Release readiness: native API contracts are explicit doubles, not live Qt."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
import hashlib,json,random
import pytest
from PIL import Image,ImageSequence
from addon.answers import remove_answers,save_answers,load_answers
from addon.storage import Store
from addon.core import CardInfo,PracticeSession,Exam
from addon.collection_reader import read_snapshot
from test_release_095 import companion
from test_release_094 import setup_study,result
from test_window_contract import integration,Op
ROOT=Path(__file__).resolve().parents[1]

def test_hidden_native_movie_is_paused_not_rewound(companion,monkeypatch):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show();badge.play('pet')
    rewinds=[];pauses=[]
    monkeypatch.setattr(badge.movie,'stop',lambda:rewinds.append(True))
    monkeypatch.setattr(badge.movie,'setPaused',lambda v:pauses.append(v))
    badge._pause_movie()
    assert pauses==[True] and not rewinds and badge._playing==(1,'pet')
    assert badge._remaining_action_ms==1700
    badge._resume_movie()
    assert pauses==[True,False] and not rewinds and badge.return_timer.running

def test_same_stage_refresh_preserves_pet_and_idle_frame(companion,monkeypatch):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show();badge.play('pet')
    starts=[];monkeypatch.setattr(badge.movie,'start',lambda:starts.append(True))
    badge.configure(1,True)
    assert badge._playing==(1,'pet') and not starts

def test_unchanged_idle_never_restarts_movie(companion,monkeypatch):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show();badge.play('idle')
    starts=[];monkeypatch.setattr(badge.movie,'start',lambda:starts.append(True))
    for _ in range(50):badge.play('idle')
    assert not starts and badge._playing==(1,'idle')

def test_inactive_window_freezes_current_frame(companion,monkeypatch):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show();badge.play('water');badge._frame(14)
    frame=badge._pixmap;app.applicationState=lambda:0;badge._activity(0)
    assert not badge.movie.running and badge._pixmap is frame and badge._playing==(1,'water')
    app.applicationState=lambda:1;badge._activity(1);assert badge.movie.running

def test_corrupt_movie_stays_as_still_without_repeated_loop(companion,monkeypatch):
    m,c,app=companion;badge=m.TinyPip(c,None);badge.show()
    monkeypatch.setattr(badge.movie,'isValid',lambda:False)
    badge.play('water');assert badge._playing is None and badge._pixmap.path.endswith('.png')

def test_remove_answers_keeps_other_exams(tmp_path):
    st=Store(tmp_path);st.save_settings({**st.state['settings'],'remember_answers':True})
    save_answers(st,'a',{'1':'answer a'});save_answers(st,'b',{'2':'answer b'})
    remove_answers(st,{'a'});assert load_answers(st)=={'b':{'2':'answer b'}}
    remove_answers(st,{'b'});assert not (st.folder/'practice_answers.json').exists()

def test_removing_unknown_answers_creates_no_file(tmp_path):
    st=Store(tmp_path);remove_answers(st,{'missing'});assert not st.folder.exists()

def test_exam_deletion_erases_prose_and_cache(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch);r=result();c.store.add_result(r)
    c.store.save_settings({**c.store.state['settings'],'remember_answers':True})
    c.responses={r['id']:{'1':'private'}};save_answers(c.store,r['id'],{'1':'private'})
    c.growth_cache={'exam':{'stage':1}};c.active_exam_id='exam'
    d.bridge('exam-sprout:'+json.dumps({'id':'a','action':'delete_exam','payload':{'id':'exam'}}))
    assert not c.responses and not c.growth_cache and c.active_exam_id==''
    assert not c.store.state['history'] and not c.store.state['exams'] and load_answers(c.store)=={}

def test_focus_late_query_never_overlays_started_reviewer(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch)
    e=c.store.get_exam('exam');snap=read_snapshot(col,e);c.mw.state='review'
    with pytest.raises(ValueError,match='scheduled review started'):d._launch_focus(e,snap,1,{})
    assert c.runner is None

def test_mistake_late_query_rejects_second_runner(integration,monkeypatch):
    c,d,col,_,_=setup_study(integration,monkeypatch);r=result();c.store.add_result(r)
    sent=[];monkeypatch.setattr(d,'send',lambda *a,**kw:sent.append((a,kw)))
    d._review_misses('a',{'id':'exam','result_id':r['id']});op=Op.queued[-1]
    c.runner=SimpleNamespace(force_close=lambda:None)
    # QueryOp's captured transform is called on completion; its guard must fail.
    op.success({1,3})
    assert any('Another card session' in str(v) for v in sent)

@pytest.mark.parametrize('stage',[1,2,3,4])
@pytest.mark.parametrize('action',['idle','pet','water'])
def test_30fps_art_timing_is_exact_and_complete(stage,action):
    folder=ROOT/'addon/web/pip';manifest=json.loads((folder/'asset_manifest.json').read_text())
    for prefix in ['','tiny-']:
        name=f'{prefix}stage{stage}-{action}.webp';path=folder/name
        entry=manifest['assets'][name];durations=[]
        with Image.open(path) as im:
            assert im.n_frames==(180 if action=='idle' else 96)
            assert im.info['loop']==(0 if action=='idle' else 1)
            for frame in ImageSequence.Iterator(im):
                frame.load();durations.append(frame.info['duration'])
            assert set(durations)<={33,34} and sum(durations)==(6000 if action=='idle' else 3200)
            assert sum(durations)==entry['duration_ms']


def test_idle_loop_seam_has_no_pose_jump():
    import numpy as np
    for stage in range(1,5):
        with Image.open(ROOT/f'addon/web/pip/tiny-stage{stage}-idle.webp') as im:
            im.seek(0);first=np.array(im.convert('RGBA')).astype(float)
            im.seek(1);second=np.array(im.convert('RGBA')).astype(float)
            im.seek(im.n_frames-1);last=np.array(im.convert('RGBA')).astype(float)
            seam=np.abs(last-first).mean();normal=np.abs(second-first).mean()
            assert seam<max(1.5,normal*4), (stage,seam,normal)


@pytest.mark.parametrize('measurement', [None, [], [100,100,100], [None,100,100,100],
    [100,100,True,100], [100,100,float('nan'),100], [100,float('inf'),100,100],
    [100,100,'100',100], [100,0,100,100], [100,-1,100,100]])
def test_fit_card_rejects_invalid_template_measurements(integration,monkeypatch,measurement):
    from test_release_096 import exam_runner
    obj=exam_runner(integration,monkeypatch);zoom=[];callbacks=[]
    obj._web=SimpleNamespace(evalWithCallback=lambda script,fn:callbacks.append(fn),
                            zoomFactor=lambda:1.,setZoomFactor=lambda v:zoom.append(v))
    obj._open=True;obj._fit_card();callbacks[0](measurement)
    assert not zoom


def test_fit_card_scales_whole_document_and_ignores_stale_card(integration,monkeypatch):
    from test_release_096 import exam_runner
    obj=exam_runner(integration,monkeypatch);zoom=[];callbacks=[]
    obj._web=SimpleNamespace(evalWithCallback=lambda script,fn:callbacks.append(fn),
                            zoomFactor=lambda:1.,setZoomFactor=lambda v:zoom.append(v))
    obj._open=True;obj._fit_card();callbacks[0]([1000,800,800,600])
    assert zoom==[.7124999999999999] or zoom==[.7125]
    obj._fit_card();obj.session.go(1);callbacks[1]([1000,800,800,600])
    assert len(zoom)==1

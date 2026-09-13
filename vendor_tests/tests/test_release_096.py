"""0.9.6 native contracts (explicit test doubles), artifact provenance, regressions."""
import hashlib,json,random
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image,ImageSequence
from addon.core import CardInfo,PracticeSession,sample_cards
from test_release_094 import load_runner_stub,make_runner,result,setup_study
from test_window_contract import integration
ROOT=Path(__file__).resolve().parents[1]

class Navigator:
    def __init__(self):self.labels=[];self.signals=[];self.visible=False;self.index=-1
    def blockSignals(self,v):self.signals.append(v)
    def clear(self):self.labels=[]
    def addItem(self,v):self.labels.append(v)
    def setCurrentIndex(self,v):self.index=v
    def setVisible(self,v):self.visible=v

def exam_runner(integration,monkeypatch):
    mod=load_runner_stub(monkeypatch,integration);obj=make_runner(mod)
    obj.session=PracticeSession('exam',[CardInfo(i,i,1) for i in range(1,7)],'exam')
    obj.navigator=Navigator();obj.shows=[];obj._show_current=lambda:obj.shows.append(obj.session.index)
    obj.response=SimpleNamespace(toPlainText=lambda:'A retained answer')
    return obj

def test_question_jump_preserves_written_response(integration,monkeypatch):
    obj=exam_runner(integration,monkeypatch);obj._jump(4)
    assert obj.session.index==4 and obj.shows==[4]
    assert obj.session.responses=={1:'A retained answer'}

@pytest.mark.parametrize('index',[-1,6,100,None,'1',1.5])
def test_invalid_question_jump_does_not_move_or_save(integration,monkeypatch,index):
    obj=exam_runner(integration,monkeypatch);obj._jump(index)
    assert obj.session.index==0 and not obj.session.responses and not obj.shows

def test_no_question_jump_after_submission(integration,monkeypatch):
    obj=exam_runner(integration,monkeypatch);obj.session.submit();obj._jump(4)
    assert obj.session.index==0 and obj.session.phase=='grading' and not obj.shows

def test_flagged_question_navigator_and_hidden_grading(integration,monkeypatch):
    obj=exam_runner(integration,monkeypatch);obj.session.flags.add(3);obj.session.index=2;obj._update_navigator()
    assert obj.navigator.labels[2]=='Question 3 · unanswered · bookmarked' and obj.navigator.index==2
    assert obj.navigator.visible and obj.navigator.signals==[True,False]
    obj.session.submit();obj._update_navigator();assert not obj.navigator.visible

def test_old_profile_callback_does_not_leak_answers_to_new_profile(integration,monkeypatch):
    c,d,*_=setup_study(integration,monkeypatch);captured=d.store
    monkeypatch.setattr(d,'valid',lambda:False);c.responses={'new-profile':{'9':'Keep this'}}
    r=result();r['_responses']={'1':'Private old-profile answer'}
    d._runner_finished(r)
    assert c.responses=={'new-profile':{'9':'Keep this'}}
    assert captured.state['history'][-1]['id']==r['id']
    assert 'Private old-profile' not in captured.path.read_text()

def test_failed_optional_answer_write_keeps_score_and_original_ids(integration,monkeypatch):
    import addon.integration as mod
    c,d,*_=setup_study(integration,monkeypatch)
    def fail(*a):raise OSError('simulated optional file failure')
    monkeypatch.setattr(mod,'save_answers',fail)
    monkeypatch.setattr(d,'emit_ui_event',lambda *a:None)
    r=result();r['_responses']={'1':'Not lost in memory'};d._runner_finished(r)
    stored=c.store.state['history'][-1]
    assert len(stored['items'])==3 and stored['id']==r['id']
    assert c.responses[r['id']]=={'1':'Not lost in memory'}

def test_asset_export_tracks_current_live_model_and_all_stages():
    folder=ROOT/'addon/web/pip';m=json.loads((folder/'asset_manifest.json').read_text())
    assert m['scene_sha256']==hashlib.sha256((ROOT/'addon/web/pip-scene.js').read_bytes()).hexdigest()
    assert len(m['assets'])==24
    for name,entry in m['assets'].items():
        assert entry['sha256']==hashlib.sha256((folder/name).read_bytes()).hexdigest()

@pytest.mark.parametrize('stage',[1,2,3,4])
def test_native_art_cache_is_small_and_same_character(stage):
    folder=ROOT/'addon/web/pip'
    for mode in ('idle','pet','water'):
        with Image.open(folder/f'tiny-stage{stage}-{mode}.webp') as im:
            assert im.size==(96,96) and im.n_frames==(180 if mode=='idle' else 96)
            assert im.n_frames*im.width*im.height*4<=7_000_000
    with Image.open(folder/f'stage{stage}.png') as full,Image.open(folder/f'tiny-stage{stage}.png') as tiny:
        expected=full.convert('RGBA').resize((96,96),Image.Resampling.LANCZOS)
        assert expected.tobytes()==tiny.convert('RGBA').tobytes()

@pytest.mark.parametrize('size',[1,2,3,5,10,25,50,75,99,100])
def test_each_supported_sample_size_keeps_unique_cards_and_notes(size):
    pool=[CardInfo(i,i//2,(i%4)+1) for i in range(2,700)]
    s=sample_cards(pool,size,{1:5,2:3,3:2,4:1},rng=random.Random(size))
    assert len(s.cards)==size and len({c.id for c in s.cards})==size
    assert len({c.note_id for c in s.cards})==size
    assert sum(s.counts.values())==size
    if size>=4:assert set(c.owner for c in s.cards)=={1,2,3,4}

def test_no_old_model_geometry_in_installed_implementation():
    web=ROOT/'addon/web';app=(web/'app.js').read_text();native=(ROOT/'addon/companion.py').read_text()
    assert 'es-pip-stages' not in app and '<canvas class="pip-canvas"' in app
    assert 'tiny-stage{self.stage}-{action}.webp' in native and 'BADGE_SIZE' in native
    assert 'QDockWidget' not in native and 'AnkiWebView' not in native
    assert 'QRect(0, 0, 96, 96)' in native

def test_installed_scene_is_local_and_owns_gpu_cleanup():
    code=(ROOT/'addon/web/pip-scene.js').read_text()
    assert 'https://' not in code and 'fetch(' not in code and 'XMLHttpRequest' not in code
    for call in ['deleteVertexArray','deleteBuffer','deleteTexture','deleteFramebuffer','deleteProgram','cancelAnimationFrame']:
        assert call in code

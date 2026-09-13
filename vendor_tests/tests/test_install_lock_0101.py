"""Windows updater regression: QBuffer/QMovie contract doubles, not real Qt.

The asset is read by real Python file I/O. Tests assert that its handle has
closed before passing bytes to the decoder; none claims to execute Windows COM.
"""
import ast
import io
from pathlib import Path
import pytest
from test_release_095 import companion
from test_window_contract import integration

ROOT=Path(__file__).resolve().parents[1]


def visible_badge(companion):
    m,c,app=companion
    badge=m.TinyPip(c,None)
    badge.show()
    return m,badge


@pytest.mark.parametrize('stage',[1,2,3,4])
@pytest.mark.parametrize('action',['idle','pet','water'])
def test_each_animation_uses_exact_asset_bytes_not_an_open_filename(companion,stage,action):
    m,b=visible_badge(companion)
    b.configure(stage, True)
    b.play(action)
    assert b._playing==(stage,action)
    assert b.movie.fileName()==''
    assert b.movie.device() is b._movie_buffer
    assert b._movie_buffer.parent is b.movie
    assert b._movie_buffer.isOpen()
    assert b._movie_buffer.data()==(m.ASSETS/f'tiny-stage{stage}-{action}.webp').read_bytes()
    assert b.movie.format==b'webp'
    assert b.movie.running


def test_real_asset_file_closes_before_decoder_sees_it(companion,monkeypatch):
    m,b=visible_badge(companion)
    original=Path.open;opened=[];started=[]
    def tracked(path,*a,**kw):
        f=original(path,*a,**kw)
        if path.name=='tiny-stage1-idle.webp': opened.append(f)
        return f
    def start():
        assert opened and all(f.closed for f in opened)
        started.append(True)
    monkeypatch.setattr(Path,'open',tracked)
    monkeypatch.setattr(b.movie,'start',start)
    b.play('idle')
    assert started==[True] and all(f.closed for f in opened)


def test_paused_badge_keeps_memory_only_and_resumes_same_device(companion):
    m,b=visible_badge(companion);b.play('idle')
    device=b.movie.device(); calls=len(b.movie.device_calls)
    b._pause_movie();b._resume_movie()
    assert b.movie.device() is device and len(b.movie.device_calls)==calls
    assert b.movie.fileName()=='' and b.movie.running


def test_same_action_does_not_reread_file_on_footer_remount(companion,monkeypatch):
    m,b=visible_badge(companion);b.play('idle')
    def forbidden(*a,**k):raise AssertionError('same animation must stay in memory')
    monkeypatch.setattr(Path,'open',forbidden)
    for _ in range(100):
        b._pause_movie();b.configure(1,True);b.play('idle')
    assert b._playing==(1,'idle')


def test_can_delete_asset_copy_after_read_while_memory_animation_remains(companion,tmp_path,monkeypatch):
    m,b=visible_badge(companion)
    data=(m.ASSETS/'tiny-stage1-idle.webp').read_bytes()
    assets=tmp_path/'exam_sprout'/'web'/'pip';assets.mkdir(parents=True)
    file=assets/'tiny-stage1-idle.webp';file.write_bytes(data)
    monkeypatch.setattr(m,'ASSETS',assets)
    b.play('idle');file.unlink();assets.rmdir()
    assert b.movie.device().data()==data
    assert b.movie.running and b.movie.fileName()==''
    b._pause_movie();b._resume_movie();assert b.movie.running


def test_action_replacement_detaches_before_buffer_clear(companion):
    m,b=visible_badge(companion);b.play('idle')
    buffer=b._movie_buffer;b.play('pet');b.play('water')
    # The stand-in itself rejects setData/close while attached or still open.
    assert b._movie_buffer is buffer
    assert b.movie.device() is buffer
    assert buffer.data()==(m.ASSETS/'tiny-stage1-water.webp').read_bytes()


def test_dispose_releases_bytes_immediately_and_is_idempotent(companion):
    m,b=visible_badge(companion);b.play('pet')
    b.dispose();b.dispose()
    assert b.movie.device() is None and not b.movie.running
    assert b._movie_buffer.data()==b'' and not b._movie_buffer.isOpen()
    assert b._playing is None and not b.return_timer.running and b.deleted
    assert not b._failed_movies


def test_queued_activity_click_and_frame_after_dispose_cannot_reopen_file(companion,monkeypatch):
    m,b=visible_badge(companion);b.play('idle');b.dispose()
    def fail(*a,**k):raise AssertionError('disposed badge performed disk I/O')
    monkeypatch.setattr(Path,'open',fail)
    b._activity(1);b.play('pet');b.configure(4,True);b._frame(1);b._resume_movie()
    assert b.movie.device() is None and b._movie_buffer.data()==b''


@pytest.mark.parametrize('error',[FileNotFoundError('removed during update'),PermissionError('denied'),OSError('I/O failure')])
def test_failed_disk_read_leaves_still_no_timer_no_decode_retry(companion,monkeypatch,error):
    m,b=visible_badge(companion);calls=[];original=Path.open
    def fail(path,*a,**k):
        if path.suffix!='.webp': return original(path,*a,**k)
        calls.append(1);raise error
    monkeypatch.setattr(Path,'open',fail)
    for _ in range(4):b.play('idle')
    assert calls==[1]
    assert b._playing is None and b.movie.device() is None
    assert not b.return_timer.running and not b._movie_buffer.isOpen()
    assert b._movie_buffer.data()==b''
    assert b._pixmap.path.endswith('.png')


@pytest.mark.parametrize('payload',[b'',b'RIFF',b'not a webp image',b'RIFF0000WEBP'+b'x'*(4*1024*1024)], ids=['empty','truncated','not-webp','oversize'])
def test_empty_wrong_or_oversize_payload_never_reaches_decoder(companion,monkeypatch,payload):
    m,b=visible_badge(companion);streams=[]
    def open(*a,**k):
        f=io.BytesIO(payload);streams.append(f);return f
    monkeypatch.setattr(Path,'open',open)
    b.play('idle')
    assert all(f.closed for f in streams)
    assert b._playing is None and b.movie.device() is None
    assert b._movie_buffer.data()==b''


def test_decoder_invalid_releases_buffer_and_does_not_retry(companion,monkeypatch):
    m,b=visible_badge(companion);calls=[]
    monkeypatch.setattr(b.movie,'isValid',lambda:calls.append(1) or False)
    b.play('idle');b.play('idle')
    assert calls==[1] and b._playing is None
    assert b.movie.device() is None and b._movie_buffer.data()==b''


def test_memory_buffer_open_failure_is_contained(companion,monkeypatch):
    m,b=visible_badge(companion)
    monkeypatch.setattr(b._movie_buffer,'open',lambda _:False)
    b.play('idle')
    assert b._playing is None and b.movie.device() is None
    assert b._movie_buffer.data()==b''


def test_decoder_start_failure_cleans_up(companion,monkeypatch):
    m,b=visible_badge(companion)
    def fail():raise RuntimeError('decoder stopped')
    monkeypatch.setattr(b.movie,'start',fail)
    b.play('idle')
    assert b._playing is None and not b.return_timer.running
    assert b.movie.device() is None and b._movie_buffer.data()==b''


def test_stage_change_frees_old_animation_even_while_hidden(companion):
    m,b=visible_badge(companion);b.play('idle');b.hide();b.configure(2,True)
    assert b.movie.device() is None and b._movie_buffer.data()==b''
    b.show();b.play('idle');assert b._playing==(2,'idle')


def test_every_packaged_native_animation_fits_cap():
    files=list((ROOT/'addon/web/pip').glob('tiny-*.webp'))
    assert len(files)==12
    assert all(12<=f.stat().st_size<=4*1024*1024 for f in files)


def test_no_native_animation_filename_constructor_or_setter_in_runtime():
    calls=[]
    for p in (ROOT/'addon').rglob('*.py'):
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n,ast.Call):
                if isinstance(n.func,ast.Attribute):assert n.func.attr!='setFileName'
                if isinstance(n.func,ast.Name) and n.func.id=='QMovie':
                    calls.append(n)
                    assert len(n.args)==1 and isinstance(n.args[0],ast.Name) and n.args[0].id=='self'
    assert len(calls)==1


def test_repair_does_not_modify_anki_installer_or_increase_badge_size():
    src=(ROOT/'addon/companion.py').read_text()
    assert 'deleteAddon' not in src and 'send_to_trash' not in src
    assert 'shutil.rmtree' not in src and 'QDockWidget' not in src
    assert 'setFixedSize(BADGE_SIZE, BADGE_SIZE)' in src

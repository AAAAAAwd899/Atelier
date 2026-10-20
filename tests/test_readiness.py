"""Release hardening: disk failures, stale callbacks, duplicate installs and rollback.

The Anki objects in these tests are explicit mocks, not native runtime evidence.
"""
import importlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from fixtures import core, SRC
from test_release import app, onigiri

life = importlib.import_module('atelier_testing.lifecycle')


def pref(label='Exam 1', ids=('2',)):
    return core.profile_settings({'studies': [{'id':'first','name':label,'date':'2026-10-01','deck_ids':list(ids),'active':True}], 'favorites':['2'], 'surfaces_version':1})

@pytest.mark.parametrize('bad',[b'null',b'[]',b'"lost"',b'42',b'{broken',b'\xff\xfe',b'['*1200 + b']'*1200])
def test_invalid_primary_is_fail_closed(tmp_path,bad):
    s=core.ProfileStore(tmp_path,'profile');s.path.write_bytes(bad)
    s.read();assert s.damaged
    with pytest.raises(core.ValidationError):s.write(pref())
    assert s.path.read_bytes()==bad


def test_atomic_previous_snapshot_and_explicit_restore(tmp_path):
    s=core.ProfileStore(tmp_path,'profile')
    s.write(pref('before')); old=s.path.read_bytes()
    s.write(pref('after')); after=s.path.read_bytes()
    assert s.backup_path.read_bytes()==old
    assert s.restore_previous()['studies'][0]['name']=='before'
    assert s.path.read_bytes()==old
    assert list(tmp_path.glob('*.before-restore-*.json'))[0].read_bytes()==after
    assert not list(tmp_path.glob('*.tmp'))


def test_backup_failure_never_touches_primary(tmp_path,monkeypatch):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref());before=s.path.read_bytes()
    real=s._atomic
    def write(path,raw):
        if path==s.backup_path:raise PermissionError('read only')
        real(path,raw)
    monkeypatch.setattr(s,'_atomic',write)
    with pytest.raises(PermissionError):s.write(pref('Changed'))
    assert s.path.read_bytes()==before


def test_primary_replace_failure_leaves_old_primary_and_backup(tmp_path,monkeypatch):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref());before=s.path.read_bytes()
    replace=core.os.replace
    def fail(src,dest):
        if Path(dest)==s.path:raise OSError('simulated replace failure')
        return replace(src,dest)
    monkeypatch.setattr(core.os,'replace',fail)
    with pytest.raises(OSError):s.write(pref('Changed'))
    assert s.path.read_bytes()==before and s.backup_path.read_bytes()==before
    assert not list(tmp_path.glob('.atelier-*.tmp'))


def test_external_corruption_after_read_is_not_overwritten(tmp_path):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref());s.read()
    s.path.write_bytes(b'{ damaged externally')
    with pytest.raises(core.ValidationError):s.write(pref('Changed'))
    assert s.path.read_bytes()==b'{ damaged externally'


def test_missing_primary_does_not_clobber_surviving_backup(tmp_path):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref());s.write(pref('next'));s.path.unlink()
    s.read();assert s.damaged
    with pytest.raises(core.ValidationError):s.write(pref('empty'))
    assert s.restore_previous()['studies'][0]['name']=='Exam 1'


def test_broken_backup_recovery_changes_nothing(tmp_path):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref());before=s.path.read_bytes()
    s.backup_path.write_text('null')
    with pytest.raises(core.ValidationError):s.restore_previous()
    assert s.path.read_bytes()==before and not list(tmp_path.glob('*.before-restore-*.json'))


def test_duplicate_noop_write_keeps_useful_previous_snapshot(tmp_path):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref('before'));s.write(pref('after'))
    backup=s.backup_path.read_bytes();s.write(pref('after'))
    assert s.backup_path.read_bytes()==backup


def test_corrupt_primary_recovery_preserves_damaged_bytes(tmp_path):
    s=core.ProfileStore(tmp_path,'profile');s.write(pref());s.write(pref('next'))
    s.path.write_bytes(b'not json');s.read();assert s.damaged
    s.restore_previous();assert not s.damaged
    assert list(tmp_path.glob('*.before-restore-*.json'))[0].read_bytes()==b'not json'


def test_profiles_isolated_and_unicode_roundtrip(tmp_path):
    a=core.ProfileStore(tmp_path,'C:/Anki/学习');b=core.ProfileStore(tmp_path,'C:/Anki/Other')
    a.write(pref('心脏 🫀'));b.write(pref('Other'))
    assert a.path!=b.path and a.read()['studies'][0]['name']=='心脏 🫀'
    assert b.read()['studies'][0]['name']=='Other'

@pytest.mark.parametrize('ids',[['1','2'],['2','1','2'],['1']])
def test_parent_child_equivalent_duplicates_rejected_at_save(ids):
    catalog={'1':{'name':'Course'},'2':{'name':'Course::Lecture'}}
    existing=pref(ids=('1',))
    another={'id':'second','name':'Another label','deck_ids':ids,'active':True}
    with pytest.raises(core.ValidationError,match='already an active exam'):
        core.upsert_study(existing,another,catalog)


def test_missing_new_study_decks_rejected_without_mutation():
    original=pref();raw=json.dumps(original)
    with pytest.raises(core.ValidationError):core.upsert_study(original,{'id':'new','name':'New','deck_ids':['999']},{'2':{'name':'Lecture'}})
    assert json.dumps(original)==raw


def test_stored_overlap_is_finished_not_deleted():
    p=pref(ids=('1','2'));p['studies'].append({'id':'second','name':'Keep my name','deck_ids':['1'],'active':True,'date':'2026-11-01'})
    out=core.canonical_profile(p,{'1':{'name':'Course'},'2':{'name':'Course::Lecture'}})
    assert len(out['studies'])==2 and sum(s['active'] for s in out['studies'])==1
    assert out['studies'][1]['name']=='Keep my name' and out['studies'][1]['date']=='2026-11-01'


def manager_for(root, entries):
    return NS(all_addon_meta=lambda:entries,addonsFolder=lambda p=None:str(root/p) if p else str(root))

@pytest.mark.parametrize('name,enabled,manifest,expected',[
    ('123456',True,{'package':'daedalus_atelier'},['123456']),
    ('123456',False,{'package':'daedalus_atelier'},[]),
    ('similar',True,{'package':'not_atelier'},[]),
    ('daedalus_atelier',True,{'package':'daedalus_atelier'},[]),
])
def test_duplicate_installation_identity(tmp_path,name,enabled,manifest,expected):
    d=tmp_path/name;d.mkdir();(d/'manifest.json').write_text(json.dumps(manifest));(d/'__init__.py').touch()
    manager=manager_for(tmp_path,[NS(dir_name=name,enabled=enabled)])
    assert life.check_duplicates(manager,'daedalus_atelier')==expected


def test_duplicate_paths_do_not_escape_addons_directory(tmp_path):
    m=manager_for(tmp_path,[NS(dir_name='../../outside',enabled=True)])
    assert life.check_duplicates(m,'daedalus_atelier')==[]


def test_registration_removes_only_own_hooks():
    foreign=lambda:None;ours=lambda:None;hooks=[foreign]
    r=life.Registration();r.hook(hooks,ours);r.rollback();r.rollback()
    assert hooks==[foreign]


def test_cleanup_continues_after_foreign_failure():
    events=[];r=life.Registration();r.cleanup(lambda:events.append('released'))
    r.cleanup(lambda:(_ for _ in ()).throw(RuntimeError('gone')));r.rollback()
    assert events==['released']


class QueuedOp:
    pending=[]
    def __init__(self,parent=None,op=None,success=None,*a):self.op=op;self.ok=success;self.err=None
    def success(self,f):self.ok=f;return self
    def failure(self,f):self.err=f;return self
    def run_in_background(self):self.pending.append(self)
    def finish(self,col):
        try:result=self.op(col)
        except Exception as exc:
            if self.err:self.err(exc)
            else:raise
        else:
            if self.ok:self.ok(result)


def queue_ops(app,monkeypatch):
    a,mw,*_=app;mod=importlib.import_module('atelier_testing.integration')
    QueuedOp.pending=[];monkeypatch.setattr(mod,'CollectionOp',QueuedOp)
    return a,mw


def test_double_study_start_is_not_queued(app,monkeypatch):
    a,mw=queue_ops(app,monkeypatch);a.dispatch('test','r1','study_now',{'id':'2'})
    with pytest.raises(core.ValidationError):a.dispatch('test','r2','study_now',{'id':'3'})
    assert len(QueuedOp.pending)==1;QueuedOp.pending[0].finish(mw.col);assert not a.busy


def test_stale_study_does_not_select_in_another_collection(app,monkeypatch):
    a,mw=queue_ops(app,monkeypatch);original=mw.col
    a.dispatch('test','r1','study_now',{'id':'2'});a.nonce='other';mw.col=NS()
    QueuedOp.pending[0].finish(original)
    assert not app[2] and 'profile or screen changed' in app[4][-1]['error']


def test_late_callback_does_not_release_new_busy_lock(app,monkeypatch):
    a,mw=queue_ops(app,monkeypatch);a.dispatch('test','r1','study_now',{'id':'2'})
    a.nonce='other';new=object();a.operation_ticket=new;a.busy=True
    QueuedOp.pending[0].finish(mw.col)
    assert a.busy and a.operation_ticket is new


def test_failed_queue_setup_releases_busy_lock(app,monkeypatch):
    a,mw=queue_ops(app,monkeypatch)
    def fail(self):raise RuntimeError('queue failed')
    monkeypatch.setattr(QueuedOp,'run_in_background',fail)
    with pytest.raises(RuntimeError):a.dispatch('test','r1','study_now',{'id':'2'})
    assert not a.busy and a.operation_ticket is None


def test_profile_close_releases_wrappers_and_pending_commands(app):
    a,mw,*_=app;a.review_theme=NS(layout_token='old',layout_pending=True)
    a.sprout_link._practice_serial=7
    a.closed()
    assert not a.ownership._wrapped and not a.nonce and a.store is None
    assert a.review_theme.layout_token=='' and not a.review_theme.layout_pending
    assert a.sprout_link._practice_serial==8


def install_host(app,monkeypatch,fail_menu=False):
    a,mw,*_=app;mod=importlib.import_module('atelier_testing.integration')
    hooks=NS(**{k:[] for k in ('webview_will_set_content','webview_did_receive_js_message','state_did_change','state_will_change','profile_will_close','profile_did_open','top_toolbar_did_redraw','reviewer_did_show_question','reviewer_did_show_answer')})
    mod.gui_hooks=hooks;import sys;sys.modules['aqt'].gui_hooks=hooks
    class Guard:
        def __init__(self,*a):pass
    monkeypatch.setattr(mod,'InputShortcutGuard',Guard)
    filters=[];qtapp=NS(installEventFilter=lambda f:filters.append(f),removeEventFilter=lambda f:filters.remove(f))
    monkeypatch.setattr(mod,'QApplication',NS(instance=lambda:qtapp))
    class Action:
        def __init__(self,*a):self.triggered=NS(connect=lambda f:None)
    monkeypatch.setattr(mod,'QAction',Action)
    menus=[]
    class Menu:
        def __init__(self):self.dead=False;self.actions=[]
        def menuAction(self):return self
        def deleteLater(self):self.dead=True
        def addAction(self,a):
            if fail_menu:raise RuntimeError('synthetic menu failure')
            self.actions.append(a)
    def add_menu(name):m=Menu();menus.append(m);return m
    mw.form=NS(menuTools=NS(addMenu=add_menu,removeAction=lambda m:menus.remove(m)))
    mw.addonManager.setWebExports=lambda *a:None;mw.addonManager.setConfigAction=lambda *a:None
    return mod,hooks,filters,menus,mw


def test_install_failure_rolls_back_every_registered_callback(app,monkeypatch):
    mod,hooks,filters,menus,mw=install_host(app,monkeypatch,True)
    marker=lambda:None;hooks.state_did_change.append(marker)
    with pytest.raises(RuntimeError,match='synthetic menu'):mod.install('daedalus_atelier')
    assert hooks.state_did_change==[marker]
    assert all(not v for k,v in vars(hooks).items() if k!='state_did_change')
    assert not filters and not menus and not getattr(mw,'_daedalus_atelier_runtime',None)


def test_install_is_idempotent_in_same_session(app,monkeypatch):
    mod,hooks,filters,menus,mw=install_host(app,monkeypatch)
    monkeypatch.setattr(importlib.import_module('atelier_testing.suite'),'install_engine',lambda owner,registration:None)
    monkeypatch.setattr(importlib.import_module('atelier_testing.authoring'),'install_authoring',lambda owner,registration:None)
    first=mod.install('daedalus_atelier');counts=[len(v) for v in vars(hooks).values()]
    assert mod.install('daedalus_atelier') is first and counts==[len(v) for v in vars(hooks).values()]
    assert len(filters)==2 and len(menus)==1  # input guard + opt-in remote guard
    first._registration.rollback()


def test_required_hook_check_occurs_before_changes(app,monkeypatch):
    mod,hooks,filters,menus,mw=install_host(app,monkeypatch)
    del hooks.reviewer_did_show_answer
    with pytest.raises(life.StartupBlocked):mod.install('daedalus_atelier')
    assert not filters and not menus and all(not x for x in vars(hooks).values())


def test_duplicate_singleton_cannot_register_again(app,monkeypatch):
    mod,hooks,filters,menus,mw=install_host(app,monkeypatch)
    mw._daedalus_atelier_runtime=NS(module='123456')
    with pytest.raises(life.StartupBlocked):mod.install('daedalus_atelier')
    assert all(not x for x in vars(hooks).values())

@pytest.mark.parametrize('nonce,action', [('stale','preference'), ('test','__import__'), ('test','settings')])
def test_untrusted_bridge_shape_cannot_write(app,nonce,action):
    a,mw,*_=app;mod=importlib.import_module('atelier_testing.integration');mw.deckBrowser=mod.DeckBrowser()
    message='atelier:v1:'+nonce+':'+json.dumps({'id':'x','action':action,'data':{'visual_owner':'atelier'}})
    before=json.dumps(app[-1]);result=a.receive((False,None),message,mw.deckBrowser)
    assert result[0] and json.dumps(app[-1])==before


def test_production_wordmarks_have_no_period():
    for filename in ['atelier.js','home.js']:
        text=(SRC/'web'/filename).read_text()
        assert '>atelier.</' not in text
        assert 'atelier<span class="brand-dot">.</span>' not in text


def test_failed_detection_is_not_assumed_to_mean_no_competitor():
    own=importlib.import_module('atelier_testing.ownership')
    cfg=own.resolve_config(core.settings({'visual_owner':'ask'}),{'metadata_checked':False,'onigiri':False,'makeovers':[]})
    assert cfg['visual_owner']=='ask'
    cfg=own.resolve_config(core.settings({'visual_owner':'ask'}),{'metadata_checked':True,'onigiri':False,'makeovers':[]})
    assert cfg['visual_owner']=='atelier'


def test_json_schema_accepts_defaults_and_rejects_bad_enum():
    import jsonschema
    schema=json.loads((SRC/'config.schema.json').read_text());cfg=json.loads((SRC/'config.json').read_text())
    jsonschema.validate(cfg,schema)
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate({**cfg,'visual_owner':'both'},schema)

@pytest.mark.parametrize('theme', core.THEMES)
def test_palette_text_tokens_meet_contrast_threshold(theme):
    palette=json.loads((SRC/'web/palettes.json').read_text())[theme]
    def lum(h):
        c=[int(h[i:i+2],16)/255 for i in (1,3,5)]
        return sum((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(c,[.2126,.7152,.0722]))
    for fg in ['text','muted','quiet']:
        for bg in ['bg','side','panel','raised','hover']:
            a,b=sorted([lum(palette[fg]),lum(palette[bg])])
            assert (b+.05)/(a+.05)>=4.5,(theme,fg,bg)


def test_installer_reproducible_and_free_of_private_files(tmp_path):
    import sys,zipfile,hashlib
    sys.path.insert(0,str(SRC.parent))
    from release_tools import build_installer
    a=tmp_path/'a.ankiaddon';b=tmp_path/'b.ankiaddon'
    build_installer(a);build_installer(b)
    assert a.read_bytes()==b.read_bytes()
    with zipfile.ZipFile(a) as z:
        assert '__init__.py' in z.namelist() and z.testzip() is None
        assert {n for n in z.namelist() if n.startswith('user_files/')}=={'user_files/README.txt'}
        assert not any('__pycache__' in n or n.endswith(('.pyc','.ttf','.woff','.woff2','.otf')) or n=='meta.json' for n in z.namelist())
        assert json.loads(z.read('manifest.json'))['min_point_version']==250905  # documented minimum desktop API requirement


def test_local_update_filesystem_simulation_preserves_preferences(tmp_path):
    """Mirrors the documented preserve-user_files install boundary, not native Qt."""
    import zipfile,sys,shutil
    sys.path.insert(0,str(SRC.parent));from release_tools import build_installer
    folder=tmp_path/'daedalus_atelier';folder.mkdir()
    with zipfile.ZipFile(SRC.parent/'tests/data/baseline-071.ankiaddon') as z:z.extractall(folder)
    local=folder/'user_files/profile-test.json';local.write_text(json.dumps(pref('Keep this exam')))
    backup=folder/'user_files/profile-test.json.bak';backup.write_text('previous data')
    before={p.name:p.read_bytes() for p in (folder/'user_files').iterdir()}
    archive=tmp_path/'new.ankiaddon';build_installer(archive)
    saved=tmp_path/'saved';shutil.move(str(folder/'user_files'),saved);shutil.rmtree(folder);folder.mkdir();shutil.move(saved,folder/'user_files')
    with zipfile.ZipFile(archive) as z:
        for n in z.namelist():
            if n.startswith('user_files/') and (folder/n).exists():continue
            z.extract(n,folder)
    assert before=={p.name:p.read_bytes() for p in (folder/'user_files').iterdir()}
    assert json.loads((folder/'manifest.json').read_text())['human_version']==core.VERSION

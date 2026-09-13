"""Integration-contract regression tests. Qt/Anki are explicit doubles, not native certification."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import json,sys,time,importlib
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ui_harness import Host
from addon import collection,core

@pytest.fixture
def host(tmp_path):
    h=Host(tmp_path,sample=False)
    # Reload this boundary only because each test intentionally replaces aqt with a new double.
    mod=importlib.reload(importlib.import_module('addon.integration'))
    h.workspace.__class__=mod.Workspace
    h.workspace.controller.record=lambda action,e:h.errors.append({'action':action,'error':str(e)})
    yield h
    h.col.close()

def req(h,route,**data):
    msg='workshop:'+json.dumps({'id':str(len(h.requests)+1),'action':route,'payload':data})
    return h.dispatch(msg)

def project(h):return h.store.project({'title':'Native contract project'})
def draft(h,p):return h.store.save_draft({'project_id':p['id'],'front':'Which source supports this claim?','back':'The passage recorded with this note.','deck_id':2})
def commit(h):
    p=project(h);d=draft(h,p);r=req(h,'preflight',draft_ids=[d['id']]);assert not r['error']
    r=req(h,'commit',token=r['data']['token'],approved=True);assert not r['error'];return d,r

def test_source_search_uses_off_collection_job(host):
    p=project(host);host.store.add_source(p['id'],'Source','text',[{'text':'A distinctive source phrase.'}])
    calls=[];original=host.workspace.task
    host.workspace.task=lambda rid,fn,**kwargs:(calls.append(kwargs),original(rid,fn,**kwargs))[-1]
    r=req(host,'source_search',query='distinctive');assert len(r['data']['results'])==1;assert calls[-1]['use_col'] is False

def test_commit_refuses_without_explicit_approval(host):
    p=project(host);d=draft(host,p);r=req(host,'preflight',draft_ids=[d['id']]);token=r['data']['token']
    r=req(host,'commit',token=token,approved=False);assert 'Approve' in r['error'];assert host.col.note_count()==0

def test_commit_token_is_single_use(host):
    p=project(host);d=draft(host,p);r=req(host,'preflight',draft_ids=[d['id']]);token=r['data']['token']
    assert req(host,'commit',token=token,approved=True)['data']['added']==1
    assert 'expired' in req(host,'commit',token=token,approved=True)['error'];assert host.col.note_count()==1

def test_commit_cannot_reuse_other_operation_token(host):
    t=host.workspace.grant('edit',{'other':True});r=req(host,'commit',token=t,approved=True)
    assert r['error'] and host.col.note_count()==0

def test_tokens_are_deep_copied(host):
    data={'list':[{'x':1}]};t=host.workspace.grant('test',data);data['list'][0]['x']=2
    assert host.workspace.consume(t,'test')['list'][0]['x']==1

def test_expired_token_refused(host):
    t=host.workspace.grant('test',{});host.workspace.tokens[t]=('test',{},time.monotonic()-901)
    with pytest.raises(core.ValidationError):host.workspace.consume(t,'test')

def test_profile_change_refuses_queued_write(host):
    called=[];w=host.workspace;w.controller.epoch+=1
    w.task('1',lambda col:called.append(True),write=True)
    assert not called and w.busy is False

def test_busy_write_cannot_double_apply(host):
    host.workspace.busy=True
    with pytest.raises(core.ValidationError):host.workspace.task('1',lambda col:None,write=True)

def test_undo_restores_draft_and_cleans_only_undone_note_links(host):
    d,r=commit(host);assert len(host.store.list('link'))==1
    r=req(host,'undo');assert not r['error'];assert host.col.note_count()==0
    assert host.store.get('draft',d['id'])['status']=='draft';assert not host.store.list('link')
    assert host.workspace.controller.last_undo is None

def test_undo_refuses_when_another_operation_owns_stack(host):
    commit(host);host.col.seed('Another user note','Another answer')
    r=req(host,'undo');assert r['error'] and host.col.note_count()==2

def test_committed_draft_cannot_be_discarded(host):
    d,r=commit(host);r=req(host,'delete_draft',id=d['id'],revision=host.store.get('draft',d['id'])['revision'])
    assert r['error'];assert host.col.note_count()==1

def test_discard_requires_current_revision(host):
    p=project(host);d=draft(host,p);host.store.save_draft({**d,'front':'A changed question?'})
    r=req(host,'delete_draft',id=d['id'],revision=d['revision']);assert r['error'];assert host.store.get('draft',d['id'])

def test_no_external_collection_change_from_local_project(host):
    n=host.col.seed('Existing question','Answer');before=host.col.db.snapshot()
    p=project(host);d=draft(host,p);req(host,'delete_draft',id=d['id'],revision=d['revision'])
    assert before==host.col.db.snapshot()

def test_browser_uses_attribute_not_nonexistent_dialogs_module(host):
    n=host.col.seed('Question','Answer');r=req(host,'native',action='browse',note_id=n.id)
    assert r['data']['opened']=='Browser';assert host.native_events[-1]['kwargs']['search']==('nid:'+str(n.id),)

def test_sprout_scope_copies_valid_existing_notes_only(host):
    p=project(host);n=host.col.seed('One linked question','Answer');host.store.link_note(n.id,p['id'])
    r=req(host,'sprout',project_id=p['id']);assert not r['error'];assert host.clipboard=='nid:'+str(n.id)
    assert host.native_events[-1]['name']=='Exam Sprout';assert 'No exam settings were changed' in r['data']['message']

def test_sprout_missing_is_honest_not_silent_write(host):
    p=project(host);n=host.col.seed('Question','Answer');host.store.link_note(n.id,p['id']);del host._exam_sprout_controller
    r=req(host,'sprout',project_id=p['id']);assert 'not enabled' in r['error'];assert host.clipboard==''

def test_provider_key_is_memory_only(host):
    r=req(host,'set_key');assert r['data']['set'];assert host.workspace.controller.provider.key
    assert 'test-key' not in json.dumps(host.store.summary());req(host,'clear_key');assert not host.workspace.controller.provider.key

def test_occlusion_preserves_unfinished_native_editor(host):
    p=project(host);blob=host.store.save_blob(b'\x89PNG\r\n\x1a\nminimal','png')
    editor=SimpleNamespace(fieldsAreBlank=lambda:False,setup_mask_editor=lambda p:None)
    host.native=lambda *a:SimpleNamespace(editor=editor)
    r=req(host,'occlude',project_id=p['id'],blob=blob)
    assert 'unfinished' in r['error'] and not host.workspace.controller.native_context

def test_native_occlusion_failure_clears_context(host):
    p=project(host);blob=host.store.save_blob(b'\x89PNG\r\n\x1a\nminimal','png')
    def fail(*a,**kw):raise RuntimeError('Native mask editor unavailable')
    editor=SimpleNamespace(fieldsAreBlank=lambda:True,setup_mask_editor=fail,setup_mask_editor_for_new_note=fail)
    host.native=lambda *a:SimpleNamespace(editor=editor,set_deck=lambda d:None)
    r=req(host,'occlude',project_id=p['id'],blob=blob)
    assert r['error'] and not host.workspace.controller.native_context

def test_native_occlusion_provenance_is_one_shot(host):
    from addon.integration import Controller
    p=project(host);s=host.store.add_source(p['id'],'Figure','text',[{'text':'The supporting figure context.'}])['source']
    tag='wsctx_'+core.uid();ctx={'tag':tag,'project_id':p['id'],'source_id':s['id'],'version_id':s['version_id'],'page':1,'quote':'','epoch':1}
    c=host.workspace.controller;c.native_context={tag:ctx}
    n=host.col.seed('Masked figure','Answer',tags=[tag]);Controller.native_added(c,n)
    assert not c.native_context and len(host.store.list('link'))==1
    unrelated=host.col.seed('An unrelated next note','Answer',tags=[tag]);Controller.native_added(c,unrelated)
    assert len(host.store.list('link'))==1

def test_stale_native_provenance_never_crosses_profile(host):
    from addon.integration import Controller
    p=project(host);tag='wsctx_'+core.uid();c=host.workspace.controller;c.native_context={tag:{'epoch':0}}
    n=host.col.seed('Question','Answer',tags=[tag]);Controller.native_added(c,n)
    assert not host.store.list('link')

def test_read_only_plan_exports_never_call_scheduler(host):
    p=project(host);before=host.col.db.snapshot();req(host,'state');req(host,'workload',cards=24)
    assert before==host.col.db.snapshot()

@pytest.mark.parametrize('count,mode,query',[(120,'anki',''),(421,'words','shared idea'),(72,'words','shared idea')])
def test_every_search_result_is_reachable_without_pagination_loss(host,count,mode,query):
    # Populate one batch (test fixture method snapshots are bounded for this loop).
    m=collection.ensure_model(host.col,'question');requests=[]
    from tests.fakes import AddNoteRequest
    for i in range(count):
        n=host.col.new_note(m);n.fields[:2]=[f'Shared idea {i}','The supporting answer.'];requests.append(AddNoteRequest(n,2))
    host.col.add_notes(requests);offset=0;seen=[]
    for _ in range(20):
        result=collection.search_notes(host.col,query,host.store.settings(),mode,limit=60,offset=offset)
        seen.extend(r['id'] for r in result['results'])
        if not result['has_more']:break
        assert result['next_offset']>offset;offset=result['next_offset']
    assert len(seen)==count and len(set(seen))==count

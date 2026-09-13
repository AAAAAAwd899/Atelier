from __future__ import annotations
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,random,sys,zipfile
import pytest
from addon import core,collection,documents,network
from addon.storage import Store
from tests.fakes import FakeCollection,AddNoteRequest,OpChanges

@pytest.fixture
def store(tmp_path):return Store(tmp_path)
@pytest.fixture
def col(tmp_path,monkeypatch):
    import types
    ac=types.ModuleType('anki.collection');ac.AddNoteRequest=AddNoteRequest;ac.OpChanges=OpChanges
    monkeypatch.setitem(sys.modules,'anki.collection',ac)
    c=FakeCollection(tmp_path);yield c;c.close()
@pytest.fixture
def project(store):return store.project({'title':'Principles of deliberate learning','cover':'botanical'})
def draft(store,p,**patch):return store.save_draft({'project_id':p['id'],'front':'What does provenance preserve?','back':'The origin and context of a claim.','kind':'question','deck_id':2,**patch})
def source(store,p,body='Provenance preserves the origin and context of a claim.',**patch):return store.add_source(p['id'],'Working from sources','text',[{'text':body}],**patch)['source']

@pytest.mark.parametrize('v',[True,False,None,1.2,'nan','inf',-1,1001,'',[],{}])
def test_bad_integer(v):
    with pytest.raises(core.ValidationError):core.integer(v,1,1000,'Count')
@pytest.mark.parametrize('v',[1,'1',500,'500',1000,1.0])
def test_integer_valid(v):assert core.integer(v,1,1000,'Count')==int(v)
@pytest.mark.parametrize('raw',['../x','x'*32,'../'+'a'*32,'a'*31,'a'*33,None,True,''])
def test_ids_reject(raw):
    with pytest.raises(core.ValidationError):core.identifier(raw)
@pytest.mark.parametrize('raw',['a b','a"b','x<y','wsd_fake','',None])
def test_tags_reject(raw):
    with pytest.raises(core.ValidationError):core.tags([raw])
def test_plain_and_escape():
    assert core.plain('<p>A &amp; B</p><script>window.attack()</script><img alt="leaf">')=='A & B\n leaf'
    assert '<script' not in core.escaped_field('<script>alert(1)</script>')
    assert core.normalized('  A<br>B ')==core.normalized('a b')
@pytest.mark.parametrize('front,n', [('{{c1::a}}',1),('{{c1::a}} {{c1::b}}',1),('{{c1::a}} {{c2::b::hint}}',2),('no cloze',0)])
def test_cloze_counts(front,n):assert len(core.clozes(front))==n
@pytest.mark.parametrize('front',['{{c0::x}}','{{c100::x}}','{{c1::x}','{{c1::a {{c2::b}}}}'])
def test_invalid_cloze(front):assert any(x['severity']=='error' for x in core.lint_card(front,'','cloze'))
def test_quote_is_support_not_semantics():
    assert core.quote_status('A   sound\nquestion','A sound question tests one idea.')
    assert not core.quote_status('A safe medication','The medication is unsafe.')
    assert not core.quote_status('','text')
def test_diff_insertion_preserves_alignment():
    d=core.diff_pages([{'text':x} for x in ['a','b','c']],[{'text':x} for x in ['intro','a','b','c']])
    assert d['unchanged']=={1:2,2:3,3:4};assert not d['changed'];assert d['added']==[1]
def test_diff_changed_removed():
    d=core.diff_pages([{'text':x} for x in ['a','b','c']],[{'text':x} for x in ['a','B revised']])
    assert d['changed'][0]['old_page']==2;assert d['removed']==[3]
def test_rank_discloses_matching():
    r=core.rank_matches('source context',[{'id':1,'text':'Source context'},{'id':2,'text':'A different word'}])
    assert r[0]['exact'] and r[0]['match']==1
    assert 'Exact wording' in r[0]['why']
def test_workload_not_schedule():assert core.workload(30,15,30)['introduction_days']==2

def test_store_roundtrip_optimistic(store,project):
    p=store.project({**project,'title':'Updated'});assert p['revision']==2
    with pytest.raises(core.ConflictError):store.project({**project,'title':'Stale'})
    assert store.get('project',project['id'])['title']=='Updated'
def test_store_does_not_reset_newer_schema(tmp_path):
    s=Store(tmp_path)
    with s.connection() as db:db.execute('PRAGMA user_version=999')
    with pytest.raises(core.ValidationError):Store(tmp_path)
    with s.connection() as db:assert db.execute('PRAGMA user_version').fetchone()[0]==999

def test_profiles_isolated(tmp_path):
    a=Store(tmp_path/'a');b=Store(tmp_path/'b');p=a.project({'title':'Private A'});assert b.list('project')==[]
    assert a.db_path!=b.db_path
@pytest.mark.parametrize('name',['../../collection.anki2','x.png','a'*64+'.exe','/etc/passwd'])
def test_blob_paths(store,name):
    with pytest.raises(core.ValidationError):store.blob_path(name)
def test_blob_content_addressed_closes_files(store):
    name=store.save_blob(b'hello','txt');assert store.save_blob(b'hello','txt')==name
    assert store.blob_path(name).read_bytes()==b'hello'
    store.blob_path(name).rename(store.blobs/'other.txt')
def test_blob_symlink_cannot_escape(store,tmp_path,monkeypatch):
    out=tmp_path/'outside';out.write_text('private');name='a'*64+'.txt';candidate=store.blobs/name
    try:
        candidate.symlink_to(out)
    except OSError as error:
        # Windows without Developer Mode cannot create an unprivileged symlink.
        # Exercise the same resolved-path boundary without skipping the check.
        if getattr(error,'winerror',None)!=1314:raise
        original=Path.resolve
        monkeypatch.setattr(Path,'resolve',lambda self,*a,**k:out if self==candidate else original(self,*a,**k))
    with pytest.raises(core.ValidationError):store.blob_path(name)
def test_source_versions_no_false_duplicate(store,project):
    s=source(store,project);r=store.add_source(project['id'],s['title'],'text',[{'text':'Provenance preserves the origin and context of a claim.'}],source_id=s['id']);assert r['unchanged']
    r=store.add_source(project['id'],s['title'],'text',[{'text':'New edition.'}],source_id=s['id']);assert not r['unchanged'];assert len(store.list('version'))==2

def test_source_link_and_affected_change(store,project,col):
    s=source(store,project);n=col.seed('Question','Answer');store.link_note(n.id,project['id'],s['id'],s['version_id'],1,'Provenance')
    source(store,project,'A revised interpretation.',source_id=s['id'])
    diff=documents.compare_source(store,s['id']);assert len(diff['affected'])==1

def test_draft_provenance_scope(store,project):
    s=source(store,project);p2=store.project({'title':'Elsewhere'})
    with pytest.raises(core.ValidationError):draft(store,p2,source_id=s['id'],version_id=s['version_id'])
def test_draft_saves_incomplete_not_commit(store,project,col):
    d=draft(store,project,front='',back='')
    with pytest.raises(core.ValidationError):collection.preflight(col,store,[d['id']])
def test_ai_must_be_reviewed(store,project,col):
    d=draft(store,project,origin='ai',verified=False)
    with pytest.raises(core.ValidationError):collection.preflight(col,store,[d['id']])
    d=store.save_draft({**d,'verified':True,'review_confirm':True});assert collection.preflight(col,store,[d['id']])
    d=store.save_draft({**d,'back':'Changed'});assert not d['verified']

def test_source_context_portable_escaped(store,project):
    s=source(store,project,'Safe text');d=draft(store,project,source_id=s['id'],version_id=s['version_id'],quote='<script>attack()</script>')
    html=collection.source_html(store,d);assert '&lt;script&gt;' in html;assert 'file:' not in html;assert 'version 1' in html

def test_commit_uses_native_atomic_batch_no_existing_schedules(store,project,col):
    old=col.seed('Already learned','Original');col.db.conn.execute('UPDATE cards SET queue=2,type=2,ivl=45,reps=20,lapses=2 WHERE nid=?',(old.id,))
    before=col.db.all('SELECT * FROM cards WHERE nid=?',old.id);d=draft(store,project)
    preview=collection.preflight(col,store,[d['id']]);result=collection.commit(col,store,preview,set())
    assert result.data['added']==1 and col.note_count()==2
    assert col.db.all('SELECT * FROM cards WHERE nid=?',old.id)==before
    assert col.db.all('SELECT * FROM revlog')==[]
    assert store.get('draft',d['id'])['status']=='committed';assert col.writes[-1]==('add_notes',1)
    n=col.get_note(result.data['note_ids'][0]);assert n['Front']==d['front'];assert 'wsp_'+project['id'] in n.tags

def test_commit_revalidates_revision(store,project,col):
    d=draft(store,project);p=collection.preflight(col,store,[d['id']]);store.save_draft({**d,'back':'Different answer'})
    with pytest.raises(core.ConflictError):collection.commit(col,store,p,set())
    assert col.note_count()==0

def test_commit_explicit_duplicates(store,project,col):
    col.seed('What does provenance preserve?','Old answer');d=draft(store,project);p=collection.preflight(col,store,[d['id']]);assert p['items'][0]['exact_duplicates']
    with pytest.raises(core.ValidationError):collection.commit(col,store,p,set())
    r=collection.commit(col,store,p,{d['id']});assert r.data['added']==1

def test_commit_stale_profile_zero_writes(store,project,col):
    d=draft(store,project);p=collection.preflight(col,store,[d['id']])
    with pytest.raises(core.ValidationError):collection.commit(col,store,p,set(),alive=lambda:False)
    assert not col.writes

def test_marker_reconciles_interrupted_bookkeeping(store,project,col):
    d=draft(store,project);n=col.seed(d['front'],d['back'],tags=['wsd_'+d['id']]);p=collection.preflight(col,store,[d['id']]);r=collection.commit(col,store,p,set())
    assert r.data['added']==0 and r.data['reconciled']==1 and col.note_count()==1

def test_cloze_card_count(store,project,col):
    d=draft(store,project,kind='cloze',front='A {{c1::source}} preserves {{c2::context}}.',back='')
    p=collection.preflight(col,store,[d['id']]);assert p['total_cards']==2
    r=collection.commit(col,store,p,set());assert len(col.card_ids_of_note(r.data['note_ids'][0]))==2

def test_edit_preserves_cards_and_undo(store,project,col):
    n=col.seed('Question','Old answer');before=col.db.all('SELECT * FROM cards');data=collection.note_data(col,n.id,store.settings())
    p=collection.edit_preview(col,store,n.id,{'Back':'New answer'},data['fingerprint']);collection.apply_edit(col,store,p)
    assert col.get_note(n.id)['Back']=='New answer' and col.db.all('SELECT * FROM cards')==before
    col.undo();assert col.get_note(n.id)['Back']=='Old answer'

def test_edit_stale_no_overwrite(store,col):
    n=col.seed('Question','Original');data=collection.note_data(col,n.id,store.settings());n['Back']='Elsewhere';col.update_note(n)
    with pytest.raises(core.ConflictError):collection.edit_preview(col,store,n.id,{'Back':'Wrong overwrite'},data['fingerprint'])

@pytest.mark.parametrize('tag',['AnkiHub','AnkiHub::protected','AnkiCollab'])
def test_managed_notes_protected(store,col,tag):
    n=col.seed('Managed','Value',tags=[tag]);data=collection.note_data(col,n.id,store.settings())
    with pytest.raises(core.ValidationError):collection.edit_preview(col,store,n.id,{'Back':'Edit'},data['fingerprint'])

def test_cloze_structure_protected(store,col):
    model=collection.ensure_model(col,'cloze');n=col.seed('{{c1::Fact}}','',model);data=collection.note_data(col,n.id,store.settings())
    with pytest.raises(core.ValidationError):collection.edit_preview(col,store,n.id,{'Front':'{{c2::Fact}}'},data['fingerprint'])

def test_batch_all_stale_rejected(store,col):
    a=col.seed('A','old value');b=col.seed('B','old value');p=collection.batch_preview(col,store,{'note_ids':[a.id,b.id],'operation':'replace','find':'old','replace':'new','field':'Back'})
    b['Back']='other';col.update_note(b)
    with pytest.raises(core.ConflictError):collection.apply_batch(col,store,p)
    assert col.get_note(a.id)['Back']=='old value'

def test_batch_tags_are_native_single_write(store,col):
    ns=[col.seed('Question '+str(i),'Answer') for i in range(3)];p=collection.batch_preview(col,store,{'note_ids':[n.id for n in ns],'operation':'add_tag','find':'reviewed'})
    result=collection.apply_batch(col,store,p);assert result.data['updated']==3;assert col.writes[-1]==('update_notes',3)
    assert all('reviewed' in col.get_note(n.id).tags for n in ns)

def test_repair_no_collection_write(store,project,col):
    n=col.seed('Need attention','Answer');before=col.snapshot();a=store.flag(n.id,project_id=project['id']);b=store.flag(n.id,project_id=project['id']);assert a['id']==b['id']
    store.resolve(a['id'],'resolved');assert col.snapshot()==before

def test_media_reuse_references(store,col,tmp_path):
    p=Path(col.media.dir())/'leaf.png';p.write_bytes(b'not decoded for filename test')
    n=col.seed('Leaf','<img src="leaf.png">');assert collection.media_references(col,'leaf.png')['note_ids']==[n.id]
    assert collection.media_catalog(col,'leaf')['total']==1

def test_text_document_and_html_script_exclusion(store,project,tmp_path):
    f=tmp_path/'passage.html';f.write_text('<h1>Source</h1><script>bad()</script><p>Useful text.</p>')
    s=documents.capture_file(store,project['id'],str(f))['source'];v=store.get('version',s['version_id']);assert 'bad' not in v['pages'][0]['text'];assert 'Useful text' in v['pages'][0]['text']

def test_pdf_import_real_extraction(store,project,tmp_path):
    from reportlab.pdfgen import canvas
    f=tmp_path/'Source Guide.pdf';c=canvas.Canvas(str(f));c.drawString(72,720,'Source evidence and careful questions');c.showPage();c.drawString(72,720,'A revised question preserves original context.');c.save()
    s=documents.capture_file(store,project['id'],str(f))['source'];v=store.get('version',s['version_id']);assert s['page_count']==2 and 'careful questions' in v['pages'][0]['text']
    r=documents.render_page(store,v['id'],1);assert r['text'] and (r.get('visual_unavailable') or r.get('image'))

def test_docx_text_import(store,project,tmp_path):
    f=tmp_path/'source.docx'
    with zipfile.ZipFile(f,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Original paragraph.</w:t></w:r></w:p></w:body></w:document>')
    s=documents.capture_file(store,project['id'],str(f))['source'];assert 'Original paragraph.' in store.get('version',s['version_id'])['pages'][0]['text']

@pytest.mark.parametrize('raw',[b'<!DOCTYPE a [<!ENTITY x "x">]><a/>',b'<!ENTITY x "something">'])
def test_xml_entity_rejected(raw):
    with pytest.raises(core.ValidationError):documents._xml(raw)

def test_archive_roundtrip_detaches_foreign_note_ids(store,project,col,tmp_path):
    s=source(store,project);d=draft(store,project,source_id=s['id'],version_id=s['version_id'],deck_id=3)
    r=collection.commit(col,store,collection.preflight(col,store,[d['id']]),set());path=tmp_path/'library.wslibrary';documents.export_workspace(store,path)
    target=Store(tmp_path/'target');result=documents.import_workspace(target,path);assert result['projects']==1 and result['detached_links']==1
    imported=target.list('draft')[0];assert imported['status']=='draft' and imported['deck_id']==1 and 'note_id' not in imported
    assert target.list('link')==[] and target.list('project')[0]['id']!=project['id']

@pytest.mark.parametrize('badpath',['../collection.anki2','sources/../../x','config.json','sources/fake.pdf'])
def test_archive_traversal_rejected(store,tmp_path,badpath):
    f=tmp_path/'unsafe.wslibrary'
    with zipfile.ZipFile(f,'w') as z:z.writestr('library.json',json.dumps({'format':'workshop-library-v1','entities':{}}));z.writestr(badpath,'bad')
    with pytest.raises(core.ValidationError):documents.import_workspace(store,f)
    assert not store.list('project')

def test_archive_invalid_records_no_partial_metadata(store,tmp_path):
    f=tmp_path/'invalid.wslibrary';a='a'*32;b='b'*32
    obj={'format':'workshop-library-v1','entities':{'project':[{'id':a,'title':'Valid','cover':'botanical'},{'id':b,'title':'Invalid','cover':'fake'}]}}
    with zipfile.ZipFile(f,'w') as z:z.writestr('library.json',json.dumps(obj))
    with pytest.raises(core.ValidationError):documents.import_workspace(store,f)
    assert store.list('project')==[]

@pytest.mark.parametrize('url',['http://example.com/v1','https://a:b@example.com/v1','https://example.com/v1?key=123','https://192.168.1.1/v1','https://example.com/v1#key','file:///etc/passwd','javascript:alert(1)'])
def test_provider_endpoint_rejected(url):
    with pytest.raises(core.ValidationError):network.endpoint(url)
@pytest.mark.parametrize('url',['https://example.com/v1','http://localhost:8080/v1','http://127.0.0.1:8080/v1','https://127.0.0.1/v1'])
def test_provider_endpoint_allowed(url):assert network.endpoint(url)==url

def test_no_provider_send_without_consent():
    p=network.Provider()
    with pytest.raises(core.ValidationError):p._post({'ai_enabled':True,'ai_endpoint':'https://example.com/v1'},'chat/completions',{},True)

def test_key_memory_clear():
    p=network.Provider();p.set_key('SECRET');p.clear();assert not p.key

def test_ai_quote_checks_and_unapproved(monkeypatch):
    p=network.Provider();monkeypatch.setattr(p,'_post',lambda *a,**k:{'choices':[{'message':{'content':json.dumps({'cards':[{'front':'What stays local?','back':'Sources and drafts','quote':'Sources and drafts stay local.','context':''}]})}}]})
    result=p.drafts({'ai_model':'mock'},'Sources and drafts stay local.',1)
    assert result[0]['supported_quote'] and not result[0]['verified']

def test_ai_invalid_shape_no_commit(monkeypatch):
    p=network.Provider();monkeypatch.setattr(p,'_post',lambda *a,**k:{'choices':[{'message':{'content':'{"commands":["delete"]}'}}]})
    with pytest.raises(core.ValidationError):p.drafts({'ai_model':'mock'},'Source',1)

def test_embed_finite_shape(monkeypatch):
    p=network.Provider();monkeypatch.setattr(p,'_post',lambda *a,**k:{'data':[{'index':0,'embedding':[1.0]*8},{'index':1,'embedding':[float('nan')]*8}]})
    with pytest.raises(core.ValidationError):p.rerank({'embedding_model':'mock'},'Query',[{'text':'Card','id':1}])

def test_production_source_no_scheduler_writes():
    root=Path(__file__).parents[1]/'addon'
    for name in ('collection.py','integration.py'):
        source=(root/name).read_text()
        assert '.sched.' not in source and 'grade_now' not in source and 'answer_card(' not in source
    assert 'import aqt.dialogs' not in (root/'integration.py').read_text()

def test_no_global_pypdf_alias():
    from addon.vendor.pypdf import PdfReader
    assert PdfReader.__module__.startswith('addon.vendor.pypdf')

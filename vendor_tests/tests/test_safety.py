"""Collection-reader integration uses a real SQLite fixture, not an Anki runtime.

This proves adapter query behavior and data immutability on the fixture; it
cannot prove native Qt/add-on compatibility. The live checklist covers that.
"""
import ast
from datetime import datetime,timezone
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import pytest
from addon.collection_reader import read_snapshot
from addon.core import Exam, sample_cards, plan_exam, PracticeSession
from addon.widget import countdown_html
from addon.storage import Store

ROOT=Path(__file__).resolve().parents[1]/'addon'

class DB:
    def __init__(self, conn):self.conn=conn;self.sql=[]
    def all(self, sql, *args):
        self.sql.append(sql)
        assert sql.lstrip().upper().startswith('SELECT')
        return self.conn.execute(sql,args).fetchall()

class CollectionFixture:
    def __init__(self):
        self.conn=sqlite3.connect(':memory:')
        self.conn.executescript('CREATE TABLE cards(id integer,nid integer,did integer,odid integer,queue integer,type integer,lapses integer); CREATE TABLE revlog(id integer,cid integer,ease integer,time integer,type integer);')
        cards=[(1,1,1,0,0,0,0),(2,2,2,0,2,2,1),(3,3,99,2,2,2,0),(4,4,2,0,-1,2,0),(5,5,2,0,-2,2,0),(6,6,3,0,2,2,0),(7,7,1,0,-3,2,0)]
        self.conn.executemany('INSERT INTO cards VALUES (?,?,?,?,?,?,?)',cards)
        now=int(datetime.now(timezone.utc).timestamp()*1000)
        self.conn.executemany('INSERT INTO revlog VALUES (?,?,?,?,?)',[(now,2,1,10000,1),(now+1,2,3,12000,1),(now+2,3,1,11000,4)])
        self.db=DB(self.conn)
        names=[SimpleNamespace(id=1,name='Pharmacy'),SimpleNamespace(id=2,name='Pharmacy::Cardio'),SimpleNamespace(id=3,name='Other')]
        self.decks=SimpleNamespace(all_names_and_ids=lambda **kwargs:names)
    def find_cards(self,query):
        if query=='is:due':return [2,3,6]
        if query=='tag:exam':return [1,2]
        raise ValueError('Invalid search')
    def fingerprint(self):
        return '\n'.join(self.conn.iterdump())


def exam(query=''):
    return Exam.parse({'name':'Exam','id':'exam','due':'2026-09-20T09:00','scopes':[{'deck_id':1,'name':'Pharmacy'},{'deck_id':2,'name':'Pharmacy::Cardio'}],'query':query})

def test_reader_includes_original_filtered_deck_excludes_suspended_buried():
    c=CollectionFixture();s=read_snapshot(c,exam())
    assert {x.id for x in s.cards}=={1,2,3}
    assert s.stats[1].total==1 and s.stats[2].total==2
    assert s.stats[2].attempts==2 and s.stats[2].again==1
    assert s.stats[1].new==1
    assert s.stats[2].due==2

def test_inclusion_options_do_not_unsuspend_or_unbury():
    c=CollectionFixture();before=c.fingerprint()
    s=read_snapshot(c,exam(),include_suspended=True,include_buried=True)
    assert {x.id for x in s.cards}=={1,2,3,4,5,7}
    assert c.fingerprint()==before

def test_filter_is_applied_inside_scope():
    c=CollectionFixture();s=read_snapshot(c,exam('tag:exam'))
    assert {x.id for x in s.cards}=={1,2}

def test_invalid_query_raises_instead_of_silently_broadening():
    with pytest.raises(ValueError):read_snapshot(CollectionFixture(),exam('bad'))

def test_end_to_end_fixture_collection_never_changes(tmp_path):
    c=CollectionFixture();original=c.fingerprint();e=exam()
    snapshot=read_snapshot(c,e)
    plan_exam(e,snapshot.stats)
    sample=sample_cards(snapshot.cards,100,{1:1,2:1})
    session=PracticeSession(e.id,sample.cards)
    session.save_response('not stored');session.submit()
    while session.phase!='finished':session.grade(1)
    s=Store(tmp_path);s.save_exam(e.to_dict());s.add_result(session.result())
    assert c.fingerprint()==original
    assert 'not stored' not in s.path.read_text()

def test_no_mutating_scheduler_or_collection_calls_in_source():
    prohibited={'answer_card','answerCard','set_due_date','reschedule_cards','reset_cards','set_deck','set_config_bool','update_card','update_cards','add_custom_undo_entry','new_filtered','rebuild_filtered_deck','forget_cards','flush','execute','executemany','executescript'}
    for path in ROOT.glob('*.py'):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                is_file_flush = path.name == 'storage.py' and node.func.attr == 'flush' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'out'
                assert is_file_flush or node.func.attr not in prohibited, (path.name,node.func.attr)

def test_no_reviewer_hooks_or_monkey_patches():
    src=(ROOT/'integration.py').read_text()
    assert 'gui_hooks.reviewer_will_' not in src
    assert src.count('("reviewer_did_answer_card", controller.after_native_answer)') == 1
    assert 'wrap(' not in src
    assert 'isinstance(context, DeckBrowser)' in src
    assert 'if handled[0]' in src

def test_widget_escapes_names_and_is_cached(tmp_path):
    s=Store(tmp_path);e=exam().to_dict();e['name']='<img src=x onerror=alert(1)> & "Test"';e['due']='2099-09-20T09:00';s.save_exam(e)
    html=countdown_html(s)
    assert '<img src=x' not in html and '&lt;img src=x' in html
    assert 'es-countdowns' in html
    s.save_settings({**s.state['settings'],'show_countdown':False})
    assert countdown_html(s)==''

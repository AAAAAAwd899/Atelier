"""Native-option contract tests for shuffled parent study.

Uses real protobuf messages defined from the inspected 26.08.1 field contract
and an explicit in-memory deck manager. This is not the Rust scheduler or Qt.
"""
import copy, hashlib, importlib, json, sys
from types import SimpleNamespace as NS
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from fixtures import SRC, ROOT, core
from test_release import app, onigiri  # retained real integration / explicit host doubles

folder = importlib.import_module('atelier_testing.folder_study')


def protocol():
    fd = descriptor_pb2.FileDescriptorProto(name='shuffle_contract.proto', package='shuffle', syntax='proto3')
    def msg(name, fields):
        m=fd.message_type.add(name=name)
        for name,number,kind,repeated,typename in fields:
            f=m.field.add(name=name,number=number,type=kind,label=3 if repeated else 1)
            if typename:f.type_name='.shuffle.'+typename
        return m
    def scalar(name,number,kind=5):return (name,number,kind,False,None)
    msg('Config',[
        scalar('new_card_gather_priority',34),scalar('new_card_sort_order',32),scalar('review_order',33),
        scalar('new_mix',30),scalar('interday_learning_mix',31),scalar('new_card_insert_order',20),
        scalar('new_per_day',9),scalar('reviews_per_day',10),scalar('desired_retention',37,2),
        scalar('other',255,12),('learn_steps',1,2,True,None),('relearn_steps',2,2,True,None),
        ('fsrs_params_6',6,2,True,None),scalar('bury_new',27,8),scalar('bury_reviews',28,8),
        scalar('bury_interday_learning',29,8),scalar('cap_answer_time_to_secs',24),scalar('maximum_review_interval',16),
    ])
    msg('DeckConfig',[scalar('id',1,3),scalar('name',2,9),scalar('mtime_secs',3,3),scalar('usn',4),('config',5,11,False,'Config')])
    m=msg('Limits',[scalar('review',1),scalar('new',2),scalar('review_today',3),scalar('new_today',4),scalar('review_today_active',5,8),scalar('new_today_active',6,8),scalar('desired_retention',7,2)])
    # proto3 presence for per-deck and today-only values.
    for name in ['review','new','review_today','new_today','desired_retention']:
        one=m.oneof_decl.add(name='_'+name)
        f=next(f for f in m.field if f.name==name);f.proto3_optional=True;f.oneof_index=len(m.oneof_decl)-1
    msg('CurrentDeck',[scalar('name',1,9),scalar('config_id',2,3),('parent_config_ids',3,3,True,None),('limits',4,11,False,'Limits')])
    msg('Row',[('config',1,11,False,'DeckConfig'),scalar('use_count',2)])
    global_fields=[scalar('card_state_customizer',6,9),scalar('new_cards_ignore_review_limit',7,8),scalar('fsrs',8,8),scalar('apply_all_parent_limits',9,8),scalar('fsrs_health_check',11,8)]
    msg('Snapshot',[('all_config',1,11,True,'Row'),('current_deck',2,11,False,'CurrentDeck'),*global_fields])
    msg('Request',[scalar('target_deck_id',1,3),('configs',2,11,True,'DeckConfig'),('removed_config_ids',3,3,True,None),scalar('mode',4),
                   scalar('card_state_customizer',5,9),('limits',6,11,False,'Limits'),scalar('new_cards_ignore_review_limit',7,8),
                   scalar('fsrs',8,8),scalar('apply_all_parent_limits',9,8),scalar('fsrs_reschedule',10,8),scalar('fsrs_health_check',11,8)])
    pool=descriptor_pool.DescriptorPool();pool.Add(fd)
    cls=lambda name:message_factory.GetMessageClass(pool.FindMessageTypeByName('shuffle.'+name))
    api=NS(DeckConfig=NS(Config=NS(NEW_CARD_GATHER_PRIORITY_RANDOM_CARDS=4,NEW_CARD_SORT_ORDER_RANDOM_CARD=4,REVIEW_CARD_ORDER_RANDOM=8)),
           UPDATE_DECK_CONFIGS_MODE_NORMAL=0,UpdateDeckConfigsRequest=cls('Request'),Snapshot=cls('Snapshot'))
    return api
API=protocol()


def snap(use=3):
    s=API.Snapshot();s.current_deck.name='School::Cardiology::Exam 3';s.current_deck.config_id=1
    s.current_deck.parent_config_ids.append(1)
    s.current_deck.limits.new=12;s.current_deck.limits.review=70;s.current_deck.limits.desired_retention=.93
    s.current_deck.limits.review_today=99;s.current_deck.limits.new_today=40
    s.current_deck.limits.review_today_active=False;s.current_deck.limits.new_today_active=True
    r=s.all_config.add();r.use_count=use;r.config.id=1;r.config.name='Shared class options';r.config.mtime_secs=123;r.config.usn=-1
    c=r.config.config;c.new_card_gather_priority=0;c.new_card_sort_order=0;c.review_order=2
    c.learn_steps.extend([1,10]);c.relearn_steps.append(10);c.fsrs_params_6.extend([1,2,3])
    c.new_mix=1;c.interday_learning_mix=2;c.new_card_insert_order=0;c.new_per_day=20;c.reviews_per_day=200
    c.desired_retention=.9;c.bury_new=True;c.bury_reviews=True;c.bury_interday_learning=True;c.cap_answer_time_to_secs=60;c.maximum_review_interval=36500
    c.other=b'{"another_addon":{"preserve":true}}'
    s.card_state_customizer='/* keep custom scheduling exactly */';s.new_cards_ignore_review_limit=True;s.fsrs=True;s.apply_all_parent_limits=True;s.fsrs_health_check=True
    return s


@pytest.mark.parametrize('uses',[2,3,500])
def test_shared_preset_cloned_only_for_parent(uses):
    s=snap(uses);before=s.SerializeToString();r=folder.build_request(s,123,API)
    assert s.SerializeToString()==before
    assert r.target_deck_id==123 and len(r.configs)==1 and r.configs[0].id==0
    assert r.configs[0].name.startswith('Shuffle · Exam 3') and not r.removed_config_ids and r.mode==0
    assert not r.fsrs_reschedule


def test_unique_preset_no_extra_copy():
    s=snap(1);r=folder.build_request(s,123,API)
    assert r.configs[0].id==1 and r.configs[0].name==s.all_config[0].config.name


def test_already_shuffled_has_no_write():
    s=snap()
    c=s.all_config[0].config.config;c.new_card_gather_priority=4;c.new_card_sort_order=4;c.review_order=8
    assert folder.build_request(s,123,API) is None


@pytest.mark.parametrize('field',folder.ORDER_FIELDS)
def test_partial_shuffle_still_configures_all_three_fields(field):
    s=snap();setattr(s.all_config[0].config.config,field,{'new_card_gather_priority':4,'new_card_sort_order':4,'review_order':8}[field])
    c=folder.build_request(s,123,API).configs[0].config
    assert (c.new_card_gather_priority,c.new_card_sort_order,c.review_order)==(4,4,8)


def test_no_other_option_bytes_change_including_unknown_fields():
    s=snap();c=s.all_config[0].config.config
    # Unknown protobuf field 200, varint value 7: retained by CopyFrom/deepcopy.
    c.ParseFromString(c.SerializeToString()+b'\xc0\x0c\x07')
    wanted=copy.deepcopy(c);out=folder.build_request(s,123,API).configs[0].config
    for f in folder.ORDER_FIELDS:setattr(out,f,getattr(wanted,f))
    assert out.SerializeToString()==wanted.SerializeToString()


@pytest.mark.parametrize('key',folder.GLOBAL_FIELDS)
@pytest.mark.parametrize('truth',[False,True])
def test_global_fsrs_limits_custom_scheduling_preserved(key,truth):
    s=snap();setattr(s,key,('kept' if truth else '') if key=='card_state_customizer' else truth)
    r=folder.build_request(s,123,API)
    assert getattr(r,key)==getattr(s,key) and not r.fsrs_reschedule


@pytest.mark.parametrize('ractive,nactive',[(False,False),(True,False),(False,True),(True,True)])
def test_only_active_today_overrides_are_carried(ractive,nactive):
    s=snap();s.current_deck.limits.review_today_active=ractive;s.current_deck.limits.new_today_active=nactive
    limits=folder.build_request(s,123,API).limits
    assert limits.HasField('review_today')==ractive and limits.HasField('new_today')==nactive
    assert limits.new==12 and limits.review==70
    assert limits.desired_retention==s.current_deck.limits.desired_retention


def test_zero_today_limit_stays_explicit_not_absent():
    s=snap();s.current_deck.limits.new_today=0
    r=folder.build_request(s,123,API)
    assert r.limits.HasField('new_today') and r.limits.new_today==0


def test_absent_limits_remain_absent():
    s=snap();s.current_deck.limits.Clear()
    assert not folder.build_request(s,123,API).limits.ListFields()


def test_duplicate_name_uses_new_unique_preset_name():
    s=snap();s.all_config.add().config.name='Shuffle · Exam 3 · 123'
    r=folder.build_request(s,123,API);assert r.configs[0].name.endswith('(2)')


@pytest.mark.parametrize('failure',['missing','duplicate','use_count','shape','missing_global','enum'])
def test_missing_contract_fails_closed(failure):
    s=snap();api=API
    if failure=='missing':s.current_deck.config_id=99
    elif failure=='duplicate':s.all_config.add().CopyFrom(s.all_config[0])
    elif failure=='use_count':s.all_config[0].use_count=0
    elif failure=='shape':s=NS(current_deck=NS(config_id=1))
    elif failure=='missing_global':s=NS(current_deck=s.current_deck,all_config=s.all_config)
    elif failure=='enum':api=NS(DeckConfig=NS(Config=NS()))
    with pytest.raises(core.ValidationError):folder.build_request(s,123,api)


def manager(monkeypatch):
    s=snap();s.current_deck.name='School';actions=[]
    decks={1:{'id':1,'name':'School','conf':1,'dyn':0},2:{'id':2,'name':'School::Lecture 1','conf':1,'dyn':0},3:{'id':3,'name':'School::Lecture 2','conf':1,'dyn':0}}
    class Decks:
        def get(self,n,default=False):return copy.deepcopy(decks.get(n))
        def all_names_and_ids(self):return [NS(id=n,name=d['name']) for n,d in decks.items()]
        def get_deck_configs_for_update(self,n):actions.append(('read',n));return copy.deepcopy(s)
        def update_deck_configs(self,r):actions.append(('options',r));return NS()
        def set_current(self,n):actions.append(('select',n));return NS(changes=NS())
    col=NS(decks=Decks(),add_custom_undo_entry=lambda n:actions.append(('undo',n)) or 12,merge_undo_entries=lambda n:actions.append(('merge',n)) or NS(changes=NS()))
    monkeypatch.setattr(folder,'_native_types',lambda:API)
    return col,s,actions,decks


def test_atomic_native_update_plus_selection_grouped(monkeypatch):
    c,s,actions,decks=manager(monkeypatch);before=copy.deepcopy(decks)
    folder.select_folder(c,'1','School','shuffle')
    assert [a[0] for a in actions]==['read','undo','options','select','merge']
    assert decks==before # no Python dict, card or queue mutation


def test_current_order_has_no_reads_or_changes(monkeypatch):
    c,s,a,d=manager(monkeypatch);folder.select_folder(c,'1','School','current')
    assert a==[('select',1)]


@pytest.mark.parametrize('value,expected,order',[(0,'School','shuffle'),(True,'School','shuffle'),('x','School','shuffle'),(99,'School','shuffle'),(1,'wrong','shuffle'),(2,'School::Lecture 1','shuffle'),(1,None,'shuffle'),(1,'School','bad')])
def test_invalid_stale_or_nonparent_selection_changes_nothing(monkeypatch,value,expected,order):
    c,s,a,d=manager(monkeypatch)
    with pytest.raises(core.ValidationError):folder.select_folder(c,value,expected,order)
    assert not a


def test_filtered_shuffle_rejected_current_allowed(monkeypatch):
    c,s,a,d=manager(monkeypatch);d[1]['dyn']=1
    with pytest.raises(core.ValidationError):folder.select_folder(c,1,'School','shuffle')
    assert not a
    folder.select_folder(c,1,'School','current');assert a==[('select',1)]


@pytest.mark.parametrize('capability',['get_deck_configs_for_update','update_deck_configs','add_custom_undo_entry','merge_undo_entries'])
def test_missing_native_capability_does_not_write(monkeypatch,capability):
    c,s,a,d=manager(monkeypatch)
    setattr(c.decks if capability in ['get_deck_configs_for_update','update_deck_configs'] else c,capability,None)
    with pytest.raises(core.ValidationError):folder.select_folder(c,1,'School','shuffle')
    assert all(x[0]=='read' for x in a)


def test_native_transaction_failure_does_not_start(monkeypatch):
    c,s,a,d=manager(monkeypatch)
    c.decks.update_deck_configs=lambda r:(_ for _ in ()).throw(RuntimeError('native failure'))
    with pytest.raises(core.ValidationError,match='No shuffle settings were applied'):folder.select_folder(c,1,'School','shuffle')
    assert not any(x[0]=='select' for x in a)


def test_late_selection_failure_is_not_misreported_as_rollback(monkeypatch):
    c,s,a,d=manager(monkeypatch)
    c.decks.set_current=lambda r:(_ for _ in ()).throw(RuntimeError('native failure'))
    with pytest.raises(core.ValidationError,match='order was saved'):folder.select_folder(c,1,'School','shuffle')
    assert any(x[0]=='options' for x in a)


def test_current_native_shuffle_stays_noop(monkeypatch):
    c,s,a,d=manager(monkeypatch);cfg=s.all_config[0].config.config;cfg.new_card_gather_priority=4;cfg.new_card_sort_order=4;cfg.review_order=8
    folder.select_folder(c,1,'School','shuffle')
    assert [x[0] for x in a]==['read','select']


def test_folder_dispatch_uses_single_explicit_route(app,monkeypatch):
    a,mw,actions,jobs,replies,cfg=app;called=[]
    monkeypatch.setattr(folder,'select_folder',lambda *v:called.append(v) or NS(changes=NS()))
    a.dispatch('test','r1','study_folder',{'id':'1','expected':'School','order':'shuffle'})
    assert called==[(mw.col,'1','School','shuffle')]
    assert actions==[('overview',)] and replies[-1]['result'] is True and a.profile['last_studied']=='1'


def test_folder_dispatch_failure_keeps_data(app,monkeypatch):
    a,mw,actions,jobs,replies,cfg=app;before=copy.deepcopy(a.profile)
    monkeypatch.setattr(folder,'select_folder',lambda *v:(_ for _ in ()).throw(core.ValidationError('retry me')))
    a.dispatch('test','r1','study_folder',{'id':'1','expected':'School','order':'shuffle'})
    assert a.profile==before and not actions and replies[-1]['error']=='retry me' and not a.busy


def test_no_engine_reviewer_or_remote_bytes_changed():
    baseline=json.loads((ROOT/'baseline-1.0.1.json').read_text())
    for n,h in baseline.items():
        if (n.startswith(('sprout/','workshop/')) and n not in ('workshop/web/app.js','workshop/web/app.css')) or n in ['review_model.py','remote_model.py','remotes.py','web/reviewer.css','web/remote-input.js','web/worlds.css']:
            assert hashlib.sha256((SRC/n).read_bytes()).hexdigest()==h,n


def test_reviewer_uses_actual_home_deck_not_selected_folder(app):
    a,mw,actions,jobs,replies,cfg=app
    module=importlib.import_module('atelier_testing.review_theme')
    theme=module.ReviewTheme(a)
    model={'id':1,'css':'.card {font-family: arial;font-size:20px;text-align:center;color:black;background-color:white}',
           'tmpls':[{'qfmt':'{{Front}}','afmt':'{{FrontSide}}<hr id=answer>{{Back}}'}]}
    # The currently selected parent is deliberately not used by this method.
    first=NS(id=101,current_deck_id=lambda:2,note_type=lambda:model)
    second=NS(id=102,current_deck_id=lambda:3,note_type=lambda:model)
    assert theme.card_info(first,'question')['path']==['School','Lecture A']
    assert theme.card_info(second,'question')['path']==['School','Lecture B']

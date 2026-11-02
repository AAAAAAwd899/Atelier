import copy,pytest
from fixtures import core

CAT={'1':{'name':'Biology','filtered':False},'2':{'name':'Biology::Cells','filtered':False},'3':{'name':'Biology::Plants','filtered':False},'4':{'name':'Chemistry','filtered':False},'5':{'name':'Biology::Cells::Membranes','filtered':False}}

def test_root_and_nested_orders_are_independent_and_nonmutating():
    before=copy.deepcopy(CAT)
    assert core.validate_folder_order(CAT,'0',['4','1'])==('0',['4','1'])
    assert core.validate_folder_order(CAT,'1',['3','2'])==('1',['3','2'])
    assert CAT==before

@pytest.mark.parametrize('order',[['2'],['2','2'],['2','4'],['2','3','5'],['bad','3'],None])
def test_stale_duplicate_cross_parent_or_invalid_orders_rejected(order):
    with pytest.raises(core.ValidationError):core.validate_folder_order(CAT,'1',order)

def test_old_and_malformed_profile_preferences_are_safe():
    assert core.profile_settings({})['folder_order']=={}
    assert core.profile_settings({'folder_order':{'0':['4','1','4','bad'],'1':['3','2'],'bad':['4']}})['folder_order']=={'0':['4','1'],'1':['3','2']}
    assert core.settings({'sort':'custom'})['sort']=='custom'

def test_stale_membership_is_rechecked():
    changed=copy.deepcopy(CAT);changed['6']={'name':'Biology::New lecture','filtered':False}
    with pytest.raises(core.ValidationError):core.validate_folder_order(changed,'1',['2','3'])


def test_order_catalog_follows_actual_visible_tree():
    from types import SimpleNamespace as N
    class Decks:
        def all_names_and_ids(self,**kwargs):return [N(id=int(k),name=v['name']) for k,v in {'1':{'name':'Default'},**CAT}.items()]
        def deck_tree(self):return N(children=[N(deck_id=4,children=[]),N(deck_id=2,children=[])])
    assert set(core.folder_order_catalog(N(decks=Decks())))=={'2','4'}

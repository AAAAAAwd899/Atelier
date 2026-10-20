"""Read-only card-created signal used to order the multi-folder study picker."""
from types import SimpleNamespace as NS
from fixtures import core


def collection(db=None):
    leaf=NS(deck_id=12,name='Exam 2',children=[],new_count=2,learn_count=0,review_count=3,filtered=False)
    parent=NS(deck_id=11,name='Course',children=[leaf],new_count=2,learn_count=0,review_count=3,filtered=False)
    decks=NS(all_names_and_ids=lambda:[NS(id=11,name='Course'),NS(id=12,name='Course::Exam 2')],get_current_id=lambda:11)
    return NS(decks=decks,sched=NS(deck_due_tree=lambda:NS(children=[parent])),studied_today=lambda:'0 cards',db=db)


def test_newest_card_timestamp_is_attached_by_one_read_only_group_query():
    calls=[]
    db=NS(all=lambda query:(calls.append(query) or [(12,1792300000000)]))
    snapshot=core.collection_snapshot(collection(db))
    assert calls==['select did, max(id) from cards group by did']
    assert {n['id']:n['last_card_created'] for n in snapshot['nodes']}=={'11':0,'12':1792300000000}


def test_older_host_without_db_still_loads_picker():
    snapshot=core.collection_snapshot(collection())
    assert [n['last_card_created'] for n in snapshot['nodes']]==[0,0]

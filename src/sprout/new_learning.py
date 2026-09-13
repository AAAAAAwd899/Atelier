"""Only Pip Study may introduce a currently NEW card via Anki's Grade Now API.

Never writes SQL, queues, intervals or revlog directly. Never reschedules learned,
filtered, suspended or buried cards. Independent exam/rehearsal can't reach this.
"""
from __future__ import annotations
from .core import scope_owners


def fingerprint(card):
    return tuple(int(getattr(card,k,0)) for k in ('id','nid','did','odid','type','queue','reps','mod'))


def available(col):
    return callable(getattr(getattr(col,'_backend',None),'grade_now',None))


def introduce_new(col, *, card_id, expected, exam, rating, authorized):
    if authorized is not True: raise ValueError('This is rehearsal. New learning was not enabled.')
    if type(rating) is not int or rating not in (1,2,3,4):raise ValueError('Use Anki’s Again, Hard, Good or Easy rating.')
    if not available(col):raise ValueError('This Anki version does not provide Grade Now. Use normal Study; no progress was changed.')
    card=col.get_card(card_id)
    if fingerprint(card)!=expected:raise ValueError('This card changed in Anki while it was open. No rating was saved; skip or restart the session.')
    if card.type!=0 or card.queue!=0 or card.reps!=0 or card.odid:
        raise ValueError('Only unreviewed, unfiltered, active NEW cards can be introduced here. Learned-card rehearsal never reschedules.')
    names={int(d.id):str(d.name) for d in col.decks.all_names_and_ids(include_filtered=False)}
    owners=scope_owners(exam.scopes,names)
    owner=owners.get(int(card.did))
    if owner is None or not any(s.deck_id==owner and s.weight>0 for s in exam.scopes):
        raise ValueError('The card is no longer in a positive-weight exam scope.')
    if exam.query and card_id not in col.find_cards(f'cid:{card_id} ({exam.query})'):
        raise ValueError('The card no longer matches the exam filter.')
    from anki.scheduler.v3 import CardAnswer
    native=(CardAnswer.AGAIN, CardAnswer.HARD, CardAnswer.GOOD, CardAnswer.EASY)[rating-1]
    # Exact API used by aqt.operations.scheduling.grade_now. Runs inside
    # CollectionOp so Anki's undo/change notifications are preserved.
    return col._backend.grade_now(card_ids=[card_id], rating=native)

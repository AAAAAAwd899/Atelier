"""Read-only group projections shared by Pip, export sorting and progress.

No new plan record, session schema, scheduler hook or second store.
"""
from __future__ import annotations
from hashlib import sha256
from datetime import datetime,timedelta
from .core import canonical_study, fresh_catalog, ValidationError
PREFIX='atelier_group_'

def session_id(sid):
    return PREFIX+sha256(str(sid).encode()).hexdigest()[:24]

def groups(owner,catalog):
    if hasattr(owner,'ensure_store'):owner.ensure_store()
    out=[]
    for s in owner.profile.get('studies',[]):
        if not s.get('active'):continue
        try:
            c=canonical_study(s,catalog,require_present=True)
            ids=c['deck_ids']
            if not ids or len(ids)>100 or any(catalog[i].get('filtered') or int(i)>2**53-1 for i in ids):
                raise ValidationError('This group contains unsupported filtered decks or identifiers. Choose regular lecture decks.')
            out.append({'id':s['id'],'session_id':session_id(s['id']),'name':s['name'],
                        'deck_ids':ids,'available':True,'date':s.get('date','')})
        except (ValueError,KeyError,TypeError) as exc:
            out.append({'id':s['id'],'session_id':session_id(s['id']),'name':s.get('name','Study group'),
                        'deck_ids':[],'available':False,'message':str(exc)})
    return out

def group_exam(owner,col,sid):
    from .sprout.core import Exam,Scope
    cat=fresh_catalog(col);g=next((g for g in groups(owner,cat) if g['id']==sid),None)
    if not g or not g['available']:
        raise ValidationError(g.get('message','This study group is no longer active.') if g else 'This study group is no longer active. Choose another group.')
    # due is a required engine field; independent rehearsal never presents this
    # fallback as a real deadline or saves it as a plan.
    due=g.get('date') or (datetime.now()+timedelta(days=30)).date().isoformat()
    return Exam(id=g['session_id'],name=g['name'][:120],due=due+'T09:00:00',
                topics='Active study group · not a saved exam plan',
                scopes=tuple(Scope(int(i),cat[i]['name']) for i in g['deck_ids']))

def saved_group_exam(owner,col,eid,deck_ids):
    """Recover exact already-sampled work even if its shortcut was removed.
    This function is ONLY called after the original validated draft/result is read.
    It cannot be used to start new sampling from arbitrary IDs.
    """
    from .sprout.core import Exam,Scope
    if not isinstance(eid,str) or not eid.startswith(PREFIX):raise ValidationError('Not a saved group session.')
    ids=list(dict.fromkeys(int(i) for i in deck_ids))
    if not 1<=len(ids)<=100 or any(not 0<i<2**53 for i in ids):raise ValidationError('The saved group scope is invalid.')
    cat=fresh_catalog(col)
    record=next((s for s in owner.profile.get('studies',[]) if session_id(s['id'])==eid),None)
    name=record.get('name','Saved study group') if record else 'Saved study group'
    return Exam(id=eid,name=name[:120],due='2100-01-01T09:00:00',topics='Original saved cards only',
                scopes=tuple(Scope(i,cat.get(str(i),{}).get('name','Former deck')) for i in ids))

def active_deck_ids(profile,catalog):
    roots=set()
    for s in profile.get('studies',[]):
        if s.get('active'):
            for i in s.get('deck_ids',[]):
                if str(i) in catalog:roots.add(catalog[str(i)]['name'])
    def covered(name):
        # Work is proportional to path depth, not the number of active groups.
        while name:
            if name in roots:return True
            name,sep,_=name.rpartition('::')
            if not sep:return False
        return False
    return {i for i,d in catalog.items() if covered(d['name'])}

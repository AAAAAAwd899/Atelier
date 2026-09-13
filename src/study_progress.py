"""Read-only native review-event aggregates. No readiness/retention inference.

Current effective deck membership is used; moving a card changes attribution.
Anki's current day cutoff defines day boundaries, using local civil-time arithmetic
so a daylight-saving day need not be exactly 24 hours.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from .core import ValidationError,fresh_catalog,canonical_study
from .focus_context import active_deck_ids

def read_progress(col,profile,scope='active',days=7,now_ms=None):
    if type(days) is not int or days not in (7,30):raise ValidationError('Choose 7 or 30 study days.')
    cat=fresh_catalog(col)
    if scope=='all':selected=set(cat)
    elif scope=='active':selected=active_deck_ids(profile,cat)
    else:
        s=next((s for s in profile.get('studies',[]) if s['id']==scope and s.get('active')),None)
        if s is None:raise ValidationError('That group is no longer active. Choose another scope.')
        canonical_study(s,cat,require_present=True)
        selected=active_deck_ids({'studies':[s]},cat)
    cutoff=int(col.sched.day_cutoff)
    end=datetime.fromtimestamp(cutoff)
    ends=[int((end-timedelta(days=n)).timestamp()*1000) for n in range(days+1)]
    now_ms=int(datetime.now().timestamp()*1000) if now_ms is None else int(now_ms)
    stop=min(ends[0],now_ms+1)
    bins=[{'label':(end-timedelta(days=n+1)).date().isoformat(),'start':ends[n+1],
           'end':min(ends[n],stop),'reviews':0,'cards':0,'again':0,'minutes':0.0} for n in reversed(range(days))]
    base={'days':days,'scope':scope,'deck_count':len(selected),'daily':bins,'decks':[],
          'reviews':0,'cards':0,'again':0,'minutes':0.0,'days_studied':0,
          'attribution':'Current decks, not historical deck membership. Deleted cards are excluded. Manual rescheduling and independent practice are excluded.'}
    if not selected:return base
    # IDs are validated signed decimal strings from the native deck API, not SQL input.
    ids=','.join(str(int(i)) for i in selected)
    if any(not 0<int(i)<2**63 for i in selected):raise ValidationError('Invalid deck identifiers.')
    effective='case when c.odid>0 then c.odid else c.did end'
    where=f'r.id>=? and r.id<? and r.ease between 1 and 4 and r.type in (0,1,2,3) and ({effective}) in ({ids})'
    agg='count(*),count(distinct r.cid),coalesce(sum(case when r.ease=1 then 1 else 0 end),0),coalesce(sum(max(0,r.time)),0)'
    query=f' from revlog r join cards c on c.id=r.cid where {where}'
    rows=col.db.all('select '+agg+query,ends[-1],stop)
    if rows:
        r,c,a,t=rows[0];base.update(reviews=int(r),cards=int(c),again=int(a),minutes=round(t/60000,1))
    # One grouped query for all daily bars, not one query for every card/day.
    case='case '+ ' '.join(f'when r.id>={int(b["start"])} and r.id<{int(b["end"])} then {i}' for i,b in enumerate(bins))+' else -1 end'
    for idx,r,c,a,t in col.db.all('select '+case+','+agg+query+' group by 1',ends[-1],stop):
        if 0<=idx<len(bins):bins[idx].update(reviews=int(r),cards=int(c),again=int(a),minutes=round(t/60000,1))
    for did,r,c,a,t in col.db.all('select '+effective+','+agg+query+' group by 1 order by count(*) desc limit 200',ends[-1],stop):
        base['decks'].append({'id':str(did),'name':cat.get(str(did),{}).get('name','Former deck'),
                              'reviews':int(r),'cards':int(c),'again':int(a),'minutes':round(t/60000,1)})
    base['days_studied']=sum(b['reviews']>0 for b in bins)
    return base

def export_deck(mw,did):
    from .core import deck_id
    if not getattr(mw,'col',None):raise ValidationError('Open an Anki profile first.')
    did=deck_id(did)
    if did not in fresh_catalog(mw.col):raise ValidationError('That deck is no longer available. Refresh the chooser.')
    # Original exporter owns all format/options/destination prompts. No export
    # runs until its existing explicit Export action is used.
    from aqt.import_export.exporting import ExportDialog
    dialog=ExportDialog(mw,did=int(did))
    return dialog

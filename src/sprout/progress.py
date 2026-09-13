"""Pip grows from study effort across exams, never from a readiness estimate.
One point per unique note per UTC day; incorrect effort still counts. No collection writes.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from .storage import Store


class PipProgress:
    def __init__(self, store):
        self.store=store;self.path=store.folder/'pip_progress.json'
        self.total=0;self.day='';self.seen=set();self.error=''
        if self.path.exists():
            try:
                if self.path.stat().st_size>100_000:raise ValueError('Progress file too large')
                d=json.loads(self.path.read_text(encoding='utf8'))
                if type(d.get('total')) is not int or not 0<=d['total']<=10**9:raise ValueError('Invalid progress')
                values=d.get('seen',[]);day=d.get('day','')
                if not isinstance(values,list) or len(values)>500 or not isinstance(day,str) or len(day)>10:raise ValueError('Invalid progress history')
                self.total=d['total'];self.day=day
                self.seen={int(x) for x in values if type(x)is int and 0<x<2**53}
            except (OSError,ValueError,TypeError):self.error='Pip progress could not be loaded; the file was preserved.'

    def record(self,note_ids,now=None):
        if self.error or self.store.read_only:return
        day=(now or datetime.now(timezone.utc)).date().isoformat()
        if self.day!=day:self.day=day;self.seen=set()
        before=len(self.seen)
        for nid in note_ids:
            if len(self.seen)>=500:break
            if type(nid)is int and 0<nid<2**53:self.seen.add(nid)
        gained=len(self.seen)-before
        if gained:
            self.total+=gained
            Store._atomic(self.path,json.dumps({'total':self.total,'day':self.day,'seen':sorted(self.seen)}).encode())

    def signal(self):
        thresholds=[0,200,600,1600]
        stage=1+sum(self.total>=n for n in thresholds[1:])
        lower=thresholds[stage-1];target=thresholds[stage] if stage<4 else None
        pct=100 if target is None else round(100*(self.total-lower)/(target-lower))
        return {'score':pct,'stage':stage,'label':['Just planted','Taking root','Growing strong','Sturdy little tree'][stage-1],
                'points':self.total,'next':target,'kind':'effort','detail':'Lifetime study effort across exams. Not an exam readiness score.', 'warning':self.error}

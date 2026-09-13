"""Pure exam-session telemetry, confidence, timing and resumable state.
No card scheduling or persistence. A mock timer continues while the app is closed.
"""
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
import math
import time
import re
from .core import PracticeSession, CardInfo, bounded_int, MAX_QUESTIONS, MAX_SESSION_MINUTES

ERROR_TYPES=('none','recall','concept','application','misread','calculation','guess')


class ExamSession(PracticeSession):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.confidence={};self.attempted=set();self.seen=set();self.seconds={};self.answered_at={}
        self.errors={};self.render_errors=set();self.scheduled=set();self.cold=set()
        self.sampling='representative';self.pip_study=False;self.allow_new_learning=False
        self._timing_id=None;self._entered_at=None;self.deadline=time.time()+self.minutes*60 if self.minutes else None
        self._elapsed_before=0.

    def enter(self):
        if self.phase not in ('answering','practice') or self.revealed:return
        self.seen.add(self.current.id)
        if self._timing_id!=self.current.id:
            self.leave();self._timing_id=self.current.id;self._entered_at=time.monotonic()

    def leave(self):
        if self._timing_id is not None and self._entered_at is not None:
            cid=self._timing_id;elapsed=max(0,min(86400,time.monotonic()-self._entered_at))
            self.seconds[cid]=self.seconds.get(cid,0)+elapsed
            self.answered_at[cid]=time.time()
        self._timing_id=None;self._entered_at=None

    def save_response(self,response):
        if self.phase not in ('answering','practice') or self.revealed:return
        super().save_response(response)
        if response.strip():self.attempted.add(self.current.id)

    def mark_attempted(self,value=True):
        if self.phase not in ('answering','practice') or self.revealed:return
        if value:self.attempted.add(self.current.id)
        else:self.attempted.discard(self.current.id)

    def set_confidence(self,value):
        if self.phase not in ('answering','practice') or self.revealed:return
        value=bounded_int(value,0,3,'Confidence')
        self.confidence[self.current.id]=value
        if value:self.attempted.add(self.current.id)

    def set_error(self,value):
        if value not in ERROR_TYPES:raise ValueError('Unknown error category.')
        if self.revealed:self.errors[self.current.id]=value

    def go(self,delta):self.leave();super().go(delta)
    def reveal(self):self.leave();super().reveal()
    def submit(self,timed_out=False):self.leave();super().submit(timed_out)
    def advance(self):self.leave();super().advance()

    def grade(self,value):
        if type(value) not in (int,float) or value not in (0,.5,1):raise ValueError("Use missed, partial or correct.")
        if self.current.id in self.render_errors:raise ValueError('A render failure must remain ungraded.')
        # An exam's unanswered items cannot be credited after seeing the answer.
        if self.kind=='exam' and self.current.id not in self.attempted and value!=0:
            raise ValueError('This item was not marked answered before submission; it receives no credit.')
        if self.kind=='practice':self.attempted.add(self.current.id)
        super().grade(value)

    def result(self,interrupted=False):
        self.leave();out=super().result(interrupted)
        out['sampling']=self.sampling
        out['pip_study']=self.pip_study
        out['elapsed_seconds']+=int(self._elapsed_before)
        for item in out['items']:
            cid=item['card_id']
            item.update(confidence=self.confidence.get(cid,0),attempted=cid in self.attempted,seen=cid in self.seen,
                        seconds=round(self.seconds.get(cid,0),2),answered_at=self.answered_at.get(cid),
                        cold=cid in self.cold,scheduled=cid in self.scheduled,render_error=cid in self.render_errors,
                        error_type=self.errors.get(cid,'none'))
        out['blind_spots']=sum(x['confidence']==3 and x['grade'] is not None and x['grade']<1 for x in out['items'])
        return out

    def serialize(self):
        self.leave()
        return {'version':1,'id':self.id,'exam_id':self.exam_id,'cards':[asdict(c) for c in self.cards],
                'kind':self.kind,'minutes':self.minutes,'started_at':self.started_at,'deadline':self.deadline,
                'phase':self.phase,'index':self.index,'revealed':self.revealed,'timed_out':self.timed_out,
                'responses':self.responses,'grades':self.grades,'flags':list(self.flags),'skipped':list(self.skipped),
                'confidence':self.confidence,'attempted':list(self.attempted),'seen':list(self.seen),
                'seconds':self.seconds,'answered_at':self.answered_at,'errors':self.errors,
                'render_errors':list(self.render_errors),'scheduled':list(self.scheduled),'cold':list(self.cold),
                'sampling':self.sampling,'pip_study':self.pip_study,'allow_new_learning':self.allow_new_learning,
                'elapsed':self._elapsed_before+max(0,(self.ended_clock or time.monotonic())-self.start_clock)}

    @classmethod
    def restore(cls,data):
        if not isinstance(data,dict) or data.get('version')!=1:raise ValueError('Unsupported saved exam.')
        for key in ('id','exam_id'):
            if not isinstance(data.get(key),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',data[key]):raise ValueError('Invalid saved exam ID.')
        raw=data.get('cards')
        if not isinstance(raw,list) or not 1<=len(raw)<=MAX_QUESTIONS:raise ValueError('Invalid saved exam length.')
        cards=[]
        for c in raw:
            if not isinstance(c,dict):raise ValueError('Invalid card record.')
            ids=[bounded_int(c[k],1,2**53-1,'Card ID') for k in ('id','note_id','owner')]
            if any(type(c.get(k,False)) is not bool for k in ('is_new','is_due')):raise ValueError('Invalid card status.')
            cards.append(CardInfo(*ids,c.get('is_new',False),c.get('is_due',False),bounded_int(c.get('lapses',0),0,2**31-1,'Lapses')))
        s=cls(data['exam_id'],cards,data['kind'],data['minutes']);valid={c.id for c in cards}
        def mapping(key,validate):
            d=data.get(key,{})
            if not isinstance(d,dict) or len(d)>MAX_QUESTIONS:raise ValueError('Invalid saved response map.')
            out={}
            for k,v in d.items():
                cid=bounded_int(k,1,2**53-1,'Card ID')
                if cid not in valid or not validate(v):raise ValueError('Saved response is invalid or outside the exam.')
                out[cid]=v
            return out
        for key in ('revealed','timed_out','pip_study','allow_new_learning'):
            if type(data.get(key)) is not bool:raise ValueError('Invalid saved exam option.')
            setattr(s,key,data[key])
        for key in ('flags','skipped','attempted','seen','render_errors','scheduled','cold'):
            values=data.get(key,[])
            if not isinstance(values,list) or any(type(x)is not int or x not in valid for x in values):raise ValueError('Invalid saved question identifiers.')
            setattr(s,key,set(values))
        s.responses=mapping('responses',lambda v:isinstance(v,str) and len(v)<=10000)
        s.grades=mapping('grades',lambda v:type(v)in(int,float) and v in(0,.5,1))
        s.confidence=mapping('confidence',lambda v:type(v)is int and 0<=v<=3)
        s.seconds=mapping('seconds',lambda v:type(v)in(int,float) and math.isfinite(v) and 0<=v<=86400*90)
        s.answered_at=mapping('answered_at',lambda v:type(v)in(int,float) and math.isfinite(v) and 0<v<=time.time()+60)
        s.errors=mapping('errors',lambda v:v in ERROR_TYPES)
        phase=data.get('phase')
        if phase not in ('answering','practice','grading'):raise ValueError('This saved exam is no longer resumable.')
        if (s.kind=='exam' and phase=='practice') or (s.kind=='practice' and phase!='practice'):raise ValueError('Invalid saved exam phase.')
        if phase=='answering' and (s.revealed or s.grades or s.scheduled):raise ValueError('An unsubmitted exam cannot have grades or scheduling writes.')
        if s.scheduled and (not s.pip_study or not s.allow_new_learning):raise ValueError('Invalid scheduling history.')
        s.phase=phase;s.id=data['id'];s.index=bounded_int(data.get('index'),0,len(cards)-1,'Question index')
        s.sampling=data.get('sampling','representative')
        if s.sampling not in ('representative','adaptive'):raise ValueError('Unknown blueprint.')
        stamp=datetime.fromisoformat(data['started_at'])
        if stamp.tzinfo is None or stamp.timestamp()>time.time()+60:raise ValueError('Invalid saved start time.')
        s.started_at=data['started_at'];s.deadline=data.get('deadline')
        elapsed=data.get('elapsed',0)
        if type(elapsed)not in(int,float) or not math.isfinite(elapsed) or not 0<=elapsed<=90*86400:raise ValueError('Invalid saved elapsed time.')
        if s.minutes:
            if type(s.deadline)not in(int,float) or not math.isfinite(s.deadline):raise ValueError('Invalid saved timer.')
            if abs(s.deadline-(stamp.timestamp()+s.minutes*60))>5:raise ValueError('Saved exam deadline disagrees with its duration.')
            if phase=='answering':elapsed=max(elapsed,time.time()-stamp.timestamp())
        elif s.deadline is not None:raise ValueError('Untimed session has a deadline.')
        if phase in ('answering','practice'):
            # remaining_seconds uses monotonic time; carry strict wall time over restart.
            s.start_clock=time.monotonic()-elapsed;s._elapsed_before=0
        else:
            s._elapsed_before=elapsed
            if phase=='grading':s.ended_clock=s.start_clock
        if s.phase=='answering' and s.remaining_seconds()==0:s.submit(timed_out=True)
        return s

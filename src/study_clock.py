"""A voluntary study clock. No Anki, scheduling, network or card dependencies."""
from __future__ import annotations
import json,math,time
from pathlib import Path
from .core import ProfileStore

class ClockError(ValueError):pass

class StudyClock:
    def __init__(self, saved=None, now=time.monotonic):
        self.now=now;self.mode='countdown';self.minutes=25;self.base=0.0
        self.running=False;self.anchor=0.0;self.sound=False;self.pin=False
        if saved is not None:
            if not isinstance(saved,dict) or saved.get('version')!=1 or type(saved.get('version')) is not int:raise ClockError('Unsupported clock settings.')
            self.configure(saved.get('mode'),saved.get('minutes'))
            value=saved.get('elapsed')
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=604800:raise ClockError('Invalid elapsed time.')
            if self.mode=='countdown' and value>self.minutes*60:raise ClockError('Invalid countdown time.')
            for key in ['sound','pin']:
                if type(saved.get(key)) is not bool:raise ClockError('Invalid clock option.')
                setattr(self,key,saved[key])
            self.base=float(value) # Restored clocks are always paused; closed Anki is not study time.

    def configure(self,mode,minutes):
        if mode not in ('countdown','stopwatch'):raise ClockError('Choose Countdown or Stopwatch.')
        if type(minutes) is not int or not 1<=minutes<=480:raise ClockError('Choose 1 to 480 minutes.')
        self.mode=mode;self.minutes=minutes;self.reset()

    def elapsed(self):
        value=self.base+(max(0,self.now()-self.anchor) if self.running else 0)
        return min(value,self.minutes*60 if self.mode=='countdown' else 604800)

    def start(self):
        if self.running:return
        if self.complete:self.reset()
        self.anchor=self.now();self.running=True

    def pause(self):
        self.base=self.elapsed();self.running=False

    def reset(self):self.running=False;self.base=0.0

    @property
    def complete(self):return self.mode=='countdown' and self.elapsed()>=self.minutes*60

    def tick(self):
        finished=self.running and (self.complete or self.elapsed()>=604800)
        if finished:self.pause()
        return finished

    def display(self):
        seconds=max(0,math.ceil(self.minutes*60-self.elapsed()) if self.mode=='countdown' else math.floor(self.elapsed()))
        hours,rest=divmod(seconds,3600);minutes,seconds=divmod(rest,60)
        return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'

    def snapshot(self):
        return {'version':1,'mode':self.mode,'minutes':self.minutes,'elapsed':self.elapsed(),'sound':self.sound,'pin':self.pin}

class ClockStore:
    """Separate profile-scoped file; unreadable or externally changed data is retained."""
    def __init__(self,path:Path):self.path=path;self.original=None;self.blocked=False
    def _raw(self):
        try:
            with self.path.open('rb') as f:raw=f.read(4097)
        except FileNotFoundError:return None
        if len(raw)>4096:raise ClockError('Clock settings are too large.')
        return raw
    def read(self):
        try:
            self.original=self._raw()
            if self.original is None:return StudyClock()
            return StudyClock(json.loads(self.original))
        except (OSError,ValueError,TypeError,RecursionError):
            self.blocked=True;return StudyClock()
    def write(self,clock):
        if self.blocked:raise ClockError('The saved clock could not be read. It has been kept. This clock still works for this visit.')
        try:
            if self._raw()!=self.original:
                self.blocked=True;raise ClockError('Clock settings changed outside Anki and were kept. This clock still works for this visit.')
            raw=(json.dumps(clock.snapshot())+'\n').encode('utf8')
            self.path.parent.mkdir(parents=True,exist_ok=True)
            ProfileStore._atomic(self.path,raw);self.original=raw
        except OSError as exc:raise ClockError('The clock could not save. Timing still works for this visit.') from exc

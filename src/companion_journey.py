"""Voluntary keepsakes from actual Anki review activity; preference writes only."""
from datetime import datetime,timezone
from .core import ValidationError
from .social_models import KEEPSAKES,journey_settings
from .study_progress import read_progress

def status(col,profile):
 saved=journey_settings(profile.get('journey'));stats=read_progress(col,profile,'all',30)
 rewards=[dict(k,collected=k['id'] in saved['earned'],eligible=stats['reviews']>=k['reviews'] and stats['days_studied']>=k['days']) for k in KEEPSAKES]
 return {'saved':saved,'rewards':rewards,'reviews':stats['reviews'],'days_studied':stats['days_studied'],'daily':stats['daily'],'basis':'Your last 30 study days. Every normal answer rating counts equally. Collected keepsakes stay yours.'}

def claim(col,profile,key,now=None):
 current=status(col,profile);reward=next((x for x in current['rewards'] if x['id']==key),None)
 if reward is None:raise ValidationError('Choose an available keepsake.')
 if not reward['collected'] and not reward['eligible']:raise ValidationError('This keepsake is not ready yet. Keep studying at your own pace.')
 saved=current['saved'];saved['earned'].setdefault(key,now or datetime.now(timezone.utc).isoformat());return saved

def change(profile,op,value):
 saved=journey_settings(profile.get('journey'))
 if op=='equip':
  if value and value not in saved['earned']:raise ValidationError('Collect this keepsake before choosing its scene.')
  saved['equipped']=value
 elif op=='reflection':
  if 'journal' not in saved['earned']:raise ValidationError('Collect the journal nook first.')
  if not isinstance(value,str) or len(value)>2000:raise ValidationError('Keep your reflection under 2,000 characters.')
  saved['reflection']=value
 else:raise ValidationError('Choose a companion action.')
 return saved

"""Local shipped-interface preview. Fictional data; no Anki windows or online service."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit,unquote
import sys,json,mimetypes
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from suite_fixtures import home_suite,core
from test_social_115_browser import document as social_document,state as social_state
from bs4 import BeautifulSoup
OUT=ROOT/'output/preview-116';OUT.mkdir(parents=True,exist_ok=True)
RIBBON='<aside style="position:sticky;top:0;z-index:99999;padding:7px 15px;background:#172f35;color:#f2f5ed;font:12px/1.4 Arial">Atelier 1.0.16 · Browser preview · Fictional data, no Anki collection or online service. <a style="color:#c5e6cd;margin-left:15px" href="/">Workspace</a> · <a style="color:#c5e6cd" href="/journey">Companion scenes</a> · <a style="color:#c5e6cd" href="/friends">Sharing</a> · <a style="color:#c5e6cd" href="/friends-sample">Sharing sample</a></aside>'

def document(route):
 if route=='/':
  soup=BeautifulSoup(home_suite('forest',page='library'),'html.parser');soup.title.string='Atelier 1.0.16 · Browser preview · Fictional data'
  tag=soup.find(id='atelier-bootstrap');b=json.loads(tag.string);b['settings'].update(view='outline',motion=True);b['demo']['settings'].update(view='outline',motion=True);b['integrations']['onigiri']=False;tag.string=core.json_for_html(b)
  style=soup.new_tag('style');style.string='html[data-atelier-home=workspace] #atelier-root{top:var(--atelier-preview-offset,34px)!important;}';soup.head.append(style)
  band=soup.new_tag('script');band.string='(()=>{const wrap=document.createElement("div");wrap.innerHTML='+json.dumps(RIBBON)+';const band=wrap.firstElementChild;band.style.cssText+=";position:fixed;inset:0 0 auto;z-index:2147483647;opacity:1;pointer-events:auto;box-sizing:border-box;";document.documentElement.append(band);new ResizeObserver(()=>document.documentElement.style.setProperty("--atelier-preview-offset",band.offsetHeight+"px")).observe(band);})();';soup.body.append(band)
  script=soup.new_tag('script');script.string='document.addEventListener("click",e=>{if(e.composedPath().some(x=>x.dataset?.action==="friends-open")){e.preventDefault();e.stopImmediatePropagation();location.href="/friends";}},true);';soup.body.append(script);return str(soup).encode()
 s=social_state(online=route=='/friends-sample',earned=True);tab='journey' if route=='/journey' else 'shared';s['home']['friends'][0]['name']='Sample friend';s['home']['profile']['name']='Sample learner';s['notice']='Fictional browser data. Real keepsakes use your native Anki activity.'
 html=social_document(s,tab=tab,theme='forest').replace('http://atelier.fixture','')
 handler='''window.AtelierSocialBoot.request=x=>{actions.push(x);if(x.op==='ready')return;setTimeout(()=>{const s=AtelierSocial.getState();if(x.op==='journey_equip'){s.journey.saved.equipped=x.data.value;AtelierSocial.receive({state:{...s,busy:false,notice:'Preview scene chosen; no Anki data changed.'}});}else if(x.op==='journey_reflection'){s.journey.saved.reflection=x.data.value;AtelierSocial.receive({state:{...s,busy:false,notice:'Preview reflection retained in this open page only.'}});}else{AtelierSocial.receive({error:'This browser preview does not sign in, send email, publish or import. Use Atelier in Anki; online sharing also requires an approved connected service.'});}},100);};'''
 html=html.replace('window.AtelierSocialBoot.request=x=>actions.push(x);',handler)
 return ('<!doctype html><title>Atelier 1.0.16 · Fictional browser preview</title>'+RIBBON+html.replace('<!doctype html>','',1)).encode()

class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  route=unquote(urlsplit(self.path).path)
  if route.startswith('/listing/'):
   p=(ROOT/'listing/ankiweb-1.0.16'/route[len('/listing/'):]).resolve();base=(ROOT/'listing/ankiweb-1.0.16').resolve()
   if not p.is_relative_to(base) or not p.is_file() or p.suffix not in ['.html','.png','.json','.md','.txt']:self.send_error(404);return
   data=p.read_bytes();kind=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
  elif route in ['/','/journey','/friends','/friends-sample']:data=document(route);kind='text/html; charset=utf-8'
  elif route.startswith('/_addons/daedalus_atelier/'):
   rel=route[len('/_addons/daedalus_atelier/'):];p=(ROOT/'src'/rel).resolve();bases=[(ROOT/'src/web').resolve(),(ROOT/'src/sprout/web').resolve()]
   if not any(p.is_relative_to(b) for b in bases) or not p.is_file() or p.suffix not in ['.js','.css','.png','.webp','.svg','.json']:self.send_error(404);return
   data=p.read_bytes();kind=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);info={'url':'http://127.0.0.1:'+str(server.server_port)+'/','pid':__import__('os').getpid(),'category':'Local fictional-data preview; no Anki windows or hosted Friends service'};(OUT/'server.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info),flush=True);server.serve_forever()

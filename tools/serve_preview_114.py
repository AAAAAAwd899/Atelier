"""Local interactive shipped-UI preview. Fictional data; never opens Anki stores."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit,unquote
import sys,json,mimetypes
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from suite_fixtures import home_suite,core
from bs4 import BeautifulSoup
OUT=ROOT/'output/preview-114';OUT.mkdir(parents=True,exist_ok=True)

def document():
    soup=BeautifulSoup(home_suite('forest',page='library'),'html.parser')
    soup.title.string='Atelier 1.0.14 · Interactive preview · Sample data'
    tag=soup.find(id='atelier-bootstrap');boot=json.loads(tag.string)
    boot['settings'].update(view='outline',motion=True);boot['demo']['settings'].update(view='outline',motion=True)
    boot['integrations']['onigiri']=False
    boot['profile']['folder_icons']={'22':'pills','24':'science'}
    boot['demo']['profile']['folder_icons']=dict(boot['profile']['folder_icons'])
    tag.string=core.json_for_html(boot);return str(soup).encode('utf-8')

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route=unquote(urlsplit(self.path).path)
        if route in ('/','/index.html'):
            data=document();kind='text/html; charset=utf-8'
        elif route.startswith('/_addons/daedalus_atelier/web/'):
            base=(ROOT/'src/web').resolve();p=(base/route.split('/web/',1)[1]).resolve()
            if not p.is_relative_to(base) or not p.is_file():self.send_error(404);return
            data=p.read_bytes();kind=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(data)
    def log_message(self,*args):pass

server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
(OUT/'server.json').write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}/','category':'shipped Atelier UI with sample data; no Anki collection access'})+'\n')
print(f'Atelier sample preview: http://127.0.0.1:{server.server_port}/',flush=True)
server.serve_forever()

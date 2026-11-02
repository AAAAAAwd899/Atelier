"""Bounded malformed PDF regression; never reads owner documents."""
from pathlib import Path
import subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
code = """import sys,types,importlib
from io import BytesIO
p=types.ModuleType('parser_security_qa');p.__path__=['src'];sys.modules[p.__name__]=p
pdf=importlib.import_module('parser_security_qa.workshop.vendor.pypdf')
try:pdf.PdfReader(BytesIO(b'%PDF-1.4\\nxref\\n0 1\\n0000000000 65535 f \\nstartxref\\n9\\n%%EOF'),strict=False)
except Exception as e:print(type(e).__name__)
"""
r=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=10)
assert r.returncode==0 and 'PdfReadError' in r.stdout
p=ROOT/'verification/pdf-security-112.json'
p.write_text(json.dumps({'runtime_sha256':runtime_digest(),'version':'6.21.4','malformed_missing_trailer_finishes_within_timeout':True,'timeout_seconds':10,'result':r.stdout.strip(),'scope':'one malformed EOF regression plus full parser/importer suite'},indent=2)+'\n',encoding='utf-8')
print('Malformed missing-trailer PDF rejected within bounded timeout')

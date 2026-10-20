"""Pinned upstream parser, real PDF text, namespace isolation and bounded decode."""
import hashlib,importlib,json,sys,zlib
from io import BytesIO
import pytest
from reportlab.pdfgen import canvas
from fixtures import ROOT,SRC

def test_namespaced_parser_matches_every_pinned_upstream_byte():
    lock=json.loads((ROOT/'PYPDF-VENDOR-6.21.1.json').read_text())
    files={p.relative_to(SRC).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (SRC/'workshop/vendor/pypdf').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert files==lock['files'] and lock['version']=='6.21.1'
    old=json.loads((ROOT/'baseline-1.0.2.json').read_text())
    historic=json.loads((ROOT/'tests/data/pypdf-590-baseline.json').read_text())
    assert all(hashlib.sha256(text.encode('utf8')).hexdigest()==old[n] for n,text in historic.items())
    assert sorted(n for n in historic if n not in files)==lock['retired_baseline_modules']

def test_real_pdf_text_and_page_order_survive_parser_upgrade():
    original=sys.modules.get('pypdf')
    pdf=importlib.import_module('atelier_testing.workshop.vendor.pypdf')
    assert pdf.__version__=='6.21.1' and sys.modules.get('pypdf') is original
    stream=BytesIO();c=canvas.Canvas(stream)
    c.drawString(40,700,'Slide 1: atrial anatomy');c.showPage()
    c.drawString(40,700,'Slide 2: treatment choices');c.save()
    reader=pdf.PdfReader(BytesIO(stream.getvalue()),strict=False)
    assert len(reader.pages)==2
    assert 'Slide 1: atrial anatomy' in reader.pages[0].extract_text()
    assert 'Slide 2: treatment choices' in reader.pages[1].extract_text()

def test_compressed_stream_limit_is_enforced_before_large_allocation():
    pdf=importlib.import_module('atelier_testing.workshop.vendor.pypdf')
    filters=importlib.import_module('atelier_testing.workshop.vendor.pypdf.filters')
    errors=importlib.import_module('atelier_testing.workshop.vendor.pypdf.errors')
    previous=pdf.get_configuration()
    with pdf.apply_configuration(zlib_maximum_output_length=1024):
        with pytest.raises(errors.LimitReachedError):filters.decompress(zlib.compress(b'x'*4096))
        assert filters.decompress(zlib.compress(b'normal lecture content'))==b'normal lecture content'
    assert pdf.get_configuration()==previous

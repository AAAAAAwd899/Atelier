"""Synthetic source documents and native-IO contracts; never installed as content."""
from pathlib import Path
from io import BytesIO
from types import SimpleNamespace
import zipfile
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

def png():
    b=BytesIO();Image.new('RGB',(640,360),'#f1ecdf').save(b,format='PNG');return b.getvalue()

def presentation(path):
    p=Presentation();p.slide_width=Inches(12);p.slide_height=Inches(6.75)
    for i in range(2):
        s=p.slides.add_slide(p.slide_layouts[6]);box=s.shapes.add_textbox(Inches(.5),Inches(.4),Inches(10),Inches(1))
        box.text=f'Lesson {i+1} — source integrity'
        table=s.shapes.add_table(2,2,Inches(1),Inches(2),Inches(6),Inches(1)).table
        for r,row in enumerate([['Term','Meaning'],[f'Item {i+1}','A verified explanation']]):
            for c,v in enumerate(row):table.cell(r,c).text=v
        s.shapes.add_picture(BytesIO(png()),Inches(7),Inches(2),width=Inches(3))
        s.notes_slide.notes_text_frame.text=f'Speaker detail for lesson {i+1}: avoid unsupported claims.'
    # Reordering changes relationships, not slide1/slide2 filenames.
    nodes=list(p.slides._sldIdLst);p.slides._sldIdLst.remove(nodes[1]);p.slides._sldIdLst.insert(0,nodes[1])
    p.slides[0]._element.set('show','0')
    p.save(path);return path

def enable_native_io(col):
    def create():
        m=col.models.new('Image Occlusion');m['type']=1;m['originalStockKind']=6
        for name in ('Occlusion','Image','Header','Back Extra'):col.models.add_field(m,col.models.new_field(name))
        col.models.add_template(m,{'name':'Image Occlusion','qfmt':'{{cloze:Occlusion}}','afmt':'{{cloze:Occlusion}}'})
        col.models.add(m)
    col._backend=SimpleNamespace(add_image_occlusion_notetype=create,
        get_image_occlusion_fields=lambda **kw:SimpleNamespace(occlusions=0,image=1,header=2,back_extra=3))
    return col

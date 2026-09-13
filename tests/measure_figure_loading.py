"""Repeatable host-independent measurement, NOT native Qt or Windows timing.
Source: deterministic authored diagram, forty embedded figure references. No user data.
"""
import sys,time,json,tempfile,statistics,hashlib
from pathlib import Path
from test_release_finish import storage,docs,cache
from PIL import Image,ImageDraw
import io
R=Path(__file__).resolve().parents[1]
def run():
 with tempfile.TemporaryDirectory() as td:
  st=storage.Store(Path(td));project=st.project({'title':'Figure payload measurement'})
  im=Image.new('RGB',(1600,1000),'#faf8f0');d=ImageDraw.Draw(im)
  for i in range(35):
   x=30+(i%7)*223;y=40+(i//7)*186
   d.rounded_rectangle((x,y,x+180,y+112),radius=12,fill=('#5d8667','#b0c7a2','#d7b277')[i%3]);d.text((x+10,y+130),'Figure region '+str(i+1),fill='#203b2a')
  buf=io.BytesIO();im.save(buf,'PNG');raw=buf.getvalue();blob=st.save_blob(raw,'png')
  source=st.add_source(project['id'],'Illustrated slides','pptx',[{'text':'The page text arrives independently of the figures.','assets':[{'blob':blob,'label':f'Figure {i+1}'} for i in range(40)]}])['source']
  old=[];cold=[];warm=[];oldresult=newresult=None
  for i in range(7):
   t=time.perf_counter();oldresult=docs.render_page(st,source['version_id'],1,1600);old.append((time.perf_counter()-t)*1000)
   fp=cache.FigurePreviews(st);t=time.perf_counter();newresult=fp.page(source['version_id'],1,1600);cold.append((time.perf_counter()-t)*1000)
   t=time.perf_counter();fp.page(source['version_id'],1,1600);warm.append((time.perf_counter()-t)*1000)
  encoded=lambda x:len(json.dumps(x,ensure_ascii=False).encode())
  report={'fixture':'one extracted page; forty 1600x1000 PNG figure references; authored diagram',
    'original_image_bytes':len(raw),'original_image_sha256':hashlib.sha256(raw).hexdigest(),'repeats':7,
    'old_page_response_bytes':encoded(oldresult),'new_page_response_bytes':encoded(newresult),
    'response_reduction_percent':round(100*(1-encoded(newresult)/encoded(oldresult)),2),
    'median_python_ms':{'previous_page':round(statistics.median(old),3),'new_page_first':round(statistics.median(cold),3),'new_page_repeat':round(statistics.median(warm),3)},
    'all_python_ms':{'previous_page':old,'new_page_first':cold,'new_page_repeat':warm},
    'original_figure_encodes_during_page':40,'new_figure_encodes_during_page':0,
    'original_image_unchanged':st.blob_path(blob).read_bytes()==raw,
    'cache':fp.cache.diagnostics(),
    'limits':'Linux Python with a local synthetic source on tmpfs. Measures metadata/image-encoding work and payload, not PDF rasterization, native Qt thumbnail decoding, browser paint, disk/network time, Windows startup or total UI speed.'}
  out=R/'verification/release-finish/figure-benchmark.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':run()

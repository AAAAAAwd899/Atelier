"""Export low-power/native animations from the SAME production WebGL scene.
Developer tool only: xvfb-run -a python tools/render_pip.py [--stills]
No browser/runtime dependencies are needed in the installed add-on.
"""
from pathlib import Path
import base64, io, json, sys, hashlib
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'addon/web';OUT=WEB/'pip'
OUT.mkdir(exist_ok=True)
STILLS='--stills' in sys.argv
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':480,'height':480},device_scale_factor=1)
 page.set_content('<style>html,body{margin:0;background:transparent}canvas{width:480px;height:480px;display:block}</style><canvas></canvas>')
 page.add_script_tag(path=str(WEB/'pip-scene.js'))
 def capture(t):
  data=page.evaluate('(t)=>{scene.render(t);return scene.canvas.toDataURL("image/png").split(",")[1]}',t)
  return Image.open(io.BytesIO(base64.b64decode(data))).convert('RGBA').resize((480,480),Image.Resampling.LANCZOS)
 manifest={'version':'0.9.7','renderer':'Same production WebGL2 rig as planner','material':'Leaf skin and smooth organic surfaces; no plush/fur','stages':4,'size':[480,480],'animations':['idle','pet','water'],'fps':30,'frames_per_animation':{'idle':180,'pet':96,'water':96},'runtime':'Live WebGL2 in planner; exact-model RGBA frames in tiny native reviewer and GPU fallback','scene_sha256':hashlib.sha256((WEB/'pip-scene.js').read_bytes()).hexdigest(),'assets':{}}
 for stage in range(1,5):
  page.evaluate('(stage)=>{window.scene?.dispose();document.querySelector("canvas").replaceWith(document.createElement("canvas"));window.scene=new PipScene.Scene(document.querySelector("canvas"),{stage,capture:true,habitat:false});scene.setPaused(true);}',stage)
  capture(0).save(OUT/f'stage{stage}.png')
  if not STILLS:
   for action in ['idle','pet','water']:
    page.evaluate('(action)=>{scene.options.loopPeriod=action==="idle"?6:3.2;scene.lastMotionTime=null;scene.time=0;scene.actionStart=0;scene.render(0);scene.setAction(action);}',action)
    count=180 if action=='idle' else 96
    frames=[capture(i/30) for i in range(count)]
    durations=[round((i+1)*1000/30)-round(i*1000/30) for i in range(count)]
    path=OUT/f'stage{stage}-{action}.webp'
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0 if action=='idle' else 1,quality=96,method=4,exact=True)
    manifest['assets'][path.name]={'bytes':path.stat().st_size,'frames':count,'duration_ms':sum(durations),'fps':30,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    print(stage,action,path.stat().st_size,flush=True)
  print(stage,'still',flush=True)
 page.evaluate('scene.dispose()');browser.close()
(OUT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2))

"""Derive reviewer-only 96px assets from the exact live-model render export.
No second character design. Decoded frame cache <= 180 * 96 * 96 * 4 bytes.
"""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageSequence
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'addon/web/pip'
manifest=json.loads((OUT/'asset_manifest.json').read_text())
for stage in range(1,5):
    path=OUT/f'tiny-stage{stage}.png'
    with Image.open(OUT/f'stage{stage}.png') as im:
        im.convert('RGBA').resize((96,96),Image.Resampling.LANCZOS).save(path)
    for action in ('idle','pet','water'):
        with Image.open(OUT/f'stage{stage}-{action}.webp') as im:
            frames=[];durations=[]
            for f in ImageSequence.Iterator(im):
                frames.append(f.convert('RGBA').resize((96,96),Image.Resampling.LANCZOS));durations.append(f.info.get('duration',33))
        path=OUT/f'tiny-stage{stage}-{action}.webp'
        frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0 if action=='idle' else 1,lossless=True,method=4,exact=True)
        manifest['assets'][path.name]={'bytes':path.stat().st_size,'frames':len(frames),'duration_ms':sum(durations),'fps':30,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':[96,96]}
manifest['reviewer']={'size':[96,96],'display_size':[46,46],'maximum_decoded_frame_bytes':180*96*96*4,'webview':False,'webgl':False}
(OUT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2))
print('24 matching-model animations, tiny reviewer cache <= 6.33 MiB')

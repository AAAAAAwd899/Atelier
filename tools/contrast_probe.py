"""Conservative scenery-composite contrast probe, not accessibility certification."""
from pathlib import Path
import json,numpy as np,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
contract_path=ROOT/'src/web/design-contract.json';contract=json.loads(contract_path.read_text());roles=contract['worlds'];rows=[]
def rgb(h):return np.array([int(h[i:i+2],16)/255 for i in (1,3,5)])
def lum(a):return np.sum(np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)*[.2126,.7152,.0722],axis=-1)
for world,data in roles.items():
    pixels=np.asarray(Image.open(ROOT/f'src/web/world-art/{world}-1.0.3.png').convert('RGB'),dtype=np.float32)/255
    # Main uses 92%, 84%, 78% canvas stops. Probe the least opaque stop against
    # every actual scenic pixel, stronger than checking only palette swatches.
    background=lum(pixels*.22+rgb(data['roles']['canvas'])*.78)
    if '--adjust-muted' in sys.argv:
        old=data['roles']['muted'];candidate=rgb(old)
        # Light worlds require stronger helper text over their dimmest scenic
        # pixels. Keep the hue and improve every solid light-surface pairing too.
        while (np.maximum(background,lum(candidate))+.05).min()/(min(float(background.max()),float(lum(candidate)))+.05)<4.65 and lum(rgb(data['roles']['canvas']))>.5:
            candidate*=.98
        data['roles']['muted']='#'+''.join(f'{round(x*255):02x}' for x in candidate)
        data['compatibility']['quiet']=data['roles']['muted']
    values={}
    for name in ['text','muted']:
        fg=lum(rgb(data['roles'][name]));ratios=(np.maximum(background,fg)+.05)/(np.minimum(background,fg)+.05);values[name]=float(ratios.min())
    rows.append({'world':world,'minimum_contrast':values,'passes':min(values.values())>=4.5})
out=ROOT/'output/composited-contrast.json';out.write_text(json.dumps({'method':'sRGB alpha composition of actual pixels at minimum canvas opacity; scoped to main background text roles','rows':rows},indent=2)+'\n')
if '--adjust-muted' in sys.argv:contract_path.write_text(json.dumps(contract,indent=2)+'\n')
print(json.dumps(rows,indent=2))

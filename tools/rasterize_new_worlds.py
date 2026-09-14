"""Create deterministic 1672x941 scene plates for the five authored worlds.

The runtime uses these raster plates for fast backgrounds; the matching SVGs
remain the source artwork for crisp theme tiles and future scaling.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math, random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "web" / "world-art"
W, H = 1672, 941

def gradient(top, bottom):
    im = Image.new("RGB", (W, H)); p = im.load()
    a = tuple(int(top[i:i+2], 16) for i in (1,3,5)); b = tuple(int(bottom[i:i+2], 16) for i in (1,3,5))
    for y in range(H):
        t = y/(H-1)
        c = tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
        for x in range(W): p[x,y] = c
    return im

def haze(im, xy, r, color, alpha=110):
    layer = Image.new("RGBA", im.size); d=ImageDraw.Draw(layer)
    d.ellipse((xy[0]-r,xy[1]-r,xy[0]+r,xy[1]+r), fill=color+(alpha,))
    layer=layer.filter(ImageFilter.GaussianBlur(r//2)); im.paste(layer,(0,0),layer)

def stars(d, seed, color=(255,245,220,190), n=85):
    rng=random.Random(seed)
    for _ in range(n):
        x=rng.randrange(30,W-30); y=rng.randrange(30,390); r=rng.choice((1,1,2,2,3))
        d.ellipse((x-r,y-r,x+r,y+r), fill=color)

def castle():
    im=gradient("#16122f","#d58ca8"); d=ImageDraw.Draw(im,"RGBA"); stars(d,4); d.ellipse((1240,105,1330,195), fill="#fff0cf")
    d.polygon([(0,575),(180,470),(350,565),(520,470),(700,560),(870,475),(1050,570),(1250,460),(1672,570),(1672,941),(0,941)], fill="#302344")
    d.polygon([(0,650),(260,535),(510,650),(760,545),(1020,650),(1280,535),(1672,650),(1672,941),(0,941)], fill="#11162d")
    stone=(233,197,202); edge=(141,101,149); base=Image.new("RGBA",im.size); bd=ImageDraw.Draw(base)
    for x,h in ((500,300),(790,420),(1080,300)):
        bd.rectangle((x-105,580-h,x+105,580),fill=stone+(255,),outline=edge+(255,),width=8); bd.polygon([(x-130,580-h),(x,580-h-145),(x+130,580-h)],fill="#6f477d",outline=edge+(255,))
        bd.rectangle((x-45,580-h+45,x+45,580-h+140),fill="#ffe4a9")
    bd.rectangle((610,430,1060,580),fill=stone+(255,),outline=edge+(255,),width=8); bd.polygon([(590,430),(835,205),(1080,430)],fill="#7b4b84",outline=edge+(255,)); bd.rectangle((790,470,880,580),fill="#4f365d"); bd.ellipse((810,485,860,535),fill="#ad648d")
    im.paste(base,(0,0),base); d=ImageDraw.Draw(im,"RGBA"); haze(im,(835,520),240,(239,158,180),30); d.line((0,785,1672,785),fill="#6f6c95",width=8); return im

def underworld():
    im=gradient("#100c19","#792c24"); d=ImageDraw.Draw(im,"RGBA"); haze(im,(835,730),300,(255,100,55),95); stars(d,9,(255,207,118,170),35)
    d.polygon([(0,0),(350,0),(450,260),(335,420),(490,620),(0,700)],fill="#17121d"); d.polygon([(1672,0),(1322,0),(1222,260),(1337,420),(1182,620),(1672,700)],fill="#17121d")
    d.polygon([(0,690),(170,560),(360,620),(530,545),(690,640),(850,565),(1050,650),(1260,540),(1450,625),(1672,520),(1672,941),(0,941)],fill="#26171f")
    d.polygon([(0,820),(300,700),(550,830),(820,735),(1100,820),(1370,700),(1672,805),(1672,941),(0,941)],fill="#d75a35"); d.line((0,845,300,790,550,860,820,790,1100,850,1370,770,1672,830),fill="#ffd47a",width=12)
    for x,h in ((380,420),(520,510),(1150,510),(1290,420)):
        d.polygon([(x-70,760-h),(x,760-h-95),(x+70,760-h),(x+58,760)],fill="#3b2327",outline="#874538",width=10)
    d.ellipse((650,325,1022,770),fill="#140f18",outline="#b45b45",width=12); d.arc((700,360,972,740),180,360,fill="#f0a15b",width=9); return im

def mythic():
    im=gradient("#091229","#13112e"); d=ImageDraw.Draw(im,"RGBA"); haze(im,(835,390),330,(91,228,223),90); stars(d,14,(220,194,255,210),70); c=(835,410)
    for r in (310,205): d.ellipse((c[0]-r,c[1]-r,c[0]+r,c[1]+r),outline="#9de8e8",width=5)
    for a in (0,45,90,135):
        dx=math.cos(math.radians(a))*310; dy=math.sin(math.radians(a))*310; d.line((c[0]-dx,c[1]-dy,c[0]+dx,c[1]+dy),fill="#9de8e8",width=4)
    d.polygon([(0,700),(320,620),(600,710),(830,620),(1100,710),(1400,600),(1672,700),(1672,941),(0,941)],fill="#101b36")
    d.polygon([(690,735),(835,430),(980,735)],fill="#17264a",outline="#8ce3e7",width=9); d.polygon([(735,500),(835,395),(935,500)],outline="#d7c2ff",width=10); d.ellipse((790,550,880,640),fill="#8ce3e7",outline="#e7d89b",width=4); return im

def cabin():
    im=gradient("#17253b","#c6a17e"); d=ImageDraw.Draw(im,"RGBA"); d.ellipse((1330,105,1405,180),fill="#f9e8bd"); stars(d,21,(213,235,195,180),55)
    d.polygon([(0,500),(170,230),(270,410),(420,180),(560,440),(720,260),(850,450),(1030,220),(1180,450),(1370,280),(1672,510),(1672,690),(0,690)],fill="#152b2b")
    d.rectangle((0,635,W,H),fill="#102727"); d.line((0,760,1672,760),fill="#9ac6b4",width=5)
    d.polygon([(450,590),(835,315),(1220,590)],fill="#4f3b36",outline="#513c32"); d.rectangle((510,590,1160,840),fill="#76513e",outline="#513c32",width=10); d.rectangle((680,630,780,745),fill="#ffd88c"); d.rectangle((850,630,950,745),fill="#ffd88c"); d.rectangle((795,705,900,840),fill="#392b2c"); d.rectangle((1010,390,1080,570),fill="#3a3031")
    for x in (150,290,1430,1560): d.polygon([(x,760),(x+70,350),(x+140,760)],fill="#17312c")
    haze(im,(820,560),210,(241,180,119),48); return im

def sunset():
    im=gradient("#47315f","#f9d59b"); d=ImageDraw.Draw(im,"RGBA"); d.ellipse((750,280,910,440),fill="#ffe2a5"); d.rectangle((0,465,W,H),fill="#1f405b");
    for y,amp,col,w in ((555,55,"#f9d8ac",8),(650,45,"#f9d8ac",6),(780,30,"#dfb895",4)):
        pts=[]
        for x in range(0,W+1,20): pts.append((x,y+amp*math.sin(x/145)))
        d.line(pts,fill=col,width=w)
    d.polygon([(0,730),(260,590),(500,730),(760,620),(1010,735),(1350,590),(1672,710),(1672,941),(0,941)],fill="#27364b")
    for x in (150,1480):
        d.polygon([(x,800),(x+55,430),(x+110,800)],fill="#2a3044"); d.line((x+55,540,x-20,500),fill="#2a3044",width=16); d.line((x+55,600,x+135,550),fill="#2a3044",width=14)
    return im

for name, fn in (("castle",castle),("underworld",underworld),("mythic",mythic),("cabin",cabin),("sunset",sunset)):
    fn().resize((1672,941), Image.Resampling.LANCZOS).save(OUT/f"{name}-1.0.3.png", optimize=True)
    print(name)

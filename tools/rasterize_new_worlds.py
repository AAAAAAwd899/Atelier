"""Create deterministic 1672x941 scene plates for the five authored worlds.

The plates are deliberately illustrated rather than icon-like: each scene has
atmospheric gradients, a clear focal subject, depth layers, light falloff and
small hand-authored details. Matching SVGs remain the scalable source artwork.
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
        t = y/(H-1); c = tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
        for x in range(W): p[x,y] = c
    return im.convert("RGBA")

def haze(im, xy, r, color, alpha=110):
    layer = Image.new("RGBA", im.size); d=ImageDraw.Draw(layer)
    d.ellipse((xy[0]-r,xy[1]-r,xy[0]+r,xy[1]+r), fill=tuple(color)+(alpha,))
    layer=layer.filter(ImageFilter.GaussianBlur(max(2,r//3))); im.alpha_composite(layer)

def stars(d, seed, color=(255,245,220,190), n=100, y_max=430):
    rng=random.Random(seed)
    for _ in range(n):
        x=rng.randrange(28,W-28); y=rng.randrange(24,y_max); r=rng.choice((1,1,1,2,2,3))
        d.ellipse((x-r,y-r,x+r,y+r), fill=color)
        if r==3: d.line((x-5,y,x+5,y), fill=color, width=1); d.line((x,y-5,x,y+5), fill=color, width=1)

def vignette(im, edge=(4,7,20,145)):
    v=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(v)
    d.rectangle((0,0,W,H),outline=edge,width=44); im.alpha_composite(v.filter(ImageFilter.GaussianBlur(18)))

def finish(im, seed, grain=3):
    """Give the illustrated plates a restrained, print-like finish.

    The source scenes stay vector-clean, while this pass adds depth at the
    scale people actually see them: a soft atmospheric veil, low-frequency
    colour variation and barely visible grain in the darks.  It is seeded so
    the installer and source archive remain reproducible.
    """
    rng = random.Random(seed)
    # Low-frequency haze breaks the hard horizon without washing out the
    # centre where opaque UI cards are placed.
    veil = Image.new("RGBA", im.size, (0, 0, 0, 0)); vd = ImageDraw.Draw(veil, "RGBA")
    for y in range(0, H, 26):
        a = int(4 + 5 * math.sin(y / 180))
        vd.rectangle((0, y, W, y + 26), fill=(255, 236, 216, max(0, a)))
    im.alpha_composite(veil.filter(ImageFilter.GaussianBlur(14)))
    # Very light film grain makes broad colour fields feel authored rather
    # than computer-flat, while keeping text contrast untouched.
    if grain:
        px = im.load();
        for y in range(H):
            for x in range(W):
                if rng.random() < 0.08:
                    r, g, b, a = px[x, y]
                    delta = rng.choice((-grain, -1, 1, grain))
                    px[x, y] = (max(0, min(255, r + delta)), max(0, min(255, g + delta)), max(0, min(255, b + delta)), a)
    return im

def castle():
    im=gradient("#11152f","#d18aa5"); d=ImageDraw.Draw(im,"RGBA"); stars(d,4,n=150)
    haze(im,(1280,132),150,(255,220,170),80); d=ImageDraw.Draw(im,"RGBA"); d.ellipse((1235,85,1325,175),fill="#fff1ce")
    d.polygon([(0,575),(170,463),(332,553),(500,446),(694,558),(875,464),(1056,560),(1264,442),(1672,560),(1672,941),(0,941)],fill="#332448")
    d.polygon([(0,667),(270,533),(510,658),(744,536),(1010,660),(1280,525),(1672,646),(1672,941),(0,941)],fill="#10162e")
    d.polygon([(760,941),(855,600),(950,941)],fill="#29304c"); d.line((840,650,860,650),fill="#c6a6bb",width=5)
    # A broad lavender bloom behind the keep adds the moonlit, storybook
    # depth that a flat geometric plate misses at card-sized scale.
    haze(im, (836, 430), 430, (224, 165, 190), 22)
    stone=Image.new("RGBA",im.size); sd=ImageDraw.Draw(stone,"RGBA")
    for x,h,w in ((505,310,210),(835,438,250),(1160,310,210)):
        sd.rounded_rectangle((x-w//2,586-h,x+w//2,586),radius=8,fill="#e9c7cf",outline="#886397",width=8)
        for yy in range(586-h+20, 586, 32):
            sd.line((x-w//2+14, yy, x+w//2-14, yy), fill=(179, 126, 157, 55), width=2)
        sd.polygon([(x-w//2-24,586-h),(x,586-h-142),(x+w//2+24,586-h)],fill="#744782",outline="#996e9c",width=6)
        sd.rectangle((x-40,586-h+42,x+40,586-h+142),fill="#ffe8b0",outline="#b87893",width=5)
        sd.line((x,586-h+45,x,586-h+137),fill="#c58a9b",width=3); sd.line((x-38,586-h+92,x+38,586-h+92),fill="#c58a9b",width=3)
    sd.rectangle((640,434,1032,586),fill="#e5c1cb",outline="#886397",width=8)
    for yy in range(456, 580, 26): sd.line((654, yy, 1018, yy), fill=(182, 128, 157, 48), width=2)
    sd.polygon([(610,434),(836,215),(1062,434)],fill="#744782",outline="#996e9c",width=7)
    sd.rectangle((794,482,878,586),fill="#4b355b"); sd.ellipse((815,498,857,540),fill="#ca789a",outline="#f5bdc3",width=4)
    sd.line((730,466,942,466),fill="#f7dfc9",width=4); im.alpha_composite(stone); d=ImageDraw.Draw(im,"RGBA")
    # Tiny warm windows and flags read as hand-placed details rather than
    # repeated UI-like symbols.
    for x in (492,1162):
        d.line((x,230,x,350),fill="#c79b8f",width=5); d.polygon([(x,348),(x+48,365),(x,385)],fill="#eeb0ba")
    for x in range(250,1450,90):
        d.ellipse((x,735,x+10,745),fill="#e7b9c9")
        d.ellipse((x-10,725,x+20,755),fill=(238, 167, 193, 22))
    # Rose garden silhouettes and a few foreground leaves give the grounds a
    # painterly edge while preserving a quiet lower band for the UI.
    for x in range(310, 1370, 72):
        d.line((x, 808, x + (x % 3 - 1) * 10, 760), fill=(67, 61, 82, 220), width=4)
        d.ellipse((x-15, 758, x+7, 775), fill=(108, 70, 105, 180))
        d.ellipse((x+4, 748, x+25, 768), fill=(130, 78, 116, 150))
    d.polygon([(0,805),(210,728),(420,802),(610,747),(820,810),(1040,742),(1280,807),(1490,730),(1672,788),(1672,941),(0,941)],fill="#171c35")
    d.line((0,792,1672,792),fill="#77719f",width=6); vignette(im,(20,16,38,150)); return finish(im, 104)

def underworld():
    im=gradient("#0b0a16","#7f3024"); d=ImageDraw.Draw(im,"RGBA"); stars(d,9,(255,208,120,190),45,380)
    haze(im,(836,760),340,(255,91,42),120); haze(im,(836,545),180,(219,78,45),45); d=ImageDraw.Draw(im,"RGBA")
    d.polygon([(0,0),(350,0),(430,178),(345,340),(470,506),(330,670),(470,941),(0,941)],fill="#17121e")
    d.polygon([(1672,0),(1322,0),(1242,178),(1327,340),(1202,506),(1342,670),(1202,941),(1672,941)],fill="#17121e")
    for poly in [[(0,120),(210,0),(310,240),(120,360)],[(1672,120),(1462,0),(1362,240),(1552,360)],[(0,560),(230,390),(380,610),(130,750)],[(1672,560),(1442,390),(1292,610),(1542,750)]]: d.polygon(poly,fill="#251622",outline="#47262d")
    d.polygon([(0,710),(170,564),(360,625),(530,542),(690,652),(850,565),(1050,657),(1260,540),(1450,632),(1672,520),(1672,941),(0,941)],fill="#2a1821")
    d.polygon([(0,828),(280,710),(545,842),(820,735),(1100,828),(1380,700),(1672,800),(1672,941),(0,941)],fill="#c4472e")
    d.line((0,852,280,770,545,875,820,785,1100,856,1380,760,1672,833),fill="#ffd37c",width=18); d.line((0,878,280,803,545,902,820,812,1100,883,1380,790,1672,855),fill="#f06a39",width=8)
    # Meandering ember fissures and sparks add heat variation to the lava,
    # keeping the underworld from reading as a single red polygon.
    rng = random.Random(91)
    for _ in range(28):
        x = rng.randrange(0, W); y = rng.randrange(825, 935)
        d.line((x, y, x + rng.randrange(-70, 71), y + rng.randrange(8, 28)), fill=(255, 191, 94, rng.randrange(70, 170)), width=rng.choice((2,3,4)))
    for _ in range(24):
        x = rng.randrange(40, W-40); y = rng.randrange(590, 840); r = rng.choice((2,3,4))
        d.ellipse((x-r, y-r, x+r, y+r), fill=(255, 160, 82, 150))
    for x,h in ((380,420),(525,520),(1147,520),(1292,420)):
        d.polygon([(x-72,760-h),(x,760-h-102),(x+74,760-h),(x+60,760)],fill="#3b242b",outline="#92503f",width=10); d.line((x,760-h+25,x+20,760-h+165),fill="#c26247",width=4)
    d.ellipse((642,302,1030,780),fill="#120f19",outline="#bd6247",width=14); d.arc((704,345,968,730),180,360,fill="#f4a65b",width=12); d.arc((730,378,942,690),180,360,fill="#ffd27a",width=5)
    for x,y in ((470,270),(1180,220),(410,490),(1260,460),(610,180),(1030,135)):
        d.ellipse((x-4,y-4,x+4,y+4),fill="#ffc56d"); d.line((x,y-12,x,y+12),fill="#ff8c4c",width=2)
    vignette(im,(22,8,24,180)); return finish(im, 109)

def mythic():
    im=gradient("#071027","#121735"); d=ImageDraw.Draw(im,"RGBA"); stars(d,14,(222,197,255,220),140,500)
    haze(im,(836,410),330,(97,226,226),110); haze(im,(836,410),160,(204,177,255),65); d=ImageDraw.Draw(im,"RGBA"); c=(836,410)
    for r,col,w in ((315,"#85e2e4",7),(220,"#9fe9e7",5),(120,"#d2b9ff",4)): d.ellipse((c[0]-r,c[1]-r,c[0]+r,c[1]+r),outline=col,width=w)
    for a in (0,30,60,90,120,150):
        dx=math.cos(math.radians(a))*315; dy=math.sin(math.radians(a))*315; d.line((c[0]-dx,c[1]-dy,c[0]+dx,c[1]+dy),fill="#8bdfe2",width=3)
    for a in range(0,360,45):
        x=c[0]+315*math.cos(math.radians(a)); y=c[1]+315*math.sin(math.radians(a)); d.ellipse((x-8,y-8,x+8,y+8),fill="#f2d88d")
    # Fine orbit lines and constellation links make the sigil feel like a
    # crafted celestial instrument instead of a simple target graphic.
    for r in (165, 265):
        d.arc((c[0]-r, c[1]-r, c[0]+r, c[1]+r), 18, 148, fill=(226, 195, 255, 120), width=2)
        d.arc((c[0]-r, c[1]-r, c[0]+r, c[1]+r), 198, 328, fill=(226, 195, 255, 100), width=2)
    for a1, a2 in ((12, 48), (48, 96), (142, 196), (230, 286), (286, 340)):
        p1=(c[0]+260*math.cos(math.radians(a1)), c[1]+260*math.sin(math.radians(a1)))
        p2=(c[0]+260*math.cos(math.radians(a2)), c[1]+260*math.sin(math.radians(a2)))
        d.line((*p1, *p2), fill=(242, 216, 141, 110), width=2)
    d.polygon([(0,720),(280,604),(510,716),(770,595),(1000,718),(1280,580),(1672,710),(1672,941),(0,941)],fill="#101a37")
    d.polygon([(610,790),(836,420),(1060,790)],fill="#1a2c54",outline="#86dfe1",width=9); d.polygon([(720,590),(836,430),(952,590)],fill="#18233f",outline="#d9c0ff",width=8); d.polygon([(795,790),(836,515),(877,790)],fill="#112142")
    d.ellipse((800,580,872,652),fill="#92e2e2",outline="#f0d58a",width=5)
    for x in (200,250,1420,1470): d.line((x,790,x,590),fill="#6fd0d4",width=5); d.line((x-30,790,x+30,790),fill="#6fd0d4",width=5)
    vignette(im,(3,10,34,160)); return finish(im, 114)

def cabin():
    im=gradient("#12243c","#c4a27f"); d=ImageDraw.Draw(im,"RGBA"); haze(im,(1350,132),130,(255,225,175),80); d=ImageDraw.Draw(im,"RGBA"); d.ellipse((1310,92,1395,177),fill="#f9e9c0"); stars(d,21,(215,238,204,190),95,350)
    d.polygon([(0,530),(166,242),(280,425),(430,185),(570,450),(725,275),(872,463),(1030,220),(1180,461),(1370,285),(1672,520),(1672,710),(0,710)],fill="#18312f")
    # Snow catches the moon on the far ridge; irregular strokes soften the
    # otherwise triangular mountain silhouettes.
    for pts in (((430,185),(386,270),(430,248),(472,276)), ((1030,220),(986,306),(1030,278),(1070,314)), ((1370,285),(1332,350),(1370,329),(1410,354))):
        d.line(pts, fill=(177, 214, 199, 150), width=7)
    d.polygon([(0,600),(200,350),(370,535),(560,315),(720,550),(920,342),(1080,560),(1290,360),(1450,550),(1672,390),(1672,710),(0,710)],fill="#214342")
    for x in (125,300,1450,1590): d.polygon([(x,690),(x+68,350),(x+140,690)],fill="#12302e")
    d.rectangle((0,660,W,H),fill="#0e2929"); d.line((0,773,1672,773),fill="#a1d2bc",width=6)
    for y,wid,a in ((820,500,95),(850,360,80),(885,260,70)): d.line((835-wid,y,835+wid,y),fill=(154,206,188,a),width=4)
    d.polygon([(430,585),(835,300),(1240,585)],fill="#4a3833",outline="#60443a",width=12); d.rectangle((500,580,1170,846),fill="#76513f",outline="#543b34",width=12)
    for y in range(625,825,45): d.line((510,y,1160,y),fill="#9a6b4e",width=4)
    for x in range(530, 1150, 58): d.line((x, 604, x + 10, 830), fill=(74, 49, 44, 35), width=3)
    d.rectangle((668,636,778,754),fill="#ffd88a",outline="#e6af68",width=6); d.rectangle((872,636,982,754),fill="#ffd88a",outline="#e6af68",width=6); d.line((723,640,723,750),fill="#d79057",width=4); d.line((668,695,778,695),fill="#d79057",width=4); d.line((927,640,927,750),fill="#d79057",width=4); d.line((872,695,982,695),fill="#d79057",width=4)
    d.rectangle((800,738,900,846),fill="#342a2c"); d.rectangle((1020,382,1090,560),fill="#343235",outline="#523d38",width=8)
    smoke=Image.new("RGBA",im.size); sd=ImageDraw.Draw(smoke,"RGBA"); sd.ellipse((1030,310,1100,380),fill=(224,230,211,45)); sd.ellipse((1000,240,1090,330),fill=(224,230,211,30)); im.alpha_composite(smoke.filter(ImageFilter.GaussianBlur(16)))
    d=ImageDraw.Draw(im,"RGBA"); d.polygon([(330,846),(520,820),(720,846),(940,820),(1140,846),(1350,818),(1672,848),(1672,941),(0,941),(0,868)],fill="#0a2021")
    vignette(im,(10,28,29,155)); return finish(im, 121)

def sunset():
    im=gradient("#3c2c5b","#f8d69e"); d=ImageDraw.Draw(im,"RGBA"); stars(d,33,(255,238,205,160),35,240); haze(im,(835,334),190,(255,205,143),100); d=ImageDraw.Draw(im,"RGBA"); d.ellipse((760,260,910,410),fill="#ffe2a8")
    d.polygon([(0,240),(200,210),(360,260),(540,190),(730,240),(910,185),(1120,245),(1320,210),(1672,250),(1672,390),(0,390)],fill=(255,198,174,48)); d.rectangle((0,420,W,H),fill="#21465e")
    # Thin cloud bands and a warm reflected path break up the broad sky and
    # give the beach a believable light source.
    for x, y, ww in ((120, 285, 220), (510, 320, 310), (1080, 275, 260), (1390, 345, 180)):
        d.ellipse((x, y, x+ww, y+34), fill=(255, 226, 201, 22))
    d.polygon([(790, 420), (880, 420), (1040, 940), (640, 940)], fill=(255, 188, 141, 22))
    d.polygon([(0,520),(190,470),(400,520),(620,460),(850,515),(1050,468),(1300,522),(1510,470),(1672,510),(1672,941),(0,941)],fill="#2c5770")
    for y,amp,col,w in ((510,34,"#ffe0ac",9),(590,28,"#f9c99e",7),(680,22,"#dfb38e",5),(770,15,"#a9b7ad",4)):
        pts=[(x,y+amp*math.sin(x/145)) for x in range(0,W+1,18)]; d.line(pts,fill=col,width=w)
    d.polygon([(0,735),(250,594),(490,730),(750,620),(1010,735),(1350,590),(1672,710),(1672,941),(0,941)],fill="#263b51"); d.polygon([(0,840),(310,780),(610,842),(920,780),(1250,840),(1500,790),(1672,820),(1672,941),(0,941)],fill="#b97d69")
    for x,h in ((150,420),(1480,450)):
        d.polygon([(x,900),(x+58,h),(x+114,900)],fill="#242c44")
        for y,side in ((590,-1),(650,1),(710,-1)): d.line((x+58,y,x+58+side*100,y-55),fill="#242c44",width=15)
    d.line((0,910,1672,910),fill="#f0c28f",width=4); vignette(im,(45,31,65,140)); return finish(im, 133)

for name, fn in (("castle",castle),("underworld",underworld),("mythic",mythic),("cabin",cabin),("sunset",sunset)):
    fn().resize((1672,941), Image.Resampling.LANCZOS).convert("RGB").save(OUT/f"{name}-1.0.3.png", optimize=True)
    print(name)

"""Original game sprites crossing a fixed scene; locally anchored canopy wind."""
from pathlib import Path
from functools import lru_cache
import math
import json
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageStat, ImageSequence

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'exports'
REVIEW = ROOT / 'review'
for folder in (OUT, REVIEW):
    folder.mkdir(exist_ok=True)
W, H = 800, 348
FRAME_MS, DURATION_MS = 30, 20160
COUNT = DURATION_MS // FRAME_MS
SPEED, START, FOLLOW, FLOOR = 55, -100, 110, 287
SPAN = SPEED * DURATION_MS / 1000
OFFSET = 550
WIND_MS = 6720
TAU = math.tau
base = Image.open(ROOT.parent/'17_v5_weighted_walk/assets/clean-plate.png').convert('RGB').resize((W,H), Image.Resampling.LANCZOS)
evan = [Image.open(ROOT/f'sprite_trial/evan/aligned-{i}.png').convert('RGBA').transpose(Image.Transpose.FLIP_LEFT_RIGHT) for i in range(4)]
mir = [Image.open(ROOT/f'sprite_trial/mir-dragon2211/aligned-{i}.png').convert('RGBA').transpose(Image.Transpose.FLIP_LEFT_RIGHT) for i in range(6)]

def smooth(v):
    v = max(0, min(1, v))
    return v*v*(3-2*v)

def displacement(x, y, ms):
    """Inverse local branch bend, with fixed roots, trunk, house, and ground."""
    if y >= 260 or (x >= 555 and y >= 168):
        return 0., 0.
    # Lower edge of the actual crown: exposed clouds below it stay still.
    outline=((0,115),(180,175),(220,190),(300,205),(380,175),(460,150),(550,143),(630,125),(700,117),(800,96))
    bottom=outline[-1][1]
    for (x0,y0),(x1,y1) in zip(outline,outline[1:]):
        if x0<=x<=x1:
            bottom=y0+(y1-y0)*(x-x0)/(x1-x0)
            break
    crown_mask=1-smooth((y-(bottom-16))/16)
    if not crown_mask:
        return 0., 0.
    p = TAU * (ms % WIND_MS) / WIND_MS
    border = smooth(x/16)*smooth((W-x)/16)*smooth(y/12)
    dx = dy = 0.
    # Main rightward branches: motion builds from their trunk attachment.
    along = smooth((x-155)/610)
    canopy = 1-smooth((y-110)/70)
    bend = along*canopy
    dx += 4.2*bend*math.sin(p-.32*along)
    dy += 7.2*bend*math.sin(p-.48*along+.25)
    # Left crown moves slightly; the thick trunk beneath it remains fixed.
    crown = max(0,1-((x-65)/185)**2-((y-20)/85)**2)**2
    dx += 2.2*crown*math.sin(p+.3)
    dy += 1.3*crown*math.sin(p+.6)
    # Secondary branch/flower clusters, with a small lag between branches.
    for j,(cx,cy,rx,ry,amount) in enumerate(((306,169,100,49,3.2),(427,105,96,65,2.0),(610,90,130,67,2.5),(744,83,65,47,1.8))):
        local = max(0,1-((x-cx)/rx)**2-((y-cy)/ry)**2)**2
        dx += amount*local*math.sin(p-.45-j*.22)
        dy += amount*.65*local*math.sin(p-.7-j*.22)
    trunk_lock = 1-smooth((y-70)/35)*(1-smooth((x-180)/50))
    return border*trunk_lock*crown_mask*dx, border*trunk_lock*crown_mask*dy

@lru_cache(maxsize=112)
def scenery(ms):
    ms %= WIND_MS
    mesh=[]
    for y in range(0,260,10):
        for x in range(0,W,10):
            r,b=min(W,x+10),min(260,y+10)
            def src(a,c):
                dx,dy=displacement(a,c,ms)
                return a+dx,c+dy
            mesh.append(((x,y,r,b),src(x,y)+src(x,b)+src(r,b)+src(r,y)))
    # Only this canopy region is transformed; the remaining scene is a copy.
    canopy=base.transform((W,260),Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)
    out=base.copy()
    out.paste(canopy,(0,0))
    # Exact copied source pixels across the house and ground, including borders.
    out.paste(base.crop((555,168,W,H)),(555,168))
    return out

def positions(ms):
    x=START+((OFFSET+SPEED*(ms%DURATION_MS)/1000)%SPAN)
    return round(x),round(x-FOLLOW)

def actor_layer(ms):
    e,m=positions(ms)
    layer=Image.new('RGBA',(W,H))
    # Ground contact shadows translate with the actor; no terrain transform.
    shadows=Image.new('RGBA',(W,H))
    draw=ImageDraw.Draw(shadows)
    draw.ellipse((e-15,FLOOR-1,e+14,FLOOR+3),fill=(27,18,40,74))
    draw.ellipse((m-22,FLOOR-1,m+24,FLOOR+3),fill=(27,18,40,43))
    layer.alpha_composite(shadows.filter(ImageFilter.GaussianBlur(.65)))
    # Original pixels, original pose durations, original registration.
    layer.alpha_composite(mir[(ms//120)%6],(m-160,FLOOR-170))
    layer.alpha_composite(evan[(ms//180)%4],(e-47,FLOOR-96))
    return layer

def atmosphere(ms):
    layer=Image.new('RGBA',(W,H))
    draw=ImageDraw.Draw(layer)
    phase=(ms%WIND_MS)/WIND_MS
    for j in range(34):
        u=(phase+j*.61803398875)%1
        startx=(j*113)%765
        starty=28+(j*47)%132
        x=startx+68*u+9*math.sin(TAU*u+j)
        y=starty+110*u
        opacity=round(164*smooth(u/.12)*smooth((1-u)/.18))
        rx=1 if j%3 else 2
        draw.polygon([(x-rx,y),(x,y-1),(x+rx+1,y),(x+1,y+1)],fill=(255,175,207,opacity))
    # A few mail sheets follow the existing painted stack to its glowing inlet.
    for j in range(4):
        u=(phase+j/4)%1
        v=1-u
        x=v**3*613+3*v*v*u*625+3*v*u*u*699+u**3*733
        y=v**3*248+3*v*v*u*193+3*v*u*u*198+u**3*237
        alpha=round(230*smooth(u/.1)*smooth((1-u)/.15))
        paper=Image.new('RGBA',(12,9))
        pd=ImageDraw.Draw(paper)
        pd.rectangle((1,1,10,7),fill=(249,223,178,alpha),outline=(168,120,101,alpha))
        pd.line((3,3,8,3),fill=(190,149,126,alpha))
        pd.line((3,5,7,5),fill=(190,149,126,alpha))
        paper=paper.rotate(18*math.sin(TAU*u+j),Image.Resampling.NEAREST,expand=True)
        layer.alpha_composite(paper,(round(x-paper.width/2),round(y-paper.height/2)))
    return layer

def frame(ms):
    ms=round(ms)%DURATION_MS
    # Wind moves <0.5px per axis per 60ms; actors use finer 30ms travel steps.
    out=scenery((ms//60*60)%WIND_MS).convert('RGBA')
    out.alpha_composite(atmosphere(ms))
    out.alpha_composite(actor_layer(ms))
    return out.convert('RGB')

def samples():
    frame(0).save(OUT/'poster.png')
    contact=Image.new('RGB',(1200,450),'#14121b')
    d=ImageDraw.Draw(contact)
    for j in range(12):
        ms=j*60
        # Follow the two actors only in the review crop, at delivery pixel density.
        x,y=(j%4)*300,(j//4)*150
        center,_=positions(ms)
        patch=frame(ms).crop((center-180,170,center+120,320))
        contact.paste(patch,(x,y))
        d.text((x+4,y+4),f'{ms} ms',fill='white',stroke_width=1,stroke_fill='#21152e')
    contact.save(REVIEW/'motion-native-contact.png')
    sheet=Image.new('RGB',(W*2,H*2))
    for i,ms in enumerate((0,1680,3360,5040)):
        sheet.paste(scenery(ms),(i%2*W,i//2*H))
        ImageDraw.Draw(sheet).text((i%2*W+6,i//2*H+6),f'Wind: {ms/1000:.2f}s',fill='white',stroke_width=1,stroke_fill='black')
    sheet.save(REVIEW/'wind-extremes.jpg',quality=95)
    selected=(0,4500,9000,10320,10500,11520,14040,18000)
    travel=Image.new('RGB',(W*2,H*4))
    for i,ms in enumerate(selected):
        travel.paste(frame(ms),(i%2*W,i//2*H))
        ImageDraw.Draw(travel).text((i%2*W+6,i//2*H+6),f'{ms/1000:.2f}s',fill='white',stroke_width=1,stroke_fill='black')
    travel.save(REVIEW/'travel-contact.jpg',quality=94)
    print('Review samples saved',flush=True)

if __name__=='__main__':
    samples()

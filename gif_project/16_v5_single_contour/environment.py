from pathlib import Path
import math
from PIL import Image,ImageDraw,ImageFilter,ImageChops
ROOT=Path(__file__).resolve().parent
W,H=1200,522
S=W/1902
SECONDS=6
TAU=2*math.pi
base=Image.open(ROOT/'assets/clean-plate.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
def pt(x,y): return round(x*S),round(y*S)
def ease(v):
 v=max(0,min(1,v));return v*v*(3-2*v)
def fade(u):return ease(u/.09)*ease((1-u)/.12)
def wind(t):return (.5+.5*math.sin(TAU*(t%SECONDS)/SECONDS-.8))**4
crystals=[(720,332)]
def evan_index(t):return 0
def canopy(t):
    phase=(t%SECONDS)/SECONDS
    gust=wind(t)
    def source(x,y):
        # Motion fades out above the horizon; left trunk/root and ground are locked.
        # Small isolated blossom/branch-tip regions, anchored on every boundary.
        dx=dy=0
        for j,(cx,cy,rx,ry) in enumerate(((580,65,150,70),(800,105,130,80),(1030,95,145,90),(640,220,110,55))):
            q=((x-cx)/rx)**2+((y-cy)/ry)**2
            env=max(0,1-q)**2
            strength=.8+3.0*gust
            dx+=strength*env*math.sin(TAU*phase+j*.55)
            dy+=.65*env*(.4+gust)*math.sin(TAU*phase+j*.55+.5)
        # Bounded depth drift, not a global camera move or seamless world traversal.
        valley=max(0,1-((x-635)/280)**2-((y-300)/48)**2)**2
        dx+=.35*valley*math.sin(TAU*phase)
        # Near grasses move more than distant valley; foot-contact area is locked.
        for cx in (170,1000):
            grass=max(0,1-((x-cx)/145)**2-((y-425)/17)**2)**2
            dx+=1.5*grass*(.4+gust)*math.sin(TAU*phase+.3)
        return (x+dx,y+dy)
    mesh=[]
    for y in range(0,H,30):
        for x in range(0,W,40):
            r,b=min(W,x+40),min(H,y+30)
            quad=source(x,y)+source(x,b)+source(r,b)+source(r,y)
            mesh.append(((x,y,r,b),quad))
    return base.transform((W,H),Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)

# Small reusable pixel sprites: authored animation assets, not claimed extracted layers.
paper=Image.new('RGBA',(25,19)); d=ImageDraw.Draw(paper)
d.polygon([(2,1),(23,1),(21,17),(0,17)], fill='#f9dfb2',outline='#a87865')
d.line([(4,4),(19,4)],fill='#d0a887',width=1)
for y in (7,10,13): d.line([(4,y),(18-(y%3),y)],fill='#b68d7e',width=1)
petal=Image.new('RGBA',(13,9)); d=ImageDraw.Draw(petal)
d.polygon([(0,5),(3,2),(8,0),(12,2),(10,6),(5,8)],fill='#f5a1ca')
d.line([(2,5),(10,2)], fill='#ffe0e7',width=1)
glow=Image.new('RGBA',(101,101)); gd=ImageDraw.Draw(glow)
for r in range(48,0,-1):
    a=round(90*(1-r/49)**2)
    gd.ellipse((50-r,50-r,50+r,50+r), fill=(101,222,255,a))

def paste_alpha(layer,sprite,x,y,alpha=1):
    sprite=sprite.copy()
    if alpha<1: sprite.putalpha(sprite.getchannel('A').point(lambda a:round(a*max(0,alpha))))
    layer.alpha_composite(sprite,(round(x-sprite.width/2),round(y-sprite.height/2)))

def path(u):
    v=1-u
    return pt(v**3*1480+3*v*v*u*1510+3*v*u*u*1675+u**3*1737,
              v**3*588+3*v*v*u*450+3*v*u*u*480+u**3*568)

def layers(t):
    phase=(t%SECONDS)/SECONDS
    light=Image.new('RGBA',(W,H)); ld=ImageDraw.Draw(light)
    pulse=.43+.12*math.sin(TAU*phase)+.09*wind(t)
    x,y=crystals[evan_index(t)]
    paste_alpha(light,glow,x,y,pulse)
    # A restrained crystal shimmer, continuous rather than random flashes.
    rad=3+1.2*math.sin(TAU*phase)
    ld.line((x-rad,y,x+rad,y),fill=(188,247,255,round(135*pulse)),width=1)
    ld.line((x,y-rad,x,y+rad),fill=(188,247,255,round(135*pulse)),width=1)
    coords=[path(j/80) for j in range(81)]
    ld.line(coords,fill=(115,216,241,48),width=1)
    # Tiny traveling motes remain on the same postal route.
    for j in range(8):
        u=(phase+j/8)%1; xx,yy=path(u)
        ld.rectangle((xx,yy+5,xx+1,yy+6),fill=(172,239,248,round(105*fade(u))))
    # Completion indicator breathes once per arriving sheet.
    q=(phase*6)%1
    check=.28+.5*(.5+.5*math.cos(TAU*q))
    xx,yy=pt(1745,511)
    paste_alpha(light,glow.resize((43,43)),xx,yy,check)
    papers=Image.new('RGBA',(W,H))
    for j,offset in enumerate((0,.125,.32,.465,.69,.84)):
        u=(phase+offset)%1
        # Each sheet has its own smooth speed curve, route height and flutter.
        travel=u+.045*math.sin(TAU*u+j*.7)*math.sin(math.pi*u)
        travel=max(0,min(1,travel))
        xx,yy=path(travel)
        yy+=math.sin(math.pi*u)*(3*math.sin(TAU*u+j)+((j%3)-1)*4)
        angle=20*math.sin(TAU*u+j*.9)-15+27*u
        scale=.74+.2*math.sin(math.pi*u)+.06*(j%3)
        spr=paper.resize((round(25*scale),round(19*scale)),Image.Resampling.NEAREST).rotate(angle,Image.Resampling.NEAREST,expand=True)
        paste_alpha(papers,spr,xx,yy,fade(u))
    petals=Image.new('RGBA',(W,H))
    for j in range(68):
        depth=j%3
        u=(phase*(1 if depth==0 else 2)+j*.61803398875)%1
        startx=30+(j*173)%1740
        starty=170+(j*71)%310
        breeze=wind(t)
        xx,yy=pt(startx+(110+depth*65)*u+(18+depth*9)*math.sin(TAU*u+j)+breeze*(22+depth*16),starty+(110+depth*35)*u-8*breeze*math.sin(j))
        size=(.35,.7,1.05)[depth]+.08*(j%3)
        # Flutter changes width while retaining the same tiny pixel sprite.
        flutter=.45+.55*abs(math.cos(TAU*u+j))
        spr=petal.resize((max(2,round(13*size*flutter)),max(2,round(9*size))),Image.Resampling.NEAREST)
        spr=spr.rotate(35*math.sin(TAU*u+j),Image.Resampling.NEAREST,expand=True)
        paste_alpha(petals,spr,xx,yy,(.55,.72,.82)[depth]*fade(u))
    return light,papers,petals

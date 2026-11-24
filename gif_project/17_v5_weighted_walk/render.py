from pathlib import Path
import math,sys
from PIL import Image,ImageDraw,ImageFilter,ImageChops,ImageStat,ImageSequence,ImageEnhance
from terrain import apply_terrain
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'exports'; OUT.mkdir(exist_ok=True)
src=ROOT/'environment.py'
ns={'__file__':str(src)}
environment_code=src.read_text(encoding='utf-8')
exec(compile(environment_code,str(src),'exec'),ns)
W,H=1200,522
FPS,T,CYCLE,SPEED=25,12,1.5,20
Q=3
AX,AY,AW,AH=450,285,320,160
TAU=2*math.pi
sheet=Image.open(ROOT/'assets/rig-atlas.png').convert('RGBA')
parts=[]
for j in range(7):
    x0=round(j%4*sheet.width/4); y0=round(j//4*sheet.height/2)
    x1=round((j%4+1)*sheet.width/4); y1=round((j//4+1)*sheet.height/2)
    a=sheet.crop((x0+3,y0+3,x1-3,y1-3))
    # Ignore faint grid-line artifacts in the generated atlas.
    a.putalpha(a.getchannel('A').point(lambda v:0 if v<100 else v))
    b=a.getchannel('A').getbbox(); a=a.crop(b)
    parts.append(a)
sizes=[(61,81),(15,37),(50,81),(15,37),(120,74),(17,29),(24,29)]
parts=[im.resize((sz[0]*Q,sz[1]*Q),Image.Resampling.LANCZOS) for im,sz in zip(parts,sizes)]
for j,im in enumerate(parts): im.save(ROOT/'assets'/f'part-{j}.png')
eb,ea,es,el,mb,mf,mh=parts
def foot(t,offset=0,duty=.62,height=6):
    p=(t/CYCLE+offset)%1
    stride=SPEED*CYCLE*duty
    if p<duty:return stride/2-SPEED*CYCLE*p,0,True
    u=(p-duty)/(1-duty)
    # Hermite return: position AND velocity match stance at both boundaries.
    slope=-SPEED*CYCLE*(1-duty)
    x=-stride/2+stride*(3*u*u-2*u**3)+slope*(2*u**3-3*u*u+u)
    lift=height*math.sin(math.pi*u)**2
    return x,lift,False

def flex(im,kind,p):
    """Deform one continuous painted layer; do not crossfade duplicate silhouettes."""
    pad=4*Q
    src=Image.new('RGBA',(im.width+pad*2,im.height+pad*2));src.alpha_composite(im,(pad,pad))
    def source(x,y):
        xx,yy=(x-pad)/Q,(y-pad)/Q
        if kind=='evan':
            hem=max(0,min(1,(yy-50)/25))*max(0,min(1,(43-xx)/34))
            chest=max(0,1-abs(yy-44)/24)
            dx=.65*math.sin(p)*chest
            dy=2.1*math.sin(p-.65)*hem
        else:
            tail=max(0,min(1,(53-xx)/48))*max(0,min(1,(yy-34)/12))
            wing=max(0,1-((xx-43)/42)**2-((yy-28)/24)**2)
            head=max(0,min(1,(xx-85)/25))*max(0,min(1,(51-yy)/25))
            dx=.5*math.sin(p+.3)*wing
            dy=2.0*math.sin(p-.75)*tail+.9*math.sin(p+.4)*wing+.45*math.sin(p+.1)*head
        return x-dx*Q,y-dy*Q
    mesh=[]
    for y in range(0,src.height,6*Q):
        for x in range(0,src.width,6*Q):
            r,b=min(x+6*Q,src.width),min(y+6*Q,src.height)
            mesh.append(((x,y,r,b),source(x,y)+source(x,b)+source(r,b)+source(r,y)))
    return src.transform(src.size,Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)

def attach(canvas,im,pivot,anchor,angle):
    px,py=pivot[0]*Q,pivot[1]*Q
    ax,ay=(anchor[0]-AX)*Q,(anchor[1]-AY)*Q
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    points=[(ax+c*(x-px)+s*(y-py),ay-s*(x-px)+c*(y-py)) for x,y in ((0,0),(im.width,0),(0,im.height),(im.width,im.height))]
    left=math.floor(min(p[0] for p in points))-2;top=math.floor(min(p[1] for p in points))-2
    right=math.ceil(max(p[0] for p in points))+2;bottom=math.ceil(max(p[1] for p in points))+2
    coeff=(c,-s,c*(left-ax)-s*(top-ay)+px,s,c,s*(left-ax)+c*(top-ay)+py)
    out=im.transform((right-left,bottom-top),Image.Transform.AFFINE,coeff,Image.Resampling.BICUBIC)
    canvas.alpha_composite(out,(left,top))

def segment(canvas,im,source_pivot,joint,target,length):
    angle=math.degrees(math.atan2(target[0]-joint[0],target[1]-joint[1]))
    attach(canvas,im,source_pivot,joint,angle)

def leg(canvas,texture,hip,dx,lift,baseline,kind='evan',dark=False):
    tex=ImageEnhance.Brightness(texture).enhance(.75) if dark else texture
    width,height=tex.width/Q,tex.height/Q
    if kind=='evan':
        cut1,cut2=16,29; L1,L2=19,20; pawh=6
    elif kind=='front':
        cut1,cut2=13,24; L1,L2=14,15; pawh=5
    else:
        cut1,cut2=13,24; L1,L2=15,15; pawh=5
    ankle=(hip[0]+dx,baseline-lift-pawh)
    vx,vy=ankle[0]-hip[0],ankle[1]-hip[1]
    distance=math.hypot(vx,vy)
    assert distance<L1+L2+.01,(kind,distance,L1+L2)
    direction=math.atan2(vy,vx)
    turn=math.acos(max(-1,min(1,(L1*L1+distance*distance-L2*L2)/(2*L1*distance))))
    # Hind knee folds backwards; human and foreleg knees bend forwards.
    side=-1 if kind=='hind' else 1
    knee=(hip[0]+L1*math.cos(direction-side*turn),hip[1]+L1*math.sin(direction-side*turn))
    upper=tex.crop((0,0,tex.width,round((cut1+3)*Q))).resize((tex.width,round((L1+3)*Q)),Image.Resampling.LANCZOS)
    lower=tex.crop((0,round((cut1-2)*Q),tex.width,round((cut2+2)*Q))).resize((tex.width,round((L2+4)*Q)),Image.Resampling.LANCZOS)
    paw=tex.crop((0,round((cut2-1)*Q),tex.width,tex.height)).resize((tex.width,round((pawh+2)*Q)),Image.Resampling.LANCZOS)
    if kind!='evan':
        # Feather the cut ends of the original painted parts into rounded joints.
        # All texture sizes stay constant throughout the gait.
        for piece in (upper,lower):
            edge=Image.new('L',piece.size)
            ed=ImageDraw.Draw(edge)
            ed.rounded_rectangle((0,0,piece.width-1,piece.height-1),radius=4*Q,fill=255)
            piece.putalpha(ImageChops.multiply(piece.getchannel('A'),edge))
        # The calf no longer carries the wide silhouette of the painted thigh.
        calf_width=13 if kind=='front' else 15
        lower=lower.resize((calf_width*Q,lower.height),Image.Resampling.LANCZOS)
        lower_pivot=(calf_width*.43,2)
    else:
        lower_pivot=(width*.43,2)
    segment(canvas,upper,(width*.43,1),hip,knee,L1)
    segment(canvas,lower,lower_pivot,knee,ankle,L2)
    # Keep the sole level through stance; no skewing the whole leg into a new shape.
    attach(canvas,paw,(width*.43,1),ankle,0)

def actors(t):
    im=Image.new('RGBA',(AW*Q,AH*Q));d=ImageDraw.Draw(im)
    p=TAU*t/CYCLE
    bob=.8*math.cos(2*p)
    ey=313+bob; ex=652
    # All joint anchors move with the pelvis, never with a changing sprite box.
    sway=.6*math.sin(2*p)
    hip=(ex+40+sway,ey+76)
    for cx,rx in ((692,25),(548,47)):
        d.ellipse(tuple(round(v*Q) for v in (cx-rx-AX,430-AY,cx+rx-AX,435-AY)),fill=(32,23,39,65))
    dx,lift,contact=foot(t,.5)
    leg(im,el,(hip[0]-3,hip[1]),dx-sway,lift,430,dark=True)
    attach(im,ea,(7,5),(ex+34+sway,ey+44),-16*math.sin(p))
    # Coat and torso lean only one degree, so identity does not oscillate in size.
    dx,lift,contact=foot(t)
    leg(im,el,hip,dx-sway,lift,432)
    # Body overlaps the leg roots, preventing seams at the hip.
    attach(im,flex(eb,'evan',p),(44,76),(hip[0],hip[1]-4),1.1*math.sin(p+.2))
    attach(im,es,(10,36),(ex+40+sway,ey+44),2.0*math.sin(p+.25))
    # A four-beat walk; each leg has fixed bone lengths and its own contact phase.
    mx,my=479,341+.45*math.cos(2*p+.8)
    for off,hx,hy,lim in ((.5,mx+66,my+60,mh),(.75,mx+96,my+60,mf)):
        dx,lift,c=foot(t,off+.12,.74,4)
        leg(im,lim,(hx-2,hy),dx,lift,430,'hind' if lim is mh else 'front',True)
    attach(im,flex(mb,'mir',p),(84,69),(mx+80,my+65),.45*math.sin(p+.8))
    for off,hx,hy,lim in ((0,mx+66,my+60,mh),(.25,mx+96,my+60,mf)):
        dx,lift,c=foot(t,off+.12,.74,4)
        leg(im,lim,(hx,hy),dx,lift,432,'hind' if lim is mh else 'front')
    out=Image.new('RGBA',(W,H))
    out.alpha_composite(im.resize((AW,AH),Image.Resampling.LANCZOS),(AX,AY))
    return out

def scenery(t):
    # One scenery pass only. Distant structures never receive crossfade copies.
    out=ns['canopy'](t/2)
    return apply_terrain(out,t)

def frame(t):
    t=round(t%T,8)
    out=scenery(t)
    light,papers,petals=ns['layers'](t/2)
    light.paste((0,0,0,0),(610,285,800,430))
    out=Image.alpha_composite(out,petals)
    out=Image.alpha_composite(out,actors(t))
    # Soft staff glow follows the rig's modest arm rotation.
    p=TAU*t/CYCLE; angle=math.radians(2*math.sin(p+.25))
    ax,ay=692+.6*math.sin(2*p),357+.8*math.cos(2*p)
    gx=ax+30*math.cos(angle)+(-32)*math.sin(angle)
    gy=ay-30*math.sin(angle)+(-32)*math.cos(angle)
    ns['paste_alpha'](light,ns['glow'],gx,gy,.25+.055*math.sin(TAU*t/T))
    out=Image.alpha_composite(out,light)
    out=Image.alpha_composite(out,papers)
    return out.convert('RGB')

if __name__=='__main__':
    if '--sample' in sys.argv:
        grid=Image.new('RGB',(1200,600))
        for j in range(16):
            f=frame(j*CYCLE/16)
            c=f.crop((450,297,750,447))
            grid.paste(c,((j%4)*300,(j//4)*150))
            ImageDraw.Draw(grid).text(((j%4)*300+4,(j//4)*150+4),f'{j*CYCLE/16:.3f}s',fill='white',stroke_width=1,stroke_fill='black')
        grid.save(OUT/'gait-review.png');frame(0).save(OUT/'poster.png')
        print('samples complete');sys.exit()
    from export import main
    main()

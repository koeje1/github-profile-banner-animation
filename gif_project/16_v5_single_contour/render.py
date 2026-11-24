from pathlib import Path
import math,json,sys,time,subprocess
from PIL import Image,ImageDraw,ImageFilter,ImageChops,ImageStat,ImageSequence,ImageEnhance
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
ground=Image.open(ROOT/'assets/ground-tile.png').convert('RGBA').resize((240,80),Image.Resampling.LANCZOS)
# Blend the tile's small edge mismatch in texture space, once, not at loop playback.
pix=ground.load()
for y in range(80):
    for k in range(8):
        a=pix[k,y]; b=pix[239-k,y]; q=(8-k)/16
        pix[k,y]=tuple(round(a[c]*(1-q)+b[c]*q) for c in range(4))
        pix[239-k,y]=tuple(round(b[c]*(1-q)+a[c]*q) for c in range(4))
ground.save(ROOT/'assets/ground-tile-prepared.png')
road=Image.new('RGBA',(W+480,114))
for x in range(0,road.width,240):road.alpha_composite(ground,(x,0))
for y in range(80,114):
    ImageDraw.Draw(road).line((0,y,road.width,y),fill=(39,25,43,255))
mask=Image.new('L',(W,114));d=ImageDraw.Draw(mask)
for y in range(114):d.line((0,y,W,y),fill=round(255*min(1,y/10)))

def foot(t,offset=0):
    p=(t/CYCLE+offset)%1
    stride=SPEED*CYCLE*.5
    if p<.5:return stride*(.5-2*p),0,True
    u=(p-.5)*2
    # Hermite return: position AND velocity match stance at both boundaries.
    x=-stride/2+stride*(-4*u**3+6*u*u-u)
    lift=5.5*math.sin(math.pi*u)**2
    return x,lift,False

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
        cut1,cut2=16,29; L1,L2=18,20; pawh=6
    elif kind=='front':
        cut1,cut2=12,24; L1,L2=21,20; pawh=5
    else:
        cut1,cut2=12,24; L1,L2=15,16; pawh=5
    ankle=(hip[0]+dx,baseline-lift-pawh)
    if kind!='evan':
        # Preserve the painted dragon limb silhouette. Only its long axis rotates;
        # the paw is drawn level at the independently solved contact point.
        dist=math.hypot(ankle[0]-hip[0],ankle[1]-hip[1])
        upper=tex.crop((0,0,tex.width,round(25*Q))).resize((tex.width,round((dist+2)*Q)),Image.Resampling.LANCZOS)
        paw=tex.crop((0,round(23*Q),tex.width,tex.height)).resize((tex.width,round((pawh+2)*Q)),Image.Resampling.LANCZOS)
        segment(canvas,upper,(width*.43,1),hip,ankle,dist)
        attach(canvas,paw,(width*.43,1),ankle,0)
        return
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
    segment(canvas,upper,(width*.43,1),hip,knee,L1)
    segment(canvas,lower,(width*.43,2),knee,ankle,L2)
    # Keep the sole level through stance; no skewing the whole leg into a new shape.
    attach(canvas,paw,(width*.43,1),ankle,0)

def actors(t):
    im=Image.new('RGBA',(AW*Q,AH*Q));d=ImageDraw.Draw(im)
    p=TAU*t/CYCLE
    bob=1.0*math.cos(2*p)
    ey=314+bob; ex=652
    # All joint anchors move with the pelvis, never with a changing sprite box.
    hip=(ex+40,ey+76)
    for cx,rx in ((692,25),(548,47)):
        d.ellipse(tuple(round(v*Q) for v in (cx-rx-AX,430-AY,cx+rx-AX,435-AY)),fill=(32,23,39,65))
    dx,lift,contact=foot(t,.5)
    leg(im,el,(hip[0]-3,hip[1]),dx,lift,431,dark=True)
    attach(im,ea,(7,5),(ex+34,ey+44),-13*math.sin(p))
    # Coat and torso lean only one degree, so identity does not oscillate in size.
    dx,lift,contact=foot(t)
    leg(im,el,hip,dx,lift,431)
    # Body overlaps the leg roots, preventing seams at the hip.
    attach(im,eb,(40,72),(hip[0],hip[1]-4),.7*math.sin(p))
    attach(im,es,(10,36),(ex+40,ey+44),3.0*math.sin(p+.25))
    # Mir's opposing diagonal pairs follow the same ground velocity.
    mx,my=479,334+.65*math.cos(2*p+.8)
    for off,hx,hy,lim in ((.5,mx+72,my+66,mh),(0,mx+89,my+64,mf)):
        dx,lift,c=foot(t,off+.12)
        leg(im,lim,(hx-2,hy),dx,lift*.75,431,'hind' if lim is mh else 'front',True)
    attach(im,mb,(80,65),(mx+80,my+65),.6*math.sin(p+.8))
    for off,hx,hy,lim in ((0,mx+72,my+66,mh),(.5,mx+89,my+64,mf)):
        dx,lift,c=foot(t,off+.12)
        leg(im,lim,(hx,hy),dx,lift*.75,431,'hind' if lim is mh else 'front')
    out=Image.new('RGBA',(W,H))
    out.alpha_composite(im.resize((AW,AH),Image.Resampling.LANCZOS),(AX,AY))
    return out

def scenery(t):
    # One scenery pass only. Distant structures never receive crossfade copies.
    out=ns['canopy'](t/2)
    # Road is the physical contact plane and scrolls exactly at stance speed.
    shift=(SPEED*t)%240
    strip=road.transform((W,114),Image.Transform.AFFINE,(1,0,shift,0,1,0),Image.Resampling.BICUBIC)
    out.paste(strip,(0,414),mask)
    return out

def frame(t):
    t=round(t%T,8)
    out=scenery(t)
    light,papers,petals=ns['layers'](t/2)
    light.paste((0,0,0,0),(610,285,800,430))
    out=Image.alpha_composite(out,petals)
    out=Image.alpha_composite(out,actors(t))
    # Soft staff glow follows the rig's modest arm rotation.
    p=TAU*t/CYCLE; angle=math.radians(3*math.sin(p+.25))
    ax,ay=692,358+math.cos(2*p)
    gx=ax+30*math.cos(angle)-(-32)*math.sin(angle)
    gy=ay-30*math.sin(angle)+(-32)*math.cos(angle)
    ns['paste_alpha'](light,ns['glow'],gx,gy,.25+.055*math.sin(TAU*t/T))
    out=Image.alpha_composite(out,light)
    out=Image.alpha_composite(out,papers)
    return out.convert('RGB')

if __name__=='__main__':
    if '--sample' in sys.argv:
        grid=Image.new('RGB',(900,360))
        for j in range(8):
            f=frame(j*CYCLE/8)
            c=f.crop((455,305,745,443)).resize((225,180),Image.Resampling.NEAREST)
            grid.paste(c,((j%4)*225,(j//4)*180))
        grid.save(OUT/'gait-review.png');frame(0).save(OUT/'poster.png')
        print('samples complete');sys.exit()
    frames=[]
    for i in range(T*FPS):
        frames.append(frame(i/FPS))
        if i%50==0: print('render',i,flush=True)
    for page in range(12):
        grid=Image.new('RGB',(1450,750))
        for j in range(25):
            i=page*25+j
            crop=frames[i].crop((455,300,745,443))
            grid.paste(crop,((j%5)*290,(j//5)*150))
            ImageDraw.Draw(grid).text(((j%5)*290+3,(j//5)*150+2),f'{i:03d} {i/FPS:.2f}s',fill='white',stroke_width=1,stroke_fill='black')
        grid.save(ROOT/'review'/f'all-frames-{page:02d}.jpg',quality=94)
    for page in range(3):
        grid=Image.new('RGB',(1600,696))
        for j in range(16):
            i=min(299,page*100+j*6)
            grid.paste(frames[i].resize((400,174)),((j%4)*400,(j//4)*174))
        grid.save(ROOT/'review'/f'scenes-{page}.jpg',quality=94)
    frames[0].save(OUT/'poster.png')
    sample=Image.new('RGB',(W,H*4))
    for j,i in enumerate((0,53,117,185)):sample.paste(frames[i],(0,j*H))
    pal=sample.quantize(colors=256)
    indexed=[f.resize((800,348),Image.Resampling.LANCZOS).quantize(palette=pal,dither=Image.Dither.NONE) for f in frames]
    gif=OUT/'banner-v5-single-contour.gif'
    indexed[0].save(gif,save_all=True,append_images=indexed[1:],duration=40,loop=0,disposal=1,optimize=False)
    small=[f.resize((960,418),Image.Resampling.LANCZOS) for f in frames]
    small[0].save(OUT/'banner-v5-single-contour.webp',save_all=True,append_images=small[1:],duration=40,loop=0,lossless=True,method=4)
    import imageio_ffmpeg
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    proc=subprocess.Popen([ff,'-y','-f','rawvideo','-vcodec','rawvideo','-s',f'{W}x{H}','-pix_fmt','rgb24','-r',str(FPS),'-i','-','-an','-vcodec','libx264','-pix_fmt','yuv420p','-crf','18','-movflags','+faststart',str(OUT/'banner-v5-single-contour.mp4')],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
    for f in frames:proc.stdin.write(f.tobytes())
    proc.stdin.close();assert proc.wait()==0
    def delta(a,b):return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
    steps=[delta(frames[i-1],frames[i]) for i in range(1,len(frames))]
    seam=delta(frames[-1],frames[0])
    assert ImageChops.difference(frame(0),frame(T)).getbbox() is None
    assert ImageChops.difference(frame(.04),frame(T+.04)).getbbox() is None
    with Image.open(gif) as check:
        assert check.info['loop']==0
        decoded=[f.convert('RGB') for f in ImageSequence.Iterator(check)]
        assert len(decoded)==300
        assert all(ImageChops.difference(a,b.convert('RGB')).getbbox() is None for a,b in zip(decoded,indexed))
    # Check world-space stance contact, excluding phase boundaries.
    error=max(abs((foot(t+.001)[0]-foot(t)[0])/.001+SPEED) for t in (.1,.2,.3,.4,.5,.6))
    assert error<1e-7
    report={'frames':300,'duration_ms':12000,'fps':25,'infinite_loop':True,'exact_endpoint_equality':True,'next_frame_periodicity':True,'seam_pixel_MAD':seam,'ordinary_step_mean_MAD':sum(steps)/len(steps),'ordinary_step_max_MAD':max(steps),'stance_vs_ground_velocity_error_px_per_second':error,'ground_speed_px_per_second':20,'gait_cycle_seconds':1.5,'stride_px':15,'decoded_gif_matches_all_frames':True,'gif_bytes':gif.stat().st_size,'background_method':'single painted background, local canopy wind; true 240px tiled foreground, no crossfade','visual_limitations':['2D cutout rig, not hand-drawn full skeletal animation','distant landscape remains fixed; foreground provides scrolling parallax'],'browser_playback':'not verified: browser new-tab connection failure; native player app approval timed out'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

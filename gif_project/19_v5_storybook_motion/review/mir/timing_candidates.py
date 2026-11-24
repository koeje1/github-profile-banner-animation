"""Review-only timing candidates; leave source pose PNGs and root render untouched."""
from pathlib import Path
import json
import math
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FRAMES = [Image.open(ROOT / f'assets/mir/frame-{i}.png').convert('RGBA') for i in range(8)]
BASE = Image.open(ROOT.parent / '17_v5_weighted_walk/assets/clean-plate.png').convert('RGBA').resize((800,348),Image.Resampling.LANCZOS)
CANDIDATES = [
    {'id':'original', 'label':'A / Original', 'order':[0,1,2,3,4,5,6,7], 'durations_ms':[120]*8,
     'bob_phase_ms':60, 'recommended':False},
    {'id':'pingpong', 'label':'B / Ping-pong', 'order':[0,1,2,3,4,3,2,1],
     'durations_ms':[150,120,90,90,120,90,150,150], 'bob_phase_ms':30, 'recommended':True},
    {'id':'bridge', 'label':'C / Recovery bridge', 'order':[0,1,2,3,4,3,5,6,7],
     'durations_ms':[120,90,90,90,90,90,120,120,150], 'bob_phase_ms':-45, 'recommended':False},
]


def pose_at(candidate, ms):
    phase = ms % candidate['cycle_ms']
    for index, duration in zip(candidate['order'],candidate['durations_ms']):
        if phase < duration:
            return index
        phase -= duration
    raise AssertionError('unreachable')


def bob_at(candidate, ms):
    return round(math.cos(math.tau * (ms - candidate['bob_phase_ms']) / candidate['cycle_ms']))


def check(size=(160,100)):
    im = Image.new('RGBA',size,(240,236,231,255))
    d = ImageDraw.Draw(im)
    for y in range(0,size[1],10):
        for x in range(0,size[0],10):
            if (x//10+y//10)%2:
                d.rectangle((x,y,x+9,y+9),fill=(224,220,215,255))
    return im


def metrics(a,b):
    # Alpha-composited differences are descriptive only, not a smoothness score.
    aa=check();bb=check();aa.alpha_composite(FRAMES[a]);bb.alpha_composite(FRAMES[b])
    diff=ImageChops.difference(aa.convert('RGB'),bb.convert('RGB'))
    return {'whole_mae':round(sum(ImageStat.Stat(diff).mean)/3,3),
            'head_neck_mae':round(sum(ImageStat.Stat(diff.crop((100,25,124,70))).mean)/3,3),
            'paw_region_mae':round(sum(ImageStat.Stat(diff.crop((87,67,124,86))).mean)/3,3)}


for c in CANDIDATES:
    c['cycle_ms']=sum(c['durations_ms'])
    assert c['cycle_ms']==960
    c['body_bob']={'amplitude_px':1.0, 'mean_body_y':251, 'screen_y_formula':'251 + round(cos(2*pi*(t-phase_ms)/960))',
                   'phase_ms':c['bob_phase_ms'], 'positive_y':'down', 'continuous_amplitude_range':[250,252]}
    c['transition_metrics']=[{'from':a,'to':b,**metrics(a,b)} for a,b in zip(c['order'],c['order'][1:]+c['order'][:1])]
    elapsed=0
    c['timeline']=[]
    for index,duration in zip(c['order'],c['durations_ms']):
        c['timeline'].append({'frame':index,'start_ms':elapsed,'duration_ms':duration,'end_ms':elapsed+duration})
        elapsed+=duration

doc={'source_pose_pattern':'../../assets/mir/frame-{index}.png','source_frames_modified':False,
     'canvas':[160,100],'body_anchor':[80,60],'frame_step_ms':30,'candidates':CANDIDATES,
     'recommended_id':'pingpong','recommendation_basis':'Independent static anatomy inspection favors retaining first-five-pose body consistency. The large 2<->3 wing angle jump remains.',
     'screen_playback_observed':False,
     'next_check':'Compare these review videos in actual playback, especially 2<->3 and the reversal at frame 4.'}
(HERE/'timing-candidates.json').write_text(json.dumps(doc,indent=2),encoding='utf-8')

contact=Image.new('RGB',(1440,396),(246,241,235))
draw=ImageDraw.Draw(contact)
for row,c in enumerate(CANDIDATES):
    y=row*132
    draw.text((8,y+3),c['label']+'  /  960ms',fill=(47,37,44))
    for column,(index,duration) in enumerate(zip(c['order'],c['durations_ms'])):
        one=check();one.alpha_composite(FRAMES[index]);contact.paste(one.convert('RGB'),(column*160,y+18))
        draw.text((column*160+8,y+118),f'{index}: {duration}ms',fill=(47,37,44))
contact.save(HERE/'timing-candidate-contact.png')


def comparison(ms):
    canvas=Image.new('RGB',(960,430),(246,241,235))
    draw=ImageDraw.Draw(canvas)
    for column,c in enumerate(CANDIDATES):
        index=pose_at(c,ms);dy=bob_at(c,ms)
        x=column*320
        draw.text((x+8,3),f"{c['label']} / pose {index} / bob {dy:+d}px",fill=(47,37,44))
        scene=BASE.copy()
        shadow=Image.new('RGBA',scene.size)
        ImageDraw.Draw(shadow).ellipse((328,286,375,290),fill=(35,20,43,32))
        scene.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(.8)))
        scene.alpha_composite(FRAMES[index],(350-80,251-60+dy))
        canvas.paste(scene.crop((220,137,540,317)).convert('RGB'),(x,20))
        draw.text((x+8,211),f'2x view / t={ms%960:03d}ms',fill=(47,37,44))
        one=check();one.alpha_composite(FRAMES[index],(0,dy))
        canvas.paste(one.resize((320,200),Image.Resampling.NEAREST).convert('RGB'),(x,230))
    return canvas


video=HERE/'timing-candidates.mp4'
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
process=subprocess.Popen([ffmpeg,'-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-s','960x430',
                          '-pix_fmt','rgb24','-r','100/3','-i','-','-an','-c:v','libx264','-pix_fmt','yuv420p',
                          '-crf','16','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
for ms in range(0,4800,30):
    process.stdin.write(comparison(ms).tobytes())
process.stdin.close()
error=process.stderr.read().decode('utf-8',errors='replace')
assert process.wait()==0,error
check_decode=subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
assert check_decode.returncode==0,check_decode.stderr
comparison(450).save(HERE/'timing-candidates-poster.png')
print(json.dumps({'recommended_id':'pingpong','candidate_ids':[c['id'] for c in CANDIDATES],
                  'duration_ms':4800,'frame_count':160,'mp4_decode_errors':check_decode.stderr,
                  'path':str(video),'source_assets_modified':False},indent=2))

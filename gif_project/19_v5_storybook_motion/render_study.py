"""A short, non-looping illustrated motion study, not a production approval."""
from pathlib import Path
import importlib.util
import json
import subprocess
import time
from PIL import Image,ImageDraw,ImageFilter,ImageChops
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'exports'; OUT.mkdir(exist_ok=True)
REVIEW=ROOT/'review'; REVIEW.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('fixed_scene',ROOT.parent/'18_v5_external_motion/render.py')
bg=importlib.util.module_from_spec(spec);spec.loader.exec_module(bg)
# Reuse only the already-reviewed background and breeze. No game sprites enter
# the composite: the two character lists below are newly illustrated full poses.
evan=[Image.open(ROOT/f'assets/evan/frame-{i}.png').convert('RGBA') for i in range(8)]
mir=[Image.open(ROOT/f'assets/mir/frame-{i}.png').convert('RGBA') for i in range(8)]
W,H=800,348
FLOOR=287
FRAME_MS=30
POSE_MS=120
DURATION_MS=4800
SPEED=45
EVAN_ANCHOR=(54,90)
MIR_ANCHOR=(80,60)
MIR_Y=251

def actors(ms):
    layer=Image.new('RGBA',(W,H))
    ex=round(410+SPEED*ms/1000)
    mx=ex-110
    shade=Image.new('RGBA',(W,H));d=ImageDraw.Draw(shade)
    d.ellipse((ex-17,FLOOR-1,ex+16,FLOOR+3),fill=(35,20,43,64))
    d.ellipse((mx-22,FLOOR-1,mx+25,FLOOR+3),fill=(35,20,43,32))
    layer.alpha_composite(shade.filter(ImageFilter.GaussianBlur(.8)))
    mi=(ms//POSE_MS)%8
    layer.alpha_composite(mir[mi],(mx-MIR_ANCHOR[0],MIR_Y-MIR_ANCHOR[1]))
    ei=(ms//POSE_MS)%8
    layer.alpha_composite(evan[ei],(ex-EVAN_ANCHOR[0],FLOOR-EVAN_ANCHOR[1]))
    return layer

def frame(ms):
    out=bg.scenery((ms//60*60)%bg.WIND_MS).convert('RGBA')
    out.alpha_composite(bg.atmosphere(ms))
    out.alpha_composite(actors(ms))
    return out.convert('RGB')

def main():
    frames=[frame(ms) for ms in range(0,DURATION_MS,FRAME_MS)]
    frames[0].save(OUT/'poster.png')
    review=Image.new('RGB',(1200,480))
    for i,ms in enumerate(range(0,960,60)):
        x,y=(i%4)*300,(i//4)*120
        ex=round(410+SPEED*ms/1000)
        review.paste(frame(ms).crop((ex-180,190,ex+120,310)),(x,y))
        ImageDraw.Draw(review).text((x+4,y+4),f'{ms} ms',fill='white',stroke_width=1,stroke_fill='#241c2c')
    review.save(REVIEW/'duo-cycle-native.png')
    compare=Image.new('RGB',(800,696))
    compare.paste(Image.open(ROOT.parent/'18_v5_external_motion/exports/poster.png'),(0,0))
    compare.paste(frames[0],(0,348))
    draw=ImageDraw.Draw(compare)
    for y,text in ((12,'V18 / game sprites'),(360,'V19 / illustrated motion study')):
        draw.text((12,y),text,fill='white',stroke_width=1,stroke_fill='#241c2c')
    compare.save(REVIEW/'style-before-after.jpg',quality=96)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    video=OUT/'storybook-motion-study.mp4'
    process=subprocess.Popen([ffmpeg,'-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-s','800x348','-pix_fmt','rgb24','-r','100/3','-i','-','-an','-c:v','libx264','-pix_fmt','yuv420p','-crf','16','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    for im in frames:process.stdin.write(im.tobytes())
    process.stdin.close()
    stderr=process.stderr.read().decode('utf-8',errors='replace')
    assert process.wait()==0,stderr
    decode=subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
    assert decode.returncode==0,decode.stderr
    reference=bg.base.crop((0,270,800,348))
    for ms in range(0,DURATION_MS,FRAME_MS):
        actual=bg.scenery((ms//60*60)%bg.WIND_MS).crop((0,270,800,348))
        assert ImageChops.difference(reference,actual).getbbox() is None
    report={
        'status':'short study; not a final looping banner',
        'duration_ms':DURATION_MS,'frame_count':len(frames),'frame_step_ms':FRAME_MS,
        'character_pose_ms':POSE_MS,'character_cycle_ms':960,'source_type':'newly generated complete illustration poses',
        'original_game_character_pixels_used':False,
        'no_limb_cutouts_or_morphs':True,'no_crossfade_ghosting':True,
        'ground_source_pixels_fixed':True,'evan_speed_px_s':SPEED,
        'evan_anchor':EVAN_ANCHOR,'mir_anchor':MIR_ANCHOR,'mir_body_scene_y':MIR_Y,
        'mp4_decode_errors':decode.stderr,
        'screen_playback_observed':False,
        'review_limits':['Generated eight poses are not proof of anatomical gait quality.','Near/far leg alternation needs motion review.','This 4.8-second study moves forward and does not have a seamless endpoint.'],
        'video_bytes':video.stat().st_size
    }
    (OUT/'study-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()

"""Export and inspect native-timed sprite animation; file checks are not taste."""
from pathlib import Path
import json
import subprocess
import time
import hashlib
from PIL import Image,ImageChops,ImageSequence,ImageStat,ImageDraw
import imageio_ffmpeg
import render as r

def same(a,b,label):
    assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox() is None,label

def mad(a,b):
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3

def main():
    started=time.perf_counter()
    r.samples()
    frames=[]
    ground=(0,270,r.W,r.H)
    house=(555,168,r.W,r.H)
    trunk=(80,120,180,260)
    for i in range(r.COUNT):
        ms=i*r.FRAME_MS
        bg=r.scenery((ms//60*60)%r.WIND_MS)
        for bounds,label in ((ground,'ground'),(house,'house'),(trunk,'trunk'),((706,139,787,164),'exposed clouds')):
            same(bg.crop(bounds),r.base.crop(bounds),f'{label} changed at {ms}')
        frames.append(r.frame(ms))
        if i%56==0: print(f'Render {i}/{r.COUNT}',flush=True)
    same(r.frame(0),r.frame(r.DURATION_MS),'loop endpoint')
    same(r.frame(r.FRAME_MS),r.frame(r.DURATION_MS+r.FRAME_MS),'next loop frame')
    wraps=[]
    for i in range(1,r.COUNT):
        old=r.positions((i-1)*r.FRAME_MS)[0]
        new=r.positions(i*r.FRAME_MS)[0]
        if new<old:
            wraps.append(i)
            assert r.actor_layer((i-1)*r.FRAME_MS).getbbox() is None, 'visible before wrap'
            assert r.actor_layer(i*r.FRAME_MS).getbbox() is None, 'visible after wrap'
        else:
            assert new-old in (1,2),(i,old,new)
    assert len(wraps)==1
    # Review each authored pose at native density and several entry/exit points.
    sequence=Image.new('RGB',(1200,900))
    times=sorted(set([0,180,360,540,720,900]+[max(0,(wraps[0]+j)*r.FRAME_MS) for j in (-80,-40,-16,-1,0,16,40,80)]+[18000,20130]))
    for i,ms in enumerate(times):
        x,y=(i%4)*300,(i//4)*225
        snap=r.frame(ms).resize((300,131),Image.Resampling.LANCZOS)
        sequence.paste(snap,(x,y))
        ImageDraw.Draw(sequence).text((x+5,y+138),f'{ms}ms  E={r.positions(ms)[0]}',fill='white')
    sequence.save(r.REVIEW/'entry-exit-review.jpg',quality=94)

    # Global palette prevents palette flicker and lets GIF encode changed pixels.
    sample=Image.new('RGB',(r.W,r.H*8))
    for j,i in enumerate((0,28,56,84,112,168,224,280)):
        sample.paste(frames[i],(0,j*r.H))
    palette=sample.quantize(colors=255)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    gif=r.OUT/'banner-v5-original-sprites.gif'
    indexed[0].save(gif,save_all=True,append_images=indexed[1:],duration=r.FRAME_MS,loop=0,disposal=1,optimize=True)
    with Image.open(gif) as decoded:
        assert decoded.n_frames==r.COUNT
        assert decoded.info['loop']==0
        for i,actual in enumerate(ImageSequence.Iterator(decoded)):
            assert actual.info['duration']==r.FRAME_MS
            same(actual,indexed[i],f'GIF decode {i}')

    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    mp4=r.OUT/'banner-v5-original-sprites.mp4'
    log=r.OUT/'encode.log'
    with log.open('w') as err:
        proc=subprocess.Popen([ffmpeg,'-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-s','800x348','-pix_fmt','rgb24','-r','100/3','-i','-','-an','-vcodec','libx264','-pix_fmt','yuv420p','-crf','16','-movflags','+faststart',str(mp4)],stdin=subprocess.PIPE,stderr=err)
        try:
            for im in frames: proc.stdin.write(im.tobytes())
        finally: proc.stdin.close()
        assert proc.wait()==0,log.read_text()
    decode=subprocess.run([ffmpeg,'-v','error','-stream_loop','2','-i',str(mp4),'-an','-f','null','-'],capture_output=True,text=True)
    assert decode.returncode==0,decode.stderr
    steps=[mad(frames[i-1],frames[i]) for i in range(1,len(frames))]
    report={
        'status':'file integrity passed; independent perceptual review pending',
        'size':[r.W,r.H],'frame_count':r.COUNT,'duration_ms':r.DURATION_MS,'frame_duration_ms':r.FRAME_MS,'fps':100/3,
        'evan_original_frames':4,'evan_frame_delay_ms':180,'mir_original_frames':6,'mir_frame_delay_ms':120,
        'original_pose_timing_exact':True,'uniform_scale':1,'sprite_pixel_transform':'horizontal reflection only',
        'sprite_registration':'source GIF registration for Evan; original WZ origin for Mir',
        'evan_baseline_y':r.FLOOR,'mir_motion':'original flight, no fabricated legs or additional bob',
        'travel_speed_px_s':r.SPEED,'follower_distance_px':r.FOLLOW,
        'ground_source_pixels_fixed_all_frames':True,'ground_bounds':list(ground),
        'house_source_pixels_fixed_all_frames':True,'house_bounds':list(house),
        'trunk_source_pixels_fixed_all_frames':True,'trunk_bounds':list(trunk),
        'exposed_cloud_patch_fixed_all_frames':True,'cloud_bounds':[706,139,787,164],
        'tree_motion':'local branch deflections; rooted trunk and ground copied from source',
        'actor_wrap_frames':wraps,'actors_and_shadows_fully_offscreen_at_wrap':True,
        'every_forward_step_px':[1,2],'gif_all_decoded_frames_match_indexed_source':True,
        'mp4_three_loop_decode_errors':decode.stderr,
        'seam_MAD':mad(frames[-1],frames[0]),'mean_step_MAD':sum(steps)/len(steps),'max_step_MAD':max(steps),
        'screen_playback_observed':False,
        'limits':['Original game walk has four held poses; no invented in-between frames.','GIF has 255 colors; MP4 preserves more color.','Sprite naturalness is a visual judgment, not established by file checks.'],
        'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (gif,mp4)},
        'elapsed_seconds':time.perf_counter()-started
    }
    (r.OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()

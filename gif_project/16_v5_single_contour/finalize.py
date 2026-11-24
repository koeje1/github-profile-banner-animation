"""Compact delivery exports and verify against the lossless source sequence."""
from pathlib import Path
import runpy,json,subprocess,time
from PIL import Image,ImageSequence,ImageChops,ImageStat
import imageio_ffmpeg
R=Path(__file__).resolve().parent;O=R/'exports';V=R/'review'
n=runpy.run_path(str(R/'render.py'))
def mad(a,b):return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
master=V/'master-lossless.webp'
if not master.exists():(O/'banner-v5-single-contour.webp').replace(master)
with Image.open(master) as im: fs=[f.convert('RGB') for f in ImageSequence.Iterator(im)]
assert len(fs)==300
native=[];source_error=0
for i,f in enumerate(fs):
    a=n['frame'](i/25);native.append(a)
    source_error=max(source_error,mad(a.resize((960,418),Image.Resampling.LANCZOS),f))
    if i%75==0:print('source check',i,flush=True)
assert source_error<.0001,source_error
assert ImageChops.difference(n['frame'](0),n['frame'](12)).getbbox() is None
assert ImageChops.difference(n['frame'](.04),n['frame'](12.04)).getbbox() is None
# Reserve one unused palette slot so the GIF encoder can represent unchanged pixels.
gif=O/'banner-v5-single-contour.gif'
sample=Image.new('RGB',(1200,522*4))
for j,i in enumerate((0,53,117,185)):sample.paste(native[i],(0,j*522))
palette=sample.quantize(colors=255)
indexed=[f.resize((800,348),Image.Resampling.LANCZOS).quantize(palette=palette,dither=Image.Dither.NONE) for f in native]
tmp=O/'optimized.gif'
indexed[0].save(tmp,save_all=True,append_images=indexed[1:],duration=40,loop=0,disposal=1,optimize=True)
with Image.open(tmp) as im:
    assert im.n_frames==300 and im.info['loop']==0
    for expected,actual in zip(indexed,ImageSequence.Iterator(im)):
        assert actual.info['duration']==40
        assert ImageChops.difference(expected.convert('RGB'),actual.convert('RGB')).getbbox() is None
tmp.replace(gif)
print('GIF exact pixel preservation passed',flush=True)
webp=O/'banner-v5-single-contour.webp'
delivery=[f.resize((800,348),Image.Resampling.LANCZOS) for f in fs]
delivery[0].save(webp,save_all=True,append_images=delivery[1:],duration=40,loop=0,lossless=True,method=1)
errors=[];actor_errors=[]
with Image.open(webp) as im:
    assert im.n_frames==300 and im.info['loop']==0
    for a,b in zip(delivery,ImageSequence.Iterator(im)):
        b=b.convert('RGB');errors.append(mad(a,b));actor_errors.append(mad(a.crop((303,200,497,296)),b.crop((303,200,497,296))))
assert max(errors)==0 and max(actor_errors)==0
building=[n['scenery'](i/25).crop((1000,375,1060,395)) for i in range(300)]
assert all(ImageChops.difference(building[0],a).getbbox() is None for a in building)
steps=[mad(native[i-1],native[i]) for i in range(1,300)]
ff=imageio_ffmpeg.get_ffmpeg_exe();start=time.perf_counter()
p=subprocess.run([ff,'-v','error','-stream_loop','2','-re','-i',str(O/'banner-v5-single-contour.mp4'),'-progress',str(O/'realtime-decode.log'),'-f','null','-'],capture_output=True,text=True)
log=(O/'realtime-decode.log').read_text()
assert p.returncode==0 and 'frame=900' in log and 'progress=end' in log
report={'status':'test candidate; visual playback not certified','frames':300,'fps':25,'duration_ms':12000,'gif_loop':0,'gif_all_frame_duration_ms':40,'endpoint_and_next_frame_exact':True,'source_vs_lossless_master_max_frame_MAD':source_error,'gif_decoded_matches_all_quantized_source_frames':True,'static_building_patch_identical_all_frames':True,'seam_MAD':mad(native[-1],native[0]),'ordinary_step_mean_MAD':sum(steps)/len(steps),'ordinary_step_max_MAD':max(steps),'webp_lossless':True,'webp_size':[800,348],'webp_max_frame_MAD':max(errors),'webp_max_actor_crop_MAD':max(actor_errors),'frame_review':'All 300 character crops in 12 contact sheets and 48 full-scene samples inspected; no detached body or duplicated character contours observed in those stills.','realtime_decode':{'cycles':3,'frames':900,'wall_seconds':time.perf_counter()-start,'errors':p.stderr,'screen_playback':False},'playback_limit':'Browser local new-tab connection failed. Native Windows Media Player setup window access approval timed out. Unrelated browser tabs were not accessed.','remaining_limits':['2D rig remains stylized and has limited limb articulation; perceptual naturalness not certified','far scenery is stationary, foreground scrolls; no full-scene panorama travel','GIF has a 256-color palette; WebP is lossless at delivery size, larger master retained locally'],'files':{p.name:p.stat().st_size for p in O.glob('banner*')}}
(O/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))

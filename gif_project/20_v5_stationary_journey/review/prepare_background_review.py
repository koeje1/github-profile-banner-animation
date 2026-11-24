"""Background-only audit artifacts; no character pixels or final banner export."""
from pathlib import Path
import importlib.util
import json
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageDraw, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location('scrolling_world', ROOT / 'scenery.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
FRAME_MS = 40


def same(a, b):
    return ImageChops.difference(a, b).getbbox() is None


assert same(s.frame(0), s.frame(s.PERIOD_MS))
assert same(s.frame(40), s.frame(s.PERIOD_MS + 40))
for ms in range(0, s.WIND_MS, FRAME_MS):
    world = s.world_frame(ms)
    for name, box in s.STATIC_WORLD_REGIONS.items():
        assert same(world.crop(box), s.panorama.crop(box)), (name, ms)

offsets = [s.offset_at(ms) for ms in range(0, s.PERIOD_MS, FRAME_MS)]
steps = [(offsets[(i + 1) % len(offsets)] - offsets[i]) % s.WORLD_WIDTH for i in range(len(offsets))]
assert set(steps) == {1, 2}

times = [0, 3840, 7680, 11520, 15360, 19200]
contact = Image.new('RGB', (800, 594), '#201729')
draw = ImageDraw.Draw(contact)
for i, ms in enumerate(times):
    x, y = (i % 2) * 400, (i // 2) * 198
    draw.text((x + 6, y + 6), f'{ms/1000:.2f}s | world offset {s.offset_at(ms)}', fill='white')
    contact.paste(s.frame(ms).resize((400,174),Image.Resampling.LANCZOS),(x,y+24))
contact.save(HERE / 'background-scroll-contact.jpg', quality=95)
s.frame(0).save(HERE / 'background-poster.png')
s.frame(s.PERIOD_MS // 2).save(HERE / 'background-wrap-center.png')

# A 6.4s native-size sample shows the wrap join passing the fixed center of the
# screen. A thin preview-only bottom progress bar is deliberately omitted.
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
video = HERE / 'background-scroll-seam-study.mp4'
process = subprocess.Popen([ffmpeg,'-y','-v','error','-f','rawvideo','-vcodec','rawvideo',
                            '-s','800x348','-pix_fmt','rgb24','-r','25','-i','-','-an',
                            '-c:v','libx264','-pix_fmt','yuv420p','-crf','17',
                            '-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
for ms in range(8320, 14720, FRAME_MS):
    process.stdin.write(s.frame(ms).tobytes())
process.stdin.close()
error = process.stderr.read().decode('utf-8',errors='replace')
assert process.wait()==0,error
decode = subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
assert decode.returncode == 0,decode.stderr

edge_mae = ImageStat.Stat(ImageChops.difference(s.panorama.crop((0,0,1,s.H)),s.panorama.crop((s.WORLD_WIDTH-1,0,s.WORLD_WIDTH,s.H)))).mean
peak_dx = peak_dy = 0.0
for ms in range(0,s.WIND_MS,240):
    for y in range(0,180,5):
        for x in range(40,960,8):
            dx,dy=s.displacement(x,y,ms)
            peak_dx=max(peak_dx,abs(dx));peak_dy=max(peak_dy,abs(dy))
report={'size':[s.W,s.H],'world_size':list(s.panorama.size),'period_ms':s.PERIOD_MS,
        'camera_start_x':s.CAMERA_START_X,'ground_speed_px_s':s.GROUND_SPEED,'floor_y':s.FLOOR,
        'wind_period_ms':s.WIND_MS,'wind_gain':s.WIND_GAIN,'sampled_canopy_peak_displacement_px':[round(peak_dx,3),round(peak_dy,3)],
        'full_landscape_scrolls':True,'no_narrow_floor_belt':True,'no_playback_crossfade':True,
        'loop_endpoint_exact':True,'next_frame_exact':True,'offset_steps_at_25fps':sorted(set(steps)),
        'protected_world_pixels_unchanged_all_wind_samples':True,'protected_regions':s.STATIC_WORLD_REGIONS,
        'edge_rgb_mean_abs_difference':edge_mae,'edge_note':'Adjacent texture columns need not be identical; a faint sky exposure join remains possible and is documented in the visual review.',
        'source_selected':'assets/panorama-source-v1.png','seam_edit_rejected':'assets/panorama-source-v2-offset.png (changed outer artwork)',
        'preview_ms':[8320,14720],'preview_frames':160,'preview_decode_errors':decode.stderr,
        'screen_playback_observed':False}
(HERE/'background-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))

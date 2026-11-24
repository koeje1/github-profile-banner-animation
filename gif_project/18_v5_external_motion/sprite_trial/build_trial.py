"""Assemble downloaded game-authored frames; preserve their pixels and timing."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageSequence, ImageChops
import base64, hashlib, json

ROOT = Path(__file__).resolve().parent
URL = 'https://maplestory.io/api/GMS/255'
ITEMS = '1003089,1050168,20537,1082272,33157,1072443,1382105'

def digest(im):
    return hashlib.sha256(im.tobytes()).hexdigest()

def binary_alpha(im):
    return im.getchannel('A').point(lambda a: 255 if a >= 128 else 0)

def registration(raw, ref):
    # Recover placement from the service's original animated render, not from
    # changing sprite bounds. GIF palette conversion can remove a few edge pixels.
    best = (float('inf'), None)
    for x in range(-10, 21):
        for y in range(-10, 11):
            candidate = Image.new('RGBA', ref.size)
            candidate.alpha_composite(raw, (x, y))
            error = sum(ImageChops.difference(binary_alpha(candidate), binary_alpha(ref)).getdata()) // 255
            if error < best[0]:
                best = (error, (x, y))
    return best

source_gif = Image.open(ROOT / 'evan-source-walk.gif')
source_evan = [f.convert('RGBA') for f in ImageSequence.Iterator(source_gif)]
assert len(source_evan) == 4
evan, evan_meta = [], []
for i, reference in enumerate(source_evan):
    raw = Image.open(ROOT / f'evan/frame-{i}.png').convert('RGBA')
    error, offset = registration(raw, reference)
    assert error <= 2, (i, error)
    aligned = Image.new('RGBA', (128, 128))
    aligned.alpha_composite(raw, (offset[0] + 21, offset[1] + 20))
    aligned.save(ROOT / f'evan/aligned-{i}.png')
    delay = json.loads((ROOT / f'evan/delay-{i}.json').read_text())['value']
    evan.append(aligned)
    evan_meta.append(dict(index=i, file=f'evan/aligned-{i}.png', raw_file=f'evan/frame-{i}.png', raw_size=raw.size,
                          raw_sha256=digest(raw), delay_ms=delay, placement_in_source_gif=offset,
                          registration_alpha_mismatch_pixels=error, placement_in_aligned_png=[offset[0]+21, offset[1]+20]))

mir_source = json.loads((ROOT / 'mir-source.json').read_text())
mir, mir_meta = [], []
for i, frame in enumerate(mir_source['frameBooks']['move'][0]['frames']):
    raw_path = ROOT / f'mir/frame-{i}.png'
    raw_path.write_bytes(base64.b64decode(frame['image']))
    raw = Image.open(raw_path).convert('RGBA')
    origin = frame['origin']
    aligned = Image.new('RGBA', (128, 128))
    aligned.alpha_composite(raw, (64-origin['x'], 96-origin['y']))
    aligned.save(ROOT / f'mir/aligned-{i}.png')
    mir.append(aligned)
    mir_meta.append(dict(index=i, file=f'mir/aligned-{i}.png', raw_file=f'mir/frame-{i}.png', raw_size=raw.size,
                         raw_sha256=digest(raw), delay_ms=frame['delay'], origin=origin,
                         placement_in_aligned_png=[64-origin['x'], 96-origin['y']]))
assert len({f['raw_sha256'] for f in evan_meta}) == 4
assert len({f['raw_sha256'] for f in mir_meta}) == 6

def checker(size, cell=12):
    im = Image.new('RGB', size, '#e6e8ed')
    d = ImageDraw.Draw(im)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x//cell+y//cell) % 2:
                d.rectangle((x,y,x+cell-1,y+cell-1), fill='#dde0e7')
    return im

contact = checker((760, 480), 16)
draw = ImageDraw.Draw(contact)
draw.text((16,12), 'EVAN: 4 authored frames / 180 ms each / 720 ms cycle', fill='#303745')
draw.text((16,235), 'MIR: 6 authored frames / 150 ms each / 900 ms cycle', fill='#303745')
for i, frame in enumerate(evan):
    # 2x nearest-neighbor view, original aspect and authored left-facing direction.
    crop = frame.crop((14,17,101,109)).resize((174,184), Image.Resampling.NEAREST)
    contact.paste(crop,(16+i*184,42),crop)
    draw.text((20+i*184,215),f'{i}: 180ms',fill='#303745')
for i, frame in enumerate(mir):
    crop = frame.crop((40,43,100,105)).resize((120,124), Image.Resampling.NEAREST)
    contact.paste(crop,(12+i*124,280),crop)
    draw.text((16+i*124,416),f'{i}: 150ms',fill='#303745')
draw.text((16,452),'Game-authored sprites. No morphing, generated limbs, or optical-flow interpolation.',fill='#303745')
contact.save(ROOT/'contact-sheet.png')

# Original art faces left. Mirror both full aligned canvases to face right.
# Evan registration x is a display choice within the aligned source-GIF canvas;
# all inter-frame movement remains exactly the service's authored registration.
EVAN_ANCHOR = (128-81,96)
MIR_ANCHOR = (128-64,96)

def place(canvas, frame, anchor, target, scale=2):
    frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    frame = frame.resize((frame.width*scale,frame.height*scale),Image.Resampling.NEAREST)
    canvas.alpha_composite(frame,(target[0]-anchor[0]*scale,target[1]-anchor[1]*scale))

rgba_frames, checker_frames = [], []
for ms in range(0,3600,30):
    layer = Image.new('RGBA',(640,300))
    place(layer,mir[(ms//150)%6],MIR_ANCHOR,(186,236))
    place(layer,evan[(ms//180)%4],EVAN_ANCHOR,(420,236))
    rgba_frames.append(layer)
    bg=checker(layer.size,16).convert('RGBA')
    d=ImageDraw.Draw(bg)
    d.text((18,18),'ORIGINAL SPRITE MOTION / NATIVE TIMING / 3.6 s LOOP',fill='#303745')
    d.line((18,237,622,237),fill='#b3b8c4',width=1)
    bg.alpha_composite(layer)
    checker_frames.append(bg.convert('RGB'))

# Fixed palette + full opaque frames prevent trails. Transparency is a separate
# deliverable so it is not confused with the baked checkerboard review.
atlas=Image.new('RGB',(640*6,300))
for i in range(6): atlas.paste(checker_frames[i*7],(640*i,0))
palette=atlas.quantize(colors=255)
indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in checker_frames]
indexed[0].save(ROOT/'motion-test-checker.gif',save_all=True,append_images=indexed[1:],duration=30,loop=0,disposal=2,optimize=False)
transparent=[]
for im in rgba_frames:
    q=im.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE)
    q.paste(255,mask=im.getchannel('A').point(lambda a:255 if a<128 else 0))
    transparent.append(q)
transparent[0].save(ROOT/'motion-test-transparent.gif',save_all=True,append_images=transparent[1:],duration=30,loop=0,disposal=2,transparency=255,optimize=False)
rgba_frames[0].save(ROOT/'motion-test-poster.png')
checker_frames[0].save(ROOT/'motion-test-checker-poster.png')

provenance = dict(
    acquired='2026-11-24',provider='MapleStory.IO public API',region='GMS',version='255',
    rights='MapleStory and all original character sprites are copyrighted by NEXON. These are not CC0 or public-domain assets. Free unauthenticated API access does not transfer rights.',
    evan=dict(npc_id=1540407,skin_id=2000,item_ids=[int(x) for x in ITEMS.split(',')],action='walk1',
              source_json=f'{URL}/npc/1540407',source_png_template=f'{URL}/npc/1540407/render/walk1/{{frame}}',
              source_animated_gif=f'{URL}/Character/animated/2000/{ITEMS}/walk1/0',
              delay_template='https://maplestory.io/api/wz/GMS/255/Character/00002000.img/walk1/{frame}/delay',
              alignment='Original PNGs registered against API-authored GIF alpha masks, with additional safe margins. The aligned 128x128 canvas is an internal compositing canvas.',
              aligned_display_anchor=[81,96],frames=evan_meta),
    mir=dict(pet_id=5000118,action='move',source_json=f'{URL}/pet/5000118',
             actions=f'{URL}/pet/5000118/actions',alignment='Exact per-frame origin from the API JSON, mapped to [64,96].',
             aligned_display_anchor=[64,96],frames=mir_meta),
    test=dict(facing='Both originally left-facing; both mirrored to face right.',scale='Uniform 2x nearest neighbor, no aspect distortion.',
              loop_ms=3600,evan_cycle_ms=720,mir_cycle_ms=900,frame_step_ms=30,
              movement='In-place source walk cycles. No ground or full scene composited. No extra bobbing, limb transforms, morphs, or timing smoothing.'))
(ROOT/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')

validation={}
for name in ['motion-test-checker.gif','motion-test-transparent.gif']:
    im=Image.open(ROOT/name)
    duration=sum(f.info.get('duration',0) for f in ImageSequence.Iterator(im))
    assert duration==3600
    validation[name]=dict(frames=im.n_frames,duration_ms=duration,size=im.size,loop=im.info.get('loop'))
validation.update(evan_distinct_frames=4,mir_distinct_frames=6,evan_alpha_registration_error=[f['registration_alpha_mismatch_pixels'] for f in evan_meta])
(ROOT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
print(json.dumps(validation,indent=2))

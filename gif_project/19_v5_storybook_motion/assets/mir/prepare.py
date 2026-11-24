"""Split and register the generated full-pose Mir sheet without redrawing it."""
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REVIEW = ROOT / 'review' / 'mir'
REVIEW.mkdir(parents=True, exist_ok=True)
SOURCE = HERE.parent / 'mir-flight-sheet.png'
SCALE = 0.245
CANVAS = (160, 100)
BODY_ANCHOR = (80, 60)
HORN_ANCHOR = (94, 26)


def checker(size, step=10):
    out = Image.new('RGBA', size, (242, 237, 232, 255))
    draw = ImageDraw.Draw(out)
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if (x // step + y // step) % 2:
                draw.rectangle((x, y, x + step - 1, y + step - 1), fill=(226, 222, 218, 255))
    return out


sheet = Image.open(SOURCE).convert('RGBA')
fringe_alpha = [a for r, g, b, a in sheet.getdata() if r > 180 and g < 60 and b < 100]
frames = []
entries = []
for i in range(8):
    col, row = i % 4, i // 4
    box = (round(col * sheet.width / 4), round(row * sheet.height / 2),
           round((col + 1) * sheet.width / 4), round((row + 1) * sheet.height / 2))
    raw = sheet.crop(box)
    raw.save(HERE / f'raw-cell-{i}.png')
    pixels = raw.load()
    horn_pixels = [(x, y) for y in range(48, 125) for x in range(230, 350)
                   if (lambda r, g, b, a: a >= 200 and r > 120 and g > 70
                       and r > 1.13 * g and b < .8 * g)(*pixels[x, y])]
    cx = sum(x for x, y in horn_pixels) / len(horn_pixels)
    cy = sum(y for x, y in horn_pixels) / len(horn_pixels)
    inverse = (1 / SCALE, 0, cx - HORN_ANCHOR[0] / SCALE,
               0, 1 / SCALE, cy - HORN_ANCHOR[1] / SCALE)
    # Premultiplied resampling prevents invisible RGB in near-zero-alpha pixels
    # from bleeding into a visible contour. No alpha threshold or color edit.
    aligned = raw.convert('RGBa').transform(CANVAS, Image.Transform.AFFINE, inverse,
                                            Image.Resampling.BICUBIC).convert('RGBA')
    aligned.save(HERE / f'frame-{i}.png')
    high_alpha = aligned.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0)
    visible_box = high_alpha.getbbox()
    assert visible_box and 0 < visible_box[0] < visible_box[2] < CANVAS[0]
    assert 0 < visible_box[1] < visible_box[3] < CANVAS[1]
    assert aligned.mode == 'RGBA'
    frames.append(aligned)
    entries.append({'index': i, 'file': f'frame-{i}.png', 'source_cell': list(box),
                    'source_horn_centroid': [round(float(cx), 5), round(float(cy), 5)],
                    'visible_bbox_alpha_128': list(visible_box),
                    'visible_size_alpha_128': [visible_box[2] - visible_box[0], visible_box[3] - visible_box[1]],
                    'sha256': hashlib.sha256((HERE / f'frame-{i}.png').read_bytes()).hexdigest()})

assert len({entry['sha256'] for entry in entries}) == 8
metadata = {'source': str(SOURCE), 'source_size': list(sheet.size), 'source_grid': [4, 2],
            'canvas': list(CANVAS), 'body_anchor': list(BODY_ANCHOR),
            'registered_anatomical_anchor': 'golden horn pixel centroid in fixed head ROI',
            'horn_anchor': list(HORN_ANCHOR), 'uniform_scale': SCALE,
            'direction': 'right', 'mirrored': False,
            'order': list(range(8)), 'recommended_frame_ms': 120, 'recommended_cycle_ms': 960,
            'timing_note': 'Suggested playback timing for new generated art, not source game timing.',
            'processing': 'Equal-cell crop, uniform premultiplied-alpha bicubic resize, rigid translation only. No morphing, optical flow, recoloring or per-frame fitting.',
            'source_fringe': {'red_pixel_count': len(fringe_alpha),
                              'red_pixel_max_alpha': max(fringe_alpha),
                              'handling': 'Preserved source RGBA; premultiplied resampling suppresses invisible RGB bleed.'},
            'frames': entries}
(HERE / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')

contact = checker((640, 244))
draw = ImageDraw.Draw(contact)
for i, frame in enumerate(frames):
    x, y = (i % 4) * 160, (i // 4) * 122
    contact.alpha_composite(frame, (x, y))
    draw.text((x + 8, y + 102), f'{i}  |  anchor (80,60)', fill=(56, 47, 50))
contact.convert('RGB').save(REVIEW / 'contact-native.png')
contact.resize((1280, 488), Image.Resampling.NEAREST).convert('RGB').save(REVIEW / 'contact-2x.png')

base = Image.open(ROOT.parent / '17_v5_weighted_walk/assets/clean-plate.png').convert('RGBA').resize((800, 348), Image.Resampling.LANCZOS)
composites = []
for i, frame in enumerate(frames):
    composite = base.copy()
    composite.alpha_composite(frame, (350 - BODY_ANCHOR[0], 250 - BODY_ANCHOR[1]))
    composite.convert('RGB').save(REVIEW / f'background-frame-{i}.png')
    composites.append(composite)
background_contact = Image.new('RGB', (1600, 1392))
for i, composite in enumerate(composites):
    background_contact.paste(composite.convert('RGB'), ((i % 2) * 800, (i // 2) * 348))
background_contact.save(REVIEW / 'background-contact.jpg', quality=94)
composites[0].save(REVIEW / 'flight-background.apng', save_all=True, append_images=composites[1:],
                   duration=120, loop=0, disposal=0, blend=0)
checkframes = []
for frame in frames:
    one = checker(CANVAS)
    one.alpha_composite(frame)
    checkframes.append(one.convert('RGB'))
checkframes[0].save(REVIEW / 'flight-checker.gif', save_all=True, append_images=checkframes[1:],
                    duration=120, loop=0, disposal=2)
print(json.dumps({'frames': len(frames), 'canvas': CANVAS, 'body_anchor': BODY_ANCHOR,
                  'horn_anchor': HORN_ANCHOR, 'scale': SCALE,
                  'visible_bounds': [entry['visible_bbox_alpha_128'] for entry in entries]}, indent=2))

"""Combine intact original first-half poses with intact replacement poses.

This only splits, uniformly resizes, and registers complete generated images.
Color/alpha tests below locate landmarks; generated alpha is never thresholded.
"""
from pathlib import Path
import json
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'assets/evan-v2'
REVIEW = ROOT / 'review'
OUT.mkdir(parents=True, exist_ok=True)
sheet = Image.open(ROOT / 'assets/evan-halfstep-v2.png').convert('RGBA')
assert sheet.size == (1254, 1254)
CELL, NATIVE = 627, 84
SCALE = NATIVE / CELL
ANCHOR = (54, 90)
original = json.loads((REVIEW / 'evan-registration.json').read_text(encoding='utf-8'))
records = []
frames = []
for index in range(4):
    shutil.copyfile(ROOT / f'assets/evan/frame-{index}.png', OUT / f'frame-{index}.png')
    pose = Image.open(OUT / f'frame-{index}.png').convert('RGBA')
    frames.append(pose)
    records.append(dict(original['frames'][index], source_group='original top row',
                        file=f'assets/evan-v2/frame-{index}.png'))

for local in range(4):
    index = local + 4
    bounds = (local % 2 * CELL, local // 2 * CELL,
              (local % 2 + 1) * CELL, (local // 2 + 1) * CELL)
    cell = sheet.crop(bounds)
    cell.save(OUT / f'source-cell-{index}.png')
    measurable = cell.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0)
    body_bounds = measurable.getbbox()
    baseline = body_bounds[3]
    ruby_pixels = []
    for y in range(55, 125):
        for x in range(280, 370):
            red, green, blue, alpha = cell.getpixel((x, y))
            if alpha > 128 and red > 175 and green < 95 and blue < 120 and red > 1.8 * green:
                ruby_pixels.append((x, y))
    ruby_x = sum(p[0] for p in ruby_pixels) / len(ruby_pixels)
    ruby_y = sum(p[1] for p in ruby_pixels) / len(ruby_pixels)
    offset = (round(ANCHOR[0] - ruby_x * SCALE), round(ANCHOR[1] - baseline * SCALE))
    pose = Image.new('RGBA', (100, 100))
    pose.alpha_composite(cell.resize((NATIVE, NATIVE), Image.Resampling.LANCZOS), offset)
    pose.save(OUT / f'frame-{index}.png')
    frames.append(pose)
    records.append({'index': index, 'source_group': 'replacement half-step sheet',
                    'source_sheet_bounds': bounds, 'source_body_bounds_measurement_alpha_128': body_bounds,
                    'source_ruby_red_centroid': [ruby_x, ruby_y], 'source_foot_baseline': baseline,
                    'uniform_scale': SCALE, 'placement_offset': offset,
                    'head_landmark_native_x': offset[0] + ruby_x * SCALE,
                    'baseline_native_y': offset[1] + baseline * SCALE,
                    'body_height_native_px': (body_bounds[3] - body_bounds[1]) * SCALE,
                    'file': f'assets/evan-v2/frame-{index}.png'})

scene = Image.open(ROOT.parent / '17_v5_weighted_walk/assets/clean-plate.png').convert('RGB')
scene = scene.resize((800, 348), Image.Resampling.LANCZOS)
white = Image.new('RGB', (600, 280), 'white')
background = Image.new('RGB', (600, 280))
double = Image.new('RGB', (800, 400), '#f7f3f1')
for index, pose in enumerate(frames):
    x, y = index % 4 * 150, index // 4 * 140
    white.paste(pose, (x + 25, y + 20), pose)
    patch = scene.crop((375, 182, 525, 322)).convert('RGBA')
    patch.alpha_composite(pose, (25, 15))
    background.paste(patch.convert('RGB'), (x, y))
    for image in (white, background):
        ImageDraw.Draw(image).text((x + 5, y + 5), f'POSE {index}',
                                  fill='#241b28' if image is white else 'white',
                                  stroke_width=0 if image is white else 1, stroke_fill='#241b28')
    enlarged = pose.resize((200, 200), Image.Resampling.NEAREST)
    double.paste(enlarged, (index % 4 * 200, index // 4 * 200), enlarged)
    ImageDraw.Draw(double).text((index % 4 * 200 + 5, index // 4 * 200 + 5), str(index), fill='black')
white.save(REVIEW / 'evan-v2-contact-white.png')
background.save(REVIEW / 'evan-v2-contact-scene.png')
double.save(REVIEW / 'evan-v2-contact-2x.png')
boundary = Image.new('RGB', (800, 200), 'white')
for col, index in enumerate((3, 4, 7, 0)):
    pose = frames[index].resize((200, 200), Image.Resampling.NEAREST)
    boundary.paste(pose, (col * 200, 0), pose)
    ImageDraw.Draw(boundary).text((col * 200 + 4, 4), f'POSE {index}', fill='black')
boundary.save(REVIEW / 'evan-v2-boundaries-2x.png')
report = {'native_canvas': [100, 100], 'native_anchor': list(ANCHOR),
          'source_replacement_size': list(sheet.size), 'source_replacement_cell_size': CELL,
          'replacement_uniform_scale': SCALE,
          'processing': 'Complete poses only; original0..3 copied byte-for-byte; new4..7 all use one uniform scale. Original generated alpha retained.',
          'frames': records, 'visual_review': 'pending', 'candidate_timing_ms': None}
(REVIEW / 'evan-v2-registration.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'replacement_scale': SCALE,
                  'body_heights': [round(p['body_height_native_px'], 3) for p in records],
                  'head_x': [round(p['head_landmark_native_x'], 3) for p in records],
                  'baselines': [round(p['baseline_native_y'], 3) for p in records]}, indent=2))

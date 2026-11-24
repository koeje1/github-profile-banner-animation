"""Register generated complete poses without editing their painted pixels.

Alpha thresholds below measure landmarks only. They never modify image alpha.
All poses share one padded source canvas and one uniform resize operation.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
POSES = ASSETS / 'evan'
REVIEW = ROOT / 'review'
for directory in (POSES, REVIEW):
    directory.mkdir(parents=True, exist_ok=True)

sheet = Image.open(ASSETS / 'evan-walk-sheet.png').convert('RGBA')
# The head's red circlet jewel is the same horizontal landmark in every pose.
# Coordinates were read in source-cell pixels, not inferred from changing coats.
head_x = (244, 243, 244, 244, 243, 244, 245, 246)
PADDED_SOURCE = 444
NATIVE_RESIZED = 87
SCALE = NATIVE_RESIZED / PADDED_SOURCE
ANCHOR = (54, 90)
CANVAS = (100, 100)
scene = Image.open(ROOT.parent / '17_v5_weighted_walk/assets/clean-plate.png').convert('RGB')
scene = scene.resize((800, 348), Image.Resampling.LANCZOS)
frames = []
records = []

for index in range(8):
    col, row = index % 4, index // 4
    bounds = (round(col * sheet.width / 4), round(row * sheet.height / 2),
              round((col + 1) * sheet.width / 4), round((row + 1) * sheet.height / 2))
    cell = sheet.crop(bounds)
    cell.save(POSES / f'source-cell-{index}.png')
    alpha = cell.getchannel('A')
    measurable = alpha.point(lambda value: 255 if value >= 128 else 0)
    body_bounds = measurable.getbbox()
    # Below y=340 only the boots remain; exclude all staff/coat landmarks.
    foot_bounds = measurable.crop((60, 340, 390, cell.height)).getbbox()
    baseline = 340 + foot_bounds[3]
    padded = Image.new('RGBA', (PADDED_SOURCE, PADDED_SOURCE))
    padded.alpha_composite(cell)
    # One identical resize for all poses; original antialiased alpha is retained.
    scaled = padded.resize((NATIVE_RESIZED, NATIVE_RESIZED), Image.Resampling.LANCZOS)
    offset = (round(ANCHOR[0] - head_x[index] * SCALE),
              round(ANCHOR[1] - baseline * SCALE))
    aligned = Image.new('RGBA', CANVAS)
    aligned.alpha_composite(scaled, offset)
    aligned.save(POSES / f'frame-{index}.png')
    frames.append(aligned)
    histogram = alpha.histogram()
    records.append({
        'index': index, 'source_sheet_bounds': bounds, 'source_cell_size': list(cell.size),
        'source_body_bounds_at_alpha_128_for_measurement_only': body_bounds,
        'source_head_landmark_x': head_x[index], 'source_foot_baseline': baseline,
        'uniform_scale': SCALE, 'source_pad_size': PADDED_SOURCE,
        'resized_pad_size': NATIVE_RESIZED, 'placement_offset': offset,
        'head_landmark_native_x': offset[0] + head_x[index] * SCALE,
        'baseline_native_y': offset[1] + baseline * SCALE,
        'body_height_native_px': (body_bounds[3] - body_bounds[1]) * SCALE,
        'alpha_1_to_9_pixel_count': sum(histogram[1:10]),
        'source_rgba_sha256': hashlib.sha256(cell.tobytes()).hexdigest(),
        'file': f'assets/evan/frame-{index}.png',
    })

white = Image.new('RGB', (600, 280), 'white')
background = Image.new('RGB', (600, 280))
enlarged = Image.new('RGB', (800, 400), '#f7f3f1')
for index, pose in enumerate(frames):
    x, y = index % 4 * 150, index // 4 * 140
    white.paste(pose, (x + 25, y + 20), pose)
    patch = scene.crop((375, 182, 525, 322)).convert('RGBA')
    patch.alpha_composite(pose, (25, 15))
    background.paste(patch.convert('RGB'), (x, y))
    for image in (white, background):
        ImageDraw.Draw(image).text((x + 5, y + 5), f'{index}: {index*120}ms',
                                  fill='#241b28' if image is white else 'white',
                                  stroke_width=0 if image is white else 1,
                                  stroke_fill='#241b28')
    doubled = pose.resize((200, 200), Image.Resampling.NEAREST)
    enlarged.paste(doubled, (index % 4 * 200, index // 4 * 200), doubled)
    ImageDraw.Draw(enlarged).text((index % 4 * 200 + 5, index // 4 * 200 + 5), str(index), fill='black')
white.save(REVIEW / 'evan-contact-white.png')
background.save(REVIEW / 'evan-contact-scene.png')
enlarged.save(REVIEW / 'evan-contact-2x.png')
report = {
    'source_file': 'assets/evan-walk-sheet.png', 'source_size': list(sheet.size),
    'split': '4 columns by 2 rows, equal fractional cell bounds rounded to pixels',
    'alpha_policy': 'Original alpha preserved; no thresholding, erosion, or fringe deletion. Threshold128 measures landmarks only.',
    'uniform_scale': SCALE, 'native_canvas': list(CANVAS), 'native_anchor': list(ANCHOR),
    'frame_delay_ms_candidate': 120, 'cycle_ms_candidate': 960,
    'frames': records,
    'visual_review': 'Pending inspection of leg alternation and seam; these are generated complete poses, not authenticated animation frames.',
}
(REVIEW / 'evan-registration.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'source_size': sheet.size, 'uniform_scale': SCALE,
                  'body_heights': [round(item['body_height_native_px'], 2) for item in records],
                  'head_x': [round(item['head_landmark_native_x'], 2) for item in records],
                  'baselines': [round(item['baseline_native_y'], 2) for item in records]}, indent=2))

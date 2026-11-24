"""Register 16 complete generated poses, preserving their paint and alpha.

Only crops, uniform resizing and whole-frame placement are performed. Alpha
thresholds and RGB tests below are measurement tools; they never edit pixels.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
POSES = ASSETS / 'evan'
REVIEW = ROOT / 'review' / 'evan'
for directory in (POSES, REVIEW):
    directory.mkdir(parents=True, exist_ok=True)

SHEET = ASSETS / 'evan-walk-16.png'
sheet = Image.open(SHEET).convert('RGBA')
PAD = 316
RESIZED = 85
SCALE = RESIZED / PAD
ANCHOR = (54, 90)
CANVAS = (100, 100)
POSE_MS = 80
INITIAL_GROUND_SPEED = 1044 / 23.04
# Approximate ruby centers specify a small measurement window, not a new drawing.
RUBY_WINDOWS = [(168,59),(163,59),(157,59),(153,58),
                (170,57),(162,56),(157,56),(154,55),
                (169,56),(164,55),(159,55),(154,54),
                (170,52),(163,51),(159,52),(154,51)]

def centroid(points):
    return [sum(p[k] for p in points) / len(points) for k in (0, 1)]

frames, records = [], []
for index, (hx, hy) in enumerate(RUBY_WINDOWS):
    col, row = index % 4, index // 4
    bounds = tuple(round(v) for v in (col * sheet.width / 4, row * sheet.height / 4,
                                     (col + 1) * sheet.width / 4, (row + 1) * sheet.height / 4))
    cell = sheet.crop(bounds)
    cell.save(POSES / f'source-cell-{index}.png')
    alpha = cell.getchannel('A')
    solid_measurement = alpha.point(lambda v: 255 if v >= 128 else 0)
    body_box = solid_measurement.getbbox()
    ruby = []
    for y in range(hy - 7, hy + 8):
        for x in range(hx - 7, hx + 8):
            r, g, b, a = cell.getpixel((x, y))
            if r > 90 and g < 85 and b < 110 and r > g * 1.8 and a >= 128:
                ruby.append((x, y))
    ruby_center = centroid(ruby)
    # Boots are the only opaque marks in this lower source-cell region. The
    # planted sole, not the head top, defines vertical registration. Head height
    # relative to the support sole therefore retains the authored natural bob.
    foot_box = solid_measurement.crop((60, 250, 270, cell.height)).getbbox()
    baseline = 250 + foot_box[3]
    sole_points = [(x, y) for y in range(baseline - 5, baseline)
                   for x in range(60, 270) if alpha.getpixel((x, y)) >= 128]
    x_runs = []
    for x in sorted({p[0] for p in sole_points}):
        if not x_runs or x > x_runs[-1][-1] + 1:
            x_runs.append([])
        x_runs[-1].append(x)
    contacts = []
    for run in x_runs:
        points = [p for p in sole_points if run[0] <= p[0] <= run[-1]]
        contacts.append({'source_x_range': [run[0], run[-1]],
                         'source_centroid': centroid(points)})
    # At the two wide contacts choose the front heel. In subsequent held poses
    # choose the sole nearest the ground; the little rear-heel fragments in 1/9
    # are the outgoing support, not the newly planted front foot.
    selected = max(contacts, key=lambda c: c['source_centroid'][0]) if index in (0,1,8,9) else max(contacts, key=lambda c: c['source_x_range'][1] - c['source_x_range'][0])
    padded = Image.new('RGBA', (PAD, PAD))
    padded.alpha_composite(cell)
    scaled = padded.resize((RESIZED, RESIZED), Image.Resampling.LANCZOS)
    offset = (round(ANCHOR[0] - ruby_center[0] * SCALE),
              round(ANCHOR[1] - baseline * SCALE))
    assert offset[0] >= 0 and offset[1] >= 0
    assert offset[0] + RESIZED <= CANVAS[0] and offset[1] + RESIZED <= CANVAS[1]
    native = Image.new('RGBA', CANVAS)
    native.alpha_composite(scaled, offset)
    native.save(POSES / f'frame-{index}.png')
    frames.append(native)
    for contact in contacts:
        contact['native_centroid'] = [offset[k] + contact['source_centroid'][k] * SCALE for k in (0, 1)]
    records.append({
        'index': index, 'file': f'assets/evan/frame-{index}.png',
        'source_bounds': bounds, 'source_size': cell.size,
        'source_alpha128_bounds_measurement_only': body_box,
        'source_ruby_centroid': ruby_center, 'source_support_baseline': baseline,
        'placement': offset, 'ruby_native': [offset[k] + ruby_center[k] * SCALE for k in (0,1)],
        'baseline_native': offset[1] + baseline * SCALE,
        'body_height_native': (body_box[3] - body_box[1]) * SCALE,
        'support_candidates': contacts, 'selected_support': selected,
        'native_rgba_sha256': hashlib.sha256(native.tobytes()).hexdigest(),
    })

intervals = []
for i, record in enumerate(records):
    following = records[(i + 1) % 16]
    next_support = following['selected_support']
    if i in (7, 15):
        # Track the outgoing foot into the following contact pose's rear sole.
        next_support = min(following['support_candidates'], key=lambda c: c['native_centroid'][0])
    retreat = record['selected_support']['native_centroid'][0] - next_support['native_centroid'][0]
    intervals.append({'from': i, 'to': (i+1)%16, 'support_retreat_px': retreat,
                      'ground_retreat_at_initial_speed_px': INITIAL_GROUND_SPEED * POSE_MS / 1000,
                      'relative_foot_displacement_px': INITIAL_GROUND_SPEED * POSE_MS / 1000 - retreat})
stride = sum(item['support_retreat_px'] for item in intervals)

scene = Image.open(ROOT.parent / '17_v5_weighted_walk/assets/clean-plate.png').convert('RGB')
scene = scene.resize((800,348), Image.Resampling.LANCZOS)
white = Image.new('RGB',(600,560),'white')
background = Image.new('RGB',(600,560))
double = Image.new('RGB',(800,800),'#f7f3f1')
source_legs = Image.new('RGB',(800,640),'white')
for i, pose in enumerate(frames):
    x,y=i%4*150,i//4*140
    white.paste(pose,(x+25,y+20),pose)
    patch=scene.crop((375,182,525,322)).convert('RGBA')
    patch.alpha_composite(pose,(25,15))
    background.paste(patch.convert('RGB'),(x,y))
    for output in (white,background):
        ImageDraw.Draw(output).text((x+5,y+5),f'{i:02d} / {i*POSE_MS} ms',fill='black' if output is white else 'white',stroke_width=0 if output is white else 1,stroke_fill='black')
    zoom=pose.resize((200,200),Image.Resampling.NEAREST)
    double.paste(zoom,(i%4*200,i//4*200),zoom)
    ImageDraw.Draw(double).text((i%4*200+5,i//4*200+5),str(i),fill='black')
    source=Image.open(POSES/f'source-cell-{i}.png').convert('RGBA').crop((60,160,260,320))
    source_legs.paste(source,(i%4*200,i//4*160),source)
    ImageDraw.Draw(source_legs).text((i%4*200+3,i//4*160+3),str(i),fill='black')
white.save(REVIEW/'contact-white.png')
background.save(REVIEW/'contact-scene.png')
double.save(REVIEW/'contact-2x.png')
source_legs.save(REVIEW/'source-legs.png')
report={
    'source':str(SHEET.relative_to(ROOT)), 'source_size':sheet.size,
    'source_sha256':hashlib.sha256(SHEET.read_bytes()).hexdigest(),
    'split':'4 columns x 4 rows, row-major; rounded fractional cell boundaries',
    'uniform_scale':SCALE,'source_pad':PAD,'resized_pad':RESIZED,
    'canvas':CANVAS,'anchor':ANCHOR,'frame_duration_ms':POSE_MS,'cycle_ms':16*POSE_MS,
    'alpha_policy':'Generated alpha preserved; measurement thresholds never applied to output pixels.',
    'vertical_registration':'Planted sole baseline; head vertical position is not normalized, preserving drawn bob.',
    'initial_ground_speed_px_s':INITIAL_GROUND_SPEED,
    'measured_two_stance_support_travel_px':stride,
    'matching_mean_ground_speed_px_s':stride/(16*POSE_MS/1000),
    'measurement_limit':'Sole-area centroids change when a boot rotates; these are approximate contact landmarks, not persistent material points. Occlusion does not prove leg identity. Held drawings still slip against continuously scrolling ground.',
    'screen_playback_reviewed':False,
    'visual_review':'Contact sheets inspected. Low diagonal staff and coordinated wrist/forearm changes improve carrying pose. Original alpha composites cleanly. Body size and head registration stable, with 1.35 px ruby-height range. The two 8-pose halves have strongly similar leg silhouettes; opposite-leg alternation remains ambiguous. Not approved by playback.',
    'frames':records,'support_intervals':intervals,
}
(REVIEW/'registration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'canvas':CANVAS,'anchor':ANCHOR,'scale':SCALE,
 'height_range':[min(r['body_height_native'] for r in records),max(r['body_height_native'] for r in records)],
 'ruby_y_range':[min(r['ruby_native'][1] for r in records),max(r['ruby_native'][1] for r in records)],
 'stride_px':stride,'mean_speed':report['matching_mean_ground_speed_px_s'],
 'retreats':[round(r['support_retreat_px'],3) for r in intervals]},indent=2))

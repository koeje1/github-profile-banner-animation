"""Fixed companions walking against a continuously scrolling painted world."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFilter
import scenery

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'exports'
REVIEW = ROOT / 'review'
W, H = 800, 348
FRAME_MS = 40
POSE_MS = 80
EVAN_CYCLE_MS = MIR_CYCLE_MS = 16 * POSE_MS
DURATION_MS = scenery.PERIOD_MS
COUNT = DURATION_MS // FRAME_MS
FLOOR = 284
EVAN_ANCHOR = (54, 90)
MIR_ANCHOR = (80, 60)
EVAN_X, MIR_X = 471, 357
MIR_Y = 250

evan = [Image.open(ROOT / f'assets/evan/frame-{i}.png').convert('RGBA') for i in range(16)]
mir = [Image.open(ROOT / f'assets/mir/frame-{i}.png').convert('RGBA') for i in range(16)]


def positions(ms):
    return EVAN_X, MIR_X


def actor_layer(ms):
    ms %= DURATION_MS
    layer = Image.new('RGBA', (W, H))
    shadow = Image.new('RGBA', (W, H))
    draw = ImageDraw.Draw(shadow)
    draw.ellipse((EVAN_X-17, FLOOR-1, EVAN_X+16, FLOOR+3), fill=(48, 32, 42, 57))
    draw.ellipse((MIR_X-23, FLOOR-1, MIR_X+24, FLOOR+3), fill=(48, 32, 42, 27))
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(1)))
    # Wings provide the primary movement; only a small, periodic lift is added.
    my = MIR_Y + round(1.5 * math.sin(math.tau * ms / MIR_CYCLE_MS))
    pose = int(ms // POSE_MS) % 16
    layer.alpha_composite(mir[pose], (MIR_X-MIR_ANCHOR[0], my-MIR_ANCHOR[1]))
    layer.alpha_composite(evan[pose], (EVAN_X-EVAN_ANCHOR[0], FLOOR-EVAN_ANCHOR[1]))
    return layer


def frame(ms):
    ms = round(ms) % DURATION_MS
    out = scenery.frame(ms).convert('RGBA')
    out.alpha_composite(actor_layer(ms))
    return out.convert('RGB')

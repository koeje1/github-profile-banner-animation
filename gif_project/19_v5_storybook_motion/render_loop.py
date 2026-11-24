"""Illustrated full-pose characters crossing a rooted, breathing landscape."""
from pathlib import Path
import importlib.util
import math
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'exports'
REVIEW = ROOT / 'review'
for path in (OUT, REVIEW):
    path.mkdir(exist_ok=True)

# This module contains scenery only, independently of the rejected game sprites.
spec = importlib.util.spec_from_file_location('storybook_scenery', ROOT / 'scenery.py')
background = importlib.util.module_from_spec(spec)
spec.loader.exec_module(background)
base = background.base
scenery = background.scenery
W, H = 800, 348
FRAME_MS = 30
DURATION_MS = 23040
COUNT = DURATION_MS // FRAME_MS
WIND_MS = background.WIND_MS
EVAN_CYCLE_MS = 1440
MIR_CYCLE_MS = 960
FLOOR = 287
SPEED = 45.5
START = -55
OFFSET = 505
FOLLOW = 110
SPAN = SPEED * DURATION_MS / 1000
EVAN_ANCHOR = (54, 90)
MIR_ANCHOR = (80, 60)
EVAN_DURATIONS = [180, 210, 150, 180, 180, 180, 240, 120]
MIR_ORDER = [0, 1, 2, 3, 4, 3, 2, 1]
MIR_DURATIONS = [150, 120, 90, 90, 120, 90, 150, 150]

evan = [Image.open(ROOT/f'assets/evan-v2/frame-{i}.png').convert('RGBA') for i in range(8)]
mir = [Image.open(ROOT/f'assets/mir/frame-{i}.png').convert('RGBA') for i in range(8)]


def pose_at(ms, durations):
    phase = ms % sum(durations)
    for i, duration in enumerate(durations):
        if phase < duration:
            return i
        phase -= duration
    raise AssertionError('unreachable pose')


def positions(ms):
    x = START + (OFFSET + SPEED * (ms % DURATION_MS) / 1000) % SPAN
    return round(x), round(x - FOLLOW)


def actor_layer(ms):
    ex, mx = positions(ms)
    layer = Image.new('RGBA', (W, H))
    shadows = Image.new('RGBA', (W, H))
    draw = ImageDraw.Draw(shadows)
    draw.ellipse((ex-17,FLOOR-1,ex+16,FLOOR+3), fill=(35,20,43,64))
    draw.ellipse((mx-22,FLOOR-1,mx+25,FLOOR+3), fill=(35,20,43,30))
    layer.alpha_composite(shadows.filter(ImageFilter.GaussianBlur(.8)))
    my = 249 + round(math.cos(math.tau * (ms-30) / MIR_CYCLE_MS))
    mi = MIR_ORDER[pose_at(ms, MIR_DURATIONS)]
    layer.alpha_composite(mir[mi], (mx-MIR_ANCHOR[0], my-MIR_ANCHOR[1]))
    ei = pose_at(ms, EVAN_DURATIONS)
    layer.alpha_composite(evan[ei], (ex-EVAN_ANCHOR[0], FLOOR-EVAN_ANCHOR[1]))
    return layer


def frame(ms):
    ms = round(ms) % DURATION_MS
    out = scenery(ms//60*60).convert('RGBA')
    out.alpha_composite(background.atmosphere(ms))
    out.alpha_composite(actor_layer(ms))
    return out.convert('RGB')

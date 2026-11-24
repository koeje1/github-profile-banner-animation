"""A complete painted world scrolling behind stationary screen-space actors.

All layers share the same horizontal world offset. There is no separate floor
belt, translated copy dissolve, time-dependent color blend or terrain warp.
Only small canopy regions move locally, before the complete world is cropped.
"""
from functools import lru_cache
from pathlib import Path
import math

from PIL import Image

ROOT = Path(__file__).resolve().parent
W, H = 800, 348
WORLD_WIDTH = 1044
PERIOD_MS = 23040
DURATION_MS = PERIOD_MS
WIND_MS = 5760
WIND_GAIN = 1.8
FLOOR = 284
CAMERA_START_X = 120
GROUND_SPEED = WORLD_WIDTH * 1000 / PERIOD_MS
GROUND_SPEED_PX_S = GROUND_SPEED
panorama = Image.open(ROOT / 'assets/panorama.png').convert('RGB')
assert panorama.size == (WORLD_WIDTH, H)
base = panorama.crop((CAMERA_START_X, 0, CAMERA_START_X + W, H))

# These are world coordinates, not viewport coordinates. Affected regions stay
# well inside the world tile, so the texture seam is never bent by the breeze.
CROWN_REGIONS = (
    (137, 49, 85, 53, 1.2),
    (420, 60, 210, 59, 1.8),
    (628, 49, 190, 57, 2.1),
    (816, 58, 112, 44, 2.3),
    (467, 126, 139, 36, 1.6),
)
STATIC_WORLD_REGIONS = {
    'ground_roots_and_lower_scene': (0, 180, WORLD_WIDTH, H),
    'mail_workshop': (660, 150, 960, H),
    'lower_trunk': (185, 125, 285, 270),
    'left_wrap_edge': (0, 0, 40, H),
    'right_wrap_edge': (960, 0, WORLD_WIDTH, H),
}


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def displacement(x, y, ms):
    """Small inverse-coordinate crown sway; world roots and road stay rigid."""
    if y >= 180 or x <= 40 or x >= 960:
        return 0.0, 0.0
    phase = math.tau * (ms % WIND_MS) / WIND_MS
    weights, dx, dy = 0.0, 0.0, 0.0
    for j, (cx, cy, rx, ry, amount) in enumerate(CROWN_REGIONS):
        radius = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        weight = max(0.0, 1.0 - radius) ** 2
        weights += weight
        dx += weight * amount * WIND_GAIN * math.sin(phase - j * .19)
        dy += weight * amount * WIND_GAIN * .65 * math.sin(phase - j * .19 + .24)
    denominator = max(1.0, weights)
    # Protect the thick trunk and the top border, easing into the outer limbs.
    trunk_lock = 1.0 - smooth((y - 75) / 45) * (1.0 - smooth((x - 290) / 70))
    border = smooth(y / 10)
    return dx / denominator * trunk_lock * border, dy / denominator * trunk_lock * border


@lru_cache(maxsize=32)
def world_frame(wind_ms):
    """Whole world in its own coordinates; callers must not mutate it."""
    wind_ms %= WIND_MS
    mesh = []
    for y in range(0, 180, 10):
        for x in range(0, WORLD_WIDTH, 12):
            right, bottom = min(WORLD_WIDTH, x + 12), min(180, y + 10)

            def source(a, b):
                dx, dy = displacement(a, b, wind_ms)
                return a + dx, b + dy

            mesh.append(((x, y, right, bottom), source(x, y) + source(x, bottom)
                         + source(right, bottom) + source(right, y)))
    canopy = panorama.transform((WORLD_WIDTH, 180), Image.Transform.MESH,
                                mesh, Image.Resampling.BICUBIC)
    world = panorama.copy()
    world.paste(canopy, (0, 0))
    # Explicit copies also keep interpolation at protected ROI boundaries from
    # changing any ground, root, workshop or wrap-edge source pixel.
    for box in STATIC_WORLD_REGIONS.values():
        world.paste(panorama.crop(box), box[:2])
    return world


def offset_at(ms):
    """Camera moves right; the painted world therefore moves left on screen."""
    return (CAMERA_START_X + round(WORLD_WIDTH * (ms % PERIOD_MS) / PERIOD_MS)) % WORLD_WIDTH


def frame(ms):
    """Return an opaque RGB 800×348 background, periodic in milliseconds."""
    phase = round(ms) % PERIOD_MS
    source = world_frame(phase % WIND_MS)
    offset = offset_at(phase)
    first_width = min(W, WORLD_WIDTH - offset)
    out = Image.new('RGB', (W, H))
    out.paste(source.crop((offset, 0, offset + first_width, H)), (0, 0))
    if first_width < W:
        out.paste(source.crop((0, 0, W - first_width, H)), (first_width, 0))
    return out


scenery = frame

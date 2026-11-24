"""Narrow moving path; preserve the original painted foreground.

The mountain, tree roots, postal-house foundations and cliff stay in the clean
plate. Only the small walkable contact band scrolls. This is a local motion
illusion, not a physically complete scrolling panorama.
"""
from functools import lru_cache
from pathlib import Path
import math

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1200, 522
PERIOD, SPEED, TILE_WIDTH = 12.0, 20.0, 240
TOP, BOTTOM = 422, 442
TAU = 2 * math.pi


def _smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


@lru_cache(maxsize=1)
def _resources():
    plate = Image.open(ROOT / 'assets' / 'clean-plate.png').convert('RGBA')
    plate = plate.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    # This central section contains the path itself, away from the roots and
    # building. Keep its original vertical scale and painted pebble sizes.
    tile = plate.crop((450, TOP, 450 + TILE_WIDTH, BOTTOM))
    px = tile.load()
    # Match only texture-space ends once. No moving/background crossfade.
    # Both sides approach one shared edge column with a smooth derivative.
    seam_width = 12
    for y in range(tile.height):
        original = [px[x, y] for x in range(TILE_WIDTH)]
        edge = tuple(round((original[0][c] + original[-1][c]) / 2)
                     for c in range(4))
        for k in range(seam_width):
            amount = _smoothstep(k / (seam_width - 1))
            for x in (k, TILE_WIDTH - 1 - k):
                px[x, y] = tuple(round(edge[c] * (1 - amount) +
                                      original[x][c] * amount) for c in range(4))
    road = Image.new('RGBA', (WIDTH + TILE_WIDTH * 2, BOTTOM - TOP))
    for x in range(0, road.width, TILE_WIDTH):
        road.alpha_composite(tile, (x, 0))
    mask = Image.new('L', (WIDTH, BOTTOM - TOP))
    mp = mask.load()
    for x in range(WIDTH):
        # Irregular shoulders avoid a visible straight cut through the art.
        top = 425.0 + .7 * math.sin(TAU * x / 153) + .35 * math.sin(TAU * x / 47)
        bottom = 439.0 + .6 * math.sin(TAU * x / 187 + .9)
        for yy in range(BOTTOM - TOP):
            y = TOP + yy
            coverage = (_smoothstep((y - top) / 3.0) *
                        _smoothstep((bottom - y) / 3.0))
            mp[x, yy] = round(255 * coverage)
    return plate, road, mask


def apply_terrain(background, t):
    """Return a fresh 1200x522 RGBA frame; contact speed is 20 px/s leftward.

    Supply the clean scenery/canopy frame, before actors and particle effects.
    Everything outside rows 422..441 is preserved byte for byte, including the
    original richly painted cliff. The function has exact 12-second periodicity.
    """
    if background.size != (WIDTH, HEIGHT):
        raise ValueError('apply_terrain requires a 1200x522 background')
    _, road, mask = _resources()
    out = background.convert('RGBA').copy()
    shift = (SPEED * round(float(t) % PERIOD, 8)) % TILE_WIDTH
    strip = road.transform((WIDTH, BOTTOM - TOP), Image.Transform.AFFINE,
                           (1, 0, shift, 0, 1, 0), Image.Resampling.BICUBIC)
    out.paste(strip, (0, TOP), mask)
    return out


if __name__ == '__main__':
    plate, _, _ = _resources()
    review = ROOT / 'review'
    review.mkdir(exist_ok=True)
    frames = [apply_terrain(plate, t) for t in (0, 3)]
    for t, frame in zip((0, 3), frames):
        frame.save(review / f'terrain-{t:02d}.png')
    assert ImageChops.difference(frames[0].convert('RGB'), apply_terrain(plate, 12).convert('RGB')).getbbox() is None
    for frame in frames:
        assert ImageChops.difference(frame.crop((0, BOTTOM, WIDTH, HEIGHT)).convert('RGB'),
                                     plate.crop((0, BOTTOM, WIDTH, HEIGHT)).convert('RGB')).getbbox() is None
    # Original / phase 0 / phase 3, same scale, useful for visual inspection.
    rows = []
    for name, frame in [('original', plate), ('t=0', frames[0]), ('t=3', frames[1])]:
        crop = frame.crop((0, 396, WIDTH, HEIGHT)).convert('RGB')
        ImageDraw.Draw(crop).text((5, 4), name, fill='white', stroke_width=1, stroke_fill='black')
        rows.append(crop)
    sheet = Image.new('RGB', (WIDTH, rows[0].height * 3))
    for i, row in enumerate(rows):
        sheet.paste(row, (0, i * row.height))
    sheet.save(review / 'terrain-comparison.png')
    print('terrain previews created; exact 12 s periodicity and unchanged lower foreground verified')

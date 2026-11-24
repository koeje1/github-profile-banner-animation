"""Register sixteen newly drawn whole-body Mir poses, preserving source alpha.

Only equal-cell extraction, one uniform scale, and rigid translation are used.
Color/alpha thresholds below measure landmarks and bounds; they do not edit
the image. No limbs are cut apart, no contour is erased, and no poses morph.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops, ImageDraw, ImageStat

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source-sheet-relaxed.png"
SCALE = 0.35
CANVAS = (160, 100)
BODY_ANCHOR = (80, 60)
HORN_ANCHOR = (94, 26)
FRAME_MS = 80


def checker(size, step=10):
    image = Image.new("RGBA", size, (241, 236, 232, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if (x // step + y // step) % 2:
                draw.rectangle((x, y, x+step-1, y+step-1), fill=(224, 221, 218, 255))
    return image


def gold_centroid(image, roi):
    pixels = image.load()
    points = [(x, y) for y in range(roi[1], roi[3]) for x in range(roi[0], roi[2])
              if (lambda red, green, blue, alpha: alpha >= 200 and red > 120 and green > 70
                  and red > 1.13 * green and blue < .8 * green)(*pixels[x, y])]
    assert len(points) > 20, ("Too few horn pixels", len(points), roi)
    return sum(x for x, _ in points)/len(points), sum(y for _, y in points)/len(points), len(points)


sheet = Image.open(SOURCE).convert("RGBA")
assert sheet.getchannel("A").getextrema() == (0, 255), "Source must retain real transparency"
frames, entries = [], []
for index in range(16):
    col, row = index % 4, index // 4
    cell = (round(col*sheet.width/4), round(row*sheet.height/4),
            round((col+1)*sheet.width/4), round((row+1)*sheet.height/4))
    raw = sheet.crop(cell)
    raw.save(HERE / f"raw-cell-{index:02d}.png")
    roi = (round(raw.width*.52), round(raw.height*.05), round(raw.width*.80), round(raw.height*.29))
    cx, cy, count = gold_centroid(raw, roi)
    inverse = (1/SCALE, 0, cx-HORN_ANCHOR[0]/SCALE,
               0, 1/SCALE, cy-HORN_ANCHOR[1]/SCALE)
    aligned = raw.convert("RGBa").transform(CANVAS, Image.Transform.AFFINE, inverse,
                                            Image.Resampling.BICUBIC).convert("RGBA")
    path = HERE / f"frame-{index}.png"
    aligned.save(path)
    visible = aligned.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    assert visible and 0 < visible[0] < visible[2] < CANVAS[0] and 0 < visible[1] < visible[3] < CANVAS[1], (index, visible)
    ax, ay, measured_count = gold_centroid(aligned, (80, 14, 107, 35))
    frames.append(aligned)
    entries.append({"index": index, "file": path.name, "source_cell": list(cell),
                    "source_horn_roi": list(roi), "source_horn_centroid": [cx, cy], "source_horn_pixels": count,
                    "measured_output_horn_centroid": [ax, ay], "measured_output_horn_pixels": measured_count,
                    "visible_bbox_alpha_128": list(visible),
                    "visible_size_alpha_128": [visible[2]-visible[0], visible[3]-visible[1]],
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

assert len({entry["sha256"] for entry in entries}) == 16, "Terminal or intermediate pose duplicated"
red_alpha = [a for red, green, blue, a in sheet.getdata() if red > 180 and green < 60 and blue < 100]
contact = checker((640, 496))
draw = ImageDraw.Draw(contact)
for index, frame in enumerate(frames):
    x, y = (index%4)*160, (index//4)*124
    contact.alpha_composite(frame, (x, y))
    draw.text((x+8, y+104), f"{index:02d} | {index*FRAME_MS:4d} ms", fill=(54,45,52,255))
contact.convert("RGB").save(HERE / "pose-contact-native.png")
contact.resize((1280, 992), Image.Resampling.NEAREST).convert("RGB").save(HERE / "pose-contact-2x.png")
composites = []
for frame in frames:
    composite = checker(CANVAS)
    composite.alpha_composite(frame)
    composites.append(composite.convert("RGB"))
palette_sheet = Image.new("RGB", (CANVAS[0], CANVAS[1]*16))
for index, composite in enumerate(composites):
    palette_sheet.paste(composite, (0, index*CANVAS[1]))
palette = palette_sheet.quantize(colors=255)
indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in composites]
indexed[0].save(HERE / "pose-preview.gif", save_all=True, append_images=indexed[1:],
                duration=FRAME_MS, loop=0, disposal=1, palette=palette.getpalette())
with Image.open(HERE / "pose-preview.gif") as gif:
    assert gif.n_frames == 16
    for i in range(16):
        gif.seek(i)
        assert gif.info["duration"] == FRAME_MS
        assert ImageChops.difference(gif.convert("RGB"), indexed[i].convert("RGB")).getbbox() is None
diffs = []
for index in range(16):
    delta = ImageChops.difference(composites[index-1], composites[index])
    diffs.append(sum(ImageStat.Stat(delta).mean)/3)
head_x = [entry["measured_output_horn_centroid"][0] for entry in entries]
head_y = [entry["measured_output_horn_centroid"][1] for entry in entries]
metadata = {
    "source": SOURCE.name, "source_size": list(sheet.size), "source_grid": [4,4],
    "source_type": "New whole-body illustrated poses generated with built-in image_gen using approved V17 and V19 references.",
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "canvas": list(CANVAS), "body_anchor": list(BODY_ANCHOR), "horn_anchor": list(HORN_ANCHOR),
    "uniform_scale": SCALE, "direction": "right", "mirrored": False,
    "order": list(range(16)), "recommended_frame_ms": FRAME_MS, "recommended_cycle_ms": 16*FRAME_MS,
    "unique_whole_body_frames": 16, "duplicate_terminal_pose": False,
    "processing": "Equal-cell crop, uniform premultiplied-alpha bicubic resampling and rigid head registration only. No recolor, alpha threshold edit, contour erase, per-frame fitting, limb cutting or morphing.",
    "source_alpha_preserved": True,
    "source_fringe": {"red_pixel_count": len(red_alpha), "red_pixel_max_alpha": max(red_alpha, default=0),
                      "handling": "Preserved untouched in source; premultiplied-alpha sampling prevents invisible RGB bleed."},
    "registration": {"landmark": "golden horn centroid in fixed upper-head ROI",
                     "measured_output_horn_x_range": [min(head_x),max(head_x)],
                     "measured_output_horn_y_range": [min(head_y),max(head_y)]},
    "adjacent_frame_MAD_with_seam_first": diffs,
    "preview_gif_all_frames_decoded_exactly": True,
    "limits": ["Generated drawings can retain small contour and proportion changes; landmark registration does not prove visual identity.",
               "Wing motion quality must be reviewed at native size in the full banner.",
               "An 80ms authored pose hold is a timing choice, not an assertion of source-game animation."],
    "frames": entries,
}
(HERE / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps({"frames":16,"canvas":CANVAS,"body_anchor":BODY_ANCHOR,"horn_anchor":HORN_ANCHOR,
                  "scale":SCALE,"frame_ms":FRAME_MS,"cycle_ms":16*FRAME_MS,
                  "visible_sizes":[entry["visible_size_alpha_128"] for entry in entries],
                  "registration":metadata["registration"],"source_fringe":metadata["source_fringe"],
                  "adjacent_frame_MAD_with_seam_first":diffs}, indent=2))

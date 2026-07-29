from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "gif_project"
WORK = ROOT / "work"

SOURCE_ALPHA = WORK / "dragon_walk_generated_alpha.png"
REFERENCE = PROJECT / "00_reference" / "master_reference.png"
BACKGROUND = PROJECT / "02_master" / "background_master.png"
HERO_SHEET = PROJECT / "03_assets" / "characters" / "hero_walk_sheet.png"

SHEET_OUT = PROJECT / "03_assets" / "characters" / "dragon_walk_sheet.png"
PREVIEW_DIR = PROJECT / "04_previews"
FRAME_PREVIEW_OUT = PREVIEW_DIR / "dragon_walk_frame_preview.png"
COMPOSITE_OUT = PREVIEW_DIR / "dragon_walk_composite_preview.png"
ANIMATION_OUT = PREVIEW_DIR / "dragon_walk_animation_preview.gif"
COMPARE_OUT = PREVIEW_DIR / "dragon_walk_vs_original.png"

CELL_W = 240
CELL_H = 190
BASELINE_Y = 180
SCENE_ORIGIN = (455, 416)
HERO_ORIGIN = (625, 344)
HERO_CELL_W = 300
TARGET_WIDTH = 204

# Exact isolated runs in the chroma-removed generation. Each run is one frame.
SOURCE_BOXES = (
    (77, 190, 525, 524),
    (594, 192, 1041, 524),
    (1099, 192, 1545, 524),
    (1608, 192, 2053, 524),
)


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def checker(size: tuple[int, int], tile: int = 12) -> Image.Image:
    out = Image.new("RGBA", size, (25, 23, 40, 255))
    draw = ImageDraw.Draw(out)
    colors = ((35, 32, 54, 255), (48, 43, 67, 255))
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            draw.rectangle(
                (x, y, min(x + tile - 1, size[0] - 1), min(y + tile - 1, size[1] - 1)),
                fill=colors[((x // tile) + (y // tile)) % 2],
            )
    return out


def harden_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    rgba.putalpha(alpha)
    return rgba


def build_frames() -> list[Image.Image]:
    source = Image.open(SOURCE_ALPHA).convert("RGBA")
    frames: list[Image.Image] = []
    for box in SOURCE_BOXES:
        crop = source.crop(box)
        bbox = crop.getchannel("A").getbbox()
        if bbox is None:
            raise RuntimeError(f"No visible pixels in source frame box: {box}")
        crop = crop.crop(bbox)
        scale = TARGET_WIDTH / crop.width
        target_h = round(crop.height * scale)
        resized = crop.resize((TARGET_WIDTH, target_h), Image.Resampling.NEAREST)
        resized = harden_alpha(resized)

        frame = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        x = (CELL_W - TARGET_WIDTH) // 2
        y = BASELINE_Y - target_h
        frame.alpha_composite(resized, (x, y))
        frames.append(frame)
    return frames


def build_sheet(frames: list[Image.Image]) -> Image.Image:
    sheet = Image.new("RGBA", (CELL_W * len(frames), CELL_H), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * CELL_W, 0))
    return sheet


def build_scene(frame: Image.Image) -> Image.Image:
    scene = Image.open(BACKGROUND).convert("RGBA")
    scene.alpha_composite(frame, SCENE_ORIGIN)
    hero_sheet = Image.open(HERO_SHEET).convert("RGBA")
    hero_frame = hero_sheet.crop((0, 0, HERO_CELL_W, hero_sheet.height))
    scene.alpha_composite(hero_frame, HERO_ORIGIN)
    return scene


def build_frame_preview(frames: list[Image.Image]) -> Image.Image:
    scale = 3
    label_h = 64
    gap = 12
    panel_w = CELL_W * scale
    panel_h = CELL_H * scale
    width = panel_w * 4 + gap * 3
    out = Image.new("RGBA", (width, label_h + panel_h), (18, 16, 30, 255))
    draw = ImageDraw.Draw(out)
    font = load_font(22)
    labels = ("F1 CONTACT A", "F2 PASS A", "F3 CONTACT B", "F4 PASS B")

    for index, frame in enumerate(frames):
        x0 = index * (panel_w + gap)
        panel = checker((panel_w, panel_h), tile=18)
        scaled = frame.resize((panel_w, panel_h), Image.Resampling.NEAREST)
        panel.alpha_composite(scaled)
        out.alpha_composite(panel, (x0, label_h))

        draw.text((x0 + 12, 18), labels[index], font=font, fill=(244, 222, 234, 255))
        center_x = x0 + (CELL_W // 2) * scale
        ground_y = label_h + BASELINE_Y * scale
        draw.line((center_x, label_h, center_x, label_h + panel_h - 1), fill=(57, 214, 239, 255), width=2)
        draw.line((x0, ground_y, x0 + panel_w - 1, ground_y), fill=(255, 194, 90, 255), width=3)
        draw.rectangle((x0, label_h, x0 + panel_w - 1, label_h + panel_h - 1), outline=(105, 91, 133, 255), width=2)
    return out


def build_animation(frames: list[Image.Image]) -> list[Image.Image]:
    scale = 3
    out_frames: list[Image.Image] = []
    font = load_font(18)
    labels = ("F1 CONTACT A", "F2 PASS A", "F3 CONTACT B", "F4 PASS B")
    for index, frame in enumerate(frames):
        canvas = checker((CELL_W * scale, CELL_H * scale + 42), tile=18)
        draw = ImageDraw.Draw(canvas)
        scaled = frame.resize((CELL_W * scale, CELL_H * scale), Image.Resampling.NEAREST)
        canvas.alpha_composite(scaled, (0, 0))
        ground_y = BASELINE_Y * scale
        draw.line((0, ground_y, canvas.width - 1, ground_y), fill=(255, 194, 90, 255), width=3)
        draw.text((12, CELL_H * scale + 9), labels[index], font=font, fill=(244, 222, 234, 255))
        out_frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
    return out_frames


def build_comparison(new_scene: Image.Image) -> Image.Image:
    crop_box = (430, 400, 710, 630)
    ref_crop = Image.open(REFERENCE).convert("RGBA").crop(crop_box)
    new_crop = new_scene.crop(crop_box)
    scale = 2
    label_h = 54
    gap = 18
    panel_w = ref_crop.width * scale
    panel_h = ref_crop.height * scale
    out = Image.new("RGBA", (panel_w * 2 + gap, label_h + panel_h), (18, 16, 30, 255))
    draw = ImageDraw.Draw(out)
    font = load_font(22)
    draw.text((14, 15), "ORIGINAL", font=font, fill=(244, 222, 234, 255))
    draw.text((panel_w + gap + 14, 15), "NEW COMPOSITE / F1", font=font, fill=(244, 222, 234, 255))
    out.alpha_composite(ref_crop.resize((panel_w, panel_h), Image.Resampling.NEAREST), (0, label_h))
    out.alpha_composite(new_crop.resize((panel_w, panel_h), Image.Resampling.NEAREST), (panel_w + gap, label_h))
    return out


def main() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    SHEET_OUT.parent.mkdir(parents=True, exist_ok=True)

    frames = build_frames()
    sheet = build_sheet(frames)
    sheet.save(SHEET_OUT)

    frame_preview = build_frame_preview(frames)
    frame_preview.convert("RGB").save(FRAME_PREVIEW_OUT)

    scene = build_scene(frames[0])
    scene.convert("RGB").save(COMPOSITE_OUT)

    animation_frames = build_animation(frames)
    animation_frames[0].save(
        ANIMATION_OUT,
        save_all=True,
        append_images=animation_frames[1:],
        duration=140,
        loop=0,
        disposal=2,
        optimize=False,
    )

    comparison = build_comparison(scene)
    comparison.convert("RGB").save(COMPARE_OUT)

    for index, frame in enumerate(frames, start=1):
        print(f"F{index} alpha bbox: {frame.getchannel('A').getbbox()}")
    print(f"sheet: {SHEET_OUT} {sheet.size}")
    print(f"scene origin: {SCENE_ORIGIN}; scene baseline: {SCENE_ORIGIN[1] + BASELINE_Y}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "03_assets"
EXPORTS = ROOT / "05_exports"
REPORT_PATH = ROOT / "04_previews" / "github_profile_banner_dev_validation.json"

CANVAS_SIZE = (1913, 822)
TOTAL_DURATION_MS = 5040

HERO_DURATION_MS = 120
DRAGON_DURATION_MS = 180
PAPER_DURATION_MS = 140
MAGIC_DURATION_MS = 140
LANTERN_DURATION_MS = 300
VINE_DURATION_MS = 320
SPEECH_DURATION_MS = 120
LOWER_TEXT_DURATION_MS = 200

HERO_ORIGIN = (625, 344)
DRAGON_ORIGIN = (421, 416)
HERO_SHADOW_ORIGIN = (697, 579)
DRAGON_SHADOW_ORIGIN = (487, 583)
VINE_ORIGIN = (380, 334)
EFFECT_ORIGIN_Y = 241
PAPER_ORIGIN_X = 850
SPEECH_ORIGIN = (638, 225)
LOWER_BANNER_ORIGIN = (335, 673)

HERO_GEM_SCENE_X = 884
MAGIC_LOCAL_START_X = (34, 28, 30, 30)

OUTPUT_GIF = EXPORTS / "github_profile_banner_dev_preview.gif"
OUTPUT_PNG = EXPORTS / "github_profile_banner_dev_preview.png"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()


def split_sheet(path: Path, frame_size: tuple[int, int], frame_count: int) -> list[Image.Image]:
    sheet = Image.open(path).convert("RGBA")
    expected = (frame_size[0] * frame_count, frame_size[1])
    if sheet.size != expected:
        raise RuntimeError(f"{path}: expected {expected}, got {sheet.size}")
    return [
        sheet.crop(
            (
                index * frame_size[0],
                0,
                (index + 1) * frame_size[0],
                frame_size[1],
            )
        )
        for index in range(frame_count)
    ]


def load_assets() -> tuple[dict[str, object], list[Path]]:
    paths = {
        "background": ROOT / "02_master" / "background_master.png",
        "hero": [
            ASSETS / "characters" / f"hero_walk_{index:02d}.png"
            for index in range(1, 7)
        ],
        "dragon": ASSETS / "characters" / "dragon_walk_sheet.png",
        "hero_shadow": ASSETS / "characters" / "shadows" / "hero_shadow.png",
        "dragon_shadow": ASSETS / "characters" / "shadows" / "dragon_shadow.png",
        "vine": ASSETS / "foliage" / "vine_cluster_A_sheet.png",
        "lantern": ASSETS / "effects" / "lantern_glow_sheet.png",
        "magic": ASSETS / "effects" / "magic_effect_sheet.png",
        "paper": ASSETS / "effects" / "paper_effect_sheet.png",
        "speech_bubble": ASSETS / "ui" / "speech_bubble.png",
        "speech_text": ASSETS / "ui" / "speech_bubble_text_sheet.png",
        "lower_banner": ASSETS / "ui" / "lower_banner.png",
        "lower_text": ASSETS / "ui" / "lower_banner_text_sheet.png",
    }
    flat_paths: list[Path] = []
    for value in paths.values():
        if isinstance(value, list):
            flat_paths.extend(value)
        else:
            flat_paths.append(value)
    missing = [str(path) for path in flat_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing render inputs:\n" + "\n".join(missing))

    assets = {
        "background": Image.open(paths["background"]).convert("RGBA"),
        "hero": [Image.open(path).convert("RGBA") for path in paths["hero"]],
        "dragon": split_sheet(paths["dragon"], (240, 190), 4),
        "hero_shadow": Image.open(paths["hero_shadow"]).convert("RGBA"),
        "dragon_shadow": Image.open(paths["dragon_shadow"]).convert("RGBA"),
        "vine": split_sheet(paths["vine"], (62, 88), 4),
        "lantern": split_sheet(paths["lantern"], CANVAS_SIZE, 4),
        "magic": split_sheet(paths["magic"], (850, 360), 4),
        "paper": split_sheet(paths["paper"], (850, 360), 4),
        "speech_bubble": Image.open(paths["speech_bubble"]).convert("RGBA"),
        "speech_text": split_sheet(paths["speech_text"], (366, 109), 10),
        "lower_banner": Image.open(paths["lower_banner"]).convert("RGBA"),
        "lower_text": split_sheet(paths["lower_text"], (1284, 92), 6),
    }
    if assets["background"].size != CANVAS_SIZE:
        raise RuntimeError("background_master canvas size changed")
    if any(frame.size != (300, 280) for frame in assets["hero"]):
        raise RuntimeError("latest hero frames must all be 300x280")
    return assets, flat_paths


def alpha_composite_at(base: Image.Image, layer: Image.Image, origin: tuple[int, int]) -> None:
    base.alpha_composite(layer, origin)


def state_at(time_ms: int) -> dict[str, int]:
    return {
        "hero": (time_ms // HERO_DURATION_MS) % 6,
        "dragon": (time_ms // DRAGON_DURATION_MS) % 4,
        "paper": (time_ms // PAPER_DURATION_MS) % 4,
        "magic": (time_ms // MAGIC_DURATION_MS) % 4,
        "lantern": (time_ms // LANTERN_DURATION_MS) % 4,
        "vine": (time_ms // VINE_DURATION_MS) % 4,
        "speech": min(time_ms // SPEECH_DURATION_MS, 9),
        "lower_text": min(time_ms // LOWER_TEXT_DURATION_MS, 5),
    }


def compose(assets: dict[str, object], time_ms: int) -> Image.Image:
    state = state_at(time_ms)
    frame = assets["background"].copy()

    # Preserve the documented first-complete-render layer order.
    alpha_composite_at(frame, assets["vine"][state["vine"]], VINE_ORIGIN)
    alpha_composite_at(frame, assets["lantern"][state["lantern"]], (0, 0))
    alpha_composite_at(frame, assets["hero_shadow"], HERO_SHADOW_ORIGIN)
    alpha_composite_at(frame, assets["dragon_shadow"], DRAGON_SHADOW_ORIGIN)
    alpha_composite_at(frame, assets["dragon"][state["dragon"]], DRAGON_ORIGIN)
    alpha_composite_at(frame, assets["hero"][state["hero"]], HERO_ORIGIN)

    magic_index = state["magic"]
    magic_origin_x = HERO_GEM_SCENE_X - MAGIC_LOCAL_START_X[magic_index]
    alpha_composite_at(
        frame,
        assets["magic"][magic_index],
        (magic_origin_x, EFFECT_ORIGIN_Y),
    )
    alpha_composite_at(
        frame,
        assets["paper"][state["paper"]],
        (PAPER_ORIGIN_X, EFFECT_ORIGIN_Y),
    )
    alpha_composite_at(frame, assets["speech_bubble"], SPEECH_ORIGIN)
    alpha_composite_at(
        frame,
        assets["speech_text"][state["speech"]],
        SPEECH_ORIGIN,
    )
    alpha_composite_at(frame, assets["lower_banner"], LOWER_BANNER_ORIGIN)
    alpha_composite_at(
        frame,
        assets["lower_text"][state["lower_text"]],
        LOWER_BANNER_ORIGIN,
    )
    return frame.convert("RGB")


def event_times() -> list[int]:
    times = {0, TOTAL_DURATION_MS}
    for duration in (
        HERO_DURATION_MS,
        DRAGON_DURATION_MS,
        PAPER_DURATION_MS,
        MAGIC_DURATION_MS,
        LANTERN_DURATION_MS,
        VINE_DURATION_MS,
    ):
        times.update(range(duration, TOTAL_DURATION_MS, duration))
    times.update(
        index * SPEECH_DURATION_MS
        for index in range(1, 10)
        if index * SPEECH_DURATION_MS < TOTAL_DURATION_MS
    )
    times.update(
        index * LOWER_TEXT_DURATION_MS
        for index in range(1, 6)
        if index * LOWER_TEXT_DURATION_MS < TOTAL_DURATION_MS
    )
    return sorted(times)


def hero_anchor_validation(hero_frames: list[Image.Image]) -> dict[str, object]:
    ground_y = []
    crystal_centers = []
    for frame in hero_frames:
        rgba = np.asarray(frame)
        alpha = rgba[:, :, 3]
        yy, _ = np.nonzero(alpha == 255)
        ground_y.append(int(yy.max()))

        rgb = rgba[:, :, :3].astype("int16")
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        crystal = (
            (alpha == 255)
            & (r >= 105)
            & (g >= 135)
            & (b >= 175)
            & (b >= r + 12)
            & (b >= g - 2)
        )
        opaque_y, opaque_x = np.nonzero(alpha == 255)
        crystal[:, : max(0, int(opaque_x.max()) - 32)] = False
        cy, cx = np.nonzero(crystal)
        crystal_centers.append(
            (round(float(cx.mean())), round(float(cy.mean())))
        )

    assert ground_y == [252] * 6
    assert crystal_centers == [(259, 78)] * 6
    return {
        "local_ground_y": ground_y,
        "scene_ground_y": [HERO_ORIGIN[1] + value for value in ground_y],
        "local_crystal_centers": crystal_centers,
        "scene_crystal_centers": [
            (HERO_ORIGIN[0] + x, HERO_ORIGIN[1] + y)
            for x, y in crystal_centers
        ],
    }


def main() -> None:
    assets, input_paths = load_assets()
    hashes_before = {str(path): sha256(path) for path in input_paths}
    anchors = hero_anchor_validation(assets["hero"])

    timeline = event_times()
    preview = compose(assets, TOTAL_DURATION_MS - 1)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    preview.save(OUTPUT_PNG, optimize=True)

    palette_reference = preview.quantize(
        colors=256,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    palette = palette_reference.getpalette()

    encoded_frames: list[Image.Image] = []
    durations: list[int] = []
    previous_bytes: bytes | None = None
    for start, end in zip(timeline[:-1], timeline[1:]):
        rgb = compose(assets, start)
        indexed = rgb.quantize(
            palette=palette_reference,
            dither=Image.Dither.NONE,
        )
        indexed.putpalette(palette)
        frame_bytes = indexed.tobytes()
        duration = end - start
        if frame_bytes == previous_bytes:
            durations[-1] += duration
            continue
        encoded_frames.append(indexed)
        durations.append(duration)
        previous_bytes = frame_bytes

    encoded_frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=encoded_frames[1:],
        duration=durations,
        loop=0,
        disposal=1,
        optimize=True,
    )

    hashes_after = {str(path): sha256(path) for path in input_paths}
    assert hashes_before == hashes_after

    with Image.open(OUTPUT_GIF) as animation:
        decoded_durations = [
            int(frame.info.get("duration", 0))
            for frame in ImageSequence.Iterator(animation)
        ]
        decoded_count = len(decoded_durations)
        decoded_size = animation.size
        decoded_loop = animation.info.get("loop")

    assert decoded_size == CANVAS_SIZE
    assert sum(decoded_durations) == TOTAL_DURATION_MS
    assert decoded_loop == 0

    old_gif = EXPORTS / "github_profile_banner_final.gif"
    with Image.open(old_gif) as animation:
        old_durations = [
            int(frame.info.get("duration", 0))
            for frame in ImageSequence.Iterator(animation)
        ]

    report = {
        "status": "PASS",
        "branch_expected": "test",
        "canvas_size": CANVAS_SIZE,
        "layer_order": [
            "background_master",
            "vine_cluster_A",
            "lantern_glow",
            "hero_shadow / dragon_shadow",
            "dragon_walk / hero_walk",
            "magic_effect",
            "paper_effect",
            "speech_bubble / speech_bubble_text",
            "lower_banner / lower_banner_text",
        ],
        "timing_ms": {
            "hero": HERO_DURATION_MS,
            "dragon": DRAGON_DURATION_MS,
            "paper": PAPER_DURATION_MS,
            "magic": MAGIC_DURATION_MS,
            "lantern": LANTERN_DURATION_MS,
            "vine": VINE_DURATION_MS,
            "speech_typing": SPEECH_DURATION_MS,
            "lower_text_typing": LOWER_TEXT_DURATION_MS,
        },
        "hero": {
            "files": [repo_path(path) for path in input_paths if "hero_walk_0" in path.name],
            "frame_count": 6,
            "loop_duration_ms": HERO_DURATION_MS * 6,
            "origin": HERO_ORIGIN,
            "anchors": anchors,
        },
        "magic": {
            "local_start_x": MAGIC_LOCAL_START_X,
            "scene_origins_x": [
                HERO_GEM_SCENE_X - value for value in MAGIC_LOCAL_START_X
            ],
            "scene_start": (884, 422),
        },
        "lantern": {
            "file": repo_path(ASSETS / "effects" / "lantern_glow_sheet.png"),
            "frame_count": 4,
            "loop_duration_ms": LANTERN_DURATION_MS * 4,
            "origin": (0, 0),
            "new_body_file_present": False,
        },
        "outputs": {
            "gif": repo_path(OUTPUT_GIF),
            "png": repo_path(OUTPUT_PNG),
            "gif_frames": decoded_count,
            "gif_duration_ms": sum(decoded_durations),
            "gif_durations_ms": decoded_durations,
            "gif_bytes": OUTPUT_GIF.stat().st_size,
        },
        "baseline": {
            "gif": repo_path(old_gif),
            "gif_frames": len(old_durations),
            "gif_duration_ms": sum(old_durations),
            "gif_bytes": old_gif.stat().st_size,
        },
        "input_hashes_unchanged": True,
        "timeline_event_count_before_dedup": len(timeline) - 1,
        "timeline_frame_count_after_dedup": decoded_count,
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

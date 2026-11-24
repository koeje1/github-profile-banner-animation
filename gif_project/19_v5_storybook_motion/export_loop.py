"""Export V19 and verify encoding, timing, fixed scenery and loop mechanics.

These checks do not establish natural movement or replace visual review.
The renderer owns all artwork, motion choices, durations and scene geometry.
"""
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import subprocess
import time

from PIL import Image, ImageChops, ImageDraw, ImageSequence, ImageStat
import imageio_ffmpeg
import render_loop as r


def same(a, b, label):
    if ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is not None:
        raise AssertionError(label)


def mad(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fixed_bounds():
    if hasattr(r, "STATIC_BOUNDS"):
        return dict(r.STATIC_BOUNDS)
    # V19 reuses the 800x348 V18 scene. Scale its established protected regions.
    def scale(box):
        return tuple(round(value * (r.W / 800 if i % 2 == 0 else r.H / 348)) for i, value in enumerate(box))
    return {
        "ground": scale((0, 270, 800, 348)),
        "house": scale((555, 168, 800, 348)),
        "trunk": scale((80, 120, 180, 260)),
    }


def indexed_images(frames, sample_count=12):
    indices = sorted({round(i * (len(frames) - 1) / (sample_count - 1)) for i in range(sample_count)})
    atlas = Image.new("RGB", (r.W, r.H * len(indices)))
    for row, index in enumerate(indices):
        atlas.paste(frames[index], (0, row * r.H))
    palette = atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    return indexed, palette, indices


def save_and_validate_gif(indexed, palette, destination, duration_ms):
    # A single palette is supplied to every frame and the encoder. Pillow may
    # combine identical consecutive frames; validate the decoded timeline.
    indexed[0].save(destination, format="GIF", save_all=True, append_images=indexed[1:],
                    palette=palette.getpalette(), duration=duration_ms, loop=0,
                    disposal=1, optimize=True)
    source_index = 0
    encoded_durations = []
    with Image.open(destination) as decoded:
        assert decoded.info.get("loop") == 0, "GIF is not an infinite loop"
        encoded_count = decoded.n_frames
        for encoded_index, actual in enumerate(ImageSequence.Iterator(decoded)):
            actual_ms = actual.info.get("duration", 0)
            assert actual_ms > 0 and actual_ms % duration_ms == 0, ("GIF frame duration", encoded_index, actual_ms)
            repeats = actual_ms // duration_ms
            for _ in range(repeats):
                assert source_index < len(indexed), "GIF timeline exceeds source timeline"
                same(actual, indexed[source_index], f"GIF decoded frame {encoded_index}, source {source_index}")
                source_index += 1
            encoded_durations.append(actual_ms)
    assert source_index == len(indexed), ("GIF timeline truncated", source_index, len(indexed))
    return {"encoded_frames": encoded_count, "expanded_source_frames": source_index,
            "total_duration_ms": sum(encoded_durations), "frame_duration_ms_values": sorted(set(encoded_durations)),
            "all_decoded_frames_match_indexed_source": True, "loop": 0}


def write_mp4(frames, destination, fps):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    log = r.OUT / "encode.log"
    command = [ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-vcodec", "rawvideo",
               "-s", f"{r.W}x{r.H}", "-pix_fmt", "rgb24", "-r", str(fps), "-i", "-",
               "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
               "-movflags", "+faststart", str(destination)]
    with log.open("w", encoding="utf-8") as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)
        try:
            for frame in frames:
                process.stdin.write(frame.tobytes())
        finally:
            process.stdin.close()
        assert process.wait() == 0, log.read_text(encoding="utf-8")

    # Decode the finished MP4, checking its real frame count and retaining
    # samples for review. H.264 is lossy, so byte equality is not expected.
    reader = imageio_ffmpeg.read_frames(str(destination), pix_fmt="rgb24")
    metadata = next(reader)
    assert tuple(metadata["size"]) == (r.W, r.H), metadata
    assert abs(metadata["fps"] - float(fps)) < 0.02, metadata
    sample_indices = sorted({0, r.COUNT // 4, r.COUNT // 2, 3 * r.COUNT // 4, r.COUNT - 1})
    samples = {}
    count = 0
    for count, raw in enumerate(reader, start=1):
        if count - 1 in sample_indices:
            samples[count - 1] = Image.frombytes("RGB", (r.W, r.H), raw)
    assert count == r.COUNT, ("MP4 decoded frame count", count, r.COUNT)
    make_scene_sheet(samples, r.REVIEW / "mp4-decoded-review.jpg")
    decode = subprocess.run([ffmpeg, "-v", "error", "-stream_loop", "2", "-i", str(destination),
                             "-an", "-progress", "pipe:1", "-f", "null", "-"],
                            capture_output=True, text=True, timeout=max(180, r.COUNT // 2))
    (r.OUT / "three-loop-decode.log").write_text(decode.stdout + decode.stderr, encoding="utf-8")
    assert decode.returncode == 0, decode.stderr
    progress_counts = [int(line.split("=", 1)[1]) for line in decode.stdout.splitlines() if line.startswith("frame=")]
    assert progress_counts and progress_counts[-1] == 3 * r.COUNT, ("MP4 three-loop frame count", progress_counts[-1:])
    return {"codec": metadata.get("codec"), "fps": metadata["fps"], "decoded_frames": count,
            "three_loop_decoded_frames": progress_counts[-1], "decode_errors": decode.stderr,
            "decoded_sample_indices": sample_indices}


def make_scene_sheet(samples, destination):
    tile_w = min(400, r.W)
    tile_h = round(r.H * tile_w / r.W)
    label_h = 24
    sheet = Image.new("RGB", (tile_w * 2, (tile_h + label_h) * math.ceil(len(samples) / 2)), "#1b1722")
    draw = ImageDraw.Draw(sheet)
    for slot, (index, frame) in enumerate(samples.items()):
        x, y = (slot % 2) * tile_w, (slot // 2) * (tile_h + label_h)
        sheet.paste(frame.resize((tile_w, tile_h), Image.Resampling.LANCZOS), (x, y + label_h))
        draw.text((x + 6, y + 6), f"Frame {index} | {index * r.FRAME_MS / 1000:.3f}s", fill="white")
    sheet.save(destination, quality=95)


def motion_review(frames, palette):
    # This short review crop follows the actors so anatomy is easy to inspect.
    # Its reset is explicitly not a production loop-boundary test.
    length = min(len(frames), max(1, round(1900 / r.FRAME_MS)))
    candidates = []
    for index in range(max(1, len(frames) - length + 1)):
        start_x = r.positions(index * r.FRAME_MS)[0]
        end_x = r.positions((index + length - 1) * r.FRAME_MS)[0]
        if start_x >= 205 and end_x <= r.W - 95 and end_x >= start_x:
            candidates.append(index)
    if not candidates:
        return {"created": False, "reason": "No fully visible 1.9-second interval."}
    start = candidates[0]
    crops = []
    for index in range(start, start + length):
        ex = r.positions(index * r.FRAME_MS)[0]
        crops.append(frames[index].crop((ex - 205, r.FLOOR - 120, ex + 95, r.FLOOR + 30)))
    indexed = [crop.quantize(palette=palette, dither=Image.Dither.NONE) for crop in crops]
    destination = r.REVIEW / "motion-review-1p9s.gif"
    result = save_and_validate_gif(indexed, palette, destination, r.FRAME_MS)
    result.update({"created": True, "file": destination.name, "start_frame": start,
                   "crop_size": [300, 150], "native_pixel_density": True,
                   "purpose": "Short motion review; crop follows actors; restart is not the production loop seam."})
    return result


def main():
    started = time.perf_counter()
    r.OUT.mkdir(parents=True, exist_ok=True)
    r.REVIEW.mkdir(parents=True, exist_ok=True)
    assert r.COUNT > 1 and r.FRAME_MS > 0
    assert r.FRAME_MS % 10 == 0, "GIF needs exact centisecond frame durations"
    assert r.COUNT * r.FRAME_MS == r.DURATION_MS, "Count/duration mismatch"
    assert r.W % 2 == 0 and r.H % 2 == 0, "H.264 yuv420p needs even dimensions"
    periods = {"evan": r.EVAN_CYCLE_MS, "mir": r.MIR_CYCLE_MS, "wind": r.WIND_MS}
    for label, cycle in periods.items():
        assert cycle > 0 and r.DURATION_MS % cycle == 0, f"{label} phase does not close at duration"
    fps = Fraction(1000, r.FRAME_MS)
    bounds = fixed_bounds()
    references = {label: r.base.crop(box) for label, box in bounds.items()}
    frames = []
    positions = []
    for index in range(r.COUNT):
        ms = index * r.FRAME_MS
        background = r.scenery((ms // 60 * 60) % r.WIND_MS)
        for label, box in bounds.items():
            same(background.crop(box), references[label], f"{label} changed at {ms}ms")
        current = r.frame(ms).convert("RGB")
        assert current.size == (r.W, r.H), (index, current.size)
        frames.append(current)
        positions.append(r.positions(ms))
        if index % max(1, r.COUNT // 12) == 0:
            print(f"Render {index}/{r.COUNT}", flush=True)
    same(r.frame(0), r.frame(r.DURATION_MS), "Loop endpoint differs")
    same(r.frame(r.FRAME_MS), r.frame(r.DURATION_MS + r.FRAME_MS), "Next loop frame differs")

    wraps, forward_steps = [], []
    for index in range(r.COUNT):
        previous = (index - 1) % r.COUNT
        old, new = positions[previous][0], positions[index][0]
        if new < old:
            wraps.append(index)
            assert r.actor_layer(previous * r.FRAME_MS).getbbox() is None, f"Actors visible before wrap at frame {index}"
            assert r.actor_layer(index * r.FRAME_MS).getbbox() is None, f"Actors visible after wrap at frame {index}"
        else:
            forward_steps.append(new - old)
    assert wraps, "No offscreen wrap was found"
    assert max(forward_steps) > 0, "Actors do not travel"
    assert max(forward_steps) - min(forward_steps) <= 1, ("Uneven actor travel", sorted(set(forward_steps)))
    steps = [mad(frames[index - 1], frames[index]) for index in range(1, len(frames))]
    seam = mad(frames[-1], frames[0])
    assert min(steps) - 1e-8 <= seam <= max(steps) + 1e-8, ("Loop seam exceeds regular frame-step range", seam, min(steps), max(steps))
    frames[0].save(r.OUT / "poster.png")
    indices = sorted({round(i * (r.COUNT - 1) / 11) for i in range(12)} |
                     {max(0, min(r.COUNT - 1, wrap + delta)) for wrap in wraps for delta in (-32, -8, -1, 0, 8, 32)})
    make_scene_sheet({i: frames[i] for i in indices}, r.REVIEW / "entry-exit-review.jpg")

    print("Encode global-palette GIF", flush=True)
    indexed, palette, palette_indices = indexed_images(frames)
    gif = r.OUT / "banner-v5-storybook.gif"
    gif_report = save_and_validate_gif(indexed, palette, gif, r.FRAME_MS)
    short_review = motion_review(frames, palette)
    del indexed
    print("Encode and decode MP4", flush=True)
    mp4 = r.OUT / "banner-v5-storybook.mp4"
    mp4_report = write_mp4(frames, mp4, fps)
    report = {
        "status": "File integrity and loop mechanics passed; perceptual quality requires visual review.",
        "size": [r.W, r.H], "frame_count": r.COUNT, "duration_ms": r.DURATION_MS,
        "frame_duration_ms": r.FRAME_MS, "fps": float(fps), "fps_fraction": str(fps),
        "cycle_periods_ms": periods, "cycle_phases_close_exactly": True,
        "endpoint_and_next_loop_frame_exact": True,
        "source_scenery_fixed_all_frames": {label: {"fixed": True, "bounds": list(box)} for label, box in bounds.items()},
        "actor_wrap_frames": wraps, "actors_and_shadows_fully_offscreen_at_wrap": True,
        "forward_step_px_values": sorted(set(forward_steps)), "evan_baseline_y": r.FLOOR,
        "seam_MAD": seam, "min_step_MAD": min(steps), "mean_step_MAD": sum(steps) / len(steps), "max_step_MAD": max(steps),
        "seam_within_regular_frame_step_range": True,
        "global_palette_sample_indices": palette_indices, "gif": gif_report, "mp4": mp4_report,
        "short_motion_review": short_review, "screen_playback_observed": False,
        "limits": ["File checks do not prove natural anatomy, gait, wind or appealing animation.",
                   "GIF uses a shared 255-color palette; MP4 is a lossy H.264 encode.",
                   "The short crop follows the actors and has an arbitrary reset; assess the full banner for the real loop seam."],
        "files": {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in (gif, mp4)},
        "elapsed_seconds": time.perf_counter() - started,
    }
    (r.OUT / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

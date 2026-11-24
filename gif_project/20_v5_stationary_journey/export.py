"""Export V20 and verify encoding, timing, fixed actors and scrolling loop mechanics.

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
import render as r
import scenery


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


def indexed_images(frames, sample_count=12):
    indices = sorted({round(i * (len(frames) - 1) / (sample_count - 1)) for i in range(sample_count)})
    atlas = Image.new("RGB", (r.W, r.H * len(indices)))
    for row, index in enumerate(indices):
        atlas.paste(frames[index], (0, row * r.H))
    palette = atlas.quantize(colors=92, method=Image.Quantize.MEDIANCUT)
    # The tiny cyan staff crystal is outvoted by the pink landscape in median
    # cut. Keep four highlight shades so it cannot turn cream like a torch.
    crystal = [80,170,205, 115,198,235, 160,220,250, 205,243,255]
    palette.putpalette(palette.getpalette()[:92*3] + crystal + [0]*((256-96)*3))
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


def main():
    started = time.perf_counter()
    r.OUT.mkdir(parents=True, exist_ok=True)
    r.REVIEW.mkdir(parents=True, exist_ok=True)
    assert r.COUNT * r.FRAME_MS == r.DURATION_MS
    assert r.DURATION_MS % r.EVAN_CYCLE_MS == 0
    assert r.DURATION_MS % r.MIR_CYCLE_MS == 0
    assert r.FRAME_MS % 10 == 0
    assert r.W % 2 == r.H % 2 == 0
    expected_positions = r.positions(0)
    frames = []
    for index in range(r.COUNT):
        ms = index * r.FRAME_MS
        assert r.positions(ms) == expected_positions, 'Characters drift horizontally'
        current = r.frame(ms)
        assert current.size == (r.W, r.H)
        frames.append(current)
        if index % 48 == 0:
            print(f'Render {index}/{r.COUNT}', flush=True)
    same(r.frame(0), r.frame(r.DURATION_MS), 'Loop endpoint differs')
    same(r.frame(r.FRAME_MS), r.frame(r.DURATION_MS+r.FRAME_MS), 'Next loop frame differs')
    for ms in range(0, r.DURATION_MS-r.EVAN_CYCLE_MS, r.EVAN_CYCLE_MS):
        same(r.actor_layer(0), r.actor_layer(ms), 'Actor cycle does not repeat in place')
    same(scenery.frame(0), scenery.frame(r.DURATION_MS), 'Scenery period differs')
    steps = [mad(frames[i-1], frames[i]) for i in range(1, len(frames))]
    seam = mad(frames[-1], frames[0])
    assert seam <= max(steps) * 1.05, ('Loop seam exceeds normal frame steps', seam, max(steps))
    frames[0].save(r.OUT / 'poster.png')
    scene_indices = sorted({round(i*(r.COUNT-1)/9) for i in range(10)})
    make_scene_sheet({i:frames[i] for i in scene_indices}, r.REVIEW/'scroll-review.jpg')

    # Native-density contact sheet, all sixteen poses against the actual scenery.
    sheet = Image.new('RGB', (320*4, 140*4), '#f4e6d3')
    draw = ImageDraw.Draw(sheet)
    for pose in range(16):
        x, y = pose%4*320, pose//4*140
        crop = frames[pose*2].crop((255, 174, 575, 294))
        sheet.paste(crop, (x,y+20))
        draw.text((x+6,y+4), f'{pose:02d} | {pose*r.POSE_MS} ms', fill='#332733')
    sheet.save(r.REVIEW/'duet-16-poses.png')
    print('Encode and decode MP4', flush=True)
    mp4 = r.OUT/'banner-v5-stationary.mp4'
    mp4_report = write_mp4(frames, mp4, Fraction(1000, r.FRAME_MS))
    print('Encode global-palette GIF', flush=True)
    indexed, palette, samples = indexed_images(frames, sample_count=24)
    gif = r.OUT/'banner-v5-stationary.gif'
    gif_report = save_and_validate_gif(indexed, palette, gif, r.FRAME_MS)
    if gif.stat().st_size >= 100_000_000:
        raise AssertionError('GIF exceeds repository single-file limit; tune palette before delivery')
    pose_review(palette)
    del indexed
    report = {
        'status':'Encoding and loop mechanics passed; visual findings are recorded in README.',
        'size':[r.W,r.H], 'frame_count':r.COUNT, 'frame_duration_ms':r.FRAME_MS,
        'duration_ms':r.DURATION_MS, 'pose_duration_ms':r.POSE_MS,
        'authored_whole_poses':{'evan':len(r.evan),'mir':len(r.mir)},
        'actors_fixed_at_x':list(expected_positions), 'evan_floor':r.FLOOR,
        'world_width':scenery.WORLD_WIDTH, 'background_speed_px_per_second':scenery.GROUND_SPEED,
        'background_scroll':'Full panorama moves left; no terrain conveyor strip or background dissolve.',
        'exact_actor_and_background_phase_closure':True,
        'endpoint_and_next_loop_frame_exact':True,
        'seam_MAD':seam, 'min_step_MAD':min(steps), 'mean_step_MAD':sum(steps)/len(steps), 'max_step_MAD':max(steps),
        'seam_within_regular_frame_step_range':seam<=max(steps),
        'global_palette_colors':96, 'global_palette_sample_indices':samples,
        'reserved_crystal_colors':[[80,170,205],[115,198,235],[160,220,250],[205,243,255]],
        'gif':gif_report,'mp4':mp4_report,
        'limits':['Whole-pose drawings can retain small anatomy changes and uneven planted-foot travel.',
                  'Pose holds are 80 ms; background output is 40 ms.',
                  'File tests do not establish natural movement.'],
        'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha256(p)} for p in (gif,mp4)},
        'elapsed_seconds':time.perf_counter()-started,
    }
    (r.OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


def pose_review(palette):
    # A short pose loop uses one still background, so its restart cannot be
    # mistaken for the full panorama's 23.04-second wrap boundary.
    base = scenery.frame(0).convert('RGBA')
    review = []
    for ms in range(0, r.EVAN_CYCLE_MS, r.FRAME_MS):
        current = base.copy()
        current.alpha_composite(r.actor_layer(ms))
        review.append(current.convert('RGB').crop((255,174,575,294)).quantize(palette=palette,dither=Image.Dither.NONE))
    return save_and_validate_gif(review, palette, r.REVIEW/'duet-native-one-cycle.gif', r.FRAME_MS)


if __name__ == '__main__':
    main()

"""Render the current rig once, export delivery media, and audit file integrity.

Contact sheets support a separate visual inspection. Successful checks here do
not establish that playback looks natural or that a screen player was observed.
"""
from pathlib import Path
import json
import runpy
import subprocess
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageSequence, ImageStat
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'exports'
REVIEW = ROOT / 'review'
FPS, SECONDS = 25, 12
FRAME_COUNT, FRAME_MS = FPS * SECONDS, 40
NATIVE_SIZE, GIF_SIZE, MASTER_SIZE = (1200, 522), (800, 348), (960, 418)


def mad(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def assert_identical(a, b, label):
    assert ImageChops.difference(a.convert('RGB'), b.convert('RGB')).getbbox() is None, label


def save_review(frames):
    for page in range(12):
        sheet = Image.new('RGB', (1500, 750))
        draw = ImageDraw.Draw(sheet)
        for cell in range(25):
            index = page * 25 + cell
            x, y = cell % 5 * 300, cell // 5 * 150
            sheet.paste(frames[index].crop((450, 297, 750, 447)), (x, y))
            draw.text((x + 4, y + 4), f'{index:03d}  {index / FPS:.2f}s',
                      fill='white', stroke_width=1, stroke_fill='black')
        sheet.save(REVIEW / f'all-frames-{page:02d}.jpg', quality=94)
    scene_indices = [round(i * (FRAME_COUNT - 1) / 47) for i in range(48)]
    for page in range(3):
        sheet = Image.new('RGB', (1600, 696))
        draw = ImageDraw.Draw(sheet)
        for cell in range(16):
            index = scene_indices[page * 16 + cell]
            x, y = cell % 4 * 400, cell // 4 * 174
            sheet.paste(frames[index].resize((400, 174), Image.Resampling.LANCZOS), (x, y))
            draw.text((x + 4, y + 4), f'{index:03d}  {index / FPS:.2f}s',
                      fill='white', stroke_width=1, stroke_fill='black')
        sheet.save(REVIEW / f'scenes-{page}.jpg', quality=94)
    frames[0].save(OUT / 'poster.png')
    return scene_indices


def main():
    start = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    REVIEW.mkdir(exist_ok=True)
    # runpy does not add the script directory for its local terrain import.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    renderer = runpy.run_path(str(ROOT / 'render.py'))
    frame = renderer['frame']
    frames = []
    for index in range(FRAME_COUNT):
        rendered = frame(index / FPS)
        assert rendered.size == NATIVE_SIZE and rendered.mode == 'RGB'
        frames.append(rendered)
        if index % 50 == 0:
            print(f'render {index}/{FRAME_COUNT}', flush=True)
    assert_identical(frames[0], frame(SECONDS), 'loop endpoint')
    assert_identical(frames[1], frame(SECONDS + 1 / FPS), 'loop next frame')
    scene_indices = save_review(frames)

    # Reserve one palette entry for unchanged-pixel transparency optimization.
    palette_sample = Image.new('RGB', (NATIVE_SIZE[0], NATIVE_SIZE[1] * 4))
    for row, index in enumerate((0, 53, 117, 185)):
        palette_sample.paste(frames[index], (0, row * NATIVE_SIZE[1]))
    palette = palette_sample.quantize(colors=255)
    indexed = [item.resize(GIF_SIZE, Image.Resampling.LANCZOS).quantize(
        palette=palette, dither=Image.Dither.NONE) for item in frames]
    gif = OUT / 'banner-v5-weighted-walk.gif'
    indexed[0].save(gif, save_all=True, append_images=indexed[1:],
                    duration=FRAME_MS, loop=0, disposal=1, optimize=True)
    with Image.open(gif) as decoded:
        assert decoded.n_frames == FRAME_COUNT and decoded.info['loop'] == 0
        assert decoded.size == GIF_SIZE
        for index, actual in enumerate(ImageSequence.Iterator(decoded)):
            assert actual.info['duration'] == FRAME_MS, ('GIF duration', index)
            assert_identical(indexed[index], actual, ('GIF pixels', index))
    for item in indexed:
        item.close()
    del indexed
    print('GIF: 300 decoded frames match the indexed source', flush=True)

    # Always overwrite from this run; never reuse a master from an older rig.
    master = REVIEW / 'master-lossless.webp'
    master_frames = [item.resize(MASTER_SIZE, Image.Resampling.LANCZOS) for item in frames]
    master_frames[0].save(master, save_all=True, append_images=master_frames[1:],
                          duration=FRAME_MS, loop=0, lossless=True, method=1)
    with Image.open(master) as decoded:
        assert decoded.n_frames == FRAME_COUNT and decoded.info['loop'] == 0
        for index, actual in enumerate(ImageSequence.Iterator(decoded)):
            assert_identical(master_frames[index], actual, ('lossless master pixels', index))
    for item in master_frames:
        item.close()
    del master_frames
    print('Lossless master: rewritten and all 300 frames verified', flush=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = OUT / 'banner-v5-weighted-walk.mp4'
    encode_log = OUT / 'encode.log'
    with encode_log.open('w', encoding='utf-8') as errors:
        proc = subprocess.Popen([
            ffmpeg, '-y', '-v', 'error', '-f', 'rawvideo', '-vcodec', 'rawvideo',
            '-s', '1200x522', '-pix_fmt', 'rgb24', '-r', str(FPS), '-i', '-',
            '-an', '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
            '-movflags', '+faststart', str(mp4)], stdin=subprocess.PIPE, stderr=errors)
        try:
            for item in frames:
                proc.stdin.write(item.tobytes())
        finally:
            proc.stdin.close()
        assert proc.wait() == 0, encode_log.read_text(encoding='utf-8')

    # The source scenery patch excludes legitimate petals/papers in the overlay.
    # This checks the painted structure, not whether overlay pixels stay fixed.
    patch_bounds = (1000, 375, 1060, 395)
    reference_patch = renderer['scenery'](0).crop(patch_bounds)
    for index in range(1, FRAME_COUNT):
        candidate = renderer['scenery'](index / FPS).crop(patch_bounds)
        assert_identical(reference_patch, candidate, ('static scenery building', index))
    steps = [mad(frames[index - 1], frames[index]) for index in range(1, FRAME_COUNT)]
    seam = mad(frames[-1], frames[0])

    decode_log = OUT / 'three-loop-decode.log'
    decode_start = time.perf_counter()
    decoded = subprocess.run([
        ffmpeg, '-v', 'error', '-stream_loop', '2', '-i', str(mp4),
        '-map', '0:v:0', '-an', '-fps_mode', 'passthrough',
        '-progress', str(decode_log), '-f', 'null', '-'], capture_output=True, text=True)
    decode_seconds = time.perf_counter() - decode_start
    progress = decode_log.read_text(encoding='utf-8')
    counts = [int(line.split('=', 1)[1]) for line in progress.splitlines() if line.startswith('frame=')]
    assert decoded.returncode == 0, decoded.stderr
    assert counts and counts[-1] == FRAME_COUNT * 3 and 'progress=end' in progress
    report = {
        'status': 'file integrity passed; visual inspection pending',
        'frames': FRAME_COUNT, 'fps': FPS, 'duration_ms': FRAME_COUNT * FRAME_MS,
        'native_size': list(NATIVE_SIZE), 'gif_size': list(GIF_SIZE),
        'gif_loop': 0, 'gif_all_frame_duration_ms': FRAME_MS,
        'gif_fixed_source_palette_colors': 255,
        'gif_decoded_matches_all_quantized_source_frames': True,
        'endpoint_and_next_frame_exact': True,
        'lossless_master': {'size': list(MASTER_SIZE), 'rewritten_this_run': True,
                            'all_decoded_frames_match_resized_source': True,
                            'path': 'review/master-lossless.webp'},
        'scenery_building_patch_identical_all_frames': True,
        'scenery_building_patch_bounds': list(patch_bounds),
        'seam_MAD': seam, 'ordinary_step_mean_MAD': sum(steps) / len(steps),
        'ordinary_step_max_MAD': max(steps),
        'seam_to_mean_step_ratio': seam / (sum(steps) / len(steps)) if sum(steps) else 0,
        'review_artifacts': {'character_contact_sheets': 12, 'character_frames': FRAME_COUNT,
                             'character_crop': [450, 297, 750, 447],
                             'full_scene_samples': 48, 'full_scene_frame_indices': scene_indices},
        'visual_review': 'pending', 'screen_playback': False,
        'three_loop_decode': {'purpose': 'file integrity only; not a screen playback check',
                              'cycles': 3, 'frames': counts[-1],
                              'wall_seconds': decode_seconds, 'errors': decoded.stderr},
        'remaining_limits': ['2D articulated painted rig; naturalness requires visual review',
                             'distant scenery stays fixed while the narrow contact path scrolls',
                             'GIF uses a fixed 255-color source palette'],
        'files': {item.name: item.stat().st_size for item in (gif, mp4, OUT / 'poster.png')},
        'elapsed_seconds': time.perf_counter() - start,
    }
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'gif_bytes': gif.stat().st_size,
                      'mp4_bytes': mp4.stat().st_size, 'seam_MAD': seam,
                      'mean_step_MAD': report['ordinary_step_mean_MAD'],
                      'decoded_loop_frames': counts[-1], 'screen_playback': False,
                      'elapsed_seconds': report['elapsed_seconds']}, indent=2), flush=True)


if __name__ == '__main__':
    main()

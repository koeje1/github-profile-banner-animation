# Mir timing comparison — existing complete poses only

## Recommendation for the next combined study

Use candidate **B, ping-pong** as the first trial:

| Pose | 0 | 1 | 2 | 3 | 4 | 3 | 2 | 1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Duration, ms | 150 | 120 | 90 | 90 | 120 | 90 | 150 | 150 |
| Start, ms | 0 | 150 | 270 | 360 | 450 | 570 | 660 | 810 |

The cycle is 960 ms, aligned to the existing 30 ms output interval. It removes the original 4→5 recovery jump, preserves the same first-five-pose body drawing family, and uses a somewhat quicker downstroke with a slower recovery. Pose 0 is not repeated at the endpoint; the loop proceeds from pose 1 to pose 0.

This is a **limited improvement**, not a complete repair. Pose 2 has the wing behind the back and close to horizontal; pose 3 has the broad membrane swung down beside the torso. That substantial 2↔3 angle change still occurs in both directions. A timing-only edit cannot create the missing intermediate wing angles.

## Anatomy comparison

- Original A, `0,1,2,3,4,5,6,7`: a directional upstroke is implied by poses 5–7, but the jump from deepest-down pose 4 to the shallower, raised pose 5 is large. The neck and leg silhouette also changes slightly in the latter pose group.
- Ping-pong B, `0,1,2,3,4,3,2,1`: avoids the largest recovery-specific substitution. Its main cost is visibly retracing the same wing shapes instead of showing a distinct feathered/folded recovery path. For this small friendly dragon, that is the safer compromise among the existing drawings.
- Bridge C, `0,1,2,3,4,3,5,6,7`: placing pose 3 after pose 4 bridges part of the wing descent, but 3→5 still changes the body/leg drawing and remains a noticeable wing-angle step. It was not clearly better on static anatomy inspection.

A second agent independently preferred B after inspecting the original sheet and registered contact sheet. Alpha-composited pixel differences were also saved for reference, but **do not establish that B is smoother**: every candidate retains the same largest 2→3 change, and the head/paw difference averages do not improve. The recommendation is based on removal of the specific 4→5 discontinuity and the visual drawing consistency, not a fabricated smoothness score.

## Low-flight body response

- Keep the existing Mir placement anchor (80,60).
- Mean body scene y: **251**.
- Amplitude: **1 px**. Do not exaggerate this to a jumping motion.
- Proposed screen-space y for B:

```python
mir_y = 251 + round(math.cos(2 * math.pi * (ms - 30) / 960))
```

The body is lowest near the beginning of the raised-wing phase (30 ms), then rises while the wing sweeps down. It reaches its highest position near 510 ms, at the center of the lowest-wing hold. This small phase relationship gives a power-stroke response without bending, scaling, or separately moving any limb. The ground at y287 has at least 6 px of clearance even under the conservative combination of the lowest wing extent and greatest downward body offset; actual phase-aligned clearance is greater.

Use the complete-pose image at an integer position. Avoid separate head bob, additional wing rotation, stretching, or crossfading. Those would obscure whether the existing whole-pose improvement works.

## Files and validation

- `timing-candidates.json`: three explicit timelines, body phase parameters, source path and unchanged-asset status.
- `timing-candidate-contact.png`: all three orders at native sprite size.
- `timing-candidates.mp4`: three candidates side by side, with native background composites and 2× checker views; five cycles, 4.8 seconds, 160 frames, 30 ms interval.
- `timing-candidates-poster.png`: one simultaneous comparison frame.
- `timing_candidates.py`: repeatable review-only generator.

The MP4 decoded without errors. The contact and source anatomy were inspected. **Actual screen playback has not been observed in this subtask**, so the next combined study should be watched before accepting the cadence. No source pose file or root renderer was modified.

# Mir full-pose asset audit

## Delivered assets and placement

- `assets/mir/frame-0.png` through `frame-7.png`: eight distinct transparent RGBA images, each 160×100.
- Facing right, already in travel direction. Do not mirror.
- Body placement anchor: **(80, 60)**. Draw top-left at `(scene_body_x - 80, scene_body_y - 60)`.
- Anatomical registration: fixed head-region golden-horn centroid placed at **(94, 26)**. Uniform source scale **0.245** for every pose. No floor alignment, morphing, limb warping, crossfading, recoloring, or per-frame fit.
- Alpha ≥128 extent is x27–123, y18–89. Typical pose height is 64–67 px, with the lowest downstroke extending to 71 px. No visible art reaches a canvas edge.
- At scene body anchor (350,250), visible bounds are x297–393 and y208–279; ground y287 remains at least 8 px below the lowest wing. Other poses have greater clearance. This is a low-flight placement, not walking.
- Suggested cadence is eight poses ×120 ms =960 ms. This is newly proposed timing for the generated illustration, not preserved original game timing.

## Inspected results

Inspected the original 4×2 sheet, native contact sheet, 2× contact sheet, and the pose-0 composite on the existing 800×348 background. All eight composites are saved in this directory for root's full-scene review. Playback itself has not been observed here; root is checking the animated scene.

- The young purple dragon, cream belly, golden curved horns, pale wing membrane, rounded friendly eye, and long horizontal tail are consistent across the eight poses. This is materially closer to the original warm illustration than the literal game sprites.
- Head registration is stable. The raw golden-horn centroid varies by less than 1.5 source pixels horizontally (less than 0.4 output pixels), and the aligned target is fixed. No need to compensate by moving the entire creature up and down per wing pose.
- Three paws are generally visible. The far fourth limb is occluded by the body/wing; the source does not visibly sprout an extra limb. The torso and tail stay coherent while the visible legs tuck and extend slightly.
- Wing order reads as raised (0–1), flattening (2), downstroke (3–4), and recovering (5–7). The 4→5 change is the largest pose step. Root should check its rhythm in actual playback before calling the movement smooth.
- The creature fits the background palette and reads clearly at native banner size. The generated contours are somewhat more polished and rounded than the textured background; this is a stylistic difference, not a clipping or registration defect.
- No visible red halo appeared on the checker or background composite. Source saturated-red fringe pixels have alpha at most 5/255 and are mostly alpha 1/255. Source RGBA was retained; premultiplied-alpha resampling prevents invisible RGB from bleeding into an opaque edge. No chroma-key cleanup or hard transparency threshold was applied.

## Review files

- `contact-native.png`, `contact-2x.png`: all eight poses on a subtle checker, with exact delivery-sized pose geometry.
- `background-frame-0.png` through `background-frame-7.png`: native-size composites with fixed body anchor (350,250).
- `background-contact.jpg`: all eight composites.
- `flight-background.apng`, `flight-checker.gif`: 960 ms review loops. These are inspection aids, not final banner exports.
- `assets/mir/metadata.json`: exact source cells, horn centroids, visible bounds, hashes, processing and suggested timing.
- `assets/mir/prepare.py`: deterministic crop/scale/registration and review generation script.

## Remaining acceptance check

Review the combined scene in motion: the 4→5 wing recovery, Mir's distance behind the walking character, the lowest wing's clearance during any added scene bob, and overall illustrated style. Avoid adding more than 1 px of bob without rechecking the low-flight placement. The static asset audit alone does not establish perceived animation quality.

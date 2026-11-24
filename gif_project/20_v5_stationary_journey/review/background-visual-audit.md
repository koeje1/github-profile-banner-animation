# V20 scrolling landscape review

The new panorama preserves the approved warm pink tree, purple valley and small mail workshop. It is a complete painted scene rather than a moving ground strip laid over a static backdrop. All of the scenery moves left together, with a small additional world-space canopy sway. Characters are deliberately absent from this module and review.

## Integration

- `scenery.frame(ms)` returns an opaque RGB image, 800×348.
- World tile: `assets/panorama.png`, 1044×348.
- `PERIOD_MS = 23040`; 18 cycles of the new 1280 ms character animation.
- `GROUND_SPEED = 45.3125` px/s to the left on screen.
- `FLOOR = 284`; the gold path surface occupies roughly y280–284 and the front grass edge begins below it.
- `CAMERA_START_X = 120` presents the giant tree on the left and workshop on the right initially.
- Wind period: 5760 ms. Crown gain increased to 1.8 after review found the original sway too subtle during scrolling. Sampled peak displacement is now approximately **4.12 px horizontal and 2.67 px vertical**. Terrain, roots, lower trunk, workshop and both wrap edges retain their exact world-source pixels.

## Visual findings

- The walkway stays level across the full width. Soil, grass and stone scale remain natural; no new stretched terrain or pasted horizontal band is visible.
- The tree and workshop pass through the viewport as coherent objects. The supplied multi-time contact shows a real journey through the world rather than a crossfade or the characters crossing a stationary picture.
- The spatial wrap joins the open valley and low vegetation naturally. A **faint sky exposure join** remains discernible under close inspection when it is placed at the center of the frame. It is subtle in the complete scene, not a hard ground break. Root reviewed and accepted retaining this version for the next composed study.
- One generated seam-repair attempt changed outer artwork too, so it was rejected. Runtime uses the uniformly resized first source, not the edited alternative.
- Canopy motion is confined to upper leaf/branch regions. The strengthened four-phase world-coordinate contact retains coherent branches, with no visible new tear at the fixed lower trunk; no terrain warping is introduced. All 144 protected-region checks were rerun successfully after the gain change.

## Verification and review files

`background-validation.json` records exact endpoint and next-frame periodicity, 1/2 px horizontal steps at 25 fps, and unchanged protected world pixels across all 144 wind samples. These checks establish the scene mechanics, not subjective motion quality.

- `background-poster.png`: initial viewport.
- `background-scroll-contact.jpg`: six positions across the complete loop.
- `background-wrap-center.png`: actual module output with the spatial join near x402.
- `background-scroll-seam-study.mp4`: 6.4 seconds at 25 fps, covering the join crossing the center. It decoded successfully.
- `wind-strength-contact.png`: four wind phases in fixed world coordinates after the 1.8× gain change.

The source, poster and contacts were visually inspected. The root's combined player review should judge the remaining faint sky join in motion. This subtask did not operate the shared player or modify V19.

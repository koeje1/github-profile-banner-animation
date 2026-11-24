# 에반 16포즈 생성

2026-11-24, Codex 내장 `image_gen` 도구. 투명 배경. 참조는 승인 삽화와 의상 세부 아틀라스이며 실제 게임 스프라이트를 참조하지 않았다.

```text
Use case: illustration-story. Asset type: production animation sheet, sixteen complete painted poses.
References: image1 establishes the warm storybook character identity and proportions. Image2 is ONLY costume/face detail; do NOT reproduce its separated body parts.
Create the same small boy adventurer in exactly SIXTEEN consecutive full-body walking poses arranged in a strict 4-column by 4-row square sheet, read left to right then top to bottom. Each equal square cell contains one complete boy facing RIGHT in the same side/three-quarter-side view. Stable camera, body scale, head identity, thin golden circlet with ruby, tousled plum-brown hair, violet gold-trim coat, burgundy lining, brown boots. Fine colored plum outlines, soft warm painterly pixel-inspired shading matching reference1, about three heads tall. No literal video game sprite.
This is an IN-PLACE relaxed walk cycle with intermediate drawings, NOT sixteen repeated contact poses and NOT a forward-moving layout. Pelvis center and head position almost fixed in every cell; soles on the same baseline. Natural short stride, ankle travel about one third of his height from front contact to rear toe-off. Exactly two interconnected legs, knees softly flexing, near and far legs alternate with clear overlap; far leg slightly darker. Low lift, no marching, no running.
Frame1 near leg forward heel contact / far leg behind toe contact.
Frames2,3,4 near foot takes weight and moves gradually rearward, far heel lifts and bends behind.
Frames5,6 near support leg passes under pelvis while far bent knee passes forward.
Frames7,8 near heel rises toward toe-off and far shin gradually extends forward, preparing opposite contact.
Frame9 FAR leg forward heel contact / NEAR leg behind toe contact, clearly opposite depth order to frame1.
Frames10,11,12 far foot takes weight and moves gradually rearward, near heel lifts and bends behind.
Frames13,14 far support passes under pelvis while near knee passes forward in front of the other leg.
Frames15,16 far heel rises and near shin extends forward, near heel still a little lifted, ending just BEFORE frame1 (do not duplicate frame1).
CRITICAL ARM AND STAFF FIX: Do NOT hold the staff upright like a torch. Carry it casually LOW beside the right hip. Staff hand stays around waist/upper-thigh height, shoulder relaxed, upper arm hangs beside torso, elbow loosely bent. Hold one slim short staff diagonally forward-up, around45degrees from vertical, so the small cyan crystal top sits around CHEST level, clearly below the face. The bottom tip stays clear of ground. The crystal is small, no fiery glow. Grip stays on the identical shaft location. The hand, forearm and staff swing TOGETHER subtly through each consecutive pose: diagonal angle naturally varies35→45→55→45→35degrees across the full cycle. No wrist dislocation, no sliding shaft, no frozen hand. The other empty arm swings gently opposite the near leg. Coat hem follows with a slight delayed sway, not changing outfit.
Use all16 distinct intermediate poses to make the shoulders/elbow/wrist/boots follow smooth connected arcs; small head bob of1-2percent character height only. Do not rotate entire character or zoom.
Every complete pose incl staff/coat/hair/boots fits with ample transparent margins in its cell. Head top around15percent cellheight, floor near88percent; character height around73percent ofcell. Consistent in-place pelvis x50percent. Genuine transparent background and clean alpha; no checkerboard, ground, cast shadows, colored matte, labels, numbers, gridlines, borders, scenery, dragon or extra props. Exactly16 coherent full-body drawings in4×4 cells.
```

출력 `exec-f2bb7ab3-e1d5-4fee-94ba-0d13c85718d8.png`를 `assets/evan-walk-16.png`에 보존한다.

# 삽화 동작 샘플 생성 기록

2026-11-24. Codex 내장 `image_gen` 도구 사용. 별도 유료 API 또는 CLI를 사용하지 않았다. 두 생성 모두 투명 배경을 요청했다. 입력은 `17_v5_weighted_walk/assets/approved-master.png`와 `rig-atlas.png`이며 실제 게임 스프라이트는 외형 참조에 넣지 않았다.

## 소년 — 입력 프롬프트

```text
Use case: illustration-story. Asset type: transparent full-pose animation sprite sheet for a warm storybook fantasy banner.
The first image is the approved illustration and the visual identity to preserve. The second image is only a detailed color/costume reference; DO NOT repeat its disassembled limbs. Create complete, coherently drawn full-body poses of the SAME BOY from the first illustration: plum-brown tousled hair, thin gold circlet with round ruby, dark violet long coat with delicate gold trim and burgundy lining, brown boots, one slim staff with a luminous cyan crystal. His proportions are about three heads tall, a youthful small adventurer, NOT the huge-headed two-head-tall in-game MapleStory sprite. Soft painterly pixel-inspired storybook shading, fine plum outlines, textured warm sunset light. This is an illustrated fantasy character, not a literal game asset.
Produce exactly 8 chronological walk-cycle frames, in a perfectly regular 4-column by 2-row sheet, read left-to-right then top-to-bottom. Wide 2:1 canvas, ideally 2048x1024 with eight equal 512x512 cells. One COMPLETE BOY per cell; every boy faces exactly RIGHT in the same side/three-quarter-side view, same clothing, same face, same size, same hairstyle and staff. The crown/head remain nearly stationary and identically sized between cells. Each cell has a consistent pelvis anchor at x256 and floor y448, the full pose fits between y64 and448 with ample clear margins, no crop or overlap.
Draw a real relaxed 8-pose walking cycle rather than rotating cutout legs: 1 near leg forward heel contact and far leg back toe contact; 2 weight settles on near foot, far foot lifts; 3 near supporting leg vertical, far bent knee passes forward; 4 near heel rises, far leg swings ahead; 5 FAR leg forward heel contact and NEAR leg back toe contact, inverse of pose1; 6 weight settles on far foot, near foot lifts; 7 far support vertical, near bent knee passes; 8 far heel rises, near leg swings ahead returning toward pose1. Short natural steps, clear knees and ankles, coherent body weight with only subtle head bob. The free arm swings slightly against the legs; the staff hand keeps the cyan crystal steadily in front and clearly above the floor; the coat hem follows softly with a slight delay. Exactly two arms and two legs per pose. No duplicated limbs, no slipping boots, no staff touching the ground. Consistent scale and side silhouette across all eight frames.
Genuinely TRANSPARENT background, preserved clean alpha around fine edges. No ground plane, no cast shadow, no background scenery, no labels or numbers, no grid lines, no borders, no other character. Do not include any limb cutouts or game UI. The deliverable is an orderly usable 8-frame complete-body walk animation sheet that matches the original illustration.
```

생성 출력: `exec-d33d728b-e581-43e9-9ff8-d7c6acadfa92.png` → `assets/evan-walk-sheet.png`.

## 어린 용 — 입력 프롬프트

```text
Use case: illustration-story. Asset type: transparent eight-frame complete-character animation sheet.
Use image1 as the approved STYLE and CHARACTER IDENTITY reference. Use image2 ONLY to see the lavender dragon's colors, face, horns, scales and wing materials in detail; do NOT copy separate cutout limbs or any background matte. Draw the same small friendly lavender-purple young dragon from image1, in complete full-body poses. Soft rounded muzzle and gentle large eyes, warm cream belly, short curved golden horns, small pink-lavender wing membranes, long curving tail, a low HORIZONTAL quadruped body and four short legs. A small, endearing companion, smaller and lower than the boy in image1. Preserve its illustrated storybook design. Do not turn it into a tall upright two-legged game dragon, dark-blue adult dragon, aggressive monster, or huge black-outlined pixel sprite.
Create exactly8chronological low-flight poses on a perfectly regular4-column2-row transparent sheet, reading lefttoright then topbottom. Ideally2048x1024, eight equal512x512cells. All8dragons faceRIGHT in the SAME side/three-quarter-side view, same size, same head, same camera, same horizontal body position. Each complete dragon incl horns,wings,tail,feet must fit within its own cell with generous margins. Keep head center nearx355y240 and torso centerx270y290 consistently; overallbody plus tail occupiesx60..440. Wings may extend upwardtoy80 and downwardtoy370 but never leavecell. Body is lightly floating only a little above a notionalground; keep fourlegs naturally and gently tucked underneath its horizontal body. Do not pose forearms against an upright chest. Head and body remain at nearlyfixedpositions throughsheet, no rotation, no morphing, no size change. Only wings flap naturally at their roots, tail follows gently and feet make tiny secondary changes.
8-phase wing cycle:1wingsfullyraised atupstroke apex;2wingsdiagonallyraised atbeginningdownstroke;3wings roughlyoutward atmiddownstroke;4wingssweptdown;5wingsatlow apex softlyfolded;6wingspartlyfolded recoveringoutward;7wingsliftupward with membranesfolded;8wingsopenjustbelowhigh apex returning smoothly to1. Draw each as a complete coherent character with exactlytwo wings andfourlegs; far legs/wings may bepartlyoccluded but no extra appendages. Constant face,horns,eyes,scales and markings. No invented symbols on forehead. Natural batlike membranes and smooth warm-shaded volumes.
Style: warm painterly pixel-inspired storybook fantasy, softly textured lavender scales, subtle gold-pink sunset rimlighting, fine colored plum outlines, delicate shading; exactsamevisualworld asimage1. No heavyblack 1pxgameoutlines, noflatcelvectorstyle, no photorealism.
Genuinely transparent background with clean alpha: no colored fringe, no red or gray halo/matte, no checkerboard, no background, no shadow, no floor, no gridlines, no labels/numbers/text, no human boy or costume parts. Only eight fully-drawn matching lavender dragon flight poses.
```

생성 출력: `exec-db5f9933-df1f-4285-aee0-fa74cf65878b.png` → `assets/mir-flight-sheet.png`.

생성된 포즈가 프롬프트의 모든 조건을 만족한다고 가정하지 않는다. 프레임별 같은 배율, 등록점, 실제 합성 크기에서의 외형과 접지를 별도로 검수한다.

## 보행 후반 교정 — 2026-11-24

계속 작업 요청 뒤 내장 `image_gen`으로 두 번 교정했다. 첫 4×2 시트 수정은 다리 구분 개선이 부족해 채택하지 않았다. 최종 반영은 별도 2×2 후반 네 포즈이며 `assets/evan-halfstep-v2.png`에 저장했다. `prepare_evan_v2.py`가 원본 전반 네 장과 새 후반 네 장을 등록한다. 알파 제거·관절 조각 변형·크로스페이드는 사용하지 않는다.

### 첫 수정 — 채택하지 않음

```text
Use case: precise-object-edit / animation correction.
Edit target: this existing transparent 4-column by 2-row eight-frame illustrated boy walk sheet. Keep the SAME character, costume, fine painterly style, size, four-column layout, transparent alpha, face, hair, gold circlet, single cyan staff, light direction and colors.
Critical change: correct ONLY the LOWER ROW's FOUR walking poses (frames 4,5,6,7). Preserve the TOP ROW'S FOUR COMPLETE POSES as supplied. The lower row currently repeats the same leading leg instead of switching legs. Redraw the lower-row legs and the naturally connected coat hem as a coherent full-body drawing, with a real second half of a relaxed forward walking gait. Every character faces RIGHT.
Clarify near/far: the leg nearer the viewer is the BRIGHTER, unobscured leg and boot. The far leg is slightly DARKER and behind the near leg where they overlap. This depth distinction stays consistent across the lower row.
LOWER ROW column1: FAR DARKER leg reaches forward toward RIGHT with heel contact, toe gently up; NEAR BRIGHTER leg extends backward toward LEFT with toe contact, heel raised. It must visibly be the OPPOSITE leading leg from upper-left frame0. Free near arm is forward.
LOWER ROW column2: FAR DARKER leg supports body nearly under pelvis with flat grounded sole; NEAR BRIGHTER leg lifts behind body toward LEFT with bent knee and toe off the ground. Small weight settling, not a run.
LOWER ROW column3: FAR DARKER leg supports under/behind pelvis, sole on ground; NEAR BRIGHTER thigh and bent knee swing forward toward RIGHT past the support leg, the bright boot is lifted clearly above ground. Free arm naturally returns back.
LOWER ROW column4: FAR DARKER leg extends backward with heel raised and toe still on ground; NEAR BRIGHTER leg extends forward toward RIGHT as a late swing, its heel hovering just ABOVE the baseline about to land in upper-left frame0. Do not duplicate a wide two-foot contact pose.
Keep upper bodies and head locations from the matching original lower-row cells, same chest/hip proportions and scale. Keep staff clear of the floor and in the same hand. Exactly two legs/two boots per character with anatomically connected hips, knees and ankles, short relaxed stride, no crossed impossible limbs. Same warm brown boots, violet trousers, burgundy coat lining. No added labels or guides.
All eight cells must remain fully separate and equally spaced with clear transparent margins. Genuinely transparent background, no floor, no cast shadow, no text, no gridlines. No other characters or game sprites.
```

### 채택한 후반 네 포즈

```text
Use case: illustration-story, character animation.
The attached sheet is a CHARACTER DESIGN REFERENCE ONLY. Make a NEW sheet with ONLY FOUR different complete poses in a regular TWO COLUMN by TWO ROW layout on a transparent square canvas. Do not reproduce the attached eight-pose layout.
Same small boy, exact same plum hair, gold circlet/red jewel, violet coat with gold trim, warm brown boots, cyan crystal staff, painterly warm fantasy style. Face RIGHT, same side view and scale in all four cells.
These FOUR poses are ONLY the second half of a walk: his camera-near leg is stepping FROM BACK TO FRONT. Clearly separate legs by overlap, the camera-near leg is in front when crossing.
Top left: near leg stretched BACKWARDS to LEFT, nearer boot under left trailing coat with lifted heel and grounded toe. Far leg stretched FORWARDS to RIGHT, farther boot in front at heel contact. The near thigh crosses in FRONT of the far thigh and slopes DOWN-LEFT. Do NOT put the near leg forward in this pose.
Top right: far leg grounded under torso, near leg folds backwards to LEFT, boot off ground behind him. Near thigh slopes down-left and near shin folds up behind.
Bottom left: far leg straight supporting body slightly behind, near knee lifted ahead to RIGHT, near boot floating in front of the support shin, clearly occluding it.
Bottom right: far leg behind with toe ground contact, near knee extending forward to RIGHT for next landing, near heel clearly elevated about 15 source pixels above the ground line, near shin reaches forward but is NOT yet at heel contact.
The near free arm starts forward and ends behind, staff stays in the far hand in front. Head and upper body nearly identical in all four poses, full bodies fit in equal square cells with generous transparent padding, no labels, no ground or shadow, no frame boxes. Make natural interconnected legs and boots as full drawings. The upper row and lower row are consecutive phases of ONE step; not four similar contact poses. Restrained relaxed walk, not jumping/running. Genuine transparent alpha.
```

참조: `assets/evan-walk-sheet.png` (디자인 참조). 생성 출력: `exec-fe926883-c932-4c42-a8ef-77e8f5cbf923.png`. 내장 도구 사용, 투명 배경. 새 6번의 다리 겹침과 7번의 들린 앞발을 반영했으나 4번의 가까운/먼 다리 구분이 명백하다고 단정하지 않는다.

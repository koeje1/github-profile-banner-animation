# 실제 메이플스토리 원본 동작 시험

결정한 조합은 **구형 에반의 걷기 + 2211 단계 미르의 낮은 비행**이다. 원본 프레임을 합성했으며 관절 회전, 다리 늘리기, 모핑, 광학 흐름 보간은 사용하지 않았다.

## 최종 합성에 사용할 파일

| 캐릭터 | 투명 PNG | 캔버스 | 왼쪽 방향 기준점 | 오른쪽으로 뒤집은 기준점 | 타이밍 |
|---|---|---|---|---|---|
| 에반 | `evan/aligned-0.png` ~ `aligned-3.png` | 128 × 128 | 81, 96 | 47, 96 | 각 180 ms, 총 720 ms |
| 미르 | `mir-dragon2211/aligned-0.png` ~ `aligned-5.png` | 320 × 240 | 160, 170 | 160, 170 | 각 120 ms, 총 720 ms |

두 원본 모두 왼쪽을 바라본다. 위 기준점은 픽셀 경계 좌표이며, 오른쪽으로 뒤집을 때 `x' = width - x`를 사용했다. 확대는 가로와 세로에 같은 배율을 적용한다.

미르의 기준점은 게임 데이터의 정확한 `origin`을 옮긴 것이다. 실제 발 끝은 이 점보다 15~18 원본 픽셀 위에 있다. 이것은 원본의 비행 높이이므로 발을 땅에 강제로 붙이거나 걷기 다리를 추가하면 원작 동작이 깨진다. 에반은 API가 이미 정렬한 원본 GIF에서 각 PNG의 위치를 복원했다. 에반의 X 기준점은 합성용 기준이며 게임 WZ 공식 좌표라고 주장하지 않는다. 프레임 사이 상대 위치는 원본에 따른다.

`selected-motion-test.gif`는 이 두 동작의 720 ms 결합 시험이다. `selected-motion-poster.png`는 그 첫 프레임이고, `mir-stage-comparison.png`는 2200/2211/2214/2217 전체 이동 프레임 비교이다. 2211은 작은 뿔, 큰 머리, 짧은 몸, 날개와 꼬리를 가진 어린 용의 외형을 유지하면서 성룡의 후광이 없어 선택했다. 네 단계 모두 확인한 `move` 동작은 지상 사족보행이 아니라 비행이다.

## 출처와 권리

2026-11-24에 로그인, API 키, 결제 없이 [MapleStory.IO](https://maplestory.io/)의 공개 API로 내려받았다. 게임 스프라이트 저작권은 **NEXON**에 있으며 **CC0 또는 퍼블릭 도메인이 아니다**. 무료 API 접근과 저작권 허락은 같은 의미가 아니다. 이 폴더에는 원본 JSON, URL, 프레임별 타이밍과 위치를 함께 보관한다.

- [에반 NPC 및 실제 외형 구성 아이템](https://maplestory.io/api/GMS/255/npc/1540407)
- [에반 걷기 원본 첫 PNG](https://maplestory.io/api/GMS/255/npc/1540407/render/walk1/0)
- [에반 원본 걷기 GIF](https://maplestory.io/api/GMS/255/Character/animated/2000/1003089,1050168,20537,1082272,33157,1072443,1382105/walk1/0)
- [에반 원본 프레임 간격 180 ms](https://maplestory.io/api/wz/GMS/255/Character/00002000.img/walk1/0/delay)
- [선택한 미르 2211의 이동 프레임 목록](https://maplestory.io/api/wz/GMS/255/Skill/Dragon/2211.img/move)
- [선택한 미르 첫 프레임 및 PNG 데이터](https://maplestory.io/api/wz/GMS/255/Skill/Dragon/2211.img/move/0)

처음 찾았던 작은 펫 미르 5000118은 `mir/`에 별도 보존했다. 최종 선택인 `mir-dragon2211/`와 혼동하지 않는다. 최종 매개변수는 `selected-motion.json`, 자세한 미르 프레임 출처는 `mir-dragon2211/metadata.json`을 사용한다.

`build_trial.py`와 `build_dragon_comparison.py`는 내려받은 원본을 다시 조립할 뿐 새로 네트워크 요청을 하지 않는다. 본 작업은 원본 17 버전을 수정하지 않았고 전체 배경 합성 및 커밋은 포함하지 않는다.

# Phase A 재실행 자산 — `candidates/` · `cache/`

2026-09-01 보존. **원본은 `/mnt/d/supersub-phaseA/`에 있고 여기 있는 것은 백업이다.**

Phase A와 B-1\~B-6은 전부 `/mnt/d/supersub-phaseA/`를 작업 루트로 썼다. 스크립트와
CSV·라벨은 이미 저장소에 들어와 있었지만 **바이너리 입력 두 종류가 그 드라이브에만
한 벌 있었다.** 합쳐 1.78MB인데, 잃으면 130MB짜리 원본 클립을 다시 모아야 하고
그 클립은 Kinetics/YouTube 링크에 매여 있어 다시 모을 수 있다는 보장이 없다.
크기 대비 위험이 맞지 않아 저장소로 옮겼다.

| | 파일 | 크기 | 없으면 |
|---|---|---|---|
| `candidates/` | 39 × `.npz` | **589KB** | **Track 1 재실행 불가** |
| `cache/` | 39 × `.npz` | **1.20MB** | Phase A 지표표를 GPU 없이 다시 낼 수 없다 |

md5 전수 대조로 원본과 동일함을 확인했다(39/39, 39/39).

## `candidates/` — 사람 후보 박스

`candidates.py`가 39클립에 RT-DETR을 돌려 남긴 **프레임별 person 후보 박스**다.
selector 평가(B-1\~B-6)의 입력이며, `labeling/targets.py:load_candidates()`가 읽는다.

```
<clip_id>.npz
  boxes       (T, 5) float32   — 프레임별로 이어 붙인 [x1, y1, x2, y2, score]
  n           (T,)   int64     — 프레임 t의 후보 수 (boxes를 잘라 쓰는 인덱스)
  frame_wh    (2,)   int64     — 원본 프레임 크기
  sampled_fps ()     float64   — read_frames의 실효 fps (target_fps=15로 만들었다)
```

39클립 합계 프레임 5,404, 후보 20,677개. 프레임당 후보 중앙 2.0, 최대 13.

**이것이 없으면 Track 1은 재실행 자체가 불가능하다.** 다시 만들려면
`clips/*.mp4` 130MB에 RT-DETR을 다시 돌려야 하고, 클립은 저장소에 없다.

## `cache/` — production selector 키포인트

`extract.py`가 **production 경로 그대로**(`pose.extract_keypoints`, `target_fps=15`,
`observe=False`) 39클립에서 뽑은 키포인트다. selector는 production의
`_largest_person_box`(= B-6의 `baseline` mode) 하나뿐이다.

```
<clip_id>.npz
  keypoints    (T, 17, 3) float64   — COCO-17, x·y·신뢰도
  source_fps   ()         float64
  sampled_fps  ()         float64
  obj_<이름>   (T, 3)     float64   — 도구 궤적 (sports_ball 등, 검출된 것만)
```

**보존 가치의 근거.** B-6의 5개 mode 중 baseline 한 줄밖에 복원하지 못하므로
selector 비교에는 부족하다. 그런데도 남기는 이유는 **임팩트 정의를 바꿀 때
GPU 없이 다시 계산할 수 있는 유일한 자산**이기 때문이다 —
`analyze_phaseA.py`·`summarize.py`·`final_checks.py`가 이 캐시만 읽고
`extract_features`를 호출한다. E-3(프레임 단위 값 물리 시간 표기)이나
E-6(탐색 범위 제한)을 시험할 때 39클립 지표표를 **CPU 수십 초**로 다시 낼 수 있다.
1.20MB에 그 값이면 남길 만하다.

## 여기 있는 사본은 아직 **읽히지 않는다**

`targets.py`와 `extract.py`, `selector_downstream.py`의 `ROOT`/`PHASE_A`가
`/mnt/d/supersub-phaseA`로 **하드코딩**돼 있다. 이 사본을 실제로 쓰려면

- `/mnt/d/supersub-phaseA/{candidates,cache}/`로 되돌려 놓거나,
- 스크립트의 경로 상수를 바꿔야 한다 (코드 변경이므로 별도 단계에서 판단한다).

**지금 상태에서 이 디렉터리는 백업이지 실행 경로가 아니다.** 이걸 넣었다고
`/mnt/d` 없이 B-6이 돌아가지는 않는다 — `clips/`(130MB)와 `labeling/`(31MB)이
여전히 그쪽에만 있다.

## 넣지 않은 것

| | 크기 | 이유 |
|---|---|---|
| `clips/*.mp4` | **130MB** | 저장소에 넣지 않는다. Kinetics 원본이고 크기가 맞지 않는다 |
| `labeling/` | 31MB | 렌더 이미지가 대부분이다. `labels.json`·`targets.py`는 이미 저장소에 있다 |
| B-6 selector별 키포인트 | ~5MB | 만들지 않기로 했다 — 재실행이 244초라 절약이 10분뿐이다 |

## 관련

- 재실행 절차와 비결정성: [`eval_b6/RERUN.md`](eval_b6/RERUN.md)
- 미결 11번 (이 의존이 남긴 위험): `jekyll/pages/pending.markdown`

# Phase A 재실행 자산 — `candidates_target{15,30}/` · `cache_target{15,30}/`

2026-09-01 보존, **2026-09-03에 실행 경로가 됐다.**

> ## 2026-09-03 — 두 가지가 바뀌었다
>
> **(1) 폴더 이름에 동작점을 넣었다.** `cache/` → `cache_target15/`,
> `candidates/` → `candidates_target15/`. 그냥 `cache/`면 어느 fps인지 이름으로
> 보이지 않아 섞어 쓰게 되고, 그게 미결 10번(서비스와 평가가 target_fps를
> 서로 다르게 얻는다)의 형태다.
>
> **(2) 현재 동작점(target 30)을 들여왔다.** 저장소에 보존해 둔 것이 target 15
> 인데 프로젝트는 2026-09-02에 target 30으로 옮겼다 — **보존 자산이 커밋된
> 결과와 다른 동작점이었다.** 미결 13번을 조사하다 드러났다(항목이 적어 둔
> 재현 경로로 `f297~f299`를 찾을 수 없었다. 저장소 사본은 150프레임이었다).
>
> | | 파일 | 크기 |
> |---|---|---|
> | `cache_target15/` | 39 × `.npz` | 1.3MB |
> | `cache_target30/` | 39 × `.npz` | **2.4MB** ← 새로 |
> | `candidates_target15/` | 39 × `.npz` | 652KB |
> | `candidates_target30/` | 39 × `.npz` + 39 × `.tools.json` | **2.2MB** ← 새로 |
>
> md5 전수 대조로 `/mnt/d` 원본과 동일함을 확인했다 (39/39, 78/78).
>
> **그리고 이제 읽힌다** — 아래 「읽히지 않는다」 절을 정정한다.

**원본은 `/mnt/d/supersub-phaseA/`에 있고 여기 있는 것은 사본이다.**

Phase A와 B-1\~B-6은 전부 `/mnt/d/supersub-phaseA/`를 작업 루트로 썼다. 스크립트와
CSV·라벨은 이미 저장소에 들어와 있었지만 **바이너리 입력 두 종류가 그 드라이브에만
한 벌 있었다.** 합쳐 몇 MB인데, 잃으면 130MB짜리 원본 클립을 다시 모아야 하고
그 클립은 Kinetics/YouTube 링크에 매여 있어 다시 모을 수 있다는 보장이 없다.
크기 대비 위험이 맞지 않아 저장소로 옮겼다.

| | 파일 | 크기 | 없으면 |
|---|---|---|---|
| `candidates_target*/` | 39 × `.npz` | 652KB / 2.2MB | **Track 1 재실행 불가** |
| `cache_target*/` | 39 × `.npz` | 1.3MB / 2.4MB | Phase A 지표표를 GPU 없이 다시 낼 수 없다 |

md5 전수 대조로 원본과 동일함을 확인했다.

## `candidates_target{15,30}/` — 사람 후보 박스

`candidates.py`가 39클립에 RT-DETR을 돌려 남긴 **프레임별 person 후보 박스**다.
selector 평가(B-1\~B-6)의 입력이며, `labeling/targets.py:load_candidates()`가 읽는다.

```
<clip_id>.npz
  boxes       (T, 5) float32   — 프레임별로 이어 붙인 [x1, y1, x2, y2, score]
  n           (T,)   int64     — 프레임 t의 후보 수 (boxes를 잘라 쓰는 인덱스)
  frame_wh    (2,)   int64     — 원본 프레임 크기
  sampled_fps ()     float64   — read_frames의 실효 fps (폴더 이름의 target 과 같다)
```

target 15 기준 39클립 합계 프레임 5,404, 후보 20,677개(프레임당 중앙 2.0, 최대 13).
target 30 은 프레임 수가 두 배라 후보도 그만큼 늘어난다.

**이것이 없으면 Track 1은 재실행 자체가 불가능하다.** 다시 만들려면
`clips/*.mp4` 130MB에 RT-DETR을 다시 돌려야 하고, 클립은 저장소에 없다.

## `cache_target{15,30}/` — production selector 키포인트

`extract.py`가 **production 경로 그대로**(`pose.extract_keypoints`, `observe=False`) 39클립에서 뽑은 키포인트다. selector는 production의
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
합쳐 3.7MB에 그 값이면 남길 만하다.

## 읽는 법 — `paths.py`를 거친다 (2026-09-03)

> **앞서 "여기 있는 사본은 아직 읽히지 않는다"고 적은 것을 정정한다.**
> 그 상태가 실제 사고로 이어졌으므로(2026-09-02, 낡은 `/mnt/d` 코드를 import),
> 사본을 두는 것으로 끝내지 않고 **읽는 경로를 만들었다.**

```python
from paths import cache_dir, candidates_dir, require_external

kps_dir = cache_dir(30)          # 저장소 사본. 없으면 외부를 본다
box_dir = candidates_dir(15)
root    = require_external("clips/*.mp4")   # 저장소에 없는 것만 외부에서
```

- **동작점을 기본값으로 두지 않는다.** 호출자가 15인지 30인지 적어야 한다
- 외부 경로는 `SUPERSUB_PHASEA_ROOT`로 바꾼다
- `require_external()`은 없으면 **왜 없는지** 말하고 멈춘다 — 조용히 빈 결과를
  내는 것이 이 계열에서 가장 비싼 실패였다

**확인**: `/mnt/d`를 가려도 캐시 기반 측정이 돈다.

```bash
SUPERSUB_PHASEA_ROOT=/nonexistent \
  uv run python eval/pending13_edge/measure_edge.py --target 30
```

### 아직 `/mnt/d`를 하드코딩하는 것들

`paths.py`로 옮긴 것은 `pending13_edge/measure_edge.py` 하나다. `extract.py`·
`analyze_phaseA.py`·`selector_downstream.py` 등 **14개는 여전히
`ROOT = Path("/mnt/d/supersub-phaseA")`** 다 (미결 14번). 이 사본을 넣었다고
`/mnt/d` 없이 B-6 전체가 돌지는 않는다 — `clips/`(130MB)와 `labeling/`(31MB)도
여전히 그쪽에만 있다.

**다만 GPU 없이 지표를 다시 내는 경로는 이제 저장소만으로 열린다.** 그것이
이 사본의 원래 보존 이유였다.

## 넣지 않은 것

| | 크기 | 이유 |
|---|---|---|
| `clips/*.mp4` | **130MB** | 저장소에 넣지 않는다. Kinetics 원본이고 크기가 맞지 않는다 |
| `labeling/` | 31MB | 렌더 이미지가 대부분이다. `labels.json`·`targets.py`는 이미 저장소에 있다 |
| B-6 selector별 키포인트 | ~5MB | 만들지 않기로 했다 — 재실행이 244초라 절약이 10분뿐이다 |

## 관련

- 재실행 절차와 비결정성: [`eval_b6/RERUN.md`](eval_b6/RERUN.md)
- 경로 해석: [`paths.py`](paths.py)
- 미결 11번(이 의존이 남긴 위험)·13번(동작점이 어긋난 것을 드러낸 조사)·14번(남은 하드코딩): `jekyll/pages/pending.markdown`

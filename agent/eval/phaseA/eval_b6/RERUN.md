# B-6 재실행 절차와 비결정성

2026-09-01 작성. **B-6을 다시 돌리기 전에 이 문서를 먼저 읽을 것.**

임팩트 정의를 바꾸는 변경(E-1·E-2·E-3·E-6)은 `_downstream()` 안의
`F.extract_features` 한 줄만 건드리지만, B-6은 그 결과를 **CSV로만** 남기고
키포인트를 보관하지 않으므로 **전 구간을 다시 돌려야 한다.**

## 재실행 명령과 소요

```bash
cd /home/ho/projects/super-sub.cloud/agent   # uv 프로젝트 루트
uv run python /mnt/d/supersub-phaseA/eval_b6/selector_downstream.py
```

**소요 244초** (2026-08-28 실측, RTX 3050) — Track1 **169초** + Track2 **75초**.
스크립트가 끝나면 `track1_seconds`·`track2_seconds`·`total_seconds`를 stdout에
JSON으로 찍는다. **파일로 남기지 않으므로 그 출력을 따로 보관할 것.**

> 이 값을 한때 "5 selector × 61클립 ≈ 2시간"으로 잘못 추정한 적이 있다. 틀렸다.
> Track 1은 검출을 하지 않고(`candidates/` 캐시를 읽는다), 5개 mode가 고른 박스의
> **합집합만** 포즈한다(`kp_cache[(t, g)]`). 포즈는 박스당 중앙 18.0ms다
> (`eval_b2/pose_quality_timing.csv`).

산출물 두 개를 **덮어쓴다.**

| 파일 | 내용 |
|---|---|
| `selector_downstream_comparison.csv` | Track 1, 195행 × 38열 |
| `selector_downstream_rubric_clips.csv` | Track 2, 110행 × 40열 |

**덮어쓰기 전에 기존 두 파일을 반드시 복사해 둘 것.** 대조(아래)의 기준선이다.

## 필요한 자산

| 자산 | 위치 | 없으면 |
|---|---|---|
| `candidates/*.npz` | `/mnt/d/supersub-phaseA/candidates/` · **저장소 `../candidates_target{15,30}/`** | Track 1 실행 불가 |
| `clips/*.mp4` (130MB) | `/mnt/d/supersub-phaseA/clips/` · **백업 없음** | Track 1 실행 불가 |
| `eval_b2/pose_quality.csv` | 저장소 `../eval_b2/` (동일본 `/mnt/d`) | Track 1 selector 실행 불가 |
| `eval_b2/eval_b2.py`, `labeling/targets.py` | 저장소·`/mnt/d` 동일 (diff 확인) | import 실패 |
| Track 2 영상 22개 | `agent/data/*.mp4` 3 + `agent/data/goldenset/soccerkicks_video/*.avi` 19 | Track 2 축소 |
| 루브릭 | `agent/rubrics/` | Track 2 등급 산출 불가 |
| 모델 가중치 | HF 캐시 (`usyd-community/vitpose-base-simple`, `PekingU/rtdetr_r50vd_coco_o365`) | 재다운로드 약 2.4GB |

경로는 `selector_downstream.py`가 `/mnt/d/supersub-phaseA`로 **여전히
하드코딩**하고 있다(미결 14번). 다만 2026-09-03에 저장소 사본이
`../cache_target{15,30}/`·`../candidates_target{15,30}/`로 바뀌고
[`../paths.py`](../paths.py)를 거쳐 **읽히게 됐다** — 앞서 "백업이며 읽히지
않는다"고 적은 것을 정정한다. 이 스크립트를 그쪽으로 옮기는 것은 아직이다
([`../PRESERVED_ASSETS.md`](../PRESERVED_ASSETS.md) 참고).

## 비결정성 요소

같은 입력으로 다시 돌려도 **결과가 같다는 보장이 없다.** 원인을 위험도 순으로 적는다.

### 높음

**N-1. 모델 가중치가 리비전 없이 이름으로만 고정돼 있다.**
`pose.py`의 `POSE_MODEL`·`PERSON_DETECTOR`가 HF 저장소 **이름**만 담고 있고
`revision=`이 없다. 업스트림이 파일을 갈아 끼우면 조용히 바뀐다. 로컬 HF 캐시가
살아 있는 동안은 드러나지 않다가, 캐시를 지우거나 다른 기계에서 돌리는 순간
어긋난다. **가장 흔하고 가장 늦게 발견되는 원인이다.**

**N-2. `MAX_BATCH=24`의 OOM 폴백이 배치 크기를 바꾼다.**
`selector_downstream.py:106`의 `except torch.cuda.OutOfMemoryError`가 배치를
24 → 12 → 6으로 반씩 줄인다. 배치 크기가 달라지면 커널의 감산 순서가 달라져
부동소수점 마지막 자리가 흔들릴 수 있다. **다른 프로세스가 GPU를 쓰고 있었는지에
따라 결과가 달라질 수 있는 구조다.** 재실행 전에 GPU를 비우고, 폴백이 일어났는지
확인할 방법이 현재 없다(로그를 남기지 않는다).

**N-3. cuDNN 비결정성과 TF32.**
`torch.backends.cudnn.deterministic`이 설정돼 있지 않고(현재 `False`),
`cudnn.allow_tf32`가 `True`다. PyTorch·CUDA·드라이버 버전이 바뀌면 알고리즘
선택이 달라진다. **아래 "현재 환경"과 다른 환경에서 돌리면 일치를 기대하지 말 것.**

### 중간

**N-4. Track 2의 입력 파일 집합이 디렉터리 상태에 딸려 있다.**
`sorted(root.glob("*.mp4")) + sorted(soccerkicks_video.glob("*.avi"))`로 정한다.
`agent/data/`에 mp4를 하나 두면 클립 수가 바뀐다. 두 glob 모두 **비재귀**라
하위 디렉터리(`data/pending7_fps/`, `data/previews/`, `data/tmp/`)는 잡히지 않는다
— 2026-09-01 확인: mp4 3 + avi 19 = **22**, 기존 CSV의 22와 일치.

**N-5. OpenCV 디코딩.**
`read_frames`가 OpenCV로 디코딩한다. 빌드·코덱 버전이 바뀌면 프레임 픽셀이
미세하게 달라질 수 있다.

### 배제됨

**selector 자체는 완전히 결정적이다.** `eval_b2.run()`은 사전 고정 가중치 +
디스크의 `pose_quality.csv` + `np.argmax`(동점은 첫 인덱스)뿐이고 RNG가 없다.
Track 2의 selector도 같은 식이며 차이는 `pose_quality`를 그 실행의 ViTPose
출력에서 즉석 계산한다는 점뿐이다 — 즉 **selector 비결정성은 포즈 비결정성에
종속이고 독립 원인이 아니다.** `_downstream`·`_grade`·`scoring.aggregate`도
전부 결정적이다.

## 재실행 후 대조 절차

기존 CSV 두 개가 **완전한 지문**이다 — 지표 11개 + `delta_*` 11개 + `grade` +
`grade_changed` + 품질 비율 + 실패 사유가 (clip × mode) 305행에 전부 들어 있다.

키는 `(track, clip_id, comparison_selector)`. 305행이 1:1로 대응해야 한다.

| 컬럼군 | 요구 |
|---|---|
| `impact_frame`, `follow_through_duration_frames`, `detected_frames`, `frames`, `multi_candidate_frames`, `selected_target_difference` | **완전 일치** (정수) |
| 각도·비율 지표 9개와 그 `delta_*` | **소수 둘째 자리까지 일치** (CSV가 `round(v, 2)`로 저장한다) |
| `usable_ratio_arm`, `usable_ratio_leg` | 소수 넷째 자리까지 일치 (`round(v, 4)`) |
| `features_ok`, `fail_reason`, `grade`, `grade_changed`, `score`, `rubric`, `rubric_status` | **문자열 완전 일치** |

**행 수와 키 집합이 먼저 같아야 한다.** 다르면 N-4(입력 파일 집합)를 먼저 의심한다.

임팩트 정의를 **의도적으로 바꾼** 재실행이라면 위 기준을 그대로 쓸 수 없다.
그때는 **바뀌지 않아야 하는 컬럼만** 대조한다 — `frames`,
`multi_candidate_frames`, `selected_target_difference`,
`selected_target_difference_ratio`, `detected_frames`, `usable_ratio_*`.
이 여섯은 selector와 포즈에만 의존하고 임팩트 정의와 무관하다.
**여기서 어긋나면 임팩트 변경이 아니라 환경이 변한 것이다.**

## 불일치가 나오면 — 캐시가 아니라 기준선 감사다

불일치는 "이번 재실행을 채택할까"의 문제가 아니다. **B-2\~B-6이 서로 다른
포즈 위에서 산출됐을 수 있다는 뜻이고, 그 결론들이 함께 흔들린다.**

순서대로 확인한다.

1. **행 수·키 집합이 다른가** → N-4. `agent/data/` 디렉터리 내용을 확인한다.
2. **`detected_frames`·`usable_ratio_*`가 다른가** → 포즈나 검출이 달라졌다.
   N-1(모델 리비전)을 가장 먼저 본다. HF 캐시의 커밋 해시를 확인하고,
   기존 CSV가 만들어진 2026-08-28 시점과 같은 가중치인지 대조한다.
3. **`selected_target_difference`가 다른가** → Track 1이면 `candidates/`나
   `pose_quality.csv`가 바뀐 것이다(둘 다 파일이므로 md5로 확인된다).
   Track 2면 포즈가 달라져 `pose_quality`가 달라진 것이다 → 2번으로 돌아간다.
4. **위 셋이 같은데 지표만 마지막 자리에서 다른가** → N-2(배치 폴백) 또는
   N-3(cuDNN·TF32). GPU를 비우고 다시 돌려 재현되는지 본다.
5. **재현되지 않고 실행마다 다른가** → N-2가 유력하다. 다른 프로세스의 VRAM
   점유를 확인한다.

**어느 경우든 판단은 "B-2\~B-6의 어느 결론까지 다시 봐야 하는가"이지 캐시나
스크립트 채택 여부가 아니다.** 특히 B-5의 A/B 검정 결과(p=0.22, 필요 표본 340건)는
selector 선택에 근거하므로 3번에서 어긋나면 함께 무효가 된다.

## 현재 환경 (2026-09-01)

기존 CSV는 2026-08-28에 산출됐다. 아래는 **오늘 기준** 값이므로 그때와 같다는
보장은 없다 — 그 사이 패키지가 갱신됐다면 그것 자체가 N-1·N-3의 후보다.

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3050, 8192 MiB, 드라이버 560.94 |
| python | 3.12.13 |
| torch | 2.8.0+cu126 (CUDA 12.6 빌드, cuDNN 91002) |
| transformers | 5.15.1 |
| opencv | 5.0.0 |
| numpy | 2.5.2 |
| `cudnn.deterministic` | **False** |
| `cudnn.benchmark` | False |
| `cudnn.allow_tf32` | **True** |
| `cuda.matmul.allow_tf32` | False |

## 관련

- 보존한 입력 자산: [`../PRESERVED_ASSETS.md`](../PRESERVED_ASSETS.md)
- B-6 결과 해석: [`selector_downstream_report.md`](selector_downstream_report.md)
- 임팩트 정의 변경이 무엇을 무효화하는지: `agent/eval/pending7_fps/PREREGISTRATION.md`
- 미결 11번 (이 의존이 남긴 위험): `jekyll/pages/pending.markdown`

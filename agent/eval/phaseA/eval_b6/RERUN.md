# B-6 재실행 절차와 비결정성

2026-09-01 작성. **B-6을 다시 돌리기 전에 이 문서를 먼저 읽을 것.**

임팩트 정의를 바꾸는 변경(E-1·E-2·E-3·E-6)은 `_downstream()` 안의
`F.extract_features` 한 줄만 건드리지만, B-6은 그 결과를 **CSV로만** 남기고
키포인트를 보관하지 않으므로 **전 구간을 다시 돌려야 한다.**

## 재실행 명령과 소요

```bash
cd <저장소>/agent                            # uv 프로젝트 루트
uv run python eval/phaseA/eval_b6/selector_downstream.py
```

> 🔴 **위 명령을 2026-09-08에 고쳤다.** 앞서 여기 적혀 있던
> `uv run python /mnt/d/supersub-phaseA/eval_b6/selector_downstream.py` 는
> **더 이상 존재하지 않는 파일을 가리킨다** — `/mnt/d` 의 `.py` 38개는
> 2026-09-02에 전부 지웠다(`/mnt/d/supersub-phaseA/README_CODE_MOVED.md`).
> 그대로 따라 했으면 "그런 파일 없음"으로 죽었을 것이고, **더 나빴던 것은
> 지우기 전에 따라 했을 경우다** — 2026-08-27에 멈춘 사본이 조용히 돌았다.

> 🔴 **소요를 다시 쟀다 (2026.09.15, 미결 43번 ㉳ 3회차)** — 같은 RTX 3050 에서
> **435초**(Track1 318 + Track2 117)와 **428초**(311 + 116)다. 아래 244초는
> **1.8배 낙관적**이다. 그 사이 `DEFAULT_TARGET_FPS` 가 15 → 30 이 됐으니
> (`f2dacdc`, 09-02) 프레임이 두 배인 것이 가장 큰 몫으로 보인다. **시간을
> 잡을 때는 7~8분으로 잡을 것.**

**소요 244초** (2026-08-28 실측, RTX 3050) — Track1 **169초** + Track2 **75초**.
스크립트가 끝나면 `track1_seconds`·`track2_seconds`·`total_seconds`를 stdout에
JSON으로 찍는다. **파일로 남기지 않으므로 그 출력을 따로 보관할 것.**

> 이 값을 한때 "5 selector × 61클립 ≈ 2시간"으로 잘못 추정한 적이 있다. 틀렸다.
> Track 1은 검출을 하지 않고(`candidates/` 캐시를 읽는다), 5개 mode가 고른 박스의
> **합집합만** 포즈한다(`kp_cache[(t, g)]`). 포즈는 박스당 중앙 18.0ms다
> (`eval_b2/pose_quality_timing.csv`).

산출물 **셋**을 덮어쓴다.

| 파일 | 내용 |
|---|---|
| `selector_downstream_comparison.csv` | Track 1, 195행 × 38열 |
| `selector_downstream_rubric_clips.csv` | Track 2, 110행 × 40열 |
| **`run_meta.json`** | 🔴 **이 실행이 무엇으로 무엇을 만들었는지** (2026-09-15 신설) |

**덮어쓰기 전에 기존 파일을 반드시 복사해 둘 것.** 대조(아래)의 기준선이다.

### 🔴 `run_meta.json` — 2026-09-15 에 규칙을 바꿨다

앞서 스크립트에 *「실행 메타는 파일로 남기지 않는다(승인된 산출물 목록에
없음). 보고서에 적는다」*고 적혀 있었다. **그 규칙이 대가를 치렀다** — 산출이
재현되지 않는데 **그때 무엇으로 돌렸는지가 아무 데도 없어서** 원인을 못 갈랐다
(미결 `ho` 47번). 「보고서에 적는다」는 **사람이 적어야 남는다**는 뜻이고,
그날 아무도 안 적었다.

| 담는 것 | 그게 답해 주는 질문 |
|---|---|
| `inputs` — **읽은 영상 전부의 md5·크기**(Track 1 39 · Track 2 22) | 🔴 **「그때와 같은 파일로 돌렸나」** — `agent/data/` 는 `.gitignore` 라 이것 말고는 되짚을 길이 없다 |
| `git` — 커밋·브랜치·**`dirty`** | 🔴 `dirty` 가 참이면 이 산출은 **어느 커밋의 것도 아니다** |
| `env` — python·torch·cuda·cudnn·transformers·opencv·numpy·GPU·TF32 설정 | 「환경이 변했나」(N-3) |
| `models` — 저장소와 **리비전** | 「같은 가중치인가」(N-1) |
| `batching` — `oom_events`·`min_batch` | 🔴 **「폴백이 일어났나」**(N-2) — 예전에는 알 방법이 없었다 |
| `constants` — target fps·`MAX_BATCH`·검출 문턱·selector 목록 | 「같은 동작점인가」(미결 10번) |
| `outputs` — 두 CSV 의 md5·크기 | 「이 메타가 **이 산출의** 것인가」 |

🔴 **CSV 를 다 쓴 뒤에 쓴다** — 메타 수집이 터져도 결과는 남는다. 수집 실패는
조용히 넘기지 않고 해당 칸에 `error` 로 적힌다.
🔴 **인프라 식별자를 안 담는다**(공개 저장소다) — 절대 경로·호스트명 대신
**파일 지문**으로 적는다.

## 필요한 자산

| 자산 | 위치 | 없으면 |
|---|---|---|
| `candidates/*.npz` | `/mnt/d/supersub-phaseA/candidates/` · **저장소 `../candidates_target{15,30}/`** | Track 1 실행 불가 |
| `clips/*.mp4` (130MB) | `/mnt/d/supersub-phaseA/clips/` · **백업 없음** | Track 1 실행 불가 |
| `eval_b2/pose_quality.csv` | 저장소 `../eval_b2/` (동일본 `/mnt/d`) | Track 1 selector 실행 불가 |
| `eval_b2/eval_b2.py`, `labeling/targets.py` | 저장소·`/mnt/d` 동일 (diff 확인) | import 실패 |
| Track 2 영상 22개 | `agent/data/*.mp4` 3 + `agent/data/goldenset/soccerkicks_video/*.avi` 19 | Track 2 축소 |
| 루브릭 | `agent/rubrics/` | Track 2 등급 산출 불가 |
| 모델 가중치 | HF 캐시 (`usyd-community/vitpose-base-simple` @ `a93ac0c6`, `PekingU/rtdetr_r50vd_coco_o365` @ `457857ce`) | 재다운로드 약 2.4GB. **해시는 `pose.py` 가 정본**이고 2026.09.11에 고정했다 |

#### ✅ 경로를 `paths.py`로 옮겼다 (2026-09-08, 미결 11·14번)

앞서 "이 스크립트를 그쪽으로 옮기는 것은 아직이다"라고 적은 것을 **정정한다.**
옮겼다.

| 무엇 | 어디서 읽나 |
|---|---|
| 후보 npz | **저장소 `../candidates_target{15,30}/`** (`targets.load_candidates`) |
| `clips/*.mp4` (130MB) | 외부 — `paths.external_root()`, 기본 `/mnt/d/supersub-phaseA` |
| 절대경로 `AGENT` | **뺐다.** `__file__` 에서 유도한다 — 다른 기계·EC2에서도 돈다 |

🔴 **이 변경으로 결과가 달라지지 않는다.** 2026-09-08에 `/mnt/d/candidates`
전수를 저장소 사본과 대조했더니 **target 30 과 39/39 바이트 동일**이었다
(target 15 와는 1/39 — 그 1개는 `8gmHKqDxXdg`, 원본 10fps라 두 동작점이 원소까지
같은 클립이다). 즉 지금까지 읽고 있던 것이 곧 `candidates_target30/` 이다.

동작점은 이제 **이름으로 보인다.** `/mnt/d/candidates` 는 이름에 동작점이 없어
마지막으로 돌린 쪽이 덮어썼고, **무엇을 읽고 있는지 알 수 없었다**(미결 10·14번).
`SUPERSUB_PHASEA_TARGET` 으로 바꾼다(기본값은 `pose.DEFAULT_TARGET_FPS`).

## 🔴 산출물의 출처 — 「2026-08-28 판」이 아니다 (2026.09.15 정정)

이 문서가 여러 곳에서 *"기존 CSV 는 2026-08-28 에 산출됐다"* 고 적어 두었는데
**틀렸다.** git 이력이 답이다:

| 커밋 | 날짜 | 왜 다시 돌았나 |
|---|---|---|
| `f8aba85` | 2026-08-28 | 최초 산출 |
| `4626870` | 2026-09-02 | target 30 전환 재실행 |
| `426de4d` | 2026-09-08 | 미결 21번(못 잰 골반 회전을 0.0 으로 지어내지 않는다) |
| (아래 참조) | **2026-09-15** | **미결 43번 ㉳ 3회차** — 마무리 길이를 구간 안에서 센다. 커밋은 `git log -- selector_downstream_comparison.csv` 로 찾는다 |

🔴 **정정 (같은 날, 47번 1회차) — 위 표의 「09-08 판」은 Track 1 뿐이다.**
**Track 2 CSV 는 `426de4d` 에서 한 바이트도 안 바뀌었고 실제로는 `4626870`
(2026-09-02) 산출이다**(md5 `7e41a201…` 이 두 커밋에서 같다). 그리고
**그 차이는 코드가 아니다** — 09-02 · 09-08 · 오늘 세 시점 코드의 Track 2
재실행이 **서로 불일치 0** 이다. 남은 후보는 **버전 관리 밖**(입력 클립 ·
그 실행의 정체)이라
[`../../pending47_baseline_audit/input_fingerprints.csv`](../../pending47_baseline_audit/input_fingerprints.csv)
에 **입력 61개의 md5** 를 남겼다 — **다음 감사는 이걸 먼저 대 볼 것.**

🔴 **아래는 발견 당시 기록이다** (현상은 그대로이고 원인 진단만 위로 바뀌었다) —
겹치는 290행 중
**85행(전부 Track 2)** 이 다르고, 임팩트 정의와 무관해야 할
`detected_frames`·`usable_ratio_*` 까지 어긋난다. **원인은 환경도 가중치도
비결정성도 아니다**(아래 「배제됨」에 실측을 붙였다). 정본과 남은 조사는
**미결 `ho` 47번**, 측정은
[`../../pending43_leak_fix/RESULTS.md`](../../pending43_leak_fix/RESULTS.md) 5절.

## 비결정성 요소

같은 입력으로 다시 돌려도 **결과가 같다는 보장이 없다.** 원인을 위험도 순으로 적는다.

> ✅ **실행 간 재현성에 처음으로 실측이 붙었다 (2026.09.15).** 같은 코드로 두
> 번 돌린 290행이 **의도적으로 바꾼 두 열 말고 전부 비트 동일**이었다
> (`pending43_leak_fix/compare_e2.out`). 🔴 **N-2·N-3 이 사라졌다는 뜻은
> 아니다** — 이 기계·이 드라이버에서 **두 번** 그랬다는 뜻이다. 다만
> **불일치를 봤을 때 「GPU 탓」을 먼저 집는 것은 이제 근거가 약하다.**

### 높음

**N-1. ✅ 닫았다 (2026.09.11) — 가중치를 커밋으로 고정했다.**

> 아래 진단은 그대로 옳았다. **고친 것은 원인이고, 기록은 남긴다.**
>
> `pose.py`에 `PERSON_DETECTOR_REVISION`·`POSE_MODEL_REVISION`을 두고
> `from_pretrained(..., revision=...)`로 넘긴다. **이 재실행 경로도 같은 상수를
> 쓴다** — `candidates.py`·`eval_b6/selector_downstream.py`·
> `eval_b2/pose_quality.py`·`eval_b2/other_sports.py`·`other_sports.py`·
> `soccer_check.py`·`eval_b2/render_soccer_diffs.py`.
>
> 🔴 **고정한 해시는 지금까지의 모든 결과를 낸 스냅숏 그대로다**(2026.09.11 HF
> 캐시의 `refs/main`). 그래서 이 조치는 **과거 CSV를 무효화하지 않는다** — 값을
> 바꾼 것이 아니라 **다음에 바뀌는 것을 막았다.**
>
> 표류는 `tests/test_model_pins.py::test_the_pin_still_matches_this_machines_cache`
> 가 알려 준다. 🔴 **빨개지면 고정을 캐시에 맞추지 말 것** — 그것이 과거 결과와
> 다른 가중치로 조용히 갈아타는 것이다. 올리려면 재실행 회차와 함께 올린다.
>
> **원래 진단**: `pose.py`의 `POSE_MODEL`·`PERSON_DETECTOR`가 HF 저장소 **이름**만
> 담고 있고 `revision=`이 없었다. 업스트림이 파일을 갈아 끼우면 조용히 바뀌고,
> 로컬 HF 캐시가 살아 있는 동안은 드러나지 않다가 캐시를 지우거나 다른 기계에서
> 돌리는 순간 어긋난다. **가장 흔하고 가장 늦게 발견되는 원인이었다.**

**N-2. `MAX_BATCH=24`의 OOM 폴백이 배치 크기를 바꾼다.**
`selector_downstream.py:106`의 `except torch.cuda.OutOfMemoryError`가 배치를
24 → 12 → 6으로 반씩 줄인다. 배치 크기가 달라지면 커널의 감산 순서가 달라져
부동소수점 마지막 자리가 흔들릴 수 있다. **다른 프로세스가 GPU를 쓰고 있었는지에
따라 결과가 달라질 수 있는 구조다.** 재실행 전에 GPU를 비운다.

> ✅ **정정 (2026-09-15) — 「폴백이 일어났는지 확인할 방법이 현재 없다」는 이제
> 아니다.** `run_meta.json` 의 `batching` 이 `oom_events` 와 `min_batch` 를
> 싣는다. **`min_batch` 가 24 보다 작으면 그 실행은 폴백이 일어난 실행**이고,
> 그 산출을 다른 실행과 마지막 자리까지 대 보는 것은 의미가 없다.
>
> 🔴 **그리고 Track 2 에서는 이 위험이 구조적으로 없다** (미결 47번 1회차):
> `_pose_batch` 에 들어가는 박스가 **한 프레임당 1~3개**라 `MAX_BATCH`=24 를
> 넘을 일이 없어 **쪼개지지 않는다.** 남는 것은 Track 1 쪽이다.

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

### 0. 🔴 **`run_meta.json` 부터 본다** (2026-09-15 신설)

CSV 를 한 줄도 열기 전에, 기존 메타와 이번 메타를 대 본다. **다르면 그
차이가 곧 원인 후보**이고, 아래 1~5단계를 건너뛸 수 있다.

```bash
# 예: 입력이 그때와 같은가
python - <<'PY'
import json
a=json.load(open("run_meta.json")); b=json.load(open("<옛 메타>"))
for k in ("git","env","models","constants","batching"):
    if a[k]!=b[k]: print("다름:", k)
fa={x["name"]:x["md5"] for x in a["inputs"]["track2"]}
fb={x["name"]:x["md5"] for x in b["inputs"]["track2"]}
print("입력이 다른 클립:", [n for n in fa if fa[n]!=fb.get(n)])
PY
```

🔴 **옛 산출에는 이 파일이 없다** (규칙이 2026-09-15 에 바뀌었다). 그때 것과
대 보려면 [`../../pending47_baseline_audit/input_fingerprints.csv`](../../pending47_baseline_audit/input_fingerprints.csv)
가 **2026-09-15 시점의 입력 지문**을 들고 있다 — 그 이전은 **기록이 없다.**

### 1. 그다음에 CSV

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
   ~~N-1(모델 리비전)을 가장 먼저 본다.~~ → **N-1은 닫혔다 (2026.09.11)** —
   가중치가 커밋으로 고정돼 있고 `tests/test_model_pins.py` 가 캐시와 대조한다.
   그 검사가 초록이면 **가중치는 용의자가 아니다.** 빨갛다면 그 메시지가
   무엇이 어긋났는지 말해 준다.
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

# Phase A/B — 분석 대상(person) selector 검증 기록

> **이 디렉터리는 기록 보존용 사본이다.** 여기 있는 스크립트의 경로는
> `/mnt/d/supersub-phaseA/`로 하드코딩돼 있고 **그대로 두었다.** 실행 위치를
> 저장소 기준으로 바꾸지 않았다 — 목적이 "그때 무엇을 어떻게 돌렸는가"의
> 보존이기 때문이다. 재현 방법은 아래 [재현](#재현) 참고.

## 목적

영상에 여러 사람이 잡힐 때 **어느 사람을 분석 대상으로 고를 것인가**를 정하는
selector를 고르기 위한 오프라인 평가다. production 파이프라인(`agent/src/`)은
이 작업에서 한 줄도 바뀌지 않았다.

비교 대상 5종 (가중치는 Phase B-0 설계안의 임시값 — **production 값이 아니다**):

| selector | 구성 |
|---|---|
| `baseline` | 면적 최대 |
| `A-geometry` | centrality 0.69 + size 0.31 |
| `B-geometry` | centrality 0.47 + size 0.20 + continuity 0.33 |
| `A-pose` | centrality 0.45 + pose_quality 0.35 + size 0.20 |
| `B-pose` | centrality 0.35 + pose_quality 0.25 + size 0.15 + continuity 0.25 |

가중치는 **사전에 고정**했고 sweep·재튜닝을 하지 않았다(39클립 GT에 대한 과적합
방지). B-2 이후 모든 단계는 `eval_b2/eval_config.json`의 값을 그대로 쓰며,
`eval_b3.py`·`design_b4.py`는 시작 시 그 값과 일치하는지 assert로 검증한다.

## 현재 결론 (2026-08-28)

**production selector를 확정하지 않았다.**

1. **계층 순서는 안정적이다.** pose 계열 > B-geometry > A-geometry >> baseline.
   라벨 출처를 바꿔도 이 순서는 유지된다.
2. **A-pose와 B-pose의 우열은 미확정이다.** B-2 전체(97건)에서 B-pose가 2건
   앞섰으나, B-3 독립 판독 표본에서는 20:20 완전 동점이었다.
3. **A-pose ≠ B-pose 프레임은 5,404 중 596건(11.0%)이고, 그중 GT가 있는 것은
   7건뿐이다.** 두 selector는 합의 프레임 91건에서 둘 다 81/91로 동일하므로,
   순위는 전적으로 이 7건이 결정한다(`eval_b4/ab_disagreement_frames.csv`).
4. **B-pose가 A-pose와 다른 사람을 독립적으로 새로 획득한 사례는 그 7건 중
   0건이다.** 7/7 모두 B-pose가 정체성을 획득한 시점에 A-pose도 같은 사람을
   보고 있었다(`eval_b4/ab_origin_trace.csv`). 즉 모든 disagreement는
   **"A-pose 이탈 vs B-pose 유지"** 형태다.
5. **따라서 B-pose의 switching 감소를 identity correctness 개선과 동일시할 수
   없다.** switching(A-pose mean 6.8% → B-pose 1.8%)은 확실히 줄지만, 그것은
   이미 획득한 대상을 유지한 결과이지 옳은 대상을 더 잘 찾은 결과가 아니다.
   현재 근거상 B-pose의 장점은 identity acquisition 개선이 아니라
   **continuity / retention(시간적 지속성)** 으로 해석해야 한다.
6. **`N5zWQkoLM3M@0.50`은 그 지속성이 역효과를 낸 regression 사례다** — B-pose가
   f74에서 잘못 획득한 identity를 continuity로 유지해 오답(A-pose 정답 2 /
   B-pose 오답 1, continuity 0.828). 계속 추적한다.
   `LhD_fnHt_xg@0.50`·`@0.80`은 A-pose·B-pose가 **함께** 틀리므로 A/B 우열
   판정에는 사용하지 않고, pose 계열 공통 failure mode로 따로 유지한다
   (`eval_b4/regression_watchlist.csv`).
7. **B-pose의 +2 우위는 단 2프레임에 100% 의존한다** (`3USSmzO001k@0.80`,
   `X6dC9pu5H3k@0.80`). 나머지 5건은 정확히 상쇄된다(A 2 : B 2). 두 건이 모두
   뒤집히면 A-pose 우세로 역전된다(`eval_b4/tier0_sensitivity.md`).
8. **그런데 그 2건은 blind 판독이 아니다.** 판독 직전 대화에서 기존 GT와 양쪽
   selector 선택이 이미 노출된 상태였다 — **blind human verification으로 취급하지
   않는다.** 실제로 blind였던 5건만 보면 **A 2 : B 2**이므로, **독립 검증
   기준으로는 B-pose 우위가 확정되지 않는다.**

### B-5에서 추가된 것 — 검수를 더 해도 갈리지 않는다

오염된 2건 때문에 **격리 디렉터리에서 60건을 처음부터 다시 판독**했다
(Tier 0 7건 + Tier 1 53건, `eval_b4/clean_review_report.md`).

9. **오염을 걷어내면 Tier 0는 A-pose 쪽으로 뒤집힌다.** clean 판독 기준
   **A 3 : B 2**(margin −1). 라벨 출처별로 `labels.json` +2 → 오염 포함 AI +1 →
   clean −1로 이동한다(`eval_b4/clean_review_sensitivity.csv`).
10. **표본을 60건으로 넓히면 방향은 다시 B지만 유의하지 않다.** 판정 가능 43건에서
    **B 26 : A 17**(60.5%), 정확 이항 p = 0.22. 클립 클러스터 부트스트랩 95% CI
    **[0.395, 0.800]** 로 0.5를 포함하고, 클립 단위 부호검정도 B 11 : A 7,
    p = 0.48이다(`eval_b4/clean_review_ab_test.json`).
11. **남은 우세는 표본 선정으로 설명된다.** Tier 1은 `info_score` 상위에서 뽑혔고
    그 점수에는 `b_locked`(2.0)와 `a_pose_switch`(1.0)라는 **A/B 비대칭 항**이
    들어 있다. B의 우세는 `a_pose_switch=1` 층에 몰려 있고(B 18 : A 10) 그 층을
    벗어나면 거의 사라진다(B 8 : A 7). 이 표본의 승률을 전체 불일치 프레임의
    승률로 읽으면 안 된다(`eval_b4/clean_review_ab_covariates.csv`).
12. **검수를 더 해도 이 데이터셋에서는 갈리지 않는다.** 관측된 60.5%가 참값이라
    가정해도 α=0.05·power=0.80이면 판정 가능 **340건**(design effect 1.92 보정)이
    필요한데, run당 1프레임 규약에서 이 데이터셋의 상한은 검수 **69장 / 판정 약
    49건**이다. 이미 60장을 봤고 남은 여유는 9장이다. **7배 부족하다.**
13. **승패는 클립 안에서 몰린다.** 2건 이상 판정된 11클립 중 6클립이 만장일치다.
    특히 regression 케이스 `N5zWQkoLM3M`은 **A 4 : B 0**으로 오염 없는 독립
    판독이 6번의 진단을 그대로 재현했고, 반대로 `3USSmzO001k`은 **B 5 : A 0**이다.
    즉 데이터가 말하는 것은 "어느 selector가 낫다"가 아니라 **continuity는 처음
    잡은 대상이 맞으면 이기고 틀리면 진다**는 것이다. 질문을 "어느 selector인가"
    에서 **"continuity를 언제 신뢰할 것인가"** 로 바꿔야 한다.

## AI-reviewed GT ≠ human-verified GT

**사람 검수자를 확보하지 못해(human review unavailable) B-3·B-4·B-5의 라벨은
Claude가 단독 판독한 것이다.**

| | `labeling/labels.json` | `eval_b3/labels_ai_reviewed.json` | `eval_b4/*_ai_clean_blind_review.csv` |
|---|---|---|---|
| 판독 주체 | Claude 1차 | Claude 독립 재판독 | Claude 격리 재판독 (B-5) |
| 사람 검증 | **없음** | **없음** | **없음** |
| provenance | `labeler: "Claude (에이전트) 1차 — 사람 검수 필요"` | `human_verified: false` | `human_verified: false` |

`labels_ai_reviewed.json`의 provenance는 **변경 금지**다:

```json
"label_source": "claude_visual_review",
"human_verified": false,
"selector_blinded": true,
"source_labels_modified": false
```

- `selector_blinded: true` — 판독 시 selector 선택 결과·기존 GT를 보지 않았다.
  렌더 이미지는 모든 후보를 같은 색·같은 굵기로 그리고 index와 검출점수만 표시한다.
- **예외 2건**: B-4의 `3USSmzO001k@0.80`, `X6dC9pu5H3k@0.80`은 판독 직전 대화에서
  이미 기존 GT와 양쪽 selector 선택이 노출된 상태에서 판독했다. blind가 아니며
  `eval_b4/tier0_ai_review.csv`의 `blind_status` 열에
  `contaminated_prior_exposure`로 기록돼 있다. **하필 판별에 결정적인 두 건이다.**
  → **B-5에서 이 2건을 포함해 60건 전부를 격리 재판독했다.**

B-5 판독(`eval_b4/ai_clean_blind_review_provenance.json`)의 조건과 그 한계도
provenance에 그대로 적혀 있다. **변경 금지**다.

```json
"label_source": "ai_independent_blind_review",
"human_verified": false,
"selector_blinded": true,
"gt_blinded": true,
"prior_ai_review_blinded": true,
"fresh_context": false,
"inaccessible_source_root": false,
"source_labels_modified": false
```

- 판독 입력은 격리 디렉터리(`/mnt/d/blind_review_run1/`)의 안내문·양식·이미지 60장
  뿐이었다. 그 사본이 `eval_b4/review_packet/`이다.
- `fresh_context: false` — 시스템 프롬프트에 프로젝트 CLAUDE.md와 메모리 **제목**
  목록이 이미 들어 있었다. 프레임별 정답에 해당하는 정보는 그 안에 없다.
- `inaccessible_source_root: false` — 원본 디렉터리가 기술적으로는 접근 가능한
  상태였다. 실제로 열지 않았지만 물리적으로 차단되지는 않았다.

그래서 B-5 결과는 **"B-pose 우위가 확증되지 않는다"는 부정적 결론의 근거로는
쓰되, production selector를 확정하는 근거로는 쓰지 않는다.**

이 라벨들은 **production selector 확정의 근거로 단독 사용할 수 없다.**

## 단계 요약

### Phase A — 데이터 확보
클립 수집·프레임 추출·후보 검출(RT-DETR person)·포즈(ViTPose) 캐시 생성.

- 입력: `ann/hb_val.csv`(Kinetics "hitting baseball" 선별), `fetch.sh`, `extract.py`
- 출력: `clips/`, `frames/`, `candidates/*.npz`, `cache/*.npz`, `phaseA_*.csv|json`
- 규모: 39클립

### Phase B-1 — geometry selector 1차 비교
- 입력: `labeling/labels.json`(117 대상 중 GT 97), `candidates/`
- 출력: `eval_b1/selector_eval_{frames,clips,transitions}.csv`, `eval_config.json`
- 대상: baseline / A-geometry / B-geometry

### Phase B-2 — pose_quality 도입, 5종 비교
- 입력: B-1 산출물 + `eval_b2/pose_quality.csv`(ViTPose 17키포인트 평균 신뢰도)
- 출력: `eval_b2/report_b2.md`, `selector_eval_*.csv`, `centrality_analysis.csv`,
  `other_sports_{summary,diffs}.csv`(축구·농구 클립 영향), `review_cases.csv`(38건 검수 목록)
- 결과: baseline 70.1% / A-geo 84.5% / B-geo 85.6% / A-pose 85.6% / **B-pose 87.6%**

### Phase B-3 — AI 독립 재판독 + 동일 조건 재평가
사람 검수 불가로 Claude가 blind 판독(38건: 야구 33 + 축구 5).

- 입력: `eval_b2/review_cases/*.jpg`(사본에 미포함), `review_input.csv`(blind form)
- 출력: `labels_ai_reviewed.json`, `ai_review_audit.csv`, `report_b3.md`,
  `selector_eval_*_ai_reviewed.csv`, `label_change_analysis.csv`,
  `soccer_review_analysis.csv`
- 판독: 후보 선택 33 / none 2 / uncertain 3, confidence high 27·medium 8·low 3
- 결과: A-pose 20/28 = **B-pose 20/28** (동점). selector 선택은 B-2와 150/150 행
  완전 일치 — **바뀐 것은 GT뿐**이다.
- 축구 5프레임: 새 selector 4종 모두 baseline 대비 5/5 개선

### Phase B-4 — A/B 판별 설계 + 민감도 분석
- 입력: B-2 selector 재현(전 5,404프레임), `labels.json`, `labels_ai_reviewed.json`
- 출력: `ab_disagreement_frames.csv`(불일치 596건 전수), `ab_origin_trace.csv`,
  `b4_review_input.csv`(Tier 1 blind form 53건), `b4_selection_rationale.csv`,
  `regression_watchlist.csv`, `tier0_*`(Tier 0 7건 판독·민감도),
  `tier0_sensitivity.md`
- 핵심: 5,404프레임 중 A-pose≠B-pose 596건(11.0%), 연속 불일치 run 104개
  (그중 검수 대상으로 뽑을 수 있는 run 62개), GT 있는 것 7건.
  두 selector는 합의 프레임 91건에서 **둘 다 81/91로 동일**하므로 순위는 이 7건이
  전부 결정한다.
  > 이 줄에 처음 적혀 있던 "실질 run 69개"는 B-5에서 다시 세어 보니 틀린 값이었다.
  > `ab_disagreement_frames.csv`를 클립별 연속 프레임으로 묶으면 104개이고,
  > `select_b4.py`의 선정 풀(`different_person=1`, `min_box_frac≥0.015`,
  > GT 없는 프레임) 기준으로는 62개다. 상한 계산(위 12번)은 62개를 쓴다.

### Phase B-5 — 오염 제거 격리 재판독 + A/B 검정
B-4의 결정적 2건이 blind가 아니었으므로, 격리 디렉터리에서 60건을 처음부터 다시
판독하고(Tier 0 7 + Tier 1 53) 그 결과로 A/B를 실제로 검정했다.

- 입력: `eval_b4/review_packet/`(안내문 + 양식 + 이미지 60장), `ab_disagreement_frames.csv`
- 출력: `clean_review_report.md`, `clean_review_ab_*.{csv,json}`,
  `clean_review_{comparison,gt_comparison,sensitivity,t0_grid,tier1_summary}.csv`,
  `tier0_ai_clean_blind_review.csv`, `tier1_ai_clean_blind_review.csv`,
  `ai_clean_blind_review_provenance.json`
- 판독: 후보 선택 46 / none 3 / uncertain 11, confidence high 32·medium 17·low 11
- 결과: 판정 43건에서 **B 26 : A 17**(p = 0.22), 클러스터 CI [0.395, 0.800],
  Tier 0만 보면 **A 3 : B 2**. **필요 표본 340건 vs 데이터셋 상한 49건 —
  이 데이터셋에서는 결론이 나지 않는다.**

## 다음 단계 (미실행)

1. **A/B를 프레임 정확도로 가르는 시도는 접는다.** 위 12번 — 같은 39클립 안에서는
   검수를 아무리 더 해도 α=0.05로 갈리지 않는다는 것이 B-5의 결론이다.
   (B-4에서 적었던 "67건 사람 검수" 계획은 필요 표본을 340건으로 다시 계산하면서
   폐기했다. 52건이라는 옛 추정은 클러스터를 무시하고 효과크기를 65%로 잡은 값이다.)
2. **라벨이 필요 없는 기준으로 옮긴다.** 우리 지표는 프레임 시계열 위에서
   계산되므로 클립 중간에 대상이 바뀌면 관절각 궤적 자체가 오염된다. switching
   빈도(A-pose 6.8% → B-pose 1.8%)와 **잘못된 대상에 고착된 구간의 길이**는 사람
   라벨 없이 측정할 수 있고, 위 13번의 트레이드오프를 그대로 정량화한다.
3. **클립을 늘린다면** 26클립·104run이 병목이다. 같은 클립에서 프레임을 더 뽑는
   것은 design effect만 키운다.
4. **사람 검수는 여전히 확보되지 않았다.** `labels.json`과
   `labels_ai_reviewed.json`은 손대지 않았고 B-5 판독도 GT로 승격하지 않았다.

## 이 사본에 넣지 않은 것

| 대상 | 용량 | 이유 |
|---|---:|---|
| `clips/` | 130 MB | 원본 영상. git에 넣을 성질이 아니며 `fetch.sh`로 재취득 가능 |
| `frames/` | 145 MB | `extract.py` 재실행으로 재생성 |
| `labeling/renders/` | 30 MB | 라벨링용 렌더 시트. `render_targets.py`로 재생성 |
| `sheets/` | 8.6 MB | 클립별 요약 시트 이미지. `sheets.py`로 재생성 |
| `cache/`, `candidates/` | 2.1 MB | 포즈·후보 npz. 모델 재실행으로 재생성 |
| `cand_*.jpg` | 0.5 MB | 후보 시각화 4장 |
| `ann/val.csv` | 792 KB | Kinetics 전체 val 인덱스(3rd-party). `hb_val.csv`만 보존 |
| `eval_b4/review_cases/` | 6.9 MB | Tier 1 렌더 53장. **같은 이미지가 `review_packet/images/`에 `T1_*.jpg`로 들어 있어 중복이다** |

### 검수 evidence 이미지는 포함했다

`eval_b2/review_cases/`(38장, 5.0 MB), `eval_b4/tier0_cases/`(7장, 0.8 MB),
`eval_b4/review_packet/`(안내문·양식 + 이미지 60장, 7.7 MB)는 다른 이미지와 달리
**git에 포함한다.** 스크립트로 재생성은 가능하지만
(`make_review_set.py` / `render_tier0.py` / `render_b4.py`), 원본 영상 `clips/`가
있어야 하고 무엇보다 **AI 판독이 실제로 보고 판단한 대상 그 자체**다. 판독 근거를
사후에 검증하려면 이 이미지가 있어야 한다. 중간 산출물이 아니라 **evidence**로
취급한다.

`review_packet/`은 특히 **B-5 판독에 주어진 입력 전부**다 — 판독자는 이 폴더
바깥을 보지 않았다고 provenance에 기록돼 있으므로, 그 주장을 검증하려면 폴더
내용 자체가 남아 있어야 한다.

렌더 규약(모든 후보 같은 색·같은 굵기, index와 검출점수만 표시, selector 선택·GT
미표시)이 이미지 자체에 남아 있으므로, blind 조건이 지켜졌는지도 이 파일들로
확인할 수 있다.

## 재현

원본 작업 디렉터리는 **`/mnt/d/supersub-phaseA/`** (WSL에서 접근하는 Windows D:
드라이브, git 저장소 아님)이고, 이 사본의 스크립트는 그 경로를 하드코딩하고 있다.
실행하려면 원본 디렉터리에서 그대로 돌린다.

```bash
cd /home/ho/projects/super-sub.cloud/agent   # uv 프로젝트 루트

# B-2 (pose_quality 필요 — GPU 권장, RTX 3050 8GB에서 약 6분)
uv run python /mnt/d/supersub-phaseA/eval_b2/pose_quality.py
uv run python /mnt/d/supersub-phaseA/eval_b2/eval_b2.py
uv run python /mnt/d/supersub-phaseA/eval_b2/report_b2.py

# B-3 (AI-reviewed 라벨 기준 재평가 — GPU 불필요)
uv run python /mnt/d/supersub-phaseA/eval_b3/ingest_review.py --strict
uv run python /mnt/d/supersub-phaseA/eval_b3/eval_b3.py
uv run python /mnt/d/supersub-phaseA/eval_b3/report_b3.py

# B-4 (불일치 전수 + 검수 대상 선정 + 민감도)
uv run python /mnt/d/supersub-phaseA/eval_b4/design_b4.py
uv run python /mnt/d/supersub-phaseA/eval_b4/select_b4.py
python3 /mnt/d/supersub-phaseA/eval_b4/sensitivity_b4.py

# B-5 (clean 판독 결과 분석 — 표준 라이브러리만 쓰므로 python3로 충분)
python3 /mnt/d/supersub-phaseA/eval_b4/clean_review_analysis.py
python3 /mnt/d/supersub-phaseA/eval_b4/clean_review_ab_test.py
```

B-5의 두 스크립트는 `ab_disagreement_frames.csv`와 판독 CSV만 읽으므로 모델·영상
없이 그대로 재현된다. 부트스트랩은 `SEED = 20260828`으로 고정돼 있다.

필요한 것:
- `candidates/*.npz`, `cache/*.npz` — 없으면 `candidates.py`, `extract.py`부터.
  **2026-09-01에 이 저장소의 `candidates/`·`cache/`로 백업했다**(합 1.78MB,
  md5 대조 완료). 다만 스크립트가 `/mnt/d` 경로를 하드코딩하므로 그 사본은
  아직 읽히지 않는다 — [`PRESERVED_ASSETS.md`](PRESERVED_ASSETS.md) 참고
- `clips/*.mp4` — 이미지 렌더 시에만 필요
- `labeling/targets.py` — 모든 평가 스크립트가 `sys.path`에 추가해 import한다
- `agent/src/supersub_agent/pose.py` — 검출·포즈 모델 상수 (읽기 전용으로 참조)

selector 구현은 `eval_b2/eval_b2.py` 한 곳에만 있고 `eval_b3.py`·`design_b4.py`가
import한다. **가중치나 선택 로직을 수정하면 B-2~B-5 결과 전체가 무효가 된다.**

## 주요 파일

| 파일 | 내용 |
|---|---|
| `eval_b4/clean_review_report.md` | B-5 전체 결과 — **먼저 읽을 것** |
| `eval_b4/clean_review_ab_test.json` | 검정·부트스트랩·소요표본·데이터셋 상한 요약 |
| `eval_b4/clean_review_ab_frames.csv` | clean 판독 60건 전수 (판독값·A/B 선택·승자·공변량) |
| `eval_b4/clean_review_ab_covariates.csv` | 표본 vs 모집단 공변량 — 선정 편향의 근거 |
| `eval_b4/ai_clean_blind_review_provenance.json` | B-5 판독 조건과 그 한계 (**수정 금지**) |
| `eval_b4/review_packet/` | B-5 판독자가 본 입력 전부 (안내문·양식·이미지 60장) |
| `eval_b2/report_b2.md` | B-2 5종 비교 전체 결과 |
| `eval_b3/report_b3.md` | AI-reviewed GT 재평가, B-2 대비 3층 비교 |
| `eval_b4/tier0_sensitivity.md` | B-pose +2 우위의 민감도 (B-4 시점 — B-5가 갱신함) |
| `eval_b4/ab_origin_trace.csv` | B-pose가 정체성을 획득한 시점 추적 (7/7 결과) |
| `eval_b4/ab_disagreement_frames.csv` | A-pose≠B-pose 596프레임 전수 |
| `eval_b4/regression_watchlist.csv` | failure mode 3건 추적 |
| `eval_b3/labels_ai_reviewed.json` | AI 판독 라벨 + provenance (**수정 금지**) |
| `labeling/labels.json` | 1차 라벨 (**수정 금지**) |
| `PRESERVED_ASSETS.md` | `candidates/`·`cache/` 백업의 내용·생성 경위·한계 |
| `eval_b6/RERUN.md` | **B-6을 다시 돌리기 전에 읽을 것** — 소요·비결정성·대조 절차 |

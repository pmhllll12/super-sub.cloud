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

## AI-reviewed GT ≠ human-verified GT

**사람 검수자를 확보하지 못해(human review unavailable) B-3·B-4의 라벨은
Claude가 단독 판독한 것이다.**

| | `labeling/labels.json` | `eval_b3/labels_ai_reviewed.json` |
|---|---|---|
| 판독 주체 | Claude 1차 | Claude 독립 재판독 |
| 사람 검증 | **없음** | **없음** |
| provenance | `labeler: "Claude (에이전트) 1차 — 사람 검수 필요"` | `human_verified: false` |

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
- 핵심: 5,404프레임 중 A-pose≠B-pose 596건(11.0%), 실질 run 69개, GT 있는 것 7건.
  두 selector는 합의 프레임 91건에서 **둘 다 81/91로 동일**하므로 순위는 이 7건이
  전부 결정한다.

## 다음 단계 (미실행)

1. **최소**: `3USSmzO001k@0.80`, `X6dC9pu5H3k@0.80` 2건을 **사람이** 판독.
   이 둘만으로 margin이 +2 / 0 / −2로 갈린다.
2. **권장**: Tier 0 7건 + Tier 1 약 60건 = 67건 사람 검수.
   65% 수준의 우세를 α=0.05로 검출하려면 판정 가능 52건이 필요하다.
3. Tier 1 이미지는 아직 렌더하지 않았다 — N 확정 후
   `select_b4.py` → `render_b4.py` 순서로 실행한다.

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

### 검수 evidence 이미지는 포함했다

`eval_b2/review_cases/`(38장, 5.0 MB)와 `eval_b4/tier0_cases/`(7장, 0.8 MB)는
다른 이미지와 달리 **git에 포함한다.** 스크립트로 재생성은 가능하지만
(`make_review_set.py` / `render_tier0.py`), 원본 영상 `clips/`가 있어야 하고
무엇보다 **AI 판독이 실제로 보고 판단한 대상 그 자체**다. 판독 근거를 사후에
검증하려면 이 이미지가 있어야 한다. 중간 산출물이 아니라 **evidence**로 취급한다.

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
```

필요한 것:
- `candidates/*.npz`, `cache/*.npz` — 없으면 `candidates.py`, `extract.py`부터
- `clips/*.mp4` — 이미지 렌더 시에만 필요
- `labeling/targets.py` — 모든 평가 스크립트가 `sys.path`에 추가해 import한다
- `agent/src/supersub_agent/pose.py` — 검출·포즈 모델 상수 (읽기 전용으로 참조)

selector 구현은 `eval_b2/eval_b2.py` 한 곳에만 있고 `eval_b3.py`·`design_b4.py`가
import한다. **가중치나 선택 로직을 수정하면 B-2~B-4 결과 전체가 무효가 된다.**

## 주요 파일

| 파일 | 내용 |
|---|---|
| `eval_b2/report_b2.md` | B-2 5종 비교 전체 결과 |
| `eval_b3/report_b3.md` | AI-reviewed GT 재평가, B-2 대비 3층 비교 |
| `eval_b4/tier0_sensitivity.md` | B-pose +2 우위의 민감도 — **가장 중요** |
| `eval_b4/ab_origin_trace.csv` | B-pose가 정체성을 획득한 시점 추적 (7/7 결과) |
| `eval_b4/ab_disagreement_frames.csv` | A-pose≠B-pose 596프레임 전수 |
| `eval_b4/regression_watchlist.csv` | failure mode 3건 추적 |
| `eval_b3/labels_ai_reviewed.json` | AI 판독 라벨 + provenance (**수정 금지**) |
| `labeling/labels.json` | 1차 라벨 (**수정 금지**) |

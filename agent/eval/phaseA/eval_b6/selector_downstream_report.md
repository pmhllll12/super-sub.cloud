# B-6 A-1 — selector 차이의 downstream 전이

*2026-08-28 · 산출: `selector_downstream.py` · GPU RTX 3050, Track1 169s + Track2 75s = **244초***

## 1. 실제 production selector 확인

`agent/src/supersub_agent/pose.py:105`

```python
def _largest_person_box(detections, threshold: float = 0.5):
    """가장 큰 사람 박스를 대상 선수로 삼는다."""
```

**production selector = `baseline`(면적 최대)** 이다. A-pose·B-pose·continuity는
production에 존재하지 않고 `eval_b2/eval_b2.py`의 평가용 구현이다. production에는
프레임 간 identity를 잇는 트래커가 없으며, 매 프레임 독립적으로 면적 최대를
다시 고른다. `PoseResult`는 선택된 박스도, 나머지 후보도, person 검출 점수도
저장하지 않는다.

B-2의 프레임 정확도는 baseline 70.1% / A-geo 84.5% / B-geo 85.6% /
A-pose 85.6% / **B-pose 87.6%** 였다. 이 17%p 격차가 지표와 등급까지 내려오는지가
이번 질문이다.

## 2. 비교한 selector

`eval_b2.WEIGHTS`를 그대로 import했다. 새 selector·가중치·임계값을 만들거나
튜닝하지 않았다.

| selector | 구성 |
|---|---|
| `baseline` | 면적 최대 — **production** |
| `A` | centrality 0.69 + size 0.31 |
| `B` | centrality 0.47 + size 0.20 + continuity 0.33 |
| `A_pose` | centrality 0.45 + pose_quality 0.35 + size 0.20 |
| `B_pose` | centrality 0.35 + pose_quality 0.25 + size 0.15 + continuity 0.25 |

## 3. 사용한 데이터 범위

| | Track 1 | Track 2 |
|---|---|---|
| 클립 | Phase A 39 (Kinetics `hitting baseball`) | rubric 보유 22 (야구 투구 1·농구 2·축구 19) |
| 검출 | `candidates/*.npz` 재사용 (재검출 없음) | RT-DETR 신규 실행 |
| 포즈 | 선택 박스 합집합에 ViTPose 실행 | 후보 전체에 ViTPose 실행 |
| grade | **산출 안 함** — 야구 **타격** rubric이 없다 | 산출함 |

**Track 1에서 grade를 내지 않은 이유**: `ann/hb_val.csv`의 39클립은 전부
`hitting baseball`(타격)인데 보유 rubric은 투구·점프슛·레이업·인스텝슈팅·
인사이드패스뿐이다. 타격 rubric은 없다. 투구 rubric을 타격에 적용하는 것은
미결 3번이 이미 기각한 오류이므로 하지 않았고, CSV에는
`grade = no_batting_rubric`으로 명시했다.

Track 1의 feature 산출에는 impact 정의가 필요해 **모든 selector에 동일하게**
`arm` / `extension_peak`을 적용했다. 이는 rubric이 아니며 타격 역학에 대한
주장도 아니다. selector **간 차이**를 재는 것이 목적이므로 공통 상수로 상쇄된다.

## 4. selector별 결과

### Track 1 — 39클립

| selector | feature 산출 성공 | usable(arm) 평균 | usable(leg) 평균 | baseline과 선택이 다른 프레임 | 영향 클립 |
|---|---:|---:|---:|---:|---:|
| **`baseline`** | **18/39** | **0.442** | **0.804** | — | — |
| `A` | 24/39 | 0.490 | 0.854 | 1,255 | 27 |
| `B` | 22/39 | 0.495 | 0.864 | 1,291 | 27 |
| `A_pose` | 23/39 | 0.513 | 0.870 | 1,387 | 27 |
| `B_pose` | **24/39** | 0.507 | **0.878** | 1,408 | 27 |

**baseline이 모든 축에서 최하위다.** 5,404프레임 중 66.1%가 다중후보이고
33/39 클립에 다중후보 프레임이 있다.

baseline 실패 21건은 **전부 `InsufficientQuality`** 다 — 품질 게이트에서 막힌다.

| | 회복(baseline 실패 → 성공) | 손실(성공 → 실패) |
|---|---|---|
| `A_pose` | **7건** `5-jBTNp5IQA` `ZS-wgeg2qkI` `Zp9aDp2YTBw` `g_wHimPF9o8` `idueIYDAbZc` `sYl2jCqsSKo` `w-AQcjcoDyA` | 2건 `N5zWQkoLM3M` `hz-SpF35_BE` |
| `B_pose` | **7건** `5-jBTNp5IQA` `X6dC9pu5H3k` `Zp9aDp2YTBw` `g_wHimPF9o8` `idueIYDAbZc` `sYl2jCqsSKo` `w-AQcjcoDyA` | 1건 `hz-SpF35_BE` |

즉 **순증 +6건** (B_pose 기준). 팔 유효 프레임 비율이 크게 오르는 클립들:

| 클립 | baseline | B_pose | |
|---|---:|---:|---:|
| `N5zWQkoLM3M` | 0.113 | 0.607 | **+0.493** |
| `g_wHimPF9o8` | 0.247 | 0.720 | +0.473 |
| `X6dC9pu5H3k` | 0.185 | 0.570 | +0.385 |
| `5-jBTNp5IQA` | 0.187 | 0.480 | +0.293 |
| … | | | |
| `3R1kvNrGJK0` | 0.733 | 0.613 | −0.120 |

### Track 2 — rubric 보유 22클립

| selector | feature 성공 | 선택 차이 | 영향 클립 | **grade_changed** |
|---|---:|---:|---|---:|
| `baseline` | 19/22 | — | — | — |
| `A` / `B` / `A_pose` / `B_pose` | 19/22 | **5프레임** | `10_penalty1.avi` **1개** | **1** |

다중후보 프레임이 있는 클립은 8개뿐이고, 그중 7개는 선택이 전혀 바뀌지 않았다.

| 클립 | 다중후보 프레임 |
|---|---|
| `10_penalty1.avi` | **31/31 (100%)** |
| `16_penalty1.avi` | 7/32 |
| `23_freekick.avi`, `OpenPose_5T.avi` | 4 |
| `21_freekick.avi` | 3 |
| `11_freekick`, `13_freekick`, `19_freekick1` | 1 |

## 5. downstream feature 영향

Track 1에서 baseline·B_pose **양쪽 다 feature가 나온 17클립** 중
**지표가 하나라도 달라진 것은 7클립**이다. 나머지 10클립은 완전히 동일하다.

| 지표 | n | 절대차 중앙값 | 최대 |
|---|---:|---:|---:|
| `impact_frame` | 17 | **0.00** | **74.0** |
| `swing_knee_angle_at_impact` | 17 | 0.00 | 37.2° |
| `plant_knee_angle_at_impact` | 17 | 0.00 | 42.1° |
| `trunk_forward_lean_deg_at_impact` | 17 | 0.00 | 11.1° |
| `hip_rotation_range_deg` | 15 | 0.00 | 41.8° |
| `follow_through_duration_frames` | 17 | 0.00 | 21.0 |

**중앙값 0, 최대 매우 큼** — 분포가 양극단이다. 영향이 있는 곳에서는 결정적으로
크고, 없는 곳에서는 완전히 없다.

| 클립 | 선택 차이 | 달라진 지표 |
|---|---:|---|
| `N5zWQkoLM3M` | 134프레임 | impact 42, hip_rot 41.8°, trunk 11.1° |
| `Fz16t9SrF3U` | 109 | impact 61, plant_knee 42.1°, follow 16 |
| `3R1kvNrGJK0` | 54 | impact 74, swing_knee 37.2°, follow 21 |
| `6hrcRyIYTrA` | 44 | swing/plant_knee 11.8° |
| `8gmHKqDxXdg` | 26 | impact 23, hip_rot 20.1° |
| `IYFifBJ9lH8` | 21 | hip_rot 8.8° |
| `O2GSaYqH8JY` | 17 | impact 17, trunk 5.7° |

## 6. grade 변경 건수

**Track 2에서 22클립 중 1클립(4.5%)의 등급이 바뀌었다.**

`10_penalty1.avi` (`football/instep_shot`, 31프레임 전부 다중후보):

| selector | 선택 차이 | impact_frame | swing_knee | plant_knee | trunk_lean | hip_rot | score | **grade** |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| `baseline` | — | 28.0 | 153.6° | 100.1° | −13.2° | 45.6° | 47 | **D** |
| `A`/`B`/`A_pose`/`B_pose` | 5 | **13.0** | 161.8° | **174.1°** | **10.0°** | 10.4° | **56** | **C** |

**단 5프레임의 선택 차이가 임팩트 프레임을 28→13으로 옮겼고, 그 결과 등급이
D→C로 한 단계 올라갔다.** 네 selector가 모두 동일한 결과를 냈다 — 즉 이 클립에서
갈리는 것은 **baseline이냐 아니냐**이지 A냐 B냐가 아니다.

Track 1의 grade는 산출하지 않았다(`no_batting_rubric`).

## 7. 기존 라벨과의 관계

feature가 회복된 클립과 B-5 clean review 결과를 대조하면 방향이 일치한다.

- `N5zWQkoLM3M` — B-5에서 **A 4 : B 0** (알려진 continuity regression). 여기서도
  B_pose는 feature를 잃었고(`A_pose` 손실 목록에 포함), 반대로 팔 유효 프레임은
  0.113→0.607로 가장 크게 올랐다. **"유효 프레임이 늘었다"가 "옳은 사람을
  봤다"를 뜻하지 않는다**는 것을 그대로 보여주는 사례다.
- `X6dC9pu5H3k`, `sYl2jCqsSKo`, `idueIYDAbZc`, `5-jBTNp5IQA` — B-5 판독 대상이었고
  여기서 feature가 회복됐다.

⚠️ **usable_ratio·feature 산출 성공률은 self-consistency / 측정 가능성 지표이지
correctness가 아니다.** 잘못된 사람을 안정적으로 추적해도 유효 프레임은 늘어난다.
이 절의 대조는 방향의 일관성을 본 것이며 정확도 주장이 아니다.

## 8. Effect concentration

효과는 **강하게 집중된다.**

- Track 1: 선택이 달라진 클립 27/39, 그러나 **지표까지 달라진 것은 7클립**
- Track 2: 선택이 달라진 클립 **1/22**, 등급이 달라진 것도 **1/22**
- 두 트랙 모두 **다중후보 프레임 비율이 높은 클립에서만** 효과가 난다

`10_penalty1.avi`(100% 다중후보), `N5zWQkoLM3M`·`Fz16t9SrF3U`(100%)처럼 화면에
사람이 계속 여럿인 클립에서만 selector가 의미를 갖는다. 단독 피사체 클립에서는
모든 selector가 정의상 같은 선택을 한다.

## 9. 한계

1. **Track 1에 등급이 없다.** 타격 rubric이 없어 "정확도 격차 → 등급 격차"의
   최종 고리를 39클립에서는 확인하지 못했다. 등급 근거는 Track 2의 **1클립**뿐이다.
2. **Track 2 표본이 작고 편향돼 있다.** 22클립 중 8개만 다중후보이고 그중 1개만
   selector가 갈린다. 등급 변경 1건으로 비율을 추정할 수 없다.
3. **correctness를 재지 않았다.** 어느 selector의 지표가 *옳은지*는 판정하지
   않았다. B-5에서 A/B 우열은 확정 불가로 결론났고 이번에도 새로 주장하지 않는다.
4. **분포 불일치.** Kinetics 타격 클립은 다중인원 66%인 반면 rubric 보유 클립은
   대부분 단독 피사체다. **실제 서비스 입력(생활체육 경기 영상)이 어느 쪽에
   가까운지가 결론의 크기를 좌우하는데, 그것을 이 데이터로는 알 수 없다.**
5. Track 1의 `arm`/`extension_peak` 설정은 selector 비교용 공통 상수이며,
   그 절대값을 타격 지표로 읽으면 안 된다.
6. `basketball/layup`은 `status: draft`다(검수 전). Track 2에 포함했으나 선택
   차이가 0이라 결론에 영향이 없다.

## 10. production selector 교체 여부에 대한 결론

**데이터가 지지하는 범위에서: baseline은 교체 후보로 올릴 근거가 있다. 다만
이 데이터만으로 교체를 확정할 수는 없다.**

교체를 **지지하는** 근거:

- baseline은 feature 산출 성공률이 **18/39로 최하위**이고 pose 계열은 22~24/39다.
  순증 +6클립, 실패는 **전부 품질 게이트 탈락**이다. 즉 프레임 정확도 격차가
  "분석 자체가 불가능해지는" 형태로 downstream에 실제로 전이된다.
- 팔·다리 유효 프레임 비율이 모든 pose 계열에서 baseline보다 높다.
- 등급까지 바뀐 사례가 실재한다(`10_penalty1.avi`, D→C). 5프레임 차이로 등급이
  움직였다.
- 네 대안(A/B/A_pose/B_pose)이 Track 2에서 **동일한 결과**를 냈다 — 교체 결정은
  "어느 대안이냐"를 먼저 풀지 않아도 된다. B-5에서 A/B가 갈리지 않는다는 결론과
  모순되지 않는다.

교체를 **확정하지 못하게 하는** 근거:

- 등급 변경 근거가 **22클립 중 1건**뿐이다.
- 어느 쪽 지표가 옳은지 판정하지 않았다. `N5zWQkoLM3M`처럼 pose 계열이 오히려
  잘못된 대상을 안정적으로 잡는 사례가 B-5에서 확인됐다.
- 서비스 실제 입력의 다중인원 비율을 모른다. 단독 피사체가 대부분이라면 교체
  효과는 0에 가깝고, 다중인원이 많다면 크다.
- production 교체에는 `_largest_person_box` 수정 + `PoseResult` 확장 +
  pose_quality 계산 경로 추가가 필요하다(현재 production은 후보별 포즈를 뽑지
  않는다). **비용이 0이 아니다.**

### 권장

1. **지금 교체하지 않는다.** 대신 **다중후보 비율을 서비스 입력에서 먼저 측정**한다
   — 이것이 교체 효과의 크기를 결정하는 단일 변수이고, 사람 라벨이 필요 없다.
2. 교체를 진행한다면 **A/B 중 선택은 미뤄도 된다.** 이번 결과에서 네 대안이
   같았고, B-5는 A/B를 가릴 수 없다고 결론냈다. `A_pose`가 continuity를 쓰지 않아
   `N5zWQkoLM3M`류 고착 위험이 없고 구현이 단순하다는 점은 기록해 둔다 — 다만
   이는 선호이지 데이터가 입증한 우위가 아니다.
3. Track 1의 등급 고리를 닫으려면 **야구 타격 rubric**이 필요하다. 이는 미결
   3번(종목당 1동작)과 미결 2번(지도자 검수)에 걸린 문제다.

---

## 산출물

| 파일 | 역할 |
|---|---|
| `selector_downstream.py` | 분석 스크립트 (Track 1·2) |
| `selector_downstream_comparison.csv` | Track 1 — 39클립 × 5 selector = 195행 |
| `selector_downstream_rubric_clips.csv` | Track 2 — 22클립 × 5 selector = 110행 |
| `selector_downstream_report.md` | 이 문서 |

## 보호 파일 확인

production code(`pose.py`·`features.py`·`scoring.py`), `eval_b2/`, `eval_b3/`,
`eval_b4/`, `eval_config.json`, `labels.json`, `labels_ai_reviewed.json`,
`agent/rubrics/`, 기존 `cache/`·`candidates/` — **전부 읽기 전용으로만 사용했고
수정하지 않았다.** 신규 결과는 `eval_b6/`에만 기록했다.

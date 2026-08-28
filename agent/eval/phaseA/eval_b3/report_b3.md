# Phase B-3 재평가 — AI-reviewed GT (Human Review Unavailable)

> **이 보고서의 GT는 사람이 검증한 것이 아니다 (AI-reviewed / unverified).**
> `labels_ai_reviewed.json` = Claude 단독 visual review. `human_verified: false`.
> production selector 최종 확정의 근거로 단독 사용할 수 없다.

## 1. 표본 (B-2와 다르다)

| | B-2 full | B-3 AI-reviewed |
|---|---:|---:|
| 평가 프레임 | 117 대상 중 valid 97 | 38건 중 30 (uncertain 3 제외, soccer 5 별도) |
| valid GT (정확도 분모) | 97 | 28 |
| 클립 | 39 | 17 |
| multi-candidate 프레임 | 64 | 28 |

**표본이 다를 뿐 아니라 성질이 다르다.** B-3의 33개 야구 프레임은 B-2에서
baseline/A/B 세 selector의 선택이 **갈린 프레임만** 골라낸 집합이다
(`make_review_set.py`). 즉 의도적으로 고른 난이도 상위 표본이므로, 절대
정확도는 B-2 full보다 낮게 나오는 것이 정상이다. 두 절대값을 직접 비교하면 안 된다.

## 2. 메인 결과 — AI-reviewed GT (n=28)

| Metric | Baseline | A-geometry | B-geometry | A-pose | B-pose |
|---|---:|---:|---:|---:|---:|
| Valid GT n | 28 | 28 | 28 | 28 | 28 |
| Correct | 5 | 18 | 19 | 20 | 20 |
| Wrong | 23 | 10 | 9 | 8 | 8 |
| Wrong-person rate | 82.1% | 35.7% | 32.1% | 28.6% | 28.6% |
| Accuracy | 17.9% | 64.3% | 67.9% | 71.4% | 71.4% |
| Multi-cand correct | 5/28 | 18/28 | 19/28 | 20/28 | 20/28 |
| Multi-cand wrong-rate | 82.1% | 35.7% | 32.1% | 28.6% | 28.6% |
| Multi-cand accuracy | 17.9% | 64.3% | 67.9% | 71.4% | 71.4% |
| Clip-level accuracy | 1/8 = 12.5% | 4/8 = 50.0% | 6/8 = 75.0% | 5/8 = 62.5% | 6/8 = 75.0% |
| Switching median | 8.4% | 4.4% | 1.4% | 4.4% | 1.0% |
| Switching mean | 10.8% | 7.3% | 1.9% | 6.8% | 1.8% |
| Clips >10% switching | 7/16 | 4/16 | 0/16 | 4/16 | 0/16 |

- clip-level은 **검수된 프레임이 2개 이상인 클립만** 대상으로 했다(B-2의 '3개 중 2개' 규칙을
  그대로 쓰면 검수 프레임이 1개인 클립은 구조적으로 항상 오답이 된다). 대상 클립 수가
  8개로 작아 이 지표는 참고용이다.
- switching은 **라벨과 무관한 지표**다(클립 전체에서 selector가 사람을 바꾼 비율).
  같은 17개 클립에 대한 값이라 B-2와 동일하게 나오는 것이 정상이다.

## 3. B-2 vs B-3 비교

### 3-1. 같은 30프레임, 라벨만 교체 (라벨 효과의 순수 측정)

| Selector | B-2 labels.json | B-3 AI-reviewed | Δ accuracy | wrong-rate Δ |
|---|---:|---:|---:|---:|
| Baseline | 4/26 = 15.4% | 5/28 = 17.9% | +2.5pp | -2.5pp |
| A-geometry | 18/26 = 69.2% | 18/28 = 64.3% | -4.9pp | +4.9pp |
| B-geometry | 19/26 = 73.1% | 19/28 = 67.9% | -5.2pp | +5.2pp |
| A-pose | 20/26 = 76.9% | 20/28 = 71.4% | -5.5pp | +5.5pp |
| B-pose | 20/26 = 76.9% | 20/28 = 71.4% | -5.5pp | +5.5pp |

두 열의 분모가 다르다(26 vs 28). 기존 라벨에서 null이던 4프레임 중 2건을
AI review가 후보로 지목했기 때문이다. 분모까지 맞춘 비교는 아래.

### 3-1b. 양쪽 모두 GT가 있는 26프레임 (분모까지 고정)

| Selector | 기존 GT | AI GT | Δ |
|---|---:|---:|---:|
| Baseline | 4/26 = 15.4% | 4/26 = 15.4% | +0.0pp |
| A-geometry | 18/26 = 69.2% | 18/26 = 69.2% | +0.0pp |
| B-geometry | 19/26 = 73.1% | 19/26 = 73.1% | +0.0pp |
| A-pose | 20/26 = 76.9% | 20/26 = 76.9% | +0.0pp |
| B-pose | 20/26 = 76.9% | 20/26 = 76.9% | +0.0pp |

**모든 selector에서 Δ가 0이다.** 이 26프레임에서 기존 라벨과 AI 판독이 갈린 것은
1건뿐이고(`X6dC9pu5H3k@0.50`),
그 프레임에서는 다섯 selector가 **기존 GT(6)도 AI GT(1)도 아닌 다른 후보**를 골랐다
(picks: baseline 3, 나머지 0). 즉 어느 라벨을 쓰든 5개 전부 오답이라 지표가 움직이지 않는다.
라벨 교체는 selector 간 상대 비교를 전혀 흔들지 않았다.

### 3-2. multi-candidate (같은 30프레임)

| Selector | B-2 multi acc | B-3 multi acc | Δ |
|---|---:|---:|---:|
| Baseline | 4/26 = 15.4% | 5/28 = 17.9% | +2.5pp |
| A-geometry | 18/26 = 69.2% | 18/28 = 64.3% | -4.9pp |
| B-geometry | 19/26 = 73.1% | 19/28 = 67.9% | -5.2pp |
| A-pose | 20/26 = 76.9% | 20/28 = 71.4% | -5.5pp |
| B-pose | 20/26 = 76.9% | 20/28 = 71.4% | -5.5pp |

이 표본에서는 **multi-candidate 지표가 전체 지표와 같다.** 검수 대상이 'selector들의
선택이 갈린 프레임'이라 후보가 1개인 프레임은 구조적으로 포함될 수 없기 때문이다
(최소 후보 수 2).

### 3-3. 참고 — B-2 full (97) 대비

| Selector | B-2 full acc | B-2 matched(30) | B-3 AI(28) |
|---|---:|---:|---:|
| Baseline | 70.1% (68/97) | 15.4% (4/26) | 17.9% (5/28) |
| A-geometry | 84.5% (82/97) | 69.2% (18/26) | 64.3% (18/28) |
| B-geometry | 85.6% (83/97) | 73.1% (19/26) | 67.9% (19/28) |
| A-pose | 85.6% (83/97) | 76.9% (20/26) | 71.4% (20/28) |
| B-pose | 87.6% (85/97) | 76.9% (20/26) | 71.4% (20/28) |

### 3-4. 순위

- **B-2 full**: B-pose(87.6%) > B-geometry(85.6%) > A-pose(85.6%) > A-geometry(84.5%) > Baseline(70.1%)
- **B-2 matched(30)**: A-pose(76.9%) > B-pose(76.9%) > B-geometry(73.1%) > A-geometry(69.2%) > Baseline(15.4%)
- **B-3 AI-reviewed**: A-pose(71.4%) > B-pose(71.4%) > B-geometry(67.9%) > A-geometry(64.3%) > Baseline(17.9%)

## 4. A-pose vs B-pose

| | A-pose | B-pose | 차이 |
|---|---:|---:|---:|
| Accuracy | 71.4% (20/28) | 71.4% (20/28) | +0.0pp |
| Wrong-person rate | 28.6% | 28.6% | +0.0pp |
| Multi-cand accuracy | 71.4% (20/28) | 71.4% (20/28) | +0.0pp |
| Switching mean | 6.8% | 1.8% | |

A-pose → B-pose 전이: recovery 2, regression 2, net +0
- `5-jBTNp5IQA@0.50` recovery: 1 → 0 (GT 0, 후보 9, AI conf medium)
- `IeDin6oB-IY@0.50` recovery: 0 → 4 (GT 4, 후보 9, AI conf high)
- `N5zWQkoLM3M@0.50` regression: 2 → 1 (GT 2, 후보 4, AI conf medium)
- `N5zWQkoLM3M@0.80` regression: 2 → 1 (GT 2, 후보 6, AI conf medium)

## 5. 라벨 변경 영향

| 유형 | 건수 |
|---|---:|
| unchanged | 25 |
| candidate->candidate | 1 |
| none->candidate | 2 |
| none->none | 2 |
| label->uncertain | 1 |
| none->uncertain | 2 |
| **합계** | **33** |

기존 라벨과 다르게 판단한 건: **8/33** (24%)

| clip@ratio | 기존 | AI | 유형 | conf | 후보 |
|---|---:|---:|---|---|---:|
| `5-jBTNp5IQA@0.80` | null | uncertain | none->uncertain | low | 20 |
| `CFjNxCZhn_8@0.80` | null | 0 | none->candidate | medium | 11 |
| `Fz16t9SrF3U@0.80` | null | uncertain | none->uncertain | low | 8 |
| `LXjM7nBZcak@0.50` | 1 | uncertain | label->uncertain | low | 13 |
| `X6dC9pu5H3k@0.50` | 6 | 1 | candidate->candidate | medium | 7 |
| `Zp9aDp2YTBw@0.20` | null | none | none->none | high | 2 |
| `Zp9aDp2YTBw@0.50` | null | none | none->none | high | 2 |
| `sYl2jCqsSKo@0.80` | null | 2 | none->candidate | medium | 3 |

## 6. B-2 핵심 regression 재확인

| case | AI GT | conf | baseline | A | B | A-pose | B-pose | 판정 |
|---|---|---|---|---|---|---|---|---|
| `LhD_fnHt_xg@0.50` | 0 | high | 0O | 1X | 1X | 1X | 1X | regression 재현 |
| `LhD_fnHt_xg@0.80` | 0 | high | 0O | 1X | 1X | 1X | 1X | regression 재현 |
| `N5zWQkoLM3M@0.50` | 2 | medium | 2O | 2O | 1X | 2O | 1X | regression 재현 |

표기: `선택index` + O(정답)/X(오답).

## 7. 축구 5프레임 (10_penalty1.avi)

| frame | AI GT | conf | baseline | 새 selector 4종 | 판정 |
|---|---:|---|---:|---:|---|
| 0 | 0 | high | 1 | 0 | 개선 |
| 21 | 1 | high | 0 | 1 | 개선 |
| 24 | 0 | high | 1 | 0 | 개선 |
| 26 | 0 | high | 1 | 0 | 개선 |
| 27 | 0 | high | 1 | 0 | 개선 |

- **A-geometry**: 개선 5 / 동일 0 / 악화 0
- **B-geometry**: 개선 5 / 동일 0 / 악화 0
- **A-pose**: 개선 5 / 동일 0 / 악화 0
- **B-pose**: 개선 5 / 동일 0 / 악화 0

네 selector 모두 이 5프레임에서 동일하게 선택했고, 5프레임 전부 baseline과 달랐다.
baseline은 **면적 최대**를 고르는데, 페널티킥 장면에서 카메라에 가까운 골키퍼가
키커보다 크게 잡히는 구간이 있어 그때 키커를 놓친다.

## 8. 최종 해석

AI-reviewed GT(n=28)에서 최고 정확도: **A-pose, B-pose** (71.4%).

### 판정

> **순위 불안정 — A-pose와 B-pose의 우열은 이 표본에서 판정되지 않는다.**

- A-pose 20/28, B-pose 20/28 — **완전 동점**이다.
  전이도 recovery 2 / regression 2로 상쇄된다(net 0).
- B-2 full에서 B-pose가 A-pose를 앞선 근거(85건 vs 83건, 2건 차)는 **이번 검수
  대상 밖의 프레임에서 나온 것**이다. 이 33프레임 안에서는 기존 라벨로도(20/26 동점)
  AI 라벨로도(20/28 동점) 두 selector가 갈리지 않는다.
- 즉 이번 재평가는 B-pose 우세를 **반박하지도 확증하지도 않는다.** 2건 차이를
  가르려면 검수 대상이 아니었던 나머지 프레임의 라벨 검증이 필요하다.

### 안정적으로 확인된 것

- **계층 순서는 라벨 교체와 무관하게 유지된다**: pose 계열(71.4%) > B-geometry(67.9%)
  > A-geometry(64.3%) >> Baseline(17.9%). 세 층 모두 B-2 matched와 같은 순서다.
- **Baseline(면적 최대)은 다인 프레임에서 무너진다.** 이 표본에서 17.9%로,
  네 selector 중 최하위이며 격차가 46pp 이상이다. 축구 5프레임에서도 5/5 열세다.
- **continuity는 switching을 확실히 줄인다**: mean 6.8%(A-pose)
  → 1.8%(B-pose), >10% 클립 4개 → 0개. 이 지표는 GT와 무관하므로 라벨 불확실성의 영향을 받지 않는다.
- 다만 continuity는 `N5zWQkoLM3M@0.50/0.80`에서 **틀린 대상에 고착**시키는 방향으로도
  작동했다(B-geometry·B-pose가 A 계열 대비 regression). 정확도와 안정성의 트레이드오프다.

### 남은 불확실성

- 유효 표본 28건은 selector 간 2건 차이를 가르기에 부족하다.
- AI 판독 자체가 medium confidence인 건이 이 표본에 8건 있고, A-pose/B-pose 전이
  4건 중 3건이 medium 구간에 걸쳐 있다.
- 이 33프레임은 난이도 상위로 편향된 표본이므로 절대 정확도를 서비스 품질 추정에
  쓸 수 없다.

## 9. Production readiness

**Human verified GT가 아니므로 production selector 최종 확정의 근거로 단독 사용 불가.**

- 이번 단계에서 production code / tests / rubric / goldenset / 가중치 / selector 구현은
  변경하지 않았다. selector 선택 결과는 B-2와 150/150 행 완전 일치로, **바뀐 것은 GT뿐**이다.
- 확정에 필요한 것: (1) 지도자 또는 사람 검수자의 라벨 검증, (2) 검수 대상이 아니었던
  프레임까지 포함한 재검증, (3) A-pose/B-pose 동점을 가를 추가 표본.


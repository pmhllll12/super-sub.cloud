# 상한 초과가 0등급으로 새는 양 — 전 루브릭 측정 (미결 20번)

2026-09-08. [`measure_ceiling.py`](measure_ceiling.py) · 원본 출력
[`measure_ceiling.out`](measure_ceiling.out)

**왜 다시 쟀나.** 항목의 수치는 **야구 타격 46클립에서만** 나와 있었고
(분리각 8/15, 팔로스루 12/20), 투구·축구·농구는 "같은 구조다"라고만 적혀
있었다. 그 문장을 확인한 적이 없다.

🔴 **이것은 처방이 아니라 크기 재기다.** 어느 처방(가·나·다)이 옳은지는
임계값 검수(미결 2번)에 달려 있고 여기서 고르지 않는다.

## 분류기가 맞다는 근거

야구 타격에서 **항목이 적어 둔 수치가 그대로 재현됐다** —
`hip_shoulder_separation` **8/15**, `follow_through` **12/20**. 다른 경로로 얻은
값과 일치하므로 분류(위/아래)가 맞다고 본다.

판정은 production 을 쓴다(`Criterion.grade_for`), 상한은 `bands` 의 최상위 등급
구간에서 읽는다 — 루브릭 YAML 을 다시 해석하지 않는다.

## 실측 — 0등급 117건 중 **23건(20%)이 상한 초과**

| 루브릭 | 표본 | 항목 | 0등급 | **상한 초과** |
|---|---|---|---|---|
| baseball/batting (draft) | JHMDB 46 | `lead_arm_extension` | 26 | **1** |
| | | `hip_shoulder_separation` | 15 | **8** |
| | | `hip_rotation` | 24 | 0 |
| | | `follow_through` | 20 | **12** |
| **football/instep_shot (active)** | B-6 Track2 18편 | `swing_knee_extension` | 11 | **2** |
| | | `plant_knee_flexion` · `trunk_lean` · `hip_rotation` · `follow_through` | 20 | 0 |
| basketball/jump_shot (active) | 1편 | `release_arm_extension` | 1 | 0 |
| basketball/layup (draft) | 1편 | — | 0 | 0 |

🔴 **active 루브릭에서도 샌다.** `football_instep_shot`의 `swing_knee_extension`
2건이다. 타격(draft)만의 문제라고 볼 수 없다.

⚠ **`baseball/pitching` 은 재지 못했다.** B-6 Track 2 에 1편 있는데
`features_ok=0`(측정 실패)이라 표본이 0이다. **"투구도 같은 구조"는 아래
구조 점검으로만 확인했고 실측이 아니다.**

⚠ 농구 두 종목은 표본이 **각 1편**이다. 0이 나왔다고 안 샌다는 뜻이 아니다 —
셀 것이 없었다.

## 구조 점검 — **6개 루브릭 30개 항목 전부** 상한이 닫혀 있다

표본과 무관하게, 위가 닫힌 최상위 구간을 가진 항목은 초과값이 갈 곳이 0등급뿐이다.

| 루브릭 | status | 닫힌 항목 |
|---|---|---|
| baseball_batting | draft | **5/5** |
| baseball_pitching | active | **5/5** |
| basketball_jump_shot | active | **5/5** |
| basketball_layup | draft | **4/4** |
| football_inside_pass | draft | **5/5** |
| football_instep_shot | active | **6/6** |

**열린 항목이 하나도 없다.** 「타격만의 문제가 아니다」는 이제 추정이 아니라
확인된 사실이다 — 다만 위에서 본 대로 **실제로 새는 빈도는 종목마다 다르다**
(타격 21/85 대 축구 2/31).

## 아직 하지 않은 것

- **처방을 고르지 않았다.** 가(상한을 `PLAUSIBLE_RANGE`로) · 나(밴드에 `excluded`
  구간) · 다(그대로 두고 표시만) 중 어느 쪽도. 임계값이 검수 전이라 무엇을
  "범위 밖"이라 부를지 자체가 임시값이다
- **하한 쪽(각도의 기하 한계)은 재지 않았다.** 항목의 「아래쪽 끝도 같다」 절이
  그것이고, `PLAUSIBLE_RANGE` 를 좁히는 것은 `features` 가 달라져 **B-6 재실행을
  부른다**. 이번 회차는 밴드 상한만 봤다

## ✅ (다)를 넣었다 (같은 날)

`breakdown[]` 에 **`out_of_band`** 를 더했다 — 0등급이 구간 위에서 왔으면
`"above"`, 아니면 `""`. 붙는 자리는 `scoring.aggregate` 한 곳뿐이다.

- **점수·등급이 한 비트도 안 바뀐다.** `features` 를 안 주면 빈 문자열이고
  나머지는 동일하다 (`test_out_of_band_does_not_move_the_score`)
- **B-6 재실행을 안 부른다.** `selector_downstream.py` 는 `features` 를 안 넘긴다
- 축구 18편에 대어 **10건**에 표시가 붙었다. 테스트 251 → **253**
- 🔴 **선수 화면에 그대로 내지 않는다** — 임계값이 검수 전이라 `band` 와 같은
  취급이다(미결 24번). 지금은 개발 확인용이다

## 🔴 재면서 드러난 것 — 층이 하나 더 있다

항목은 「상한 초과 → 0등급」으로 적었는데 **실제로는 사다리다.** 상한을 **막
넘긴** 값은 대개 **1등급**으로 간다 — 1등급 구간이 2등급 구간을 감싸기 때문이다.
0등급은 **더 멀리** 넘어야 걸린다.

| 초과가 가능한 22개 항목 | |
|---|---|
| 막 넘기면 **1등급** | **13개** |
| 막 넘기면 곧바로 **0등급** | **9개** |

`football_inside_pass` 는 네 항목 전부 1등급으로 받는다 — **(가)·(나)를 고를 때
참고할 본보기가 이미 저장소 안에 있다.**

그리고 **`PLAUSIBLE_RANGE` 안에서는 어느 값도 등급 구간을 벗어나지 않는다.**
`grade_for` 가 `RubricError` 를 내는 조합이 있긴 하지만 전부 그 범위 밖이라
`_drop_implausible` 이 먼저 걸러낸다 — **도달하지 않는다.** (조사 도중 이것을
도달 가능한 결함으로 잘못 본 적이 있다. 상한 + 50 으로 찔러 보다가 물리 한계인
180 을 넘긴 것이 원인이었다.)

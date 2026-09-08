# 결과 — 미결 21번 (지어낸 `hip_rotation_range_deg = 0.0` 제거)

2026-09-08. 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md)에 **코드 변경 전에**
고정했고(커밋 `82abf54`), 여기서 고치지 않았다.

## 판정: ✅ 전 항목 합격 — 채택

B-6 전 구간을 다시 돌렸다. **Track1 330초 / Track2 142초 / 총 472초** (RTX 3050,
cuda). `RERUN.md`의 244초보다 길지만 그때는 target 15였다.

| | Track 1 (195행) | Track 2 (110행) |
|---|---|---|
| 키 집합 | 일치 ✅ | 일치 ✅ |
| **A** selector·포즈 의존 7컬럼 | 완전 일치 ✅ | 완전 일치 ✅ |
| **B** `impact_frame` | 완전 일치 ✅ | 완전 일치 ✅ |
| **C** `hip_rotation_range_deg` | **0.0이던 10행만 빈칸** ✅ | 0행(변화 없음) ✅ |
| **D** 나머지 지표 8개 + `delta_*` | 완전 일치 ✅ | 완전 일치 ✅ |
| **E** `grade`·`grade_changed`·`score` | 변동 0건 ✅ | 변동 0건 ✅ |
| **F** `features_ok`·`fail_reason`·`rubric` | 완전 일치 ✅ | 완전 일치 ✅ |

A가 완전 일치라는 것이 중요하다 — 이 컬럼들은 selector와 포즈에만 의존하므로,
어긋났다면 내 변경이 아니라 **환경이 변한 것**(N-1 모델 리비전 등)이었다.

빈칸이 된 10행은 **2클립 × 5 selector**다.

| 클립 | `usable_ratio_leg` | 예전 값 |
|---|---|---|
| `YNMHMKb5Md4` | — | `0.0` (미결 21번이 지목한 그 클립) |
| `GS-PcxmaHmQ` | **0.0133 (1.3%)** | `0.0` |

**다리를 사실상 못 본 클립들이다.** `np.ptp`가 정확히 `0.0`을 내려면 구간의 모든
각도가 완전히 같아야 하는데 실측에서 나올 수 없다 — 지어낸 값이 맞았다.

## 🔴 합격했지만 **이 재실행이 증명하지 못한 것**

**등급 변동 0건은 공허한 결과다.** 확인해 보니:

- **Track 1은 애초에 채점을 하지 않는다.** 195행 전부 `rubric='n/a'`,
  `grade='no_batting_rubric'` 이다. 39클립이 야구 타격인데 타격 루브릭이 draft라
  B-6이 등급을 내지 않았다
- **Track 2는 `hip_rotation_range_deg == 0.0`인 행이 0개**였다. 바뀔 것이 없었다

즉 **"항목이 빠지면 가중치가 재정규화되어 등급이 어떻게 되는가"는 이 재실행으로
확인되지 않았다.** 확인된 것은 "지어낸 값이 사라졌고 나머지는 한 비트도 안
바뀌었다"까지다. 그 이상을 주장하면 안 된다.

그 경로는 **단위 검사로** 막았다 —
`test_unmeasurable_legs_yield_no_hip_rotation_key`가 다리를 못 본 조건에서 키가
빠지는 것을, `test_hip_rotation_is_declared_limb_dependent`가 면제 선언을 검사한다.
`LIMB_DEPENDENT_METRICS` 규약 자체(빠진 항목 제외 + 가중치 재정규화)는
`scoring.applicable_criteria`·`aggregate`가 이미 갖고 있고 도구 미검출로 검증돼 있다.

## 남은 것

🔴 **`football_instep_shot`(active)의 `hip_rotation` 항목이 같은 지표를 쓴다.**
지금 열려 있는 축구 루브릭에서 다리가 안 보이는 클립은 이제 그 항목이 **빠진다**
(예전에는 "골반이 잠겼다" 0등급이었다). 실클립으로 확인한 적은 없다 — 평가셋
39클립이 전부 야구 타격이라 축구 경로를 밟지 못한다.

## 재현

```bash
cd agent
uv run python eval/phaseA/eval_b6/selector_downstream.py   # 약 470초, GPU 필요
uv run python eval/pending21_hip_rotation/check.py         # 기준 A~F 대조
```

`check.py`는 `before_*.csv`(변경 전 산출물)와 `eval_b6/`의 현재 CSV를 비교한다.
테스트 249 → **251**.

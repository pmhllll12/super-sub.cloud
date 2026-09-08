# 사전 등록 — 미결 21번 (`hip_rotation_range_deg`의 지어낸 0.0 제거)

**2026-09-08 작성. 아래 기준은 B-6을 돌리기 전에 고정했고, 결과를 보고 고치지
않는다.** (`agent/CLAUDE.md` 「구현 전 사전 등록」)

## 무엇을 바꾸나

`features.py`의 한 줄이다. 준비 구간에 다리 유효 프레임이 2개 미만이면
회전량을 `0.0`으로 두던 것을 **키를 넣지 않는 것**으로 바꾼다.

```python
if len(span_idx) >= 2:
    unwrapped = np.unwrap(hip_axis[span_idx], period=180.0)
    hip_rotation_range = float(np.ptp(unwrapped))
else:
    hip_rotation_range = 0.0        # ← 이것을 없앤다
```

`LIMB_DEPENDENT_METRICS`에 `hip_rotation_range_deg`를 더해
`verify_rubric_coverage`가 면제하게 한다. 같은 파일의
`hip_shoulder_separation_deg`가 이미 쓰는 규약이다.

**하지 않는 것**: 0.0을 다른 기본값으로 바꾸지 않는다. 값을 안 내는 것이
답이지 더 그럴듯한 값을 지어내는 것이 아니다(E-3의 `fps=12.0`이 그랬다).

## 왜 B-6 재실행을 부르나

`features` 딕셔너리에서 **키가 빠진다** = 판정 입력이 달라진다. 미결 11번이
적어 둔 그 형태다. E-3(시간 표기)은 형제 블록이라 해당 없었지만 이건 해당한다.

## 착수 전에 센 것 (기존 CSV, 2026-09-04 산출)

| | Track 1 (`comparison.csv`, 195행) | Track 2 (`rubric_clips.csv`, 110행) |
|---|---|---|
| `hip_rotation_range_deg == 0.0` | **10행** | **0행** |
| 빈칸 | 107행 | 25행 |

`np.ptp`가 정확히 `0.0`을 내려면 구간의 모든 각도가 완전히 같아야 한다 —
실측에서 나올 수 없는 값이다. **그 10행이 지어낸 값이다.**

## 합격 기준 — 이대로 나오면 채택한다

키는 `(track, clip_id, comparison_selector)`. **행 수와 키 집합이 먼저 같아야
한다**(`RERUN.md` 대조 절차).

| # | 컬럼 | 요구 |
|---|---|---|
| **A** | `frames` · `multi_candidate_frames` · `selected_target_difference` · `selected_target_difference_ratio` · `detected_frames` · `usable_ratio_arm` · `usable_ratio_leg` | **완전 일치.** selector·포즈에만 의존하고 이번 변경과 무관하다. **어긋나면 내 변경이 아니라 환경이 변한 것이다**(N-1 모델 리비전을 먼저 본다) |
| **B** | `impact_frame` | **완전 일치.** 임팩트 정의를 건드리지 않았다 |
| **C** | `hip_rotation_range_deg` · `delta_hip_rotation_range_deg` | **위 10행에서만** `0.0` → 빈칸. 나머지 행은 완전 일치 |
| **D** | 나머지 지표 8개와 그 `delta_*` | **완전 일치** (소수 둘째 자리) |
| **E** | `grade` · `grade_changed` · `score` | **10행이 속한 클립에서만** 달라질 수 있다. 항목이 빠지면 가중치가 재정규화되므로 점수는 바뀔 수 있다. **그 외 행에서 바뀌면 불합격** |
| **F** | `features_ok` · `fail_reason` · `rubric` · `rubric_status` | **완전 일치.** 키가 빠지는 것은 품질 게이트 실패가 아니다 |

## 불합격이면

**되돌리고 원인부터 본다.** 특히 A가 어긋나면 이번 변경의 문제가 아니라
기준선 감사다 — `RERUN.md` 「불일치가 나오면」 절의 5단계를 따른다.
그때 판단할 것은 "이 변경을 채택할까"가 아니라 **"B-2~B-6의 어느 결론까지
다시 봐야 하는가"** 이다.

## 절차

1. 기존 CSV 두 개를 복사해 둔다 (`RERUN.md`가 요구한다 — 덮어쓴다)
2. 코드를 고친다
3. `uv run python eval/phaseA/eval_b6/selector_downstream.py` (약 244초)
4. 위 A~F로 대조한다
5. 결과를 이 폴더의 `RESULTS.md`에 적는다 — **합격이든 불합격이든**

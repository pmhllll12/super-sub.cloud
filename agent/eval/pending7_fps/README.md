# 미결 7번 — 프레임레이트 의존성 조사

같은 영상을 다른 프레임레이트로 넣으면 다른 등급이 나오는 문제
([미결 7번](../../../jekyll/pages/pending.markdown))의 원인 규명과 수정안 사전 산정.

**GPU가 필요 없다. 전 단계 약 2분, 그중 CSV 파싱이 10초다.**
포즈가 이미 들어 있는 외부 데이터(PitcherMotion)와 합성 영상만 쓴다.

production code는 **import만** 한다. `agent/src/`·`agent/rubrics/`·`agent/tests/`를
수정하지 않는다.

## 실행 순서

```bash
cd agent
.venv/bin/python eval/pending7_fps/load_pm.py 400     # 캐시 생성 (약 10초, 1회)
.venv/bin/python eval/pending7_fps/step1_reproduce.py
.venv/bin/python eval/pending7_fps/step2_decompose.py
.venv/bin/python eval/pending7_fps/step3_margin.py
.venv/bin/python eval/pending7_fps/step4_downstream.py
.venv/bin/python eval/pending7_fps/step5_sampling.py
.venv/bin/python eval/pending7_fps/step6_where.py
.venv/bin/python eval/pending7_fps/step7_atten.py
.venv/bin/python eval/pending7_fps/step8_e1e2_impact.py
.venv/bin/python eval/pending7_fps/step9_e1e2_downstream.py   # 약 55초
```

step1\~step7은 서로 독립이라 순서 없이 돌려도 된다. step8·step9는 `methods.py`의
E-1/E-2 모형을 쓴다.

## 입력과 산출

| | 경로 | 비고 |
|---|---|---|
| 입력 | `agent/data/goldenset/pitchermotion/Pitcher_Motion_Data.csv` | 1.06GB, `.gitignore` 대상 |
| 캐시 | `agent/data/pending7_fps/pm_clips.npz` | 26MB, `load_pm.py`가 재생성 |
| 합성 영상 | `agent/data/pending7_fps/synthetic/*.avi` | `step5`가 재생성 |
| 중간 산출 | `agent/data/pending7_fps/step{1,2}.npz`, `step1_res.json` | 재실행으로 복원 |

`agent/data/`는 `.gitignore` 대상이므로 **저장소에는 스크립트만 들어간다.**

## 데이터 — 왜 PitcherMotion인가

MLB 투구 포즈 3,324클립, 투수 232명, **60fps**, KAPAO 추출. 영상은 없고 포즈만 있다.
`load_pm.py`가 앞 400클립을 `(T,17,3)`로 복원한다(클립당 101\~558프레임).

`[::k]`로 솎아 30/20/15/12fps를 만든다. **같은 물리 프레임의 정확한 부분집합**이라
샘플링·검출 오차가 실험에 섞이지 않는다 — 이것이 이 데이터를 쓰는 이유다.

주의할 함정 셋 (2026-08-26 확인):

- `V1~V51`은 **COCO-17 × (x, y, 신뢰도)** 와 같은 순서다 (기하 검증 통과).
- README의 `720 - y` 안내는 **적용하면 안 된다** — 원본이 이미 이미지 좌표계다.
- `pitch_id`는 투수 안에서만 유일하다. `pitcher`와 묶어야 클립 키가 된다.

## arm 임계값 0.5 오버라이드 — 근거와 안전장치

`core.external_pose_threshold()`가 `features.LIMB_MIN_CONFIDENCE["arm"]`을
0.6 → **0.5**로 바꿨다가 되돌린다.

**왜 0.5인가.** KAPAO는 이미 0.5에서 잘라 내고 미검출을 0으로 채운 **검열된
점수**를 준다 — 신뢰도 255만 개를 전수 조사하니 0과 0.5 사이 값이 하나도 없었다
(0인 값 35.4%, 나머지는 전부 0.5 이상). ViTPose의 **연속** 점수에 맞춰 실측한 0.6을
그대로 적용하면 근거 없이 통과율이 5.8%로 떨어진다. 0.5로 낮추면 21%가 되고
지표 분포·jitter·기존 클립 측정값은 그대로다. 0.5 **아래는 아무 효과가 없다**.

**production 값 0.6은 ViTPose 경로에 대해 그대로 유지한다.** 파일은 바뀌지 않는다.

**안전장치.** 이 값은 모듈 최상단에서 대입하지 않는다. `import core`만으로는
아무것도 바뀌지 않고, `with external_pose_threshold():` 블록 안에서만 효력이 있으며
예외가 나도 `finally`가 되돌린다. 최상단 대입이었다면 같은 프로세스에서 core를
import한 다른 코드가 조용히 0.5로 채점하게 된다.

## 각 step이 내는 표

| step | 표 | 무엇을 답하는가 |
|---|---|---|
| `step1_reproduce` | 1\~2 | 08-26 증상 재현. fps별 팔꿈치각 중앙과 밴드 적중, 60 vs 30 차이 |
| `step2_decompose` | 3\~5 | **핵심.** 임팩트 이동을 후보 격자(E1) / 스텐실(E2) 로 2×2 분해 |
| `step3_margin` | 6\~9 | 전역 argmax 승자 마진과 예측 검정, 차등 감쇠, 스윙 팔 뒤집힘 |
| `step4_downstream` | 10\~15 | 지표 → 등급 → 총점 전파 (야구 투구 루브릭) |
| `step5_sampling` | 16\~18 | `read_frames`가 고르는 물리 인덱스, 격자 어긋남, `max_frames` |
| `step6_where` | 19\~20 | 임팩트가 어디로 옮겨 가는가, fps별 반려 사유 |
| `step7_atten` | — | 차등 감쇠를 짝수 프레임만으로 재측정 (**보고용 값**) |
| `step8_e1e2_impact` | 21\~24 | E-1/E-2 임팩트 영향, fps 불변성, 60fps 수렴 검정, 실패 모드 |
| `step9_e1e2_downstream` | 25\~28 | E-1/E-2 지표·등급 영향 (채택 영향 / fps 일관성) |

`step3` 표 8은 60fps 임팩트가 홀수 프레임일 때 30fps 격자에 그 자리가 없어 감쇠를
과대평가한다. **보고에는 `step7`의 값(0.46 / 1.06 / 2.33배)을 쓴다.**

## methods.py — E-1/E-2는 수정안이 아니라 모형이다

`patched_segment()`가 `features.segment_phases`를 컨텍스트 매니저 안에서만 갈아
끼운다. 경계 규칙(`impact - first < 2`)과 `first`/`last` 계산은 production과 글자
그대로 같게 두고 **임팩트 선택만** 바꾼다.

`wide_central(s, 1)`은 `np.gradient(s)`와 경계 처리까지 정확히 같다(테스트로 확인).

알아 둘 성질 둘:

- **E-1 τ=1/60초는 base와 정확히 같다.** 반폭이 `max(1, round(τ·fps))`인데
  τ=1/60이면 모든 k에서 1이 된다.
- **E-2 단독(선형 보간)도 base와 정확히 같다.** 조각선형 함수를 표본 간격의
  배수 반폭으로 미분하면 값이 구간마다 선형이라 최댓값이 항상 표본점에서 나온다.
  선형 보간은 argmax에 정보를 더하지 못한다.

## 사전 등록

E-1/E-2 구현 전에 고정한 합격/불합격 기준은 [`PREREGISTRATION.md`](PREREGISTRATION.md)에
있다. **데이터를 본 뒤 기준을 바꾸지 않는다.**

## 재현성

난수를 쓰지 않는다. `load_pm.py`가 만드는 캐시는 CSV의 앞 400클립으로 결정된다.
2026-09-01 실행에서 20개 표 전부가 이전 실행과 자릿수까지 일치했다.

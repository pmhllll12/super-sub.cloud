# 야구 타격 루브릭 — JHMDB 54클립 실행 기록 (2026-09-04)

`rubrics/baseball_batting.yaml`의 `validated_on`이 가리키는 근거다.
**영상도 GPU도 쓰지 않았다** — 사람이 붙인 관절 시계열만으로 돌렸다.

```bash
uv run python scripts/analyze_keypoints.py \
    --root /mnt/d/sports_dataset/_jhmdb/joint_positions \
    --action swing_baseball --rubric rubrics/baseball_batting.yaml \
    --out eval/jhmdb_batting/features_swing_baseball.json

uv run python eval/jhmdb_batting/grade_dist.py \
    eval/jhmdb_batting/features_swing_baseball.json
```

## 무엇을 말하는가

| 물음 | 답 |
|---|---|
| 파이프라인이 이 동작에서 지표를 내는가 | **낸다** — 54건 중 46건 |
| 실패 8건의 원인 | **전부 같다** — 임팩트가 마지막 프레임에 잡혀 경계 규칙에 걸렸다. 클립이 15\~40프레임으로 짧아 동작 전후가 잘려 있다 |
| 임계값이 맞는가 | 🔴 **말하지 않는다.** 정답은 관절이지 **자세 등급이 아니다** |
| 점수가 실력을 재는가 | 🔴 **말하지 않는다.** 위와 같은 이유다 |

## 🔴 임계값을 이 분포에 맞춰 고치지 않았다

분포는 루브릭 파일 머리에 적어 두었다. 요약하면 `lead_arm_extension`과
`hip_rotation`은 2등급 구간이 실측보다 높고, `trunk_posture`는 46건 중 43건이
2등급이라 사실상 갈리지 않는다.

**그래도 옮기지 않았다.** 정답이 없는 분포에 구간을 맞추면 등급이 고르게
퍼질 뿐 맞아지지 않는다 — target 30 전환에서 이미 겪은 착각이다(로드맵 2절).
구간은 지도자 검수(미결 2번)로 정하고, 이 분포는 그때 참고 자료로 올린다.

## 이 경로의 한계 — 결과 JSON의 `caveat`와 같은 내용

- 가림 정보가 없어 **신뢰도를 1.0으로 채웠다.** 품질 게이트가 한 번도 걸리지
  않는다 — 영상 경로의 `features_ok`와 **같은 뜻이 아니다**
- 원본 fps가 없어 프레임을 초로 환산하지 않는다 (미결 7번 E-3)
- 공 궤적이 없어 도구 의존 지표는 산출되지 않는다
- 좌우 배정은 발표된 순서를 그대로 믿는다. 우리 지표는 좌우 전역 교환에
  대칭이라 숫자는 안 바뀌고 **표기만** 바뀐다

## 라이선스

JHMDB는 **CC BY 4.0**이라 상업적 이용이 허용된다 — 미결 15번의 라이선스
축에서 깨끗한 후보다. 받는 곳: `https://files.is.tue.mpg.de/jhmdb/joint_positions.zip`

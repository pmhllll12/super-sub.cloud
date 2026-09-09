# 분석 리포트가 담는 것 — 읽는 쪽을 위한 지도

**누구를 위한 문서인가.** `POST /analyses` 적재(정어진)와 리포트 조회 경로
(미결 `paik` 7번), 그리고 화면 배선(백성검, `min` 9번 3조각)이 **같은 JSON 을
읽습니다.** 무엇이 어디 있는지 한 장에 둡니다.

**어디에 있나.** `reports/<user_id>/<video_id>/report.json` (S3). 그 자리는
완료 보고에 `report_key` 로 실려 옵니다 — 계산하지 마시고 그 값을 쓰세요
(미결 `paik` 11번).

🔴 **이 문서는 사본입니다. 정본은 코드입니다** — `scripts/analyze_s3.py` 의
리포트 딕셔너리와 `scoring.aggregate`. 어긋나면 코드가 맞습니다.

---

## `paik` 7번이 요구한 네 가지가 어디 있는가

| 요구 | 자리 | 비고 |
|---|---|---|
| **요약 문장** | `result.summary` | 두 문장 이내. 🔴 **숫자가 없습니다** — 계약 3장 4 |
| **특징 문장들** | `result.breakdown[].evidence` | 항목마다 하나. 자세 서술만 담습니다 |
| **받은 호칭** | `result.breakdown[].title` | 「채찍이 된 다리」 같은 등급별 칭호 |
| **근거가 된 장면** | `frame_metrics_seconds.impact_frame`(시각) · `result.breakdown[].metric_ref`(무엇) · `previews`(그림) | 아래 「근거가 된 장면」 절 |

---

## 봉투 (최상위 키)

| 키 | 무엇 |
|---|---|
| `video_id` | **어느 영상의 리포트인가.** 되짚을 때 이것을 쓰세요 — 🔴 **S3 키를 파싱하지 마세요.** 배치·평가 실행에는 없어서 `null` 입니다(백엔드 작업이 아닙니다) |
| `source_video` | 분석 시점의 원본 S3 URI. 🔴 **「저장」 뒤에는 낡습니다** — `keep` 이 원본을 옮기고 `videos/` 쪽을 지웁니다(`jin` 24번). 그래서 위 `video_id` 가 있습니다 |
| `analyzed_at` · `code_version` | 언제·어느 코드로 냈나. 계약 자리에는 타임스탬프가 없어 **재분석이 앞의 것을 덮으므로**, 「언제 낸 것인가」는 이 값이 답합니다 |
| `rubric` | `sport` · `motion` · `version` · `impact_limb` · `impact_event` |
| `swing_side` | `auto`\|`left`\|`right` |
| `focus` | 올린 사람이 고른 집중 항목 — `{requested, applied, unknown}` (`paik` 8번). 🔴 **채점에 영향이 없습니다.** 화면 강조·정렬용입니다 |
| `target_fps` · `sampled_fps` · `frames` | 분석 격자 |
| `frame_metrics_seconds` | 프레임 지표의 **초 환산**. 🔴 `features` 쪽 원값은 프레임이라 **직접 나누지 마세요** — 어느 것이 인덱스이고 어느 것이 길이인지는 이쪽만 압니다 |
| `previews` | 스켈레톤 미리보기 S3 URI. 비어 있으면 렌더링만 실패한 것이고 측정·판정은 유효합니다 |
| `subject` | **누구를** 분석했나 — 지정·자동·폴백과 선택 박스. 🔴 `source` 가 `specified_uncertain` 이면 **찍은 사람을 끝까지 따라갔다고 보장 못 합니다**(미결 18번) |
| `judge_backend` · `judge_model` · `timing` | 판정 백엔드와 소요 시간 |
| `features` | 측정값 원본. 적재용입니다(`jin` 23번) |
| `result` | 아래 |

## `result` — 실제 산출 예시

```json
{
  "score": 57,
  "grade": "C",
  "summary": "디딤발 무릎 굽히기가 「흔들리지 않는 축」으로 이번 동작의 강점입니다. 상체 기울기는 「젖혀진 상체」로 가장 아쉬웠습니다.",
  "breakdown": [
    {
      "criterion_id": "plant_knee_flexion",
      "name": "디딤발 무릎 굽히기",
      "grade": 2,
      "weight": 0.15,
      "contribution": 15.0,
      "title": "흔들리지 않는 축",
      "band": "150~170",
      "out_of_band": "",
      "stat": null,
      "evidence": "디딤발이 공 옆에 안정적으로 놓였습니다.",
      "metric_ref": "plant_knee_angle_at_impact"
    }
  ],
  "skipped": [{"criterion_id": "plant_foot_position", "name": "디딤발 위치", "weight": 0.15}],
  "rubric_version": "0.1",
  "pipeline_version": "pose-v0.1",
  "provisional": true
}
```

> `band` 는 구간이 둘로 갈릴 수 있습니다 — `"135~150 또는 170~180"`. 문자열을
> 숫자로 파싱하려 하지 마세요. **애초에 선수 화면에 내지 않습니다**(아래).

### 화면에 낼 때 지켜야 할 것

| | |
|---|---|
| 🔴 `band` 를 **선수에게 내지 마세요** | 임계값이 지도자 검수 전이라 확정 수치가 아닙니다 (미결 24번) |
| 🔴 `provisional: true` 면 확정 점수가 아닙니다 | 검수 전 루브릭으로 낸 값입니다 |
| 🔴 `summary` 에 점수를 덧붙이지 마세요 | 계약 3장 4 가 금지합니다. 숫자는 `score` 가 따로 가집니다 |
| 🔴 `skipped` 는 **0점이 아니라 제외**입니다 | 촬영 조건으로 못 잰 항목입니다. 0점으로 그리면 선수를 감점하는 것이 됩니다 |
| `stat` 은 표시 전용 | 레이더 차트 축 값(0~100). 🔴 **총점은 이것의 평균이 아닙니다** — 등급의 가중합입니다 |
| `out_of_band` 가 비어 있지 않으면 | 0등급이 **구간 위**에서 왔다는 표시입니다(미결 20번). 개발 확인용이고 선수 화면용이 아닙니다 |

---

## 근거가 된 장면

「시각 + 무엇」을 이렇게 맞춥니다.

| | |
|---|---|
| 시각 | `frame_metrics_seconds.impact_frame` (초). 🔴 없으면 **격자를 몰라 초를 지어내지 않은 것**입니다 — 0 으로 채우지 마세요 |
| 무엇 | `breakdown[].metric_ref` 가 그 항목이 근거로 삼은 지표 코드입니다. 사람이 읽을 이름·단위는 `contracts/metric_definitions.yaml` |
| 그림 | `previews` |

---

## `summary` 는 **모델이 쓰지 않습니다**

`evidence`(항목별 근거 문장)는 EXAONE 이 쓰지만 **요약은 코드가 짓습니다**
(`scoring.summarize`). 등급이 가장 높은 항목과 가장 낮은 항목의 칭호를 엮습니다.

- **숫자를 쓸 자리를 안 만듭니다.** 근거 문장 쪽에서는 이것을 지키는 데 2회차가
  걸렸고 아직 1건이 남아 있습니다(미결 23번)
- **같은 판정이 같은 문장을 냅니다** — 재현됩니다
- 🔴 **없는 것을 지어내지 않습니다**: 전부 잘했으면 아쉬운 점을 만들지 않고,
  전부 못했으면 강점을 만들지 않으며, **1등급을 「강점」이라 부르지 않습니다**
- 검사는 `tests/test_summary.py` (루브릭 6종 × 등급 전 조합)

모델이 쓰는 코칭 문장으로 바꾸는 것은 **별도 회차 + 사전 등록**입니다.
「더 나은 요약」은 정답이 없어 좋아졌는지 판정할 방법이 없습니다.

---

## 아직 없는 것

| | |
|---|---|
| 리포트를 **읽는 API** | 미결 `paik` 7번 (정어진) |
| 완료 보고의 `report_key` **받는 칸** | 미결 `paik` 11번 (정어진). 싣는 쪽은 됐습니다 |
| `metric_definition` **시드** | 미결 `jin` 23번 (정어진). 목록·형식은 냈습니다 |
| 화면 배선 | `min` 9번 3조각 (백성검) |

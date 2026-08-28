# 서비스 입력 관측 (service input observability)

> **These metrics measure input exposure and measurement behavior, not target
> correctness.**
>
> 화면에 사람이 몇 명 잡혔는지는 관측할 수 있지만, 그중 누가 분석 대상이어야
> 했는지는 라벨 없이 알 수 없다. 이 문서의 어떤 값도 정확도의 근거가 아니다.

분석 1건마다 입력 분포 메타데이터를 남긴다. 목적은 Phase B-6의 질문
**"실제 서비스 입력에 다중인원 장면이 얼마나 흔한가"** 에 답할 근거를 쌓는 것이다.
selector를 바꾸기 위한 것이 아니라 바꿀지 말지를 판단할 데이터를 모으는 것이다.

## 무엇을 남기는가

원본 영상은 **저장하지 않는다.** 집계값만 남기고 사용자 식별 정보를 복제하지
않는다 — 레코드는 `analysis_id`로만 다른 도메인과 이어진다.

```json
{
  "analysis_id": "9f2c…",
  "analyzed_at": "2026-08-28T07:12:33+00:00",
  "rubric_key": "football/instep_shot",
  "source_fps": 29.97,
  "sampled_fps": 14.985,
  "analyzed_frame_count": 150,
  "frames_with_0_person": 3,
  "frames_with_1_person": 51,
  "frames_with_2_person": 60,
  "frames_with_3plus_person": 36,
  "frames_with_ge2_person": 96,
  "multi_person_frame_ratio": 0.64,
  "max_candidate_count": 7,
  "candidate_count_histogram": {"0": 3, "1": 51, "2": 60, "3": 20, "4": 16},
  "raw_frames_with_ge2_person": 118,
  "raw_multi_person_frame_ratio": 0.786667,
  "raw_candidate_count_histogram": {"1": 32, "2": 44, "3": 40, "6+": 34}
}
```

## 용어 정의

이 정의는 코드·저장·문서에서 동일하게 쓴다.

| 이름 | 정의 |
|---|---|
| **candidate count** | 프레임 하나에서 **person detector(RT-DETR)가 낸 사람 후보의 수**. 최종적으로 선택된 사람 수가 **아니다**(그건 항상 0 또는 1이다). |
| **eligible candidate count** | 그중 검출 점수 ≥ `pose.PERSON_ELIGIBLE_THRESHOLD`(0.5)인 것. **production selector `_largest_person_box`가 실제로 후보로 보는 집합**이며, Phase A/B 평가의 `DET_THRESHOLD`와 같은 기준이라 그 결과와 비교된다. **기본 지표는 이쪽이다.** |
| **raw candidate count** | 검출기가 person으로 낸 것 전부(후처리 임계값 0.3 통과분). eligible과의 차이는 "낮은 점수로 잡힌 사람이 얼마나 있는가"를 보여준다. |
| **analyzed_frame_count** | **pose 분석에 실제로 사용된 샘플링 프레임 수.** 원본 영상의 전체 프레임 수가 아니다. 원본 프레임 수는 현재 관측하지 않는다(`read_frames`가 돌려주지 않는다). |
| **source_fps** | 원본 영상의 fps (`cv2.CAP_PROP_FPS`). |
| **sampled_fps** | **실효** 샘플링 fps = `source_fps / step`. 목표값(`target_fps`)이 아니다 — 간격이 정수라 25fps에 target 15를 주면 12.5fps가 된다. |
| **multi_person_frame_ratio** | `frames_with_ge2_person / analyzed_frame_count`. **분모에 사람이 0명인 프레임을 포함한다** — "여럿인 상황에 얼마나 노출되는가"가 질문이므로, 사람이 안 잡힌 프레임을 빼면 노출이 과대평가된다. |
| **clip-level multi-person exposure** | 클립 하나의 `multi_person_frame_ratio`. **raw ratio만 저장하고 "substantial" 여부를 판정하지 않는다** — 아래 참조. |

### "substantial multi-person exposure"를 정의하지 않은 이유

프로젝트에 이 임계값에 해당하는 기존 기준이 **없다.** 지금 숫자를 하나 정하면
그것이 근거 없이 제품 기준으로 굳는다. 그래서 **raw ratio만 저장한다.**
구간이 필요하면 분석 시점에 exploratory metric으로 제시하되 correctness 의미를
부여하지 않는다.

## 어디서 관측하는가 — 파이프라인이 보장한다

**기록은 HTTP 진입점이 아니라 `extract_keypoints()` 안에서 일어난다.**

```python
extract_keypoints(video, observe=True, rubric_key=None)   # observe 기본값 True
```

진입점에 붙여 두면 새 호출자(백엔드 job worker 등)가 생길 때마다 사람이 기록을
기억해야 하고, 빠뜨려도 아무 신호가 없다. 실제로 이 저장소에는
`scripts/analyze.py`·`scripts/measure.py`가 이미 `extract_keypoints()`를 직접
호출하고 있었다 — 진입점 배선이었다면 둘 다 조용히 누락됐을 것이다.

그래서 **기본값을 `observe=True`로 두어 fail-safe 방향으로 만들었다.**
관측에서 빠지려면 명시해야 하고, 아무것도 하지 않으면 포함된다.

| 경로 | 관측 |
|---|---|
| `POST /api/analyze/video` → `extract_keypoints()` | ✅ 자동 |
| 향후 백엔드 job worker → `extract_keypoints()` | ✅ 자동 (배선 불필요) |
| `POST /api/analyze/synthetic` | ❌ — 합성 키포인트라 영상도 후보도 없다. **서비스 입력이 아니므로 기록하지 않는다** |
| `scripts/analyze.py`, `scripts/measure.py` | ❌ — `observe=False` **명시적** 제외 |
| `eval/phaseA/extract.py` (Phase A 오프라인 추출) | ❌ — `observe=False` **명시적** 제외 |

> ⚠️ `eval/phaseA/extract.py`는 저장소 사본을 고쳤다. 그런데 README의 재현 절차는
> **`/mnt/d/supersub-phaseA/`의 원본을 실행**하라고 안내한다(스크립트가 그 경로를
> 하드코딩하고 있다). 그 원본은 보존 대상이라 고치지 않았으므로, 거기서 재실행할
> 때는 `SUPERSUB_METRICS_SINK`를 임시 경로로 돌려 서비스 sink를 비켜 가야 한다.
>
> ```bash
> SUPERSUB_METRICS_SINK=/tmp/offline.jsonl python3 /mnt/d/supersub-phaseA/extract.py
> ```

CLI·오프라인 평가를 제외하는 이유는 개발 중 반복 실행이 서비스 입력 분포에
섞이면 그 분포로 내리는 판단이 오염되기 때문이다. **실제 서비스 입력과 오프라인
평가를 구조적으로 분리한다.**

### 프레임 루프 안에서는

분석 대상을 고르기 **전에** 센다.

```
후보 박스들
    ↓
candidate count 관측     ← _count_person_candidates()  (읽기만 한다)
    ↓
가장 큰 사람 선택         ← _largest_person_box()       (변경 없음)
    ↓
PoseResult
```

선택 이후에는 셀 수 없다. `_largest_person_box`가 가장 큰 것 하나만 남기고
나머지를 버리기 때문이다.

**관측은 선택의 부수 효과가 아니다.** `detections`를 읽기만 하고 바꾸지 않으며,
관측을 넣기 전과 후의 선택 결과가 같다는 것을 테스트가 지킨다
(`test_observability.py::test_counting_does_not_change_the_selection`).

`PERSON_ELIGIBLE_THRESHOLD`는 `_largest_person_box`의 기본 임계값과 **같아야
한다.** 갈라지면 기록이 selector의 실제 후보 집합을 설명하지 못한다. 이 일치도
테스트가 지킨다(`test_eligible_threshold_matches_the_selector`).

## 어디에 남는가

append-only JSONL. 기본 경로는 `agent/data/observability/service_input_metrics.jsonl`
이고 환경변수 `SUPERSUB_METRICS_SINK`로 덮어쓴다. `agent/data/`는 `.gitignore`
대상이라 런타임 데이터가 커밋되지 않는다.

**저장 실패(OSError)는 예외를 올리지 않는다.** 관측 때문에 사용자의 분석이
실패하면 안 된다. 다만 **프로세스당 한 번 경고를 남긴다** — 조용히 넘기면
"서비스 입력이 0건"과 "sink가 고장남"을 구분할 수 없다. 집계 CLI도 두 경우를
나눠 출력한다(파일 없음 / 파일은 있는데 유효 레코드 0건).

**직렬화 오류는 삼키지 않는다.** `build_record`가 내는 값은 전부 우리가 통제하는
기본형이므로, 직렬화가 깨졌다면 운영 환경 문제가 아니라 프로그래밍 오류다.
그래서 파일을 열기 전에 직렬화하고 `TypeError`를 그대로 올린다.

### 왜 DB 테이블이 아닌가

백엔드(`fastapi/`)에 영상·분석 도메인이 아직 없다 — 테이블은 user·card 계열
8개뿐이고 백엔드가 agent를 호출하지도 않는다. 지금 테이블을 만들면 아무도 쓰지
않는 스키마가 생기고 `analysis_id`의 의미·FK·보존정책을 도메인 소유자 없이
확정하게 된다.

그래서 레코드를 **그대로 한 행으로 INSERT할 수 있는 평면 구조**로 만들었다.
영상 도메인이 생기면 아래 스키마로 옮기고 sink를 어댑터로 바꾸면 된다.

```sql
-- 제안 (아직 만들지 않았다). 영상·분석 도메인이 생길 때 함께 정한다.
CREATE TABLE analysis_input_metrics (
    id                        BIGSERIAL PRIMARY KEY,
    analysis_id               UUID        NOT NULL UNIQUE,
    analyzed_at               TIMESTAMPTZ NOT NULL,
    rubric_key                TEXT,
    source_fps                REAL        NOT NULL,
    sampled_fps               REAL        NOT NULL,
    analyzed_frame_count      INTEGER     NOT NULL,
    frames_with_0_person      INTEGER     NOT NULL,
    frames_with_1_person      INTEGER     NOT NULL,
    frames_with_2_person      INTEGER     NOT NULL,
    frames_with_3plus_person  INTEGER     NOT NULL,
    frames_with_ge2_person    INTEGER     NOT NULL,
    multi_person_frame_ratio  REAL        NOT NULL,
    max_candidate_count       INTEGER     NOT NULL,
    candidate_count_histogram JSONB       NOT NULL,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

사용자 식별자를 이 표에 넣지 않는다. 필요하면 영상 도메인 쪽에서
`analysis_id`로 조인한다.

## 조회 방법

```bash
cd agent
uv run python scripts/service_input_metrics.py                 # 표 1~3 출력
uv run python scripts/service_input_metrics.py --csv out.csv   # 클립 단위 CSV
uv run python scripts/service_input_metrics.py --sink /path/to/metrics.jsonl
```

레코드가 없으면 `SERVICE_INPUT_AVAILABLE = FALSE`를 출력하고 **숫자를 만들지
않는다.**

## 이 값으로 하면 안 되는 것

Phase B-5·B-6에서 확인한 구분을 그대로 지킨다.

| 관측되는 것 | 관측되지 않는 것 |
|---|---|
| selection divergence — selector들이 다르게 행동하는 정도 | 어느 selector가 옳은지 |
| multi-person exposure — 여럿인 상황에 노출되는 정도 | 다중인원에서 어느 selector가 나은지 |
| measurement availability — 지표가 산출되는 비율 | 산출된 지표가 정확한지 |
| self-consistency / stability | correctness |

특히 **잘못된 사람을 안정적으로 추적해도 measurement availability는 올라간다.**
B-5에서 `N5zWQkoLM3M`이 그 사례였다. 안정성을 정확성의 증거로 읽지 않는다.

## 앞으로 필요한 것

이 계층은 관측 기반일 뿐이고, selector 교체 판단은 **실제 서비스 데이터가
충분히 쌓인 뒤 별도 evaluation 단계**에서 한다. 이번 단계에서
`KEEP BASELINE` / `CHANGE SELECTOR`를 결정하지 않는다.

현재 이 계층에 데이터를 흘려보내는 경로는 `POST /api/analyze/video`
(로컬 확인용 UI) 하나다. 앱 → 백엔드 → 분석 경로가 붙을 때, **그 경로가
`extract_keypoints()`를 쓴다면 추가 배선 없이 자동으로 기록된다.**

정확히 말하면 이렇다 — 초기 문서에 "서비스 경로가 붙으면 코드 변경 없이 데이터가
쌓인다"고 적었는데 그때는 기록이 HTTP 핸들러에 붙어 있어서 사실이 아니었다.
기록을 파이프라인 안으로 옮긴 지금은 **`extract_keypoints()`를 사용하는
production analysis에 한해** 참이다. 파이프라인을 우회해 포즈를 직접 만드는
경로가 생긴다면 그쪽은 여전히 별도 배선이 필요하다.

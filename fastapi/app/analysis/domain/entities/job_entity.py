"""워커가 집어 간 분석 작업. 부록 D 도메인 ② (영상·분석)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ClaimedJobEntity:
    """워커가 하나 집었을 때 돌려주는 것.

    **작업 자체가 아니라 "이 작업을 하려면 알아야 할 것"** 이다. 그래서 상태·시각은
    없다 — 집은 순간 `running` 이고 `started_at` 은 서버가 찍었다.

    🔴 **동작(루브릭)이 여기 없다.** `video` 에 담을 자리가 아직 없어서다
    (미결 `jin` 17번). `sport_code` 만으로는 축구·농구에서 루브릭이 둘로 갈리므로,
    **워커가 종목만 보고 기본값으로 돌리면 안 된다** — 갈리는 종목은 실행하지 말고
    실패로 보고하는 편이 맞다. 기본값(`football_instep_shot`)으로 채점된 결과는
    틀렸다는 것이 값에 안 나타난다.
    """

    job_id: UUID
    video_id: UUID
    storage_key: str
    sport_code: str
    side: str | None
    duration_ms: int | None
    # 「이 사람으로 분석」 대상 (미결 `paik` 6번). 정규화 `[x, y, w, h]`(0~1)와
    # 그 박스를 그린 시각(ms). 지정이 없으면 둘 다 None — 「자동으로 고르기」다.
    subject_box: list[float] | None = None
    subject_at_ms: int | None = None
    # 「집중해서 볼 항목」 (미결 `paik` 8번). 루브릭 criteria id 리스트. 빈/None 이면 「전체」.
    focus: list[str] | None = None
    # `"analyze"` | `"detect"` (미결 `ho` 44번). `detect`면 `sport_code`·
    # `subject_box`·`focus`는 워커가 무시하면 된다 — `storage_key`와
    # `subject_at_ms`(검출할 시각)만 본다.
    job_type: str = "analyze"


@dataclass(frozen=True)
class DetectionStatusEntity:
    """지금까지 나온 `detect` 작업 하나의 상태 (미결 `ho` 44번).

    `ClaimedJobEntity`와 다른 자리다 — 이건 워커가 아니라 **화면이** 폴링해서
    본다("이 작업을 하려면 알아야 할 것"이 아니라 "이 작업이 어떻게 됐는지").
    """

    job_id: UUID
    status: str
    failure_reason: str | None
    # `{"people": [{"box":[x,y,w,h], "score":...}], "ball": {...}|None}` —
    # `detect_subjects.py --result-json` 이 낸 것 그대로. `succeeded` 가 아니면
    # None.
    detection_result: dict | None

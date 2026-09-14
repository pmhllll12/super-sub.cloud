"""읽기 경로가 화면에 내보내는 리포트 모양. 미결 `jin` 27번 · `paik` 7번 · `ho` 28번.

🔴 **허용목록이다.** 계약 3-1 이 "DB 조립"을 택한 이유가 이것 — DB 에 있는 것을
전부 흘리지 않고 여기 적힌 필드만 나간다. `band`·`weight`·`contribution`·
`out_of_band`·`view_dependent` 는 여전히 여기 없다(개발 확인용이거나 — `band` 는
임계값이 검수 전이라 선수에게 내지 않는다, 미결 24번).

🔴 **정정 (`ho` 28번, 2026-09-11)**: 이 파일이 앞서 "수치는 카드 경로가 따로
읽는다"고 적었던 것은 틀렸다. 계약 3장 4가 막은 것은 `summary` 문장 **안에**
숫자를 넣는 것이지, 총점·오버롤 등급·항목별 `stat` 자체가 아니다 — 이 셋은
**리포트 경로로 나가는 것이 계약**이다(`ho` 28번 확인). 그래서 `total_score`·
`overall_grade`·`ReportCriterionView.stat` 을 아래에 더한다. `player_card` 에
능력치를 안 두는 원칙(부록 D.5)은 그대로다 — `card_rules.FORBIDDEN_CARD_FIELDS`
가 그쪽을 막는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ReadReportQuery:
    video_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class ReportCriterionView:
    criterion_id: str
    name: str
    grade: int | None       # None = 제외(skipped). 0 점이 아니다.
    title: str | None
    evidence: str | None
    metric_ref: str | None
    skipped: bool
    # 레이더 축 값 0~100(`ho` 28번). `stat.{sport}.{motion}.{criterion_id}` 로
    # 저장된 값. `skipped` 나 루브릭 정보(옛 행)가 없으면 None — 0 을 지어내지
    # 않는다. 🔴 총점은 이 평균이 아니다(등급의 가중합).
    stat: float | None


@dataclass(frozen=True)
class ReportSceneView:
    """판단의 근거가 된 장면. 시각은 수치가 아니라 찾아가는 자리다."""

    metric_code: str
    label: str
    at_seconds: float


@dataclass(frozen=True)
class ReportView:
    video_id: UUID
    analyzed_at: datetime
    summary: str
    provisional: bool | None
    # 총점 0~100(항목 가중합, `stat` 평균이 아니다) · 글자 등급(A/B/C/D).
    # 영상 하나(=분석 1회)의 오버롤이다 — 선수 단위로 합친 것이 아니다(`ho` 28번
    # "오버롤 단위" 확인). 옛 행(이 필드가 생기기 전 적재분)은 둘 다 None.
    total_score: float | None
    overall_grade: str | None
    breakdown: list[ReportCriterionView]
    scenes: list[ReportSceneView]
    previews: dict[str, Any] | None
    keypoint_quality: dict[str, Any] | None

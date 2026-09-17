"""경기 조건(`paik` 18번)·후보(`paik` 20번) 엔티티. 저장 형태가 아니라 앱이
다루는 모양이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from uuid import UUID


@dataclass(frozen=True)
class SlotEntity:
    weekday: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class TeamPreferenceEntity:
    team_id: UUID
    region_ids: list[UUID] = field(default_factory=list)
    slots: list[SlotEntity] = field(default_factory=list)


@dataclass(frozen=True)
class MemberPreferenceEntity:
    user_id: UUID
    region_ids: list[UUID] = field(default_factory=list)
    slots: list[SlotEntity] = field(default_factory=list)
    position_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class MemberPreferenceSummaryEntity:
    """`paik` 21번 — 팀장이 보는 팀원 한 명의 조건."""

    user_id: UUID
    nickname: str
    region_ids: list[UUID]
    slots: list[SlotEntity]
    position_ids: list[UUID]


@dataclass(frozen=True)
class RegionFactEntity:
    """지역 id를 계층 비교 가능한 값으로 푼 것(`paik` 20번 — 같은 구/같은 시)."""

    city: str
    district: str


@dataclass(frozen=True)
class CandidateFactsEntity:
    """후보 팀의 원자료. 소프트 점수는 인터랙터(도메인 규칙)가 계산한다 —
    쿼리가 아니라 순수 함수라야 테스트하기 쉽다(`paik` 20번).
    """

    team_id: UUID
    team_name: str
    region_label: str  # team.region — 표시용 "연고지", 선호 지역과는 다르다
    formation: str
    regions: list[RegionFactEntity]  # 선호 지역(paik 18번), 계층 비교용으로 이미 해석됨
    slots: list[SlotEntity]
    last_active_at: datetime | None


@dataclass(frozen=True)
class MatchReason:
    kind: str  # "time" | "region"
    detail: str


@dataclass(frozen=True)
class MatchCandidateResultEntity:
    team_id: UUID
    team_name: str
    region_label: str
    formation: str
    reasons: list[MatchReason]


@dataclass(frozen=True)
class SquadCandidateFactsEntity:
    """빈 자리 후보 1명의 원자료 (`paik` 27번). 포지션·자기 팀/이미 앉은 사람
    제외·시간 하드 필터는 저장소가 이미 걸었다 — 여기 있다는 것 자체가
    "이 셋을 통과했다"는 뜻이다. 등급 산출(`analysis`·`review` 원시 교차
    읽기)도 저장소가 한다 — 순수 함수(`candidate_grade_rules.py`)로는 DB를
    못 읽는다.
    """

    user_id: UUID
    nickname: str
    card_public_slug: str | None
    grade: str | None
    provisional: bool | None
    last_active_at: datetime | None
    # 추천 판 카드의 불릿 한두 줄(`paik` 33번). 등급과 **같은 리포트**에서
    # 왔다 — 화면이 「왜 이 사람인가」를 쓸 문장이다. `card` 없는 봉투로
    # 적재됐거나 분석 전이면 `None`.
    notes: list[str] | None = None


@dataclass(frozen=True)
class SquadRecruitmentFactsEntity:
    """추천 조립에 필요한 원자료 한 벌. `seated_grades`는 팀 평균을 내는
    분모다(등급 있는 사람만 — `ho` 21번과 같은 판단, 모르는 사람은 셈에서 뺀다)."""

    seated_grades: list[str]
    candidates: list[SquadCandidateFactsEntity]

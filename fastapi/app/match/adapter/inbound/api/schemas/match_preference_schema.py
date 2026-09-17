"""경기 조건·후보 HTTP 모델. 계약 문서. `paik` 18·20·21번."""

from __future__ import annotations

from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SlotSchema(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class SetTeamPreferenceSchema(BaseModel):
    """통째로 교체한다(PUT) — 보낸 목록이 곧 새 조건 전체다."""

    region_ids: list[UUID] = Field(default_factory=list)
    slots: list[SlotSchema] = Field(default_factory=list)


class TeamPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    region_ids: list[UUID]
    slots: list[SlotSchema]


class SetMemberPreferenceSchema(BaseModel):
    region_ids: list[UUID] = Field(default_factory=list)
    slots: list[SlotSchema] = Field(default_factory=list)
    position_ids: list[UUID] = Field(default_factory=list)


class MemberPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    region_ids: list[UUID]
    slots: list[SlotSchema]
    position_ids: list[UUID]


class MemberPreferenceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nickname: str
    region_ids: list[UUID]
    slots: list[SlotSchema]
    position_ids: list[UUID]


class MatchReasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    detail: str


class MatchCandidateResponse(BaseModel):
    """`paik` 20번 — "맞는 상대" 한 팀. 🔴 유사도 점수는 없다, 순서는 이미
    정렬돼 있고 `reasons`가 사실값 근거다.
    """

    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    team_name: str
    region_label: str
    formation: str
    reasons: list[MatchReasonResponse]


class SquadCandidateResponse(BaseModel):
    """`paik` 27번 — 빈 자리 추천 후보 한 명. `GET /teams/{id}/squad/candidates`.

    🔴 유사도·거리 점수는 없다 — 순서는 이미 정렬돼 있다. `grade`가 `null`이면
    아직 분석 전이다(0 이나 F 가 아니다). `provisional` 이 `true`인 동안은
    화면이 등급 옆에 "검수 전"을 달아야 한다(26번과 같은 원칙).
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nickname: str
    card_public_slug: str | None
    grade: str | None
    provisional: bool | None
    # 카드에 그릴 불릿 **한두 줄**(`paik` 33번). 🔴 **화면이 짓지 않는다** —
    # 분석이 낸 문장이다. `null`(옛 봉투로 적재·분석 전)이면 그 줄을 안
    # 그리면 되고, **한 줄뿐인 것도 정상이다**(두 줄을 채우려고 지어내지
    # 않는 것이 봉투 쪽 규칙이다).
    notes: list[str] | None = None

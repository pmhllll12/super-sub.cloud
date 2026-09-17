"""용병 매칭 프로필·검색 HTTP 모델."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PositionRefSchema(BaseModel):
    sport_code: str = Field(max_length=20)
    code: str = Field(max_length=20)


class AvailableSlotSchema(BaseModel):
    day: str = Field(max_length=3)  # "MON".."SUN"
    start: str = Field(max_length=5)  # "HH:MM"
    end: str = Field(max_length=5)


class UpdateMercenaryProfileSchema(BaseModel):
    """전부 선택 필드 — 보낸 것만 바뀐다(PATCH). `null`은 "안 건드림"이다.

    `location`·`skill_summary`를 지우고 싶으면 빈 문자열 `""`을 보낸다.
    """

    preferred_positions: list[PositionRefSchema] | None = None
    available_slots: list[AvailableSlotSchema] | None = None
    location: str | None = None
    skill_summary: str | None = Field(default=None, max_length=2000)
    is_searchable: bool | None = None


class MercenaryProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    preferred_positions: list[PositionRefSchema]
    available_slots: list[AvailableSlotSchema]
    location: str | None
    skill_summary: str | None
    is_searchable: bool


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nickname: str
    location: str | None
    skill_summary: str | None
    similarity: float


class SearchCandidatesSchema(BaseModel):
    sport_code: str = Field(max_length=20)
    position_code: str = Field(max_length=20)
    query_text: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)

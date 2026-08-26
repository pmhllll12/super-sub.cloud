"""내 정보 HTTP 모델. 계약 문서 2장."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.user.domain.value_objects.nickname_vo import MAX_NICKNAME_LENGTH

from app.core.shared import Rfc3339


class TeamMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: Rfc3339


class UpdateMeSchema(BaseModel):
    """지금은 닉네임만 바꾼다.

    이메일은 계정 식별자라 여기서 받지 않는다 — 바꾸려면 재인증과 중복 검사가
    붙으므로 별도 엔드포인트다.
    """

    nickname: str = Field(min_length=1, max_length=MAX_NICKNAME_LENGTH)


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339
    teams: list[TeamMembershipResponse]

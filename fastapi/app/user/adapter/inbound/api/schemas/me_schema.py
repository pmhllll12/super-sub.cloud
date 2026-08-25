"""내 정보 HTTP 모델. 계약 문서 2장."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.shared import Rfc3339


class TeamMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: Rfc3339


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339
    teams: list[TeamMembershipResponse]

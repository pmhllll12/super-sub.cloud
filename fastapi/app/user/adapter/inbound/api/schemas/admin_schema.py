"""회원 관리(admin) HTTP 모델."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.shared import Rfc3339


class AdminUserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    size: int


class AdminMembershipResponse(BaseModel):
    """`TeamMembershipResponse`(me_schema.py)와 달리 `left_at` 을 포함한다.

    관리자 화면은 나간 팀도 보여준다.
    """

    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: Rfc3339
    left_at: Rfc3339 | None


class AdminUserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339
    teams: list[AdminMembershipResponse]
    has_card: bool

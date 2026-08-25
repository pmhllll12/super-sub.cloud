"""사용자 컨텍스트의 HTTP 모델. 계약 문서 2장.

**도메인 모델과 별개다.** 이쪽은 바깥과의 약속이라 함부로 못 바꾸고,
도메인은 안쪽 사정이라 자유롭게 바꾼다.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.shared import Rfc3339
from app.user.domain.value_objects import MAX_NICKNAME_LENGTH, MIN_PASSWORD_LENGTH


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
    nickname: str = Field(min_length=1, max_length=MAX_NICKNAME_LENGTH)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339


class TeamMembershipResponse(BaseModel):
    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: Rfc3339


class MeResponse(UserResponse):
    # 지금 소속된 팀만. 거르는 규칙은 domain/rules.py 에 있다.
    teams: list[TeamMembershipResponse]

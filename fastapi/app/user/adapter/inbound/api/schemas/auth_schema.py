"""가입·로그인 HTTP 모델. 계약 문서 2장.

응답 모델은 `from_attributes` 라 **유스케이스가 돌려준 DTO 를 그대로 받아 변환한다.**
그래서 라우터에 변환 코드가 없고, 도메인 엔티티도 임포트하지 않는다.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.shared import Rfc3339
from app.user.domain.value_objects.nickname_vo import MAX_NICKNAME_LENGTH
from app.user.domain.value_objects.password_vo import MIN_PASSWORD_LENGTH


class SignupSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
    nickname: str = Field(min_length=1, max_length=MAX_NICKNAME_LENGTH)


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class SignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str
    expires_in: int

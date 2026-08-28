"""내 정보 HTTP 모델. 계약 문서 2장."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.user.domain.value_objects.nickname_vo import MAX_NICKNAME_LENGTH
from app.user.domain.value_objects.password_vo import MIN_PASSWORD_LENGTH

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


class ChangePasswordSchema(BaseModel):
    """비밀번호 변경.

    **현재 비밀번호를 함께 받는다.** 토큰만으로 바꾸게 하면, 토큰을 훔친 쪽이
    비밀번호를 갈아 주인을 밀어낼 수 있다.

    새 비밀번호의 길이 하한은 가입과 같은 값을 쓴다 — 두 곳이 갈리면 어느 쪽이
    정책인지 알 수 없게 된다.
    """

    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class DeleteMeSchema(BaseModel):
    """탈퇴.

    비밀번호 로그인 계정은 **현재 비밀번호를 요구한다**(변경과 같은 이유).
    구글로만 가입한 계정은 비밀번호가 없으므로 생략할 수 있다.
    """

    password: str | None = None


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339
    teams: list[TeamMembershipResponse]

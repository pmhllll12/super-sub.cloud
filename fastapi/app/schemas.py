"""요청·응답 모델.

필드는 부록 D ERD의 실제 컬럼에서 왔다. 근거는 `docs/api-contract.md`.
여기 없는 필드는 스키마에도 없다 — 임의로 늘리지 않는다.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, PlainSerializer


def _rfc3339(dt: datetime) -> str:
    """`2026-08-25T10:30:00Z` 형태로 낸다.

    기본 직렬화는 `+00:00`으로 끝난다. 둘 다 RFC 3339로 유효하지만 계약 문서에
    `Z`로 적어 두었으므로 문서와 응답을 맞춘다.
    """
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


Rfc3339 = Annotated[datetime, PlainSerializer(_rfc3339, return_type=str)]


# --- 인증 -------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    # 8자 이상만 본다. 대문자·특수문자를 강제하지 않는 이유는 계약 문서 2장 참고.
    password: str = Field(min_length=8)
    nickname: str = Field(min_length=1, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# --- 사용자 -----------------------------------------------------------------

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    nickname: str
    created_at: Rfc3339


class TeamMembership(BaseModel):
    team_id: UUID
    name: str
    region: str
    sport_code: str
    role: str
    joined_at: Rfc3339


class MeResponse(UserResponse):
    # team_member 에서 left_at 이 널인 행만 담는다. 탈퇴 이력은 소프트 삭제로
    # 남아 있어서 거르지 않으면 나간 팀이 같이 나온다(부록 D 도메인 ①).
    teams: list[TeamMembership]


# --- 선수 카드 ---------------------------------------------------------------

class TitleResponse(BaseModel):
    code: str
    label: str
    category: str
    granted_at: Rfc3339


class CardOwner(BaseModel):
    id: UUID
    nickname: str


class CardResponse(BaseModel):
    """내 카드.

    능력치 수치 필드는 두지 않는다. player_card 에 그런 컬럼이 애초에 없고,
    수치를 카드에 노출하지 않는 것이 3.5 의 설계 원칙이다(부록 D.5).
    """

    id: UUID
    public_slug: str
    og_image_key: str
    user: CardOwner
    # 받은 호칭만 담는다. "못 받았다"를 값으로 표현하지 않는다 — 미달 표식이 된다.
    titles: list[TitleResponse]


class PublicCardResponse(BaseModel):
    """공유 링크로 보는 카드. 내부 id 를 뺀다."""

    public_slug: str
    og_image_key: str
    user: CardOwner
    titles: list[TitleResponse]

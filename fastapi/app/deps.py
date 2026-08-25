"""의존성 주입 지점.

**저장소 구현을 고르는 곳은 여기 한 곳뿐이다.** DB가 붙으면 아래 두 함수에서
`Stub*Repository`를 `Pg*Repository`로 바꾸면 되고, 서비스·라우터는 고치지 않는다.

인증은 컨텍스트에 걸치는 관심사라 여기 둔다.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.cards.service import CardService
from app.cards.stub_repository import StubCardRepository
from app.errors import ApiError
from app.identity.service import IdentityService
from app.identity.stub_repository import (
    DEMO_USER_ID,
    STUB_ACCESS_TOKEN,
    StubIdentityRepository,
)


def get_identity_service() -> IdentityService:
    return IdentityService(StubIdentityRepository())


def get_card_service() -> CardService:
    return CardService(StubCardRepository())


def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    """`Authorization: Bearer <token>` 을 검사하고 사용자를 돌려준다.

    401 을 두 가지로 나눈다. 클라이언트 동작이 다르기 때문이다 —
    헤더가 없으면 로그인 화면으로, 토큰이 무효면 토큰을 버리고 재로그인으로 보낸다.

    스텁 단계라 고정 토큰과 문자열 비교만 한다. DB 가 붙으면 여기서 JWT 를
    검증하고 그 안의 사용자 id 를 돌려주게 된다 — **반환 타입은 그대로다.**
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    if token != STUB_ACCESS_TOKEN:
        raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")
    return DEMO_USER_ID


CurrentUserId = Annotated[UUID, Depends(current_user_id)]

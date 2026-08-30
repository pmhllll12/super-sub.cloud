"""컨텍스트에 걸치는 의존성.

여기 있는 것은 **인증뿐이다.** 저장소 주입은 각 컨텍스트의 `dependencies.py` 에 있다.

`app.core.security` 만 임포트하므로 `card` 가 `user` 를 임포트하지 않아도 로그인 여부를
확인할 수 있다 — 컨텍스트끼리 직접 얽히지 않게 하는 것이 요점이다.

🔴 **토큰 폐기(SEC-004) 대조가 여기서 일어난다.** 서명이 맞아도 토큰에 실린 버전이
DB 의 현재 버전과 다르면 거부한다. 그래서 이 모듈은 `user` 테이블의 컬럼 하나를 읽는데,
**컨텍스트를 임포트하지 않고 `table()`/`column()` 으로 읽는다** — `card` 저장소가
닉네임을 읽는 방식과 같다. 임포트하면 공용 모듈이 특정 컨텍스트를 아는 셈이 되고,
`tests/test_architecture.py` 가 그것을 막는다.
"""

from __future__ import annotations

from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.errors import ApiError
from app.core.security import verify_access_token


class TokenVersionReader(Protocol):
    """사용자의 현재 토큰 버전을 읽는다. 사용자가 없으면 `None`."""

    def __call__(self, user_id: UUID) -> int | None: ...


def get_token_version_reader(
    session: Annotated[Session, Depends(get_session)],
) -> TokenVersionReader:
    """DB 를 읽는 기본 구현.

    DB 없이 도는 계약 테스트는 `dependency_overrides` 로 이것을 갈아끼운다.
    """
    # 🔴 컬럼 이름이 바뀌면 파이썬이 잡아 주지 않는다. DB 통합 테스트가 방어선이다
    #    (`tests/user/adapter/test_token_revocation_db.py`).
    user_table = table("user", column("id"), column("token_version"))

    def read(user_id: UUID) -> int | None:
        stmt = select(user_table.c.token_version).where(user_table.c.id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    return read


def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    read_token_version: TokenVersionReader = Depends(get_token_version_reader),
) -> UUID:
    token = verify_access_token(authorization)

    current = read_token_version(token.user_id)
    if current is None or current != token.version:
        # 사용자가 없거나(탈퇴) 버전이 올라갔다(폐기). 클라이언트가 할 일은 어느
        # 쪽이든 **토큰을 버리고 다시 로그인** 하나뿐이라 구분하지 않는다.
        raise ApiError(401, "INVALID_TOKEN", "토큰이 유효하지 않습니다.")

    return token.user_id


CurrentUserId = Annotated[UUID, Depends(current_user_id)]

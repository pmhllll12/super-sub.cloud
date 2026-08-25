"""컨텍스트에 걸치는 의존성.

여기 있는 것은 **인증뿐이다.** 저장소 주입은 각 컨텍스트의 `dependencies.py` 에 있다.

`app.security` 만 임포트하므로 `card` 가 `user` 를 임포트하지 않아도 로그인 여부를
확인할 수 있다 — 컨텍스트끼리 직접 얽히지 않게 하는 것이 요점이다.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.security import verify_access_token


def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    return verify_access_token(authorization)


CurrentUserId = Annotated[UUID, Depends(current_user_id)]

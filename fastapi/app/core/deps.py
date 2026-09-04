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

from hmac import compare_digest
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from app.core.config import settings
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


class UserEmailReader(Protocol):
    """사용자의 이메일을 읽는다. 사용자가 없으면 `None`."""

    def __call__(self, user_id: UUID) -> str | None: ...


def get_user_email_reader(
    session: Annotated[Session, Depends(get_session)],
) -> UserEmailReader:
    """`current_user_id` 위에서 관리자 여부를 가리는 데만 쓴다.

    `table()`/`column()` 로 읽는 이유는 위 `get_token_version_reader` 와 같다 —
    `app/core` 는 `user` 컨텍스트를 임포트하면 안 된다.
    """
    user_table = table("user", column("id"), column("email"))

    def read(user_id: UUID) -> str | None:
        stmt = select(user_table.c.email).where(user_table.c.id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    return read


def require_admin(
    user_id: CurrentUserId,
    read_email: UserEmailReader = Depends(get_user_email_reader),
) -> UUID:
    """회원 관리 admin 화면 전용 게이트.

    🔴 `settings.admin_emails` 가 비어 있으면 **아무도** 통과하지 못한다 — 조용한
    기본값을 두면 배포 환경에 값을 안 넣었을 때 누구나 admin 을 들어오게 된다.
    """
    email = read_email(user_id)
    if email is None or email.strip().lower() not in settings.admin_email_set:
        raise ApiError(403, "FORBIDDEN", "관리자만 접근할 수 있습니다.")
    return user_id


CurrentAdminUserId = Annotated[UUID, Depends(require_admin)]


def require_worker(
    x_worker_token: Annotated[str | None, Header()] = None,
) -> None:
    """분석 워커 전용 게이트. **사람 토큰이 아니다.**

    워커는 GPU 인스턴스에서 도는 기계라 사용자 계정에 묶지 않는다 — 묶으면 그
    계정이 탈퇴하거나 토큰이 폐기될 때 파이프라인이 조용히 멈춘다.

    🔴 `settings.worker_token` 이 비어 있으면 **아무도** 통과하지 못한다.
    `require_admin` 과 같은 이유다 — 조용한 기본값을 두면 값을 안 넣은 배포에서
    누구나 큐를 집어 갈 수 있다.

    🔴 `compare_digest` 로 비교한다. `==` 는 앞에서부터 다른 자리를 만나면 바로
    끝나서, 걸린 시간이 "몇 글자가 맞았는지"를 알려 준다.
    """
    expected = settings.worker_token
    if not expected or not x_worker_token:
        raise ApiError(401, "INVALID_TOKEN", "워커 자격이 필요합니다.")
    if not compare_digest(x_worker_token, expected):
        raise ApiError(401, "INVALID_TOKEN", "워커 자격이 유효하지 않습니다.")


WorkerAuth = Depends(require_worker)

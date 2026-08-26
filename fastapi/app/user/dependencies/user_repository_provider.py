"""저장소 프로바이더.

**이 컨텍스트에서 구현을 고르는 유일한 곳이다.** 인터랙터·라우터는 어느 구현이
들어오는지 모른다.

스텁은 지웠다 — 파일은 남겨 두었고(`adapter/outbound/stub/`) 테스트에서
`dependency_overrides` 로 끼운다. DB 없이도 계약 테스트가 돌아야 하기 때문이다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.user.adapter.outbound.pg.user_pg_repository import UserPgRepository
from app.user.application.ports.output.user_port import UserPort


def get_user_repository(
    session: Annotated[Session, Depends(get_session)],
) -> UserPort:
    return UserPgRepository(session)


UserRepositoryDep = Annotated[UserPort, Depends(get_user_repository)]
